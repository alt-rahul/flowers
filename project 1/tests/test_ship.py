import math

import numpy as np

from search import distance_map
from ship import Ship, generate_ship, grid_neighbors, ship_from_rows


def count_open(ship):
    return len(ship.open_cells())


def count_touching_pairs(ship):
    """How many pairs of open tiles are next to each other."""
    pairs = 0
    for r, c in ship.open_cells():
        if r + 1 < ship.D and ship.grid[r + 1][c].is_open:
            pairs += 1
        if c + 1 < ship.D and ship.grid[r][c + 1].is_open:
            pairs += 1
    return pairs


def test_phase_1_makes_a_tree():
    for seed in range(5):
        np.random.seed(seed)
        ship = Ship(25)
        ship.generate_blocks()
        # A tree with n tiles has exactly n - 1 touching pairs.
        assert count_touching_pairs(ship) == count_open(ship) - 1
        # Phase 1 only stops when no blocked tile has exactly one open neighbour.
        for r in range(ship.D):
            for c in range(ship.D):
                if not ship.grid[r][c].is_open:
                    assert ship.count_open_neighbors(r, c) != 1


def test_phase_2_halves_the_dead_ends():
    for seed in range(5):
        np.random.seed(seed)
        ship = Ship(30)
        ship.generate_blocks()
        ends_before = len(ship.dead_ends())
        open_before = ship.open_cells()
        ship.reduce_dead_ends()
        assert len(ship.dead_ends()) <= ends_before / 2
        for r, c in open_before:
            assert ship.grid[r][c].is_open   # phase 2 only opens tiles


def test_every_open_tile_can_be_reached():
    for seed in range(5):
        ship = generate_ship(30, seed)
        dist = distance_map(ship, [ship.open_cells()[0]], set())
        for r, c in ship.open_cells():
            assert dist[r][c] < math.inf


def test_same_seed_same_ship():
    a = generate_ship(20, 42)
    b = generate_ship(20, 42)
    assert a.open_cells() == b.open_cells()


def test_neighbors_are_the_open_tiles_next_to_each_tile():
    ship = generate_ship(15, 3)
    for r in range(ship.D):
        for c in range(ship.D):
            expected = []
            if ship.grid[r][c].is_open:
                for nr, nc in grid_neighbors(ship.D, r, c):
                    if ship.grid[nr][nc].is_open:
                        expected.append((nr, nc))
            assert ship.grid[r][c].neighbors == expected


def test_ship_from_rows_and_clear():
    ship = ship_from_rows(["#.#",
                           "...",
                           "#.#"])
    assert ship.open_cells() == [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]
    assert ship.neighbors((1, 1)) == [(0, 1), (2, 1), (1, 0), (1, 2)]   # up, down, left, right
    ship.tile((1, 1)).on_fire = True
    ship.tile((0, 1)).has_bot = True
    assert ship.fire_cells() == {(1, 1)}
    ship.clear()
    assert ship.fire_cells() == set()
    assert not ship.tile((0, 1)).has_bot
