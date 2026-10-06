"""The fire: one random realisation per trial, plus the spread rule itself."""
import numpy as np

from ship import count_neighbors

# Ignition time for cells that have not caught fire (yet).
NOT_YET = np.iinfo(np.int64).max


def spread_probabilities(q):
    """Lookup table: entry K is 1 - (1 - q)^K, the chance that a cell with K
    burning neighbours catches fire this step (K = 0..4)."""
    return 1.0 - (1.0 - q) ** np.arange(5)


def fire_step(burning, open_grid, probs, rng):
    """Return the mask of cells that ignite during one fire update.

    The update is synchronous: K is counted from `burning` as it was at the
    start of the step and the caller only ORs the result in afterwards, so a
    cell that ignites during this step cannot spread fire until the next one.
    """
    k = count_neighbors(burning)
    roll = rng.random(burning.shape)
    return open_grid & ~burning & (roll < probs[k])


class FireTrajectory:
    """One realisation of the fire, generated lazily as far as anyone needs it.

    The fire never reacts to the bot, so a trial's fire can be simulated once
    and shared by every bot evaluated on that trial. Besides saving work, this
    means all bots face exactly the same fire, so differences between bots are
    not drowned out by differences in luck (common random numbers).

    `ignite_time[i]` is the update at which cell i caught fire (0 for the
    origin, NOT_YET if it has not burned so far). Bots only ever receive
    `burning_at(t)` for the current t, never the future.
    """

    def __init__(self, ship, q, origin, rng):
        self.ship = ship
        self.q = q
        self.rng = rng
        self.probs = spread_probabilities(q)
        self.burning = np.zeros((ship.D, ship.D), dtype=bool)
        self.burning.flat[origin] = True
        self.ignite_time = np.full(ship.D * ship.D, NOT_YET, dtype=np.int64)
        self.ignite_time[origin] = 0
        self.t = 0

    def advance_to(self, t):
        while self.t < t:
            new = fire_step(self.burning, self.ship.grid, self.probs, self.rng)
            self.burning |= new
            self.t += 1
            self.ignite_time[new.ravel()] = self.t

    def burning_at(self, t):
        """Flat boolean mask of the cells burning after `t` fire updates."""
        self.advance_to(t)
        return self.ignite_time <= t

    def is_burning(self, cell, t):
        self.advance_to(t)
        return bool(self.ignite_time[cell] <= t)
