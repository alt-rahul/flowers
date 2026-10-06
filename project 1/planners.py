"""The bots' planners: one function per way of choosing a path.

Every planner has the same shape:

    planner(ship, pos, button, burning, q, **options) -> path, or None

It gets the ship, the bot's position, the button, the cells burning right
now (a flat boolean array) and the flammability q, and returns a list of
cells from `pos` to `button`, or None if no route avoids the fire. A Bot
(bots.py) just calls its planner and walks along the result, so the four
bots differ only in which planner they use and whether they replan:

    Bot 1  avoid_fire, planned once at the start (only the first fire cell
           is burning then) and never again
    Bot 2  avoid_fire, replanned every step
    Bot 3  avoid_fire_and_neighbors, replanned every step; when no path
           avoids the fire's neighbours it falls back to avoid_fire
    Bot 4  avoid_predicted_fire, replanned every step (A*, see below)

forecast_astar at the bottom is the earlier, more complex Bot 4, kept so
the two designs can be compared.
"""
import math
from functools import lru_cache

import numpy as np

from forecast import FORECASTS
from planning import (astar_path, bfs_distances, bfs_path, fire_distances, fireproof_path,
                      manhattan_distances, risk_astar, with_neighbors)
from ship import count_neighbors, grid_neighbors


# ---------------------------------------------------------------- Bots 1-3 --

def avoid_fire(ship, pos, button, burning, q):
    """Shortest path to the button that never enters a burning cell (BFS).
    Bot 2 calls this every step; Bot 1 calls it once, at the start."""
    return bfs_path(ship.neighbors, pos, button, burning.tolist())


def avoid_fire_and_neighbors(ship, pos, button, burning, q):
    """Shortest path that avoids the fire AND every cell next to it. If no
    such path exists, fall back to Bot 2's planner (avoid_fire)."""
    buffer = with_neighbors(burning, ship.D)          # fire + adjacent cells
    path = bfs_path(ship.neighbors, pos, button, buffer.tolist())
    if path is None:
        path = avoid_fire(ship, pos, button, burning, q)
    return path


# ------------------------------------------------------------------ Bot 4 --
#
# THE IDEA
#   Treat the fire as a race. The bot moves one cell per step. The fire's
#   front moves one cell per step with probability q (that is exactly how it
#   spreads along a corridor), so in k steps it advances Binomial(k, q) cells.
#   For every cell we compare:
#       k = how many steps the bot needs to get there (BFS from the bot)
#       d = how many cells the fire must travel to get there (BFS from the fire)
#   If P(the fire advances at least d cells in k steps) > threshold, we
#   assume the cell WILL be on fire by the time we arrive: "predicted fire".
#
#   Along one route this is exact: each cell on the route waits for its own
#   q-coin from the cell before it. The real fire can also arrive by other
#   routes (loops, other burning cells), which only makes it faster, so the
#   true probability is never lower than this one: the race model is a
#   slightly optimistic lower bound (forecast_check.py measures how much).
#
# THE SEARCH
#   A* from the bot to the button, where entering a cell costs
#       1                  for an ordinary cell
#       1 + penalty        for a predicted-fire cell
#       infinity           for a cell that is burning right now (never enter)
#   and the heuristic is the Manhattan distance to the button. So the bot
#   takes a detour around predicted fire when the detour is shorter than the
#   penalty, and goes through it only when every alternative is worse.
#
# WHY THIS IS NOT JUST "BOT 3 WITH A WIDER BUFFER"
#   The avoided region isn't a fixed band around the fire. A cell right next
#   to the fire that the bot can reach first is NOT avoided, and a cell far
#   from the fire that the bot would only reach much later CAN be. It also
#   depends on q: a slow fire predicts little, a fast fire a lot.


@lru_cache(maxsize=None)
def danger_radius(q, threshold, max_steps):
    """radius[k] = the largest fire distance d for which
           P(the fire advances at least d cells in k steps) > threshold,
    when the fire's advance in k steps is Binomial(k, q).

    So a cell the bot reaches in k steps, and the fire must travel d cells
    to reach, is predicted fire exactly when d <= radius[k].

    Computed once per (q, threshold, size) and cached, by building the
    binomial distribution one step at a time:
        pmf[j] = P(exactly j advances so far)
    Each extra step, an outcome either stays where it was (probability 1 - q)
    or moves up by one advance (probability q).
    """
    radius = []
    pmf = np.zeros(max_steps + 1)
    pmf[0] = 1.0                                      # after 0 steps, 0 advances
    for k in range(max_steps + 1):
        if k > 0:
            pmf[1:] = pmf[1:] * (1 - q) + pmf[:-1] * q
            pmf[0] = pmf[0] * (1 - q)
        at_least = np.cumsum(pmf[::-1])[::-1]         # at_least[d] = P(at least d advances)
        radius.append(int(np.flatnonzero(at_least > threshold)[-1]))
    return tuple(radius)


