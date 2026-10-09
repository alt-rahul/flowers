import numpy as np
# this function actually spreads the fire from one cell to another

#Looks at all open cels and that isn't currently burning, counts the # of current neighbors
#that are also on fire to track K, then with probabily of 1 - (1 - q)^K it updates the cells that 
# have caught on fire and updates the respective tiles
def spread_fire(ship, q):
    catches = []
    for r in range(ship.D):
        for c in range(ship.D):
            tile = ship.grid[r][c]
            if tile.is_open and not tile.on_fire: # check for open cells that are not already on fire
                K = 0
                for nr, nc in tile.neighbors: # checks for neighbors that are already on fire to update the K value
                    if ship.grid[nr][nc].on_fire:
                        K += 1
                if np.random.random() < 1 - (1 - q) ** K: #
                    catches.append((r, c))

    # The new fires only start after every tile has been checked, so a tile
    # that catches fire this step can't spread it until the next step. 
    # also there is catches because I want to make sure all the tiles are caught on fire at the same time
    # and if the fire is updated while going through the for loop then it will impact the probabiltiy
    for r, c in catches:
        ship.grid[r][c].on_fire = True
    return catches
