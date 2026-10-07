import math

import numpy as np
import pytest

from planning import bfs_distances
from ship import Ship, grid_neighbors


def open_tiles(ship):
    return {(r, c) for r in range(ship.D) for c in range(ship.D) if ship.grid[r][c].is_open}


def open_pairs(ship):
    """Number of pairs of open tiles that touch."""
    count = 0
    for r, c in open_tiles(ship):
        if r + 1 < ship.D and ship.grid[r + 1][c].is_open:
            count += 1
        if c + 1 < ship.D and ship.grid[r][c + 1].is_open:
            count += 1
    return count


@pytest.mark.parametrize("seed", range(10))
def test_maze_phase_is_a_maximal_tree(seed):
    ship = Ship(25)
    ship.grow_maze(np.random.default_rng(seed))
    # Every tile was opened next to exactly one open tile, so the open tiles
    # form a tree: n tiles joined by n - 1 touching pairs.
    assert open_pairs(ship) == len(open_tiles(ship)) - 1
    # Phase 1 only stops when no wall has exactly one open neighbour.
    for r in range(ship.D):
        for c in range(ship.D):
            if not ship.grid[r][c].is_open:
                assert ship.count_open_neighbors((r, c)) != 1


@pytest.mark.parametrize("seed", range(10))
def test_dead_ends_cut_at_least_in_half(seed):
    rng = np.random.default_rng(seed)
    ship = Ship(30)
    ship.grow_maze(rng)
    before = len(ship.dead_ends())
    opened_before = open_tiles(ship)
    ship.reduce_dead_ends(rng)
    assert len(ship.dead_ends()) <= before / 2
    assert opened_before <= open_tiles(ship), "phase 2 must only open tiles"


@pytest.mark.parametrize("seed", range(10))
def test_all_open_tiles_connected(seed):
    ship = Ship.generate(30, np.random.default_rng(seed))
    dist = bfs_distances(ship, ship.open_cells()[0])
    assert all(dist[r][c] < math.inf for r, c in ship.open_cells())


def test_generation_is_reproducible():
    a = Ship.generate(20, np.random.default_rng(42))
    b = Ship.generate(20, np.random.default_rng(42))
    assert open_tiles(a) == open_tiles(b)


def test_neighbors_are_open_and_adjacent():
    ship = Ship.generate(15, np.random.default_rng(3))
    for r in range(ship.D):
        for c in range(ship.D):
            tile = ship.grid[r][c]
            if not tile.is_open:
                assert tile.neighbors == []
                continue
            expected = [n for n in grid_neighbors(ship.D, r, c) if ship.tile(n).is_open]
            assert tile.neighbors == expected


def test_from_rows_and_clear():
    ship = Ship.from_rows(["#.#",
                           "...",
                           "#.#"])
    assert ship.open_cells() == [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)]
    assert ship.neighbors((1, 1)) == [(0, 1), (2, 1), (1, 0), (1, 2)]   # up, down, left, right
    ship.tile((1, 1)).on_fire = True
    ship.tile((0, 1)).has_bot = True
    ship.tile((2, 1)).has_button = True
    assert ship.fire_cells() == {(1, 1)}
    ship.clear()
    assert ship.fire_cells() == set()
    assert not any(t.has_bot or t.has_button for row in ship.grid for t in row)
