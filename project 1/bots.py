from search import a_star, bfs, map_distance
from ship import check_neighbors

# Bot 4's settings
PENALTY = 10              # how much extra "cost" bot4 pays to step onto a tile with heat of 1 
BURNING_COST = 1000000    # the "cost" of trying to step onto a tile that is already on fire - very very expensive


# this function builds the bot1 path, which is just a basic bfs 
def bot1_path(ship, pos, button):
    return bfs(ship, pos, button, ship.fire_cells())

# this function also builds the bot2 path, which also just basic bfs, however it will get called on at every 
# time step so the bot gets updated on the cells that are currently on fire.
def bot2_path(ship, pos, button):
    return bfs(ship, pos, button, ship.fire_cells())

# very similar to bot2, however it has a set of cells that it wants to avoid, the cells that are neighbors
# to cell that is currently on fire, it tries to calculate a path, however it is unsuccessful because of its
# restrictions then it just falls back to the building a path like it was done in bot2.
def bot3_path(ship, pos, button):
    fire = ship.fire_cells()
    avoid = set(fire)
    for r, c in fire:
        for n in check_neighbors(ship.D, r, c):
            avoid.add(n)
    path = bfs(ship, pos, button, avoid)
    if path is None:
        path = bfs(ship, pos, button, fire)
    return path


# bo4 is very intersting because it basically makes a "heat map" of the ship, where the closer a tile is to an existing fire, 
# the "hotter" it is. Then the bot runs A* to the button, where hot tiles cost more to step
# on or use in our path. so the bot tries to goes around the hotter cells when the way around isn't too long,
# but ultimately decides to go through it when every other way is much longer 
# the heat of each tile is based on the formula q ** (d - 1), where d is how many tiles the fire has to
# travel to get there. a tile right next to the fire (d = 1) has heat 1, and every tile further away evnetually decays in cost
# so steping ton a tile costs the BURNING_COST if you were to step on a fire cell (it's ridicously high because we never want to cell on a
# fire cell), and 1 + PENATLTY * heat for any other cell
def heat_map(ship, q):
    fire_dist = map_distance(ship, ship.fire_cells(), set())   # calcualtes the dfor every tile
    heat = [] 
    for r in range(ship.D): # iterates through every cell
        row = []
        for c in range(ship.D):
            tile = ship.grid[r][c]
            if tile.is_open and not tile.on_fire:
                d = fire_dist[r][c]
                row.append(q ** (d - 1)) # calculates the heat value of the cell
            else:
                row.append(0)
        heat.append(row)
    return heat

#this function is builds the path for bot4, first it calculates the heat values for every cell,
#then based on if the cell is already on fire or if it's not, calculates the cost for each cell
#once the cost list is built, it passes it through the a_star fuction and gets a path 
def bot4_path(ship, pos, button, q, penalty=PENALTY):
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
    #this exists because if every path does has to go through the fire then A* still returns that path
    # which is not allowed so if there the path inlcudes a fire cell - it should be marked as not possible
    for r, c in path: 
        if ship.grid[r][c].on_fire:
            return None
    return path
