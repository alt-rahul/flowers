"""The bots' planners: one function per way of choosing a path.

Every planner has the same shape:

    planner(ship, pos, button, q, **options) -> path, or None

It looks at the ship's tiles (including which ones are on fire right now), the
bot's position and the button, and returns a list of positions from `pos` to
`button`, or None if no route avoids the fire. A Bot (bots.py) just calls its
planner and walks along the result, so the four bots differ only in which
planner they use and whether they replan:

    Bot 1  avoid_fire, planned once at the start (only the first fire tile is
           burning then) and never again
    Bot 2  avoid_fire, replanned every step
    Bot 3  avoid_fire_and_neighbors, replanned every step; when no path
           avoids the fire's neighbours it falls back to avoid_fire
    Bot 4  avoid_predicted_fire, replanned every step (A*, see below)
"""
import math

from planning import astar_path, bfs_distances, bfs_path, fire_distances, with_neighbors


# ---------------------------------------------------------------- Bots 1-3 --

def avoid_fire(ship, pos, button, q):
    """Shortest path to the button that never enters a burning tile (BFS).
    Bot 2 calls this every step; Bot 1 calls it once, at the start."""
    return bfs_path(ship, pos, button, ship.fire_cells())


def avoid_fire_and_neighbors(ship, pos, button, q):
    """Shortest path that avoids the fire AND every tile next to it. If no
    such path exists, fall back to Bot 2's planner (avoid_fire)."""
    buffer = with_neighbors(ship, ship.fire_cells())
    path = bfs_path(ship, pos, button, buffer)
    if path is None:
        path = avoid_fire(ship, pos, button, q)
    return path


# ------------------------------------------------------------------ Bot 4 --
#
# THE IDEA
#   Treat the fire as a race. The bot moves one tile per step. The fire's
#   front moves one tile per step with probability q (that is exactly how it
#   spreads along a corridor), so in k steps it advances Binomial(k, q) tiles.
#   For every tile we compare
#       k = how many steps the bot needs to get there (BFS from the bot)
#       d = how many tiles the fire must travel to get there (BFS from the fire)
#   If P(the fire advances at least d tiles in k steps) > threshold, we
#   assume the tile WILL be on fire by the time we arrive: "predicted fire".
#
#   Along one route this is exact: each tile on the route waits for its own
#   q-coin from the tile before it. The real fire can also arrive by other
#   routes (loops, other burning tiles), which only makes it faster, so the
#   true probability is never lower than this one: the race model is a
#   slightly optimistic lower bound (tests/test_planning.py checks this
#   against simulated fires).
#
# THE SEARCH
#   A* from the bot to the button, where entering a tile costs
#       1                  for an ordinary tile
#       1 + penalty        for a predicted-fire tile
#       infinity           for a tile that is burning right now (never enter)
#   and the heuristic is the Manhattan distance to the button. So the bot
#   takes a detour around predicted fire when the detour is shorter than the
#   penalty, and goes through it only when every alternative is worse.
#
# WHY THIS IS NOT JUST "BOT 3 WITH A WIDER BUFFER"
#   The avoided region isn't a fixed band around the fire. A tile right next
#   to the fire that the bot can reach first is NOT avoided, and a tile far
#   from the fire that the bot would only reach much later CAN be. It also
#   depends on q: a slow fire predicts little, a fast fire a lot.

# Tables built by danger_radius(), remembered so each one is only built once:
# (q, threshold, max_steps) -> the table.
radius_tables = {}


