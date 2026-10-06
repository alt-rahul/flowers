"""Probabilistic forecasts of where the fire will be, used by Bot 4.

Both forecasts answer the same question: given the cells burning right now,
what is p_t[c] = P(cell c is burning after t more fire updates)? Planning
uses the risk -log(1 - p_t[c]) (see planning.risk_astar).

MessagePassingForecast is the one Bot 4 uses. MeanFieldForecast is the
simpler first attempt, kept for comparison: forecast_check.py shows it is far
too pessimistic on these ships, and the README explains why.
"""
from __future__ import annotations

import numpy as np

from ship import Ship

# Floor on the forecast chance that a cell is NOT burning, so -log stays
# finite. Only cells burning right now get infinite risk.
MIN_SAFE = 1e-12


class _Forecast:
    """Shared lazy layer cache. Subclasses implement _advance() and keep
    self._safe, a flat array of 1 - p_t for the latest t."""

    def __init__(self, q: float, burning: np.ndarray):
        self.q = q
        self._burning_now = np.where(burning, np.inf, 0.0)
        self._static = q == 0.0  # with q = 0 the fire never moves
        self._risk: list[np.ndarray] = []

    def risk_at(self, t: int) -> np.ndarray:
        """Flat array of -log(1 - p_t): the risk cost of being in each cell at
        time t (inf for cells that are already burning). Layers are computed
        lazily, so the planner only pays for the time steps it reaches."""
        if self._static:
            return self._risk[0]
        while len(self._risk) <= t:
            self._advance()
            self._push_layer()
        return self._risk[t]

    def prob_at(self, t: int) -> np.ndarray:
        """p_t as a flat array (for analysis and tests, not used in planning)."""
        return -np.expm1(-self.risk_at(t))

    def _push_layer(self) -> None:
        risk = -np.log(np.maximum(self._safe, MIN_SAFE))
        risk += self._burning_now
        self._risk.append(risk)

    def _advance(self) -> None:
        raise NotImplementedError


class MeanFieldForecast(_Forecast):
    """Naive mean-field forecast.

    The true rule is that a non-burning cell ignites with probability
    1 - (1 - q)^K. Treating each neighbour n as burning independently with
    probability p_t[n], the chance that c does NOT ignite is
    prod_n (1 - q * p_t[n]), so with safe = 1 - p:

        safe_{t+1}[c] = safe_t[c] * prod_n (1 - q + q * safe_t[n]).

    Problem: probability "echoes". Cell A raises its neighbour B's p, which
    in turn raises A's p, and so on, so the forecast fire spreads along every
    walk through the maze (including back-and-forth ones) rather than only
    along real paths. On these tree-like ships it badly overestimates how
    fast the fire spreads.
    """

    def __init__(self, ship: Ship, q: float, burning: np.ndarray):
        super().__init__(q, burning)
        D = ship.D
        self._open = ship.grid
        self._safe2d = 1.0 - burning.reshape(D, D)
        # Padded copy of (1 - q * p) with a border of ones, so each cell's
        # four neighbours are four shifted views and need no edge cases.
        self._pad = np.ones((D + 2, D + 2))
        self._safe = self._safe2d.ravel()
        self._push_layer()

    def _advance(self) -> None:
        pad = self._pad
        inner = pad[1:-1, 1:-1]
        np.multiply(self._safe2d, self.q, out=inner)
        inner += 1.0 - self.q
        none_ignite = pad[:-2, 1:-1] * pad[2:, 1:-1]
        none_ignite *= pad[1:-1, :-2]
        none_ignite *= pad[1:-1, 2:]
        self._safe2d = np.where(self._open, self._safe2d * none_ignite, 1.0)
        self._safe = self._safe2d.ravel()


