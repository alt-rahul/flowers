import copy
import math

import numpy as np

from fire import spread_chances, spread_fire
from ship import Ship


def corridor_ship(length=15):
    """A single corridor along the middle row of the grid."""
    rows = ["#" * length] * length
    rows[length // 2] = "." * length
    return Ship.from_rows(rows)


def test_spread_chances():
    q = 0.3
    assert np.allclose(spread_chances(q), [1 - (1 - q) ** k for k in range(5)])


def test_update_is_synchronous():
    # With q = 1 every tile next to the fire must catch fire, but a tile that
    # catches fire this step must not pass the fire on until the next step, so
    # after t updates exactly the tiles within distance t are burning.
    ship = corridor_ship()
    ship.tile((7, 7)).on_fire = True
    chance = spread_chances(1.0)
    rng = np.random.default_rng(0)
    for t in range(1, 8):
        new = spread_fire(ship, chance, rng)
        assert ship.fire_cells() == {(7, c) for c in range(7 - t, 8 + t)}
        assert set(new) == {(7, 7 - t), (7, 7 + t)}


def test_no_spread_when_q_is_zero():
    ship = corridor_ship()
    ship.tile((7, 7)).on_fire = True
    chance = spread_chances(0.0)
    rng = np.random.default_rng(0)
    for _ in range(50):
        spread_fire(ship, chance, rng)
    assert ship.fire_cells() == {(7, 7)}


def test_fire_stays_on_open_tiles():
    ship = Ship.generate(20, np.random.default_rng(1))
    ship.tile(ship.open_cells()[0]).on_fire = True
    chance = spread_chances(0.7)
    rng = np.random.default_rng(1)
    for _ in range(60):
        spread_fire(ship, chance, rng)
    assert all(ship.tile(pos).is_open for pos in ship.fire_cells())


def test_catch_rate_matches_formula():
    # A tile with K burning neighbours should catch fire with chance 1-(1-q)^K.
    q, trials = 0.2, 20000
    ship = Ship.from_rows(["...", "...", "..."])
    chance = spread_chances(q)
    rng = np.random.default_rng(5)
    for burning in [[(0, 1)], [(0, 1), (1, 0)], [(0, 1), (1, 0), (1, 2), (2, 1)]]:
        hits = 0
        for _ in range(trials):
            ship.clear()
            for pos in burning:
                ship.tile(pos).on_fire = True
            spread_fire(ship, chance, rng)
            hits += ship.tile((1, 1)).on_fire
        expected = 1 - (1 - q) ** len(burning)
        assert abs(hits / trials - expected) < 4 * math.sqrt(expected * (1 - expected) / trials)


def test_same_generator_same_fire():
    # Two runs that start the generator from the same point get the same fire:
    # this is how every bot on a trial faces the same fire.
    ship = Ship.generate(20, np.random.default_rng(2))
    rng = np.random.default_rng(7)
    fires = []
    for _ in range(2):
        run_rng = copy.deepcopy(rng)
        ship.clear()
        ship.tile(ship.open_cells()[10]).on_fire = True
        history = [spread_fire(ship, spread_chances(0.4), run_rng) for _ in range(30)]
        fires.append(history)
    assert fires[0] == fires[1]
