import copy
import math

import numpy as np

from fire import spread_fire
from ship import generate_ship, ship_from_rows


def corridor(length):
    """A ship that is one corridor along the middle row."""
    rows = ["#" * length] * length
    rows[length // 2] = "." * length
    return ship_from_rows(rows)


def test_fire_update_is_synchronous():
    # At q = 1 every tile next to the fire catches fire, but a tile that just
    # caught fire can't pass it on in the same step. So after t updates,
    # exactly the tiles within distance t of the start are burning.
    ship = corridor(15)
    ship.tile((7, 7)).on_fire = True
    rng = np.random.default_rng(0)
    for t in range(1, 8):
        new = spread_fire(ship, 1.0, rng)
        assert ship.fire_cells() == {(7, c) for c in range(7 - t, 8 + t)}
        assert set(new) == {(7, 7 - t), (7, 7 + t)}


def test_no_spread_when_q_is_zero():
    ship = corridor(15)
    ship.tile((7, 7)).on_fire = True
    rng = np.random.default_rng(0)
    for t in range(50):
        spread_fire(ship, 0.0, rng)
    assert ship.fire_cells() == {(7, 7)}


def test_fire_only_burns_open_tiles():
    ship = generate_ship(20, np.random.default_rng(1))
    ship.tile(ship.open_cells()[0]).on_fire = True
    rng = np.random.default_rng(1)
    for t in range(60):
        spread_fire(ship, 0.7, rng)
    for pos in ship.fire_cells():
        assert ship.tile(pos).is_open


def test_catch_rate_matches_the_formula():
    # The middle tile should catch fire with chance 1 - (1 - q)^K.
    q = 0.2
    trials = 20000
    ship = ship_from_rows(["...", "...", "..."])
    rng = np.random.default_rng(5)
    for burning in [[(0, 1)], [(0, 1), (1, 0)], [(0, 1), (1, 0), (1, 2), (2, 1)]]:
        hits = 0
        for i in range(trials):
            ship.clear()
            for pos in burning:
                ship.tile(pos).on_fire = True
            spread_fire(ship, q, rng)
            if ship.tile((1, 1)).on_fire:
                hits += 1
        expected = 1 - (1 - q) ** len(burning)
        assert abs(hits / trials - expected) < 4 * math.sqrt(expected * (1 - expected) / trials)


def test_same_generator_same_fire():
    ship = generate_ship(20, np.random.default_rng(2))
    rng = np.random.default_rng(7)
    fires = []
    for run in range(2):
        run_rng = copy.deepcopy(rng)
        ship.clear()
        ship.tile(ship.open_cells()[10]).on_fire = True
        history = []
        for t in range(30):
            history.append(spread_fire(ship, 0.4, run_rng))
        fires.append(history)
    assert fires[0] == fires[1]