class EdgeIndex:
    """Directed edges between open cells, arranged for vectorised message
    passing. Depends only on the layout, so it is built once per ship."""

    def __init__(self, ship: Ship):
        src, dst = [], []
        for i in ship.open_cells.tolist():
            for k in ship.neighbors[i]:
                src.append(k)  # edge k -> i
                dst.append(i)
        E = len(src)
        edge_id = {(k, i): e for e, (k, i) in enumerate(zip(src, dst))}
        pad = E  # index of an extra message slot that always holds 1.0
        # incoming[c] = edges l -> c, padded to 4.
        incoming = np.full((ship.D * ship.D, 4), pad, dtype=np.intp)
        for i in ship.open_cells.tolist():
            for j, l in enumerate(ship.neighbors[i]):
                incoming[i, j] = edge_id[(l, i)]
        # cavity[e] for e = k -> i: edges l -> k with l != i, padded to 3.
        cavity = np.full((E, 3), pad, dtype=np.intp)
        for e, (k, i) in enumerate(zip(src, dst)):
            others = [edge_id[(l, k)] for l in ship.neighbors[k] if l != i]
            cavity[e, :len(others)] = others
        self.E = E
        self.src = np.array(src, dtype=np.intp)
        # Stored column by column: multiplying a few plain gathers together is
        # about 5x faster than gathering a 2D block and calling .prod(axis=1).
        self.incoming = tuple(incoming.T.copy())
        self.cavity = tuple(cavity.T.copy())

    @classmethod
    def of(cls, ship: Ship) -> "EdgeIndex":
        if getattr(ship, "_edge_index", None) is None:
            ship._edge_index = cls(ship)
        return ship._edge_index


class MessagePassingForecast(_Forecast):
    """Dynamic message passing (DMP) forecast for the fire.

    The fire is an SI epidemic: each burning cell independently ignites each
    non-burning neighbour with probability q per step. DMP (Lokhov et al.,
    2014-2015) tracks one set of messages per directed edge k -> i, computed
    on the "cavity" graph where i is held unburnt, so i can never re-ignite
    k and inflate its own risk. That removes the echo of the naive mean-field
    forecast, makes the forecast exact on trees, and keeps it close on graphs
    with few loops, such as these ships (a maze plus some extra openings).

    Messages, for each directed edge k -> i:
      theta[k->i](t)  P(k has not ignited i by time t)
      phi[k->i](t)    P(k is burning but has not ignited i by time t)
      safe[k->i](t)   P(k is not burning at t), in the cavity graph without i

    Update, for every edge at once (q = flammability):
      theta(t+1) = theta(t) - q * phi(t)
      safe[k->i](t+1) = safe_0[k] * prod_{l in N(k), l != i} theta[l->k](t+1)
      phi(t+1) = (1 - q) * phi(t) + safe(t) - safe(t+1)
    and the forecast for each cell is
      1 - p_t[c] = safe_0[c] * prod_{l in N(c)} theta[l->c](t).

    Each step is a few gathers over about 2 * (number of open cells) edges.
    The forecast is exact for q = 1 on any layout, and 1 - p_t only
    decreases over time, which the pruning in planning.risk_astar relies on.
    """

    def __init__(self, ship: Ship, q: float, burning: np.ndarray):
        super().__init__(q, burning)
        self._edges = EdgeIndex.of(ship)
        E = self._edges.E
        self._safe0 = 1.0 - burning.astype(float)
        self._theta = np.ones(E + 1)  # last slot is padding, always 1
        self._edge_safe0 = self._safe0[self._edges.src]
        self._edge_safe = self._edge_safe0
        self._phi = 1.0 - self._edge_safe
        self._safe = self._safe0
        self._push_layer()

    def _advance(self) -> None:
        edges, q = self._edges, self.q
        theta = self._theta
        theta[:-1] -= q * self._phi
        np.maximum(theta, 0.0, out=theta)  # guard against round-off below 0
        c0, c1, c2 = edges.cavity
        edge_safe = self._edge_safe0 * theta[c0] * theta[c1] * theta[c2]
        self._phi = (1.0 - q) * self._phi + (self._edge_safe - edge_safe)
        self._edge_safe = edge_safe
        i0, i1, i2, i3 = edges.incoming
        self._safe = self._safe0 * theta[i0] * theta[i1] * theta[i2] * theta[i3]


FORECASTS = {"dmp": MessagePassingForecast, "meanfield": MeanFieldForecast}
FireForecast = MessagePassingForecast