def danger_radius(q, threshold, max_steps):
    """radius[k] = the largest fire distance d for which
           P(the fire advances at least d tiles in k steps) > threshold,
    when the fire's advance in k steps is Binomial(k, q); k = 0 .. max_steps.

    So a tile the bot reaches in k steps, and the fire must travel d tiles to
    reach, is predicted fire exactly when d <= radius[k].

    The table only depends on (q, threshold, max_steps), so it is built once
    and kept in `radius_tables`.
    """
    key = (q, threshold, max_steps)
    if key in radius_tables:
        return radius_tables[key]

    # pmf[j] = P(exactly j advances so far). After k steps there are at most k
    # advances, so only pmf[0..k] can be non-zero.
    pmf = [0.0] * (max_steps + 1)
    pmf[0] = 1.0
    radius = []
    for k in range(max_steps + 1):
        if k > 0:
            # One more step: each outcome either stays where it was (chance
            # 1 - q) or moves up by one advance (chance q). Going from the top
            # down means pmf[j - 1] still holds last step's value when we use it.
            for j in range(k, 0, -1):
                pmf[j] = pmf[j] * (1 - q) + pmf[j - 1] * q
            pmf[0] = pmf[0] * (1 - q)
        # P(at least d advances) = pmf[d] + pmf[d + 1] + ... + pmf[k].
        # Adding up from the top down gives every d in one pass; it only gets
        # bigger as d gets smaller, so the largest d that passes is the last
        # one before the threshold is reached.
        at_least = [0.0] * (k + 1)
        total = 0.0
        for d in range(k, -1, -1):
            total += pmf[d]
            at_least[d] = total
        largest = -1
        d = 0
        while d <= k and at_least[d] > threshold:
            largest = d
            d += 1
        radius.append(largest)

    radius_tables[key] = radius
    return radius


def fire_arrival_probability(k, d, q):
    """P(the fire advances at least d tiles in k steps) = P(Binomial(k, q) >= d),
    written out directly. Not used by the bot (danger_radius is faster); the
    tests use it to check danger_radius."""
    return sum(math.comb(k, j) * q ** j * (1 - q) ** (k - j) for j in range(d, k + 1))


def predicted_fire(ship, pos, button, q, threshold=0.6, lookahead=True, fire_metric="maze"):
    """The set of positions Bot 4 treats as "will be on fire".

    lookahead=True (the default) uses the race described above.
    lookahead=False is the literal one-step version, for comparison: a tile is
    predicted fire if it catches fire NEXT step with probability above the
    threshold, i.e. 1 - (1 - q)^K > threshold, with K its burning neighbours.

    fire_metric="maze" measures how far the fire must travel through open
    tiles (BFS). fire_metric="manhattan" ignores walls, for comparison.
    """
    danger = set()

    if not lookahead:
        for r, c in ship.open_cells():
            tile = ship.grid[r][c]
            if tile.on_fire:
                continue
            k = sum(1 for nr, nc in tile.neighbors if ship.grid[nr][nc].on_fire)
            if 1 - (1 - q) ** k > threshold:
                danger.add((r, c))
        return danger

    fire = ship.fire_cells()
    fire_dist = fire_distances(ship, fire, ignore_walls=(fire_metric != "maze"))
    bot_dist = bfs_distances(ship, pos, restricted=fire)
    radius = danger_radius(q, threshold, ship.D * ship.D)
    for r, c in ship.open_cells():
        if ship.grid[r][c].on_fire or bot_dist[r][c] == math.inf:
            continue
        # How many fire updates happen before the bot stands on this tile: one
        # per move, except that the button is pressed before the fire moves.
        steps = bot_dist[r][c] - 1 if (r, c) == button else bot_dist[r][c]
        if fire_dist[r][c] <= radius[steps]:
            danger.add((r, c))
    return danger


def avoid_predicted_fire(ship, pos, button, q, threshold=0.6, penalty=20.0, lookahead=True,
                         fire_metric="maze"):
    """Bot 4's planner: A* with burning tiles impassable and predicted-fire
    tiles costing 1 + penalty, guided by the Manhattan distance to the button."""
    danger = predicted_fire(ship, pos, button, q, threshold, lookahead, fire_metric)
    cost = [[1.0] * ship.D for r in range(ship.D)]
    for r in range(ship.D):
        for c in range(ship.D):
            if ship.grid[r][c].on_fire:
                cost[r][c] = math.inf
            elif (r, c) in danger:
                cost[r][c] = 1.0 + penalty
    return astar_path(ship, pos, button, cost)
