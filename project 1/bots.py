"""The four bot strategies.

Every bot implements the same two-method interface:

    reset(ship, button, q)  called once at the start of a trial
    act(pos, burning)       called every time step with the bot's position and
                            a flat boolean mask of the cells burning right now;
                            returns the cell to move to (an open neighbour, or
                            `pos` to stay put), or None if no fire-free route
                            to the button exists any more.

Because the fire only ever grows, "no fire-free route right now" means no
route will ever exist again, so the simulator ends the trial as a failure
("trapped") when a bot returns None.
"""
from __future__ import annotations

import numpy as np

from forecast import FORECASTS
from planning import bfs_path, risk_astar, with_neighbors
from ship import Ship


class Bot:
    name = "Bot"

    def reset(self, ship: Ship, button: int, q: float) -> None:
        self.ship = ship
        self.button = button
        self.q = q
        self.path: list[int] | None = None
        self.k = 0  # index of the bot's current cell in self.path

    def act(self, pos: int, burning: np.ndarray) -> int | None:
        raise NotImplementedError

    # Helpers for bots that follow a precomputed path.
    def _set_plan(self, path: list[int] | None) -> None:
        self.path = path
        self.k = 0

    def _next_on_plan(self) -> int:
        self.k += 1
        return self.path[self.k]

    def _plan_still_valid(self, pos: int, blocked: np.ndarray) -> bool:
        """True if we are on our current plan and none of its remaining cells
        are blocked."""
        if self.path is None or self.path[self.k] != pos:
            return False
        rest = self.path[self.k + 1:]
        return bool(rest) and not blocked[rest].any()


class Bot1(Bot):
    """Plans the shortest path avoiding the initial fire cell once, then
    follows it no matter what the fire does."""

    name = "Bot 1"

    def reset(self, ship, button, q):
        super().reset(ship, button, q)
        self.planned = False

    def act(self, pos, burning):
        if not self.planned:
            self._set_plan(bfs_path(self.ship.neighbors, pos, self.button, burning.tolist()))
            self.planned = True
        if self.path is None:
            return None
        return self._next_on_plan()


class Bot2(Bot):
    """Every step, follows a shortest path to the button that avoids the cells
    currently on fire.

    With lazy=True (the default) the BFS is only rerun when fire has landed on
    the remaining part of the current plan. This gives the same behaviour as
    replanning every step: the set of usable cells only shrinks over time, so
    if the rest of the current shortest path is still usable it is still a
    shortest path. (The only possible difference is which of several equally
    short paths gets picked.) lazy=False replans every step regardless, and
    the tests check that the two agree on path length at every step.
    """

    name = "Bot 2"

    def __init__(self, lazy: bool = True):
        self.lazy = lazy

    def act(self, pos, burning):
        if not (self.lazy and self._plan_still_valid(pos, burning)):
            self._set_plan(bfs_path(self.ship.neighbors, pos, self.button, burning.tolist()))
            if self.path is None:
                return None
        return self._next_on_plan()


class Bot3(Bot):
    """Every step, follows a shortest path that avoids the fire and every cell
    next to the fire, if one exists; otherwise falls back to a shortest path
    that only avoids the fire (Bot 2's rule).

    The same lazy-replanning shortcut as Bot 2 is used, but only while the bot
    is on a buffered path: those cells only ever shrink too. While it is on a
    fallback path it rechecks for a buffered path every step, since moving can
    put a buffered route within reach again.
    """

    name = "Bot 3"

    def __init__(self, lazy: bool = True):
        self.lazy = lazy

    def reset(self, ship, button, q):
        super().reset(ship, button, q)
        self.buffered = False

    def act(self, pos, burning):
        danger = with_neighbors(burning, self.ship.D)
        if self.lazy and self.buffered and self._plan_still_valid(pos, danger):
            return self._next_on_plan()
        path = bfs_path(self.ship.neighbors, pos, self.button, danger.tolist())
        self.buffered = path is not None
        if path is None:
            path = bfs_path(self.ship.neighbors, pos, self.button, burning.tolist())
        self._set_plan(path)
        if path is None:
            return None
        return self._next_on_plan()


class Bot4(Bot):
    """Risk-aware, time-dependent A*.

    Every step the bot:
      1. Forecasts the fire: p_t[c] ~ P(cell c is burning t updates from now),
         from the cells burning now and the known q, using dynamic message
         passing on the ship's graph (forecast.MessagePassingForecast).
      2. Runs A* over (cell, time) states where entering cell c on move t
         costs 1 + risk_weight * (-log(1 - p_t[c])). Summed over a path, the
         risk term is -log of the chance of surviving every cell on it if the
         cells burned independently, so the planner minimises
             path length + risk_weight * (-log P(survive path)).
         Because the risk depends on *when* the bot reaches each cell, a
         longer path pays twice: its cells are visited later, when the fire
         has had longer to spread, and the button itself is reached later,
         when it is more likely to have burned. This is how the bot trades a
         short path near the fire against a long path away from it.
      3. Takes the first move of that plan.

    The A* heuristic is the true BFS distance to the button ignoring fire,
    computed once per trial. It is admissible because each move costs at
    least 1, and much tighter than Euclidean or Manhattan distance on a maze.

    With risk_weight = 0 this reduces to Bot 2 (the shortest fire-free path).
    forecast="meanfield" swaps in the naive forecast, for comparison.
    """

    name = "Bot 4"

    def __init__(self, risk_weight: float = 30.0, forecast: str = "dmp"):
        self.risk_weight = risk_weight
        self.forecast_cls = FORECASTS[forecast]

    def reset(self, ship, button, q):
        super().reset(ship, button, q)
        self.heuristic = ship.distances_from(button)
        self._forecast = None
        self._forecast_fire = None

    def act(self, pos, burning):
        # The forecast only depends on the current fire, so reuse it while the
        # fire has not changed (common when q is small).
        if self._forecast is None or not np.array_equal(burning, self._forecast_fire):
            self._forecast = self.forecast_cls(self.ship, self.q, burning)
            self._forecast_fire = burning
        path = risk_astar(self.ship.neighbors, pos, self.button, self.heuristic,
                          self._forecast.risk_at, self.risk_weight)
        if path is None:
            return None
        return path[1]


BOTS = {"bot1": Bot1, "bot2": Bot2, "bot3": Bot3, "bot4": Bot4}


def make_bot(spec: str) -> Bot:
    """Build a bot from a spec like "bot3", "bot2:lazy=false" or
    "bot4:risk_weight=30,forecast=meanfield"."""
    name, _, args = spec.partition(":")
    kwargs = {}
    for item in filter(None, args.split(",")):
        key, _, value = item.partition("=")
        if value.lower() in ("true", "false"):
            kwargs[key] = value.lower() == "true"
        else:
            try:
                kwargs[key] = float(value)
            except ValueError:
                kwargs[key] = value
    return BOTS[name](**kwargs)
