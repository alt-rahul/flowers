from search import a_star, bfs, map_distance
from ship import check_neighbors

# Bot 4's settings
PENALTY = 10              # how much extra Bot 4 pays to step onto a tile with heat 1
BURNING_COST = 1000000    # the cost of stepping onto a burning tile: so big that the bot never does


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
# Bot 4 makes a "heat map" of the ship: the closer a tile is to the fire, the
# hotter it is. Then it runs A* to the button, where hot tiles cost more to step
# on. So the bot goes around the hot area when the way around isn't too long,
# and goes through it when every other way is much longer.
#
# The heat of a tile is q ** (d - 1), where d is how many tiles the fire has to
# travel to get there. A tile right next to the fire (d = 1) has heat 1, and
# every tile further away multiplies the heat by q:
#     q = 0.2:  1, 0.2, 0.04, 0.008, ...   (a slow fire: only the tiles next to it are hot)
#     q = 0.8:  1, 0.8, 0.64, 0.51, ...    (a fast fire: tiles far away are hot too)
#
# Stepping onto a tile costs:
#     BURNING_COST           if it is burning
#     1 + PENALTY * heat     otherwise


def heat_map(ship, q):
    """heat[r][c] = q ** (d - 1) for every open tile that isn't burning, where
    d is the fire's distance to the tile. Walls and burning tiles get 0."""
    fire_dist = map_distance(ship, ship.fire_cells(), set())   # d for every tile
    heat = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            tile = ship.grid[r][c]
            if tile.is_open and not tile.on_fire:
                d = fire_dist[r][c]
                row.append(q ** (d - 1))
            else:
                row.append(0)
        heat.append(row)
    return heat


def bot4_path(ship, pos, button, q, penalty=PENALTY):
    """Bot 4: A* to the button, where each tile costs 1 + penalty * heat to
    step on, and a burning tile costs BURNING_COST. Returns None if even the
    cheapest path has to go through fire."""
    heat = heat_map(ship, q)
    cost = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if ship.grid[r][c].on_fire:
                row.append(BURNING_COST)
            else:
                row.append(1 + penalty * heat[r][c])
        cost.append(row)

    path = a_star(ship, pos, button, cost)
    if path is None:
        return None
    # BURNING_COST is bigger than any route that avoids the fire could ever
    # cost, so if the cheapest path still steps on fire, every route to the
    # button runs through fire: the bot is trapped.
    for r, c in path:
        if ship.grid[r][c].on_fire:
            return None
    return path
