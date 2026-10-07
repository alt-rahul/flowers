import heapq
import math

import numpy as np
import pytest

from fire import spread_chances, spread_fire
from planners import danger_radius, fire_arrival_probability
from planning import (astar_path, bfs_distances, bfs_path, fire_distances, manhattan_distance,
                      with_neighbors)
from ship import Ship


def pick(ship, rng, count):
    """`count` different random open tiles."""
    cells = ship.open_cells()
    return [cells[i] for i in rng.choice(len(cells), size=count, replace=False)]


def assert_valid_path(ship, path, start, goal, blocked=()):
    assert path[0] == start and path[-1] == goal
    for a, b in zip(path, path[1:]):
        assert b in ship.neighbors(a)
    assert not any(pos in blocked for pos in path[1:])


@pytest.mark.parametrize("seed", range(10))
def test_bfs_path_is_shortest(seed):
    rng = np.random.default_rng(seed)
    ship = Ship.generate(20, rng)
    start, goal = pick(ship, rng, 2)
    path = bfs_path(ship, start, goal, set())
    assert_valid_path(ship, path, start, goal)
    assert len(path) - 1 == bfs_distances(ship, start)[goal[0]][goal[1]]


def test_bfs_path_avoids_blocked_tiles_or_gives_up():
    rng = np.random.default_rng(0)
    for _ in range(30):
        ship = Ship.generate(15, rng)
        start, goal = pick(ship, rng, 2)
        blocked = {pos for pos in ship.open_cells() if rng.random() < 0.2} - {goal}
        path = bfs_path(ship, start, goal, blocked)
        if path is not None:
            assert_valid_path(ship, path, start, goal, blocked)


def test_with_neighbors():
    ship = Ship(5)
    assert with_neighbors(ship, {(2, 2)}) == {(1, 2), (2, 1), (2, 2), (2, 3), (3, 2)}


@pytest.mark.parametrize("seed", range(10))
def test_astar_with_unit_costs_finds_shortest_paths(seed):
    rng = np.random.default_rng(seed)
    ship = Ship.generate(20, rng)
    start, goal = pick(ship, rng, 2)
    cost = [[1.0] * ship.D for r in range(ship.D)]
    path = astar_path(ship, start, goal, cost)
    assert_valid_path(ship, path, start, goal)
    assert len(path) - 1 == bfs_distances(ship, start)[goal[0]][goal[1]]


def dijkstra_cost(ship, start, goal, cost):
    """Cheapest cost by plain Dijkstra (no heuristic), for comparison."""
    best = {start: 0.0}
    heap = [(0.0, start)]
    while heap:
        g, cell = heapq.heappop(heap)
        if cell == goal:
            return g
        if g > best[cell]:
            continue
        for n in ship.neighbors(cell):
            step = cost[n[0]][n[1]]
            if step == math.inf:
                continue
            if g + step < best.get(n, math.inf):
                best[n] = g + step
                heapq.heappush(heap, (best[n], n))
    return None


@pytest.mark.parametrize("seed", range(10))
def test_astar_finds_the_cheapest_path(seed):
    rng = np.random.default_rng(seed)
    ship = Ship.generate(20, rng)
    start, goal = pick(ship, rng, 2)
    # Costs like Bot 4's: mostly 1, some 21, a few impassable.
    cost = [[1.0] * ship.D for r in range(ship.D)]
    for r in range(ship.D):
        for c in range(ship.D):
            roll = rng.random()
            if roll < 0.05:
                cost[r][c] = math.inf
            elif roll < 0.3:
                cost[r][c] = 21.0
    cost[goal[0]][goal[1]] = 1.0
    path = astar_path(ship, start, goal, cost)
    expected = dijkstra_cost(ship, start, goal, cost)
    if expected is None:
        assert path is None
    else:
        assert_valid_path(ship, path, start, goal)
        assert sum(cost[r][c] for r, c in path[1:]) == pytest.approx(expected)


def test_manhattan_never_overestimates():
    rng = np.random.default_rng(1)
    ship = Ship.generate(20, rng)
    goal = ship.open_cells()[0]
    dist = bfs_distances(ship, goal)
    assert all(manhattan_distance(pos, goal) <= dist[pos[0]][pos[1]] for pos in ship.open_cells())


def test_fire_distance_through_walls_is_manhattan():
    ship = Ship.generate(15, np.random.default_rng(2))
    fire = {ship.open_cells()[0], ship.open_cells()[-1]}
    dist = fire_distances(ship, fire, ignore_walls=True)
    for r in range(ship.D):
        for c in range(ship.D):
            assert dist[r][c] == min(manhattan_distance((r, c), f) for f in fire)


@pytest.mark.parametrize("q", [0.1, 0.3, 0.7])
@pytest.mark.parametrize("threshold", [0.3, 0.6, 0.9])
def test_danger_radius_matches_the_binomial_formula(q, threshold):
    radius = danger_radius(q, threshold, 40)
    for k in range(41):
        for d in range(1, k + 2):
            p = fire_arrival_probability(k, d, q)
            if abs(p - threshold) > 1e-9:          # skip exact ties
                assert (d <= radius[k]) == (p > threshold)


def burn_frequencies(ship, origin, q, steps, runs, seed):
    """freq[t][(r, c)] = fraction of simulated fires in which (r, c) is burning
    after t updates."""
    chance = spread_chances(q)
    counts = [dict() for _ in range(steps + 1)]
    for run in range(runs):
        rng = np.random.default_rng([seed, run])
        ship.clear()
        ship.tile(origin).on_fire = True
        for t in range(1, steps + 1):
            spread_fire(ship, chance, rng)
            for pos in ship.fire_cells():
                counts[t][pos] = counts[t].get(pos, 0) + 1
    return [{pos: n / runs for pos, n in layer.items()} for layer in counts]


def test_race_model_matches_the_real_fire_on_a_corridor():
    # Along a corridor the fire really does advance one tile per step with
    # probability q, so the race model should match simulated fires.
    q, runs = 0.3, 1500
    rows = ["#" * 12] * 12
    rows[0] = "." * 12
    ship = Ship.from_rows(rows)
    freq = burn_frequencies(ship, (0, 0), q, 15, runs, seed=11)
    for t in (5, 10, 15):
        for d in (1, 3, 6, 10):
            expected = fire_arrival_probability(t, d, q)
            seen = freq[t].get((0, d), 0.0)
            assert abs(seen - expected) < 4 * math.sqrt(expected * (1 - expected) / runs) + 1e-3


def test_race_model_never_overestimates_the_fire():
    # On a real ship the fire can also arrive by other routes, which only
    # makes it faster: the real chance is never below the race model's.
    q, runs = 0.4, 800
    ship = Ship.generate(12, np.random.default_rng(12))
    origin = ship.open_cells()[len(ship.open_cells()) // 2]
    dist = bfs_distances(ship, origin)
    freq = burn_frequencies(ship, origin, q, 15, runs, seed=13)
    for t in (5, 10, 15):
        for r, c in ship.open_cells():
            model = fire_arrival_probability(t, dist[r][c], q)
            seen = freq[t].get((r, c), 0.0)
            assert seen >= model - 4 * math.sqrt(model * (1 - model) / runs) - 0.01
