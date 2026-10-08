"""The four bots. Each function returns the path the bot wants to take (a list
of positions from where it stands to the button), or None if every route to
the button runs through fire."""
import math

from search import a_star, bfs, distance_map
from ship import check_neighbors

# Bot 4's settings
THRESHOLD = 0.6   # a tile counts as "predicted fire" above this chance
PENALTY = 20      # extra cost for stepping onto a predicted-fire tile


def bot1_path(ship, pos, button):
    """Bot 1: the shortest path avoiding the fire. Bot 1 only calls this once,
    at the start, when only the first fire tile is burning."""
    return bfs(ship, pos, button, ship.fire_cells())


def bot2_path(ship, pos, button):
    """Bot 2: the shortest path avoiding the tiles that are burning now.
    Bot 2 calls this every step."""
    return bfs(ship, pos, button, ship.fire_cells())


def bot3_path(ship, pos, button):
    """Bot 3: the shortest path avoiding the fire and every tile next to it.
    If there isn't one, it does what Bot 2 does."""
    fire = ship.fire_cells()
    avoid = set(fire)
    for r, c in fire:
        for n in check_neighbors(ship.D, r, c):
            avoid.add(n)
    path = bfs(ship, pos, button, avoid)
    if path is None:
        path = bfs(ship, pos, button, fire)
    return path


# ---------------------------------------------------------------- Bot 4 ----
#
# Every tile is a race between the bot and the fire:
#     k = how many moves the bot needs to get there3
#     d = how many tiles the fire has to travel to get there
# Along one route the fire's front moves forward one tile per step with
# probability q, so in k steps it moves forward Binomial(k, q) tiles. If
# P(Binomial(k, q) >= d) > THRESHOLD, the fire will probably get there first,
# and the tile counts as "predicted fire".
#
# Then A* to the button, where stepping onto a tile costs:
#     infinity        if it is burning now
#     1 + PENALTY     if it is predicted fire
#     1               otherwise

radius_tables = {}   # saved tables, so each one is only worked out once


def danger_radius(q, threshold, max_steps):
    """radius[k] = the largest fire distance d with P(Binomial(k, q) >= d) > threshold,
    for k = 0 to max_steps. A tile the bot reaches in k moves is predicted fire
    when the fire's distance to it is at most radius[k]."""
    if (q, threshold, max_steps) in radius_tables:
        return radius_tables[(q, threshold, max_steps)]

    pmf = [0.0] * (max_steps + 1)   # pmf[j] = P(the fire has moved forward exactly j tiles)
    pmf[0] = 1.0
    radius = []
    for k in range(max_steps + 1):
        if k > 0:
            # One more step: the fire either stays (chance 1 - q) or moves forward one tile (chance q).
            for j in range(k, 0, -1):
                pmf[j] = pmf[j] * (1 - q) + pmf[j - 1] * q
            pmf[0] = pmf[0] * (1 - q)

        # Add up P(at least d) from the top; the first d above the threshold is the largest one.
        total = 0.0
        largest = -1
        for d in range(k, -1, -1):
            total += pmf[d]
            if total > threshold:
                largest = d
                break
        radius.append(largest)

    radius_tables[(q, threshold, max_steps)] = radius
    return radius


def predicted_fire(ship, pos, button, q, threshold):
    """The set of tiles Bot 4 thinks the fire will reach before the bot does."""
    fire = ship.fire_cells()
    fire_dist = distance_map(ship, fire, set())   # d for every tile
    bot_dist = distance_map(ship, [pos], fire)    # k for every tile
    radius = danger_radius(q, threshold, ship.D * ship.D)

    danger = set()
    for r, c in ship.open_cells():
        if ship.grid[r][c].on_fire or bot_dist[r][c] == math.inf:
            continue
        k = bot_dist[r][c]
        if (r, c) == button:
            k = k - 1   # the button is pressed before the fire moves
        if fire_dist[r][c] <= radius[k]:
            danger.add((r, c))
    return danger


def one_step_predicted_fire(ship, q, threshold):
    """The literal "more than 60% chance of catching fire" rule, only used to
    test it in tuning: a tile counts if it catches fire NEXT step with a chance
    above the threshold. Only tiles next to the fire can ever count."""
    danger = set()
    for r, c in ship.open_cells():
        tile = ship.grid[r][c]
        if tile.on_fire:
            continue
        K = 0
        for nr, nc in tile.neighbors:
            if ship.grid[nr][nc].on_fire:
                K += 1
        if 1 - (1 - q) ** K > threshold:
            danger.add((r, c))
    return danger


def bot4_path(ship, pos, button, q, threshold=THRESHOLD, penalty=PENALTY, one_step=False):
    """Bot 4: A* to the button, avoiding burning tiles and paying extra for
    predicted-fire tiles. one_step=True swaps the race for the literal
    one-step rule (only used in tuning)."""
    if one_step:
        danger = one_step_predicted_fire(ship, q, threshold)
    else:
        danger = predicted_fire(ship, pos, button, q, threshold)
    cost = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if ship.grid[r][c].on_fire:
                row.append(math.inf)
            elif (r, c) in danger:
                row.append(1.0 + penalty)
            else:
                row.append(1.0)
        cost.append(row)
    return a_star(ship, pos, button, cost)
