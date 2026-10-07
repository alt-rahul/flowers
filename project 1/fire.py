"""The fire: how it spreads from one time step to the next.

THE RULE (from the assignment)
    Every time step, each open tile that is not burning catches fire with
    probability 1 - (1 - q)^K, where K is how many of its neighbours are
    burning and q is the ship's flammability.

SYNCHRONOUS UPDATE (the TA's feedback)
    Every tile is judged against the fire as it was at the START of the step.
    spread_fire() first decides which tiles catch fire, and only then sets them
    on fire, so a tile that catches fire this step cannot spread it until the
    next step.
"""
import numpy as np


def spread_chances(q):
    """chance[K] = 1 - (1 - q)^K: the chance that a tile with K burning
    neighbours catches fire this step, for K = 0, 1, 2, 3, 4.

    (numpy works out the five powers. Its rounding in the last decimal place
    differs very slightly from Python's own ** for some q, and keeping numpy
    here keeps every fire identical to the experiments that were already run.)
    """
    return (1.0 - (1.0 - q) ** np.arange(5)).tolist()


def spread_fire(ship, chance, rng):
    """One fire update. Sets the newly burning tiles on fire and returns their
    positions.

    `chance` comes from spread_chances(q). A random number is drawn for every
    tile, walls and burning tiles included, in row order. That way each tile's
    random number doesn't depend on what the rest of the fire looks like, so a
    given random generator always produces exactly the same fire.
    """
    catches = []
    for r in range(ship.D):
        for c in range(ship.D):
            roll = rng.random()
            tile = ship.grid[r][c]
            if not tile.is_open or tile.on_fire:
                continue
            k = 0   # burning neighbours
            for nr, nc in tile.neighbors:
                if ship.grid[nr][nc].on_fire:
                    k += 1
            if roll < chance[k]:
                catches.append((r, c))
    # Only now are the new fires added: that is what makes the update synchronous.
    for r, c in catches:
        ship.grid[r][c].on_fire = True
    return catches