def fire_arrival_probability(k, d, q):
    """P(the fire advances at least d cells in k steps) = P(Binomial(k, q) >= d),
    written out directly. Not used by the bot (danger_radius is faster); the
    tests use it to check danger_radius."""
    return sum(math.comb(k, j) * q ** j * (1 - q) ** (k - j) for j in range(d, k + 1))


def predicted_fire(ship, pos, button, burning, q, threshold=0.6, lookahead=True,
                   fire_metric="maze"):
    """List with True for every cell Bot 4 treats as "will be on fire".

    lookahead=True (the default) uses the race described above.
    lookahead=False is the literal one-step version, for comparison: a cell
    is predicted fire if it catches fire NEXT step with probability above the
    threshold, i.e. 1 - (1 - q)^K > threshold, with K its burning neighbours.

    fire_metric="maze" measures how far the fire must travel through open
    cells (BFS). fire_metric="manhattan" ignores walls, for comparison.
    """
    D = ship.D
    n_cells = D * D
    is_burning = burning.tolist()
    danger = [False] * n_cells

    if not lookahead:
        k = count_neighbors(burning.reshape(D, D)).ravel().tolist()
        for c in ship.open_cells.tolist():
            if not is_burning[c] and 1 - (1 - q) ** k[c] > threshold:
                danger[c] = True
        return danger

    fire_cells = np.flatnonzero(burning).tolist()
    if fire_metric == "maze":
        fire_dist = fire_distances(ship.neighbors, fire_cells, n_cells)
    else:
        # BFS over the full grid, walls ignored, gives the Manhattan
        # distance to the nearest burning cell.
        fire_dist = fire_distances(grid_neighbors(D), fire_cells, n_cells)
    bot_dist = bfs_distances(ship.neighbors, pos, is_burning)
    radius = danger_radius(q, threshold, n_cells)
    for c in ship.open_cells.tolist():
        if is_burning[c] or bot_dist[c] == math.inf:
            continue
        # How many fire updates happen before the bot stands on c: one per
        # move, except that the button is pressed before the fire moves.
        steps = bot_dist[c] - 1 if c == button else bot_dist[c]
        if fire_dist[c] <= radius[steps]:
            danger[c] = True
    return danger


def avoid_predicted_fire(ship, pos, button, burning, q, threshold=0.6, penalty=20.0,
                         lookahead=True, fire_metric="maze"):
    """Bot 4's planner: A* with burning cells impassable and predicted-fire
    cells costing 1 + penalty, guided by the Manhattan distance to the button."""
    danger = predicted_fire(ship, pos, button, burning, q, threshold, lookahead, fire_metric)
    is_burning = burning.tolist()
    step_cost = []
    for c in range(ship.D * ship.D):
        if is_burning[c]:
            step_cost.append(math.inf)
        elif danger[c]:
            step_cost.append(1.0 + penalty)
        else:
            step_cost.append(1.0)
    heuristic = manhattan_distances(ship.D, button)
    return astar_path(ship.neighbors, pos, button, step_cost, heuristic)


# ------------------------------------------- the earlier Bot 4, for comparison --

def forecast_astar(ship, pos, button, burning, q, risk_weight=1000.0, forecast="dmp",
                   certain_first=True):
    """The first Bot 4 design (see the README's development log).

    If some path stays ahead of even the fastest possible fire, take it (a
    certain win). Otherwise forecast P(each cell is burning t steps from now)
    with message passing and search over (cell, time) for the path that
    minimises length + risk_weight * sum of -ln(1 - P(burning when we get there)).
    """
    if certain_first:
        fire_dist = fire_distances(ship.neighbors, np.flatnonzero(burning).tolist(), len(burning))
        sure = fireproof_path(ship.neighbors, pos, button, fire_dist)
        if sure is not None:
            return sure
    heuristic = ship.distances_from(button)
    prediction = FORECASTS[forecast](ship, q, burning)
    return risk_astar(ship.neighbors, pos, button, heuristic, prediction.risk_at, risk_weight)
