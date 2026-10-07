"""How the fire spreads from one time step to the next."""
import numpy as np


def spread_fire(ship, q):
    """One fire update. Every open tile that isn't burning catches fire with
    probability 1 - (1 - q)^K, where K is its number of burning neighbours.
    Returns the tiles that caught fire."""
    catches = []
    for r in range(ship.D):
        for c in range(ship.D):
            tile = ship.grid[r][c]
            if tile.is_open and not tile.on_fire:
                K = 0
                for nr, nc in tile.neighbors:
                    if ship.grid[nr][nc].on_fire:
                        K += 1
                if np.random.random() < 1 - (1 - q) ** K:
                    catches.append((r, c))

    # The new fires only start after every tile has been checked, so a tile
    # that catches fire this step can't spread it until the next step.
    for r, c in catches:
        ship.grid[r][c].on_fire = True
    return catches
