import math

import numpy as np

from fire import spread_fire
from ship import generate_ship
from helpers import ship_from_rows


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
    np.random.seed(0)
    for t in range(1, 8):
        new = spread_fire(ship, 1.0)
        expected = set()
        for c in range(7 - t, 8 + t):
            expected.add((7, c))
        assert ship.fire_cells() == expected
        assert set(new) == {(7, 7 - t), (7, 7 + t)}


def test_no_spread_when_q_is_zero():
    ship = corridor(15)
    ship.tile((7, 7)).on_fire = True
    np.random.seed(0)
    for t in range(50):
        spread_fire(ship, 0.0)
    assert ship.fire_cells() == {(7, 7)}


def test_fire_only_burns_open_tiles():
    ship = generate_ship(20, 1)
    ship.tile(ship.open_cells()[0]).on_fire = True
    for t in range(60):
        spread_fire(ship, 0.7)
    for pos in ship.fire_cells():
        assert ship.tile(pos).is_open


def test_catch_rate_matches_the_formula():
    # The middle tile should catch fire with chance 1 - (1 - q)^K.
    q = 0.2
    trials = 20000
    ship = ship_from_rows(["...", "...", "..."])
    np.random.seed(5)
    for burning in [[(0, 1)], [(0, 1), (1, 0)], [(0, 1), (1, 0), (1, 2), (2, 1)]]:
        hits = 0
        for i in range(trials):
            ship.clear()
            for pos in burning:
                ship.tile(pos).on_fire = True
            spread_fire(ship, q)
            if ship.tile((1, 1)).on_fire:
                hits += 1
        expected = 1 - (1 - q) ** len(burning)
        assert abs(hits / trials - expected) < 4 * math.sqrt(expected * (1 - expected) / trials)


def test_same_seed_same_fire():
    # Two runs that start from the same seed get the same fire: this is how
    # every bot on a trial faces the same fire.
    ship = generate_ship(20, 2)
    fires = []
    for run in range(2):
        np.random.seed(7)
        ship.clear()
        ship.tile(ship.open_cells()[10]).on_fire = True
        history = []
        for t in range(30):
            history.append(spread_fire(ship, 0.4))
        fires.append(history)
    assert fires[0] == fires[1]
