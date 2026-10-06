import heapq
import math

import numpy as np
import pytest

from math import comb

from forecast import FORECASTS, FireForecast
from planning import bfs_path, risk_astar, with_neighbors
from ship import Ship


def assert_valid_path(ship, path, start, goal, blocked=None):
    assert path[0] == start and path[-1] == goal
    for a, b in zip(path, path[1:]):
        assert b in ship.neighbors[a]
    if blocked is not None:
        assert not any(blocked[c] for c in path[1:])


@pytest.mark.parametrize("seed", range(10))
def test_bfs_path_is_shortest(seed):
    rng = np.random.default_rng(seed)
    ship = Ship.generate(20, rng)
    start, goal = (int(c) for c in rng.choice(ship.open_cells, 2, replace=False))
    path = bfs_path(ship.neighbors, start, goal, [False] * ship.D ** 2)
    assert_valid_path(ship, path, start, goal)
    assert len(path) - 1 == ship.distances_from(start)[goal]


def test_bfs_path_avoids_blocked_cells_or_gives_up():
    rng = np.random.default_rng(0)
    for _ in range(30):
        ship = Ship.generate(15, rng)
        start, goal = (int(c) for c in rng.choice(ship.open_cells, 2, replace=False))
        blocked = (rng.random(ship.D ** 2) < 0.2).tolist()
        blocked[goal] = False
        path = bfs_path(ship.neighbors, start, goal, blocked)
        if path is not None:
            assert_valid_path(ship, path, start, goal, blocked)


def test_with_neighbors():
    mask = np.zeros(25, dtype=bool)
    mask[12] = True  # centre of a 5x5 grid
    assert set(np.flatnonzero(with_neighbors(mask, 5))) == {7, 11, 12, 13, 17}


def path_cost(path, goal, risk_at, w):
    cost = 0.0
    for k, cell in enumerate(path[1:], start=1):
        cost += 1.0 + w * risk_at(k - 1 if cell == goal else k)[cell]
    return cost


def brute_force_cost(ship, start, goal, risk_at, w, horizon):
    """Dijkstra over every (cell, time) state with no pruning."""
    best = {(start, 0): 0.0}
    heap = [(0.0, 0, start)]
    while heap:
        g, t, cell = heapq.heappop(heap)
        if g > best[(cell, t)]:
            continue
        if cell == goal:
            return g
        if t >= horizon:
            continue
        for n in ship.neighbors[cell]:
            r = risk_at(t if n == goal else t + 1)[n]
            if r == math.inf:
                continue
            ng = g + 1.0 + w * r
            if ng < best.get((n, t + 1), math.inf):
                best[(n, t + 1)] = ng
                heapq.heappush(heap, (ng, t + 1, n))
    return None


@pytest.mark.parametrize("seed", range(15))
def test_risk_astar_matches_brute_force(seed):
    # Random risk that only grows over time, like a real fire forecast.
    rng = np.random.default_rng(seed)
    ship = Ship.generate(9, rng)
    start, goal = (int(c) for c in rng.choice(ship.open_cells, 2, replace=False))
    horizon = ship.n_open + 2
    layers = np.cumsum(rng.exponential(0.05, size=(horizon + 1, ship.D ** 2)), axis=0)
    risk_at = lambda t: layers[min(t, horizon)]
    heuristic = ship.distances_from(goal)
    for w in (0.0, 1.0, 10.0):
        path = risk_astar(ship.neighbors, start, goal, heuristic, risk_at, w)
        assert_valid_path(ship, path, start, goal)
        expected = brute_force_cost(ship, start, goal, risk_at, w, horizon)
        assert path_cost(path, goal, risk_at, w) == pytest.approx(expected)


def test_risk_astar_without_risk_is_shortest_fire_free_path():
    rng = np.random.default_rng(7)
    for _ in range(20):
        ship = Ship.generate(20, rng)
        start, goal, fire = (int(c) for c in rng.choice(ship.open_cells, 3, replace=False))
        burning = np.zeros(ship.D ** 2, dtype=bool)
        burning[fire] = True
        forecast = FireForecast(ship, 0.5, burning)
        path = risk_astar(ship.neighbors, start, goal, ship.distances_from(goal),
                          forecast.risk_at, 0.0)
        reference = bfs_path(ship.neighbors, start, goal, burning.tolist())
        if reference is None:
            assert path is None
        else:
            assert_valid_path(ship, path, start, goal, burning)
            assert len(path) == len(reference)


@pytest.mark.parametrize("kind", sorted(FORECASTS))
def test_forecast_is_exact_when_fire_is_deterministic(kind):
    rng = np.random.default_rng(2)
    ship = Ship.generate(20, rng)
    origin = int(ship.open_cells[0])
    burning = np.zeros(ship.D ** 2, dtype=bool)
    burning[origin] = True
    forecast = FORECASTS[kind](ship, 1.0, burning)
    dist = ship.distances_from(origin)
    for t in (0, 1, 5, 12):
        expected = np.array([d <= t for d in dist])
        assert np.allclose(forecast.prob_at(t), expected)


def test_message_passing_is_exact_on_a_corridor():
    # Cell d along a corridor is burning after t updates iff at least d of
    # t independent coin flips with chance q came up: P(Bin(t, q) >= d).
    q, n = 0.3, 12
    grid = np.zeros((n, n), dtype=bool)
    grid[0, :] = True
    ship = Ship(grid)
    burning = np.zeros(n * n, dtype=bool)
    burning[0] = True
    forecast = FORECASTS["dmp"](ship, q, burning)
    for t in (1, 4, 10, 20):
        p = forecast.prob_at(t)
        for d in range(1, n):
            exact = sum(comb(t, k) * q ** k * (1 - q) ** (t - k) for k in range(d, t + 1))
            assert p[d] == pytest.approx(exact, abs=1e-9)


@pytest.mark.parametrize("kind", sorted(FORECASTS))
def test_forecast_probabilities_are_valid_and_grow(kind):
    rng = np.random.default_rng(4)
    ship = Ship.generate(20, rng)
    burning = np.zeros(ship.D ** 2, dtype=bool)
    burning[rng.choice(ship.open_cells, 3, replace=False)] = True
    forecast = FORECASTS[kind](ship, 0.3, burning)
    prev = forecast.prob_at(0)
    assert (prev[burning] == 1).all()
    for t in range(1, 30):
        p = forecast.prob_at(t)
        assert ((p >= 0) & (p <= 1)).all()
        assert (p >= prev - 1e-12).all()
        assert (p[~ship.open_flat] == 0).all()
        prev = p
