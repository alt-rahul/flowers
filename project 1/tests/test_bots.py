import math

import numpy as np

from bots import bot2_path, bot3_path, bot4_path, danger_radius, predicted_fire
from fire import spread_fire
from search import bfs, distance_map
from ship import generate_ship, grid_neighbors, ship_from_rows


def corridor():
    """A ship that is one corridor along the top row: (0, 0) to (0, 11)."""
    rows = ["#" * 12] * 12
    rows[0] = "." * 12
    return ship_from_rows(rows)


def start_fire(ship, cells):
    ship.clear()
    for pos in cells:
        ship.tile(pos).on_fire = True


def fire_arrival_probability(k, d, q):
    """P(Binomial(k, q) >= d), written out directly."""
    total = 0.0
    for j in range(d, k + 1):
        total += math.comb(k, j) * q ** j * (1 - q) ** (k - j)
    return total


def test_bot3_falls_back_to_bot2():
    # The fire sits in a pocket right next to the only corridor, so every
    # route passes next to it.
    ship = ship_from_rows(["#######",
                           "#######",
                           "###.###",
                           ".......",
                           "#######",
                           "#######",
                           "#######"])
    start_fire(ship, [(2, 3)])
    path = bot3_path(ship, (3, 0), (3, 6))
    assert path == bot2_path(ship, (3, 0), (3, 6))
    assert (3, 3) in path


def test_bot3_avoids_the_tiles_next_to_the_fire_when_it_can():
    rng = np.random.default_rng(0)
    for i in range(20):
        ship = generate_ship(20, rng)
        cells = ship.open_cells()
        picks = rng.choice(len(cells), size=3, replace=False)
        start, button, fire = cells[picks[0]], cells[picks[1]], cells[picks[2]]
        start_fire(ship, [fire])
        buffer = {fire}
        for n in grid_neighbors(ship.D, fire[0], fire[1]):
            buffer.add(n)
        path = bot3_path(ship, start, button)
        if bfs(ship, start, button, buffer) is not None:
            for pos in path[1:]:
                assert pos not in buffer


def test_danger_radius_matches_the_binomial_formula():
    for q in [0.1, 0.3, 0.7]:
        for threshold in [0.3, 0.6, 0.9]:
            radius = danger_radius(q, threshold, 40)
            for k in range(41):
                for d in range(1, k + 2):
                    p = fire_arrival_probability(k, d, q)
                    if abs(p - threshold) > 1e-9:   # skip exact ties
                        assert (d <= radius[k]) == (p > threshold)


def test_predicted_fire_is_not_a_fixed_buffer():
    # Fire at (0, 11), q = 0.5.
    ship = corridor()
    start_fire(ship, [(0, 11)])
    # From (0, 9) the bot reaches (0, 10) in one step, before the fire probably does.
    assert (0, 10) not in predicted_fire(ship, (0, 9), None, 0.5, 0.6)
    # From (0, 0) it needs 10 steps to reach (0, 10), so the fire probably gets
    # there first; but the fire can't get 6 tiles to (0, 5) in 5 steps.
    far = predicted_fire(ship, (0, 0), None, 0.5, 0.6)
    assert (0, 10) in far
    assert (0, 5) not in far


def test_predicted_fire_is_exact_when_q_is_one():
    # At q = 1 the fire moves every step, so a tile is predicted fire exactly
    # when the fire is at most as far from it as the bot is.
    rng = np.random.default_rng(3)
    for i in range(10):
        ship = generate_ship(20, rng)
        cells = ship.open_cells()
        picks = rng.choice(len(cells), size=2, replace=False)
        start, fire = cells[picks[0]], cells[picks[1]]
        start_fire(ship, [fire])
        danger = predicted_fire(ship, start, None, 1.0, 0.6)
        from_fire = distance_map(ship, [fire], set())
        from_bot = distance_map(ship, [start], {fire})
        for r, c in cells:
            if (r, c) != fire and from_bot[r][c] != math.inf:
                assert ((r, c) in danger) == (from_fire[r][c] <= from_bot[r][c])


def test_bot4_without_a_penalty_takes_a_shortest_path():
    rng = np.random.default_rng(4)
    for i in range(20):
        ship = generate_ship(20, rng)
        cells = ship.open_cells()
        picks = rng.choice(len(cells), size=3, replace=False)
        start, button, fire = cells[picks[0]], cells[picks[1]], cells[picks[2]]
        start_fire(ship, [fire])
        for t in range(5):
            spread_fire(ship, 0.3, rng)
        if ship.tile(start).on_fire or ship.tile(button).on_fire:
            continue
        shortest = bot2_path(ship, start, button)
        plan = bot4_path(ship, start, button, 0.3, 0.6, 0)
        if shortest is None:
            assert plan is None
        else:
            assert len(plan) == len(shortest)


def test_race_model_matches_the_real_fire_on_a_corridor():
    # Along a corridor the fire really does move forward one tile per step
    # with chance q, so the formula should match simulated fires.
    q = 0.3
    runs = 1500
    ship = corridor()
    burning = {}   # burning[(t, d)] = in how many runs tile (0, d) was burning after t updates
    for run in range(runs):
        rng = np.random.default_rng([11, run])
        start_fire(ship, [(0, 0)])
        for t in range(1, 16):
            spread_fire(ship, q, rng)
            for d in [1, 3, 6, 10]:
                if ship.tile((0, d)).on_fire:
                    if (t, d) not in burning:
                        burning[(t, d)] = 0
                    burning[(t, d)] += 1
    for t in [5, 10, 15]:
        for d in [1, 3, 6, 10]:
            expected = fire_arrival_probability(t, d, q)
            seen = 0
            if (t, d) in burning:
                seen = burning[(t, d)] / runs
            assert abs(seen - expected) < 4 * math.sqrt(expected * (1 - expected) / runs) + 0.001
