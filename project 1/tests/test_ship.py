import numpy as np
import pytest

from ship import Ship, count_neighbors, dead_ends, generate_layout, grow_maze, reduce_dead_ends


def open_pairs(grid):
    """Number of pairs of adjacent open cells."""
    return int((grid[1:, :] & grid[:-1, :]).sum() + (grid[:, 1:] & grid[:, :-1]).sum())


@pytest.mark.parametrize("seed", range(10))
def test_maze_phase_is_a_maximal_tree(seed):
    grid = grow_maze(25, np.random.default_rng(seed))
    # Every cell was opened next to exactly one open cell, so the open cells
    # form a tree: n cells joined by n - 1 adjacencies.
    assert open_pairs(grid) == grid.sum() - 1
    # Phase 1 only stops when no blocked cell has exactly one open neighbour.
    assert not (~grid & (count_neighbors(grid) == 1)).any()


@pytest.mark.parametrize("seed", range(10))
def test_dead_ends_cut_at_least_in_half(seed):
    rng = np.random.default_rng(seed)
    maze = grow_maze(30, rng)
    ship = reduce_dead_ends(maze, rng)
    assert len(dead_ends(ship)) <= len(dead_ends(maze)) / 2
    assert (ship | ~maze).all(), "phase 2 must only open cells"


@pytest.mark.parametrize("seed", range(10))
def test_all_open_cells_connected(seed):
    ship = Ship.generate(30, np.random.default_rng(seed))
    dist = ship.distances_from(int(ship.open_cells[0]))
    assert all(dist[c] < float("inf") for c in ship.open_cells)


def test_generation_is_reproducible():
    a = generate_layout(20, np.random.default_rng(42))
    b = generate_layout(20, np.random.default_rng(42))
    assert (a == b).all()


def test_neighbors_are_open_and_adjacent():
    ship = Ship.generate(15, np.random.default_rng(3))
    for cell in range(ship.D * ship.D):
        if not ship.open_flat[cell]:
            assert ship.neighbors[cell] == []
            continue
        r, c = ship.coords(cell)
        for n in ship.neighbors[cell]:
            nr, nc = ship.coords(n)
            assert ship.open_flat[n] and abs(nr - r) + abs(nc - c) == 1
