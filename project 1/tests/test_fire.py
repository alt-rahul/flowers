import numpy as np

from fire import NOT_YET, FireTrajectory, fire_step, spread_probabilities
from ship import Ship


def corridor_ship(length=15):
    """A single horizontal corridor through the middle of the grid."""
    grid = np.zeros((length, length), dtype=bool)
    grid[length // 2, :] = True
    return Ship(grid)


def test_spread_probabilities():
    q = 0.3
    assert np.allclose(spread_probabilities(q), [1 - (1 - q) ** k for k in range(5)])


def test_update_is_synchronous():
    # With q = 1 every cell next to the fire must ignite, but a cell that
    # ignites this step must not pass the fire on until the next step, so
    # after t updates exactly the cells within distance t are burning.
    ship = corridor_ship()
    mid = ship.index(7, 7)
    fire = FireTrajectory(ship, 1.0, mid, np.random.default_rng(0))
    for t in range(1, 8):
        burning = fire.burning_at(t)
        expected = {ship.index(7, c) for c in range(7 - t, 8 + t)}
        assert set(np.flatnonzero(burning)) == expected
        assert fire.ignite_time[ship.index(7, 7 + t)] == t


def test_no_spread_when_q_is_zero():
    ship = corridor_ship()
    fire = FireTrajectory(ship, 0.0, ship.index(7, 7), np.random.default_rng(0))
    assert fire.burning_at(50).sum() == 1


def test_fire_stays_on_open_cells():
    ship = Ship.generate(20, np.random.default_rng(1))
    fire = FireTrajectory(ship, 0.7, int(ship.open_cells[0]), np.random.default_rng(1))
    assert not (fire.burning_at(60) & ~ship.open_flat).any()


def test_ignition_rate_matches_formula():
    # A cell with K burning neighbours should ignite with chance 1-(1-q)^K.
    q, trials = 0.2, 40000
    grid = np.ones((3, 3), dtype=bool)
    rng = np.random.default_rng(5)
    probs = spread_probabilities(q)
    for k, burning_cells in [(1, [(0, 1)]), (2, [(0, 1), (1, 0)]), (4, [(0, 1), (1, 0), (1, 2), (2, 1)])]:
        burning = np.zeros((3, 3), dtype=bool)
        for rc in burning_cells:
            burning[rc] = True
        hits = sum(fire_step(burning, grid, probs, rng)[1, 1] for _ in range(trials))
        expected = 1 - (1 - q) ** k
        assert abs(hits / trials - expected) < 4 * np.sqrt(expected * (1 - expected) / trials)


def test_not_yet_marker():
    ship = corridor_ship()
    fire = FireTrajectory(ship, 0.0, ship.index(7, 0), np.random.default_rng(0))
    assert fire.ignite_time[ship.index(7, 14)] == NOT_YET
