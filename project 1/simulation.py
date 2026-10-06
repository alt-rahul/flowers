"""Running bots on trials, plus a clairvoyant upper bound."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from bots import Bot
from fire import FireTrajectory
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

    @classmethod
    def generate(cls, D: int, q: float, rng: np.random.Generator) -> "Trial":
        ship = Ship.generate(D, rng)
        bot, button, fire = (int(c) for c in rng.choice(ship.open_cells, size=3, replace=False))
        return cls(ship, q, bot, button, fire, FireTrajectory(ship, q, fire, rng))

    @property
    def max_steps(self) -> int:
        return 10 * self.ship.n_open


@dataclass
class Outcome:
    success: bool
    reason: str
    steps: int
    path: list[int] = field(default_factory=list)


def run_bot(trial: Trial, bot: Bot, record_path: bool = False) -> Outcome:
    """Run one bot on one trial. Each time step: the bot picks a move, moves,
    presses the button if it is on it, and otherwise the fire advances."""
    fire = trial.fire
    button = trial.button
    neighbors = trial.ship.neighbors
    pos = trial.bot_start
    path = [pos]
    bot.reset(trial.ship, button, trial.q)
    t = 0  # number of fire updates so far
    while t < trial.max_steps:
        burning = fire.burning_at(t)
        nxt = bot.act(pos, burning)
        if nxt is None:
            return Outcome(False, TRAPPED, t, path)
        if nxt != pos and nxt not in neighbors[pos]:
            raise RuntimeError(f"{bot.name} made an illegal move {pos} -> {nxt}")
        pos = nxt
        if record_path:
            path.append(pos)
        if burning[pos]:
            return Outcome(False, ENTERED_FIRE, t + 1, path)
        if pos == button:
            return Outcome(True, SUCCESS, t + 1, path)
        t += 1
        if fire.is_burning(pos, t):
            return Outcome(False, CAUGHT, t, path)
        if fire.is_burning(button, t):
            # Nothing can press a burning button, so this is a certain loss.
            return Outcome(False, BUTTON_BURNED, t, path)
    return Outcome(False, TIMEOUT, t, path)


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
