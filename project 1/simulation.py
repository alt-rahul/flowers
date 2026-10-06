"""Running bots on trials, plus a clairvoyant upper bound."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from bots import Bot
from fire import FireTrajectory
from planning import bfs_distances, fire_distances, fireproof_path
from ship import Ship

SUCCESS = "success"
ENTERED_FIRE = "entered_fire"    # the bot stepped into a burning cell
CAUGHT = "caught"                # the fire spread onto the bot's cell
BUTTON_BURNED = "button_burned"  # the button caught fire before the bot got there
TRAPPED = "trapped"              # the bot is alive, but every route to the button is on fire
TIMEOUT = "timeout"              # safety cap, should not happen


@dataclass
class Trial:
    ship: Ship
    q: float
    bot_start: int
    button: int
    fire_start: int
    fire: FireTrajectory
    _to_button: dict[int, list[float]] = field(default_factory=dict, repr=False)

    @classmethod
    def generate(cls, D: int, q: float, rng: np.random.Generator) -> "Trial":
        ship = Ship.generate(D, rng)
        bot, button, fire = (int(c) for c in rng.choice(ship.open_cells, size=3, replace=False))
        return cls(ship, q, bot, button, fire, FireTrajectory(ship, q, fire, rng))

    def with_new_fire(self, rng: np.random.Generator) -> "Trial":
        """Same ship and starting cells, but a fresh realisation of the fire."""
        fire = FireTrajectory(self.ship, self.q, self.fire_start, rng)
        return Trial(self.ship, self.q, self.bot_start, self.button, self.fire_start, fire)

    @property
    def max_steps(self) -> int:
        return 10 * self.ship.n_open

    def fireproof(self) -> bool:
        """True if the bot can win for certain from the start: some path to
        the button stays ahead of even the fastest possible fire (q = 1).
        Decided by two BFSs, with no simulation."""
        fire_dist = fire_distances(self.ship.neighbors, [self.fire_start], self.ship.D ** 2)
        return fireproof_path(self.ship.neighbors, self.bot_start, self.button,
                              fire_dist) is not None

    def distances_to_button(self, t: int) -> list[float]:
        """Distance to the button avoiding the cells burning after t updates.
        Cached per t, since every bot on this trial sees the same fire."""
        if t not in self._to_button:
            self._to_button[t] = bfs_distances(self.ship.neighbors, self.button,
                                               self.fire.burning_at(t).tolist())
        return self._to_button[t]


@dataclass
class Outcome:
    success: bool
    reason: str
    steps: int
    path: list[int] = field(default_factory=list)
    # Moves Bot 2's rule would never make: ones that don't shorten the
    # distance to the button through currently unburnt cells.
    deviations: int = 0
    think_ms: float = 0.0  # time spent inside the bot's reset() and act() calls


def run_bot(trial: Trial, bot: Bot, record_path: bool = False,
            count_deviations: bool = False) -> Outcome:
    """Run one bot on one trial. Each time step: the bot picks a move, moves,
    presses the button if it is on it, and otherwise the fire advances.

    With count_deviations, also count the moves that Bot 2's rule could not
    have made (see Outcome.deviations). That is how we check whether Bots 3
    and 4 ever actually decide differently from Bot 2."""
    fire = trial.fire
    button = trial.button
    neighbors = trial.ship.neighbors
    pos = trial.bot_start
    path = [pos]
    deviations = 0
    clock = time.perf_counter
    t0 = clock()
    bot.reset(trial.ship, button, trial.q)
    think = clock() - t0
    t = 0  # number of fire updates so far

    def done(success: bool, reason: str, steps: int) -> Outcome:
        return Outcome(success, reason, steps, path, deviations, think * 1000)

    while t < trial.max_steps:
        burning = fire.burning_at(t)
        t0 = clock()
        nxt = bot.act(pos, burning)
        think += clock() - t0
        if nxt is None:
            return done(False, TRAPPED, t)
        if nxt != pos and nxt not in neighbors[pos]:
            raise RuntimeError(f"{bot.name} made an illegal move {pos} -> {nxt}")
        if count_deviations:
            dist = trial.distances_to_button(t)
            if dist[nxt] != dist[pos] - 1:
                deviations += 1
        pos = nxt
        if record_path:
            path.append(pos)
        if burning[pos]:
            return done(False, ENTERED_FIRE, t + 1)
        if pos == button:
            return done(True, SUCCESS, t + 1)
        t += 1
        if fire.is_burning(pos, t):
            return done(False, CAUGHT, t)
        if fire.is_burning(button, t):
            # Nothing can press a burning button, so this is a certain loss.
            return done(False, BUTTON_BURNED, t)
    return done(False, TIMEOUT, t)


def oracle_steps(trial: Trial) -> int | None:
    """Fewest steps in which a bot that knew the entire future of this fire
    could press the button, or None if no bot could possibly succeed.

    This is a BFS where cell c can be entered on move k only if it is not
    burning after k fire updates (the button: after k-1 updates, since it is
    pressed before the fire moves). Because the fire only grows, reaching a
    cell as early as possible is always best, so each cell only needs to be
    visited once. It upper-bounds every bot and tells us, for each failure,
    whether any sequence of moves could have saved the bot.
    """
    start, button = trial.bot_start, trial.button
    neighbors = trial.ship.neighbors
    fire = trial.fire
    seen = {start}
    frontier = [start]
    k = 0
    while frontier and k < trial.max_steps:
        fire.advance_to(k + 1)
        ignite = fire.ignite_time
        nxt = []
        for c in frontier:
            for n in neighbors[c]:
                if n in seen:
                    continue
                if n == button:
                    if ignite[n] > k:
                        return k + 1
                elif ignite[n] > k + 1:
                    seen.add(n)
                    nxt.append(n)
        frontier = nxt
        k += 1
    return None
