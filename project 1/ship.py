"""Ship layout generation (kept independent of the fire/bot code so it can be
reused in later projects).

The layout is a D x D boolean numpy array where True means "open". Cells are
also referred to by a flat index ``i = r * D + c``. The path planners work on
flat indices because plain Python ints are much cheaper to hash and compare
than (r, c) tuples, and the fire code works on the 2D arrays so it can be
vectorised with numpy.
"""
from __future__ import annotations

from collections import deque
from functools import lru_cache

import numpy as np


@lru_cache(maxsize=None)
def grid_neighbors(D: int) -> tuple[tuple[int, ...], ...]:
    """Flat indices of the up/down/left/right neighbours of every cell,
    ignoring walls. Cached per D because every ship of that size shares it."""
    nbrs = []
    for r in range(D):
        for c in range(D):
            cell = []
            if r > 0:
                cell.append((r - 1) * D + c)
            if r < D - 1:
                cell.append((r + 1) * D + c)
            if c > 0:
                cell.append(r * D + c - 1)
            if c < D - 1:
                cell.append(r * D + c + 1)
            nbrs.append(tuple(cell))
    return tuple(nbrs)


def count_neighbors(mask: np.ndarray) -> np.ndarray:
    """For a 2D boolean mask, count how many of each cell's 4 neighbours are True."""
    count = np.zeros(mask.shape, dtype=np.int8)
    count[1:, :] += mask[:-1, :]
    count[:-1, :] += mask[1:, :]
    count[:, 1:] += mask[:, :-1]
    count[:, :-1] += mask[:, 1:]
    return count


def dead_ends(grid: np.ndarray) -> np.ndarray:
    """Flat indices of open cells with exactly one open neighbour."""
    return np.flatnonzero(grid & (count_neighbors(grid) == 1))


def generate_layout(D: int, rng: np.random.Generator) -> np.ndarray:
    """Generate a D x D layout following the project's procedure."""
    return reduce_dead_ends(grow_maze(D, rng), rng)


def grow_maze(D: int, rng: np.random.Generator) -> np.ndarray:
    """Phase 1: open a random interior cell, then repeatedly open a random
    blocked cell that has exactly one open neighbour, until there are none.

    Rescanning the whole grid for such cells every iteration would be
    O(D^4), so we keep the candidate set up to date incrementally: opening a
    cell only changes the open-neighbour counts of its own 4 neighbours. The
    candidates live in a list plus an index map, which gives O(1) random
    choice and O(1) removal, so the whole phase is O(D^2).
    """
    if D < 3:
        raise ValueError("D must be at least 3 so the ship has an interior")
    nbrs = grid_neighbors(D)
    is_open = [False] * (D * D)
    open_count = [0] * (D * D)
    candidates: list[int] = []  # blocked cells with exactly one open neighbour
    where: dict[int, int] = {}  # cell -> its position in `candidates`

    def add(cell: int) -> None:
        where[cell] = len(candidates)
        candidates.append(cell)

    def remove(cell: int) -> None:
        i = where.pop(cell)
        last = candidates.pop()
        if i < len(candidates):
            candidates[i] = last
            where[last] = i

    def open_cell(cell: int) -> None:
        is_open[cell] = True
        if cell in where:
            remove(cell)
        for n in nbrs[cell]:
            open_count[n] += 1
            if not is_open[n]:
                if open_count[n] == 1:
                    add(n)
                elif open_count[n] == 2:
                    remove(n)

    r, c = rng.integers(1, D - 1, size=2)
    open_cell(int(r) * D + int(c))
    while candidates:
        open_cell(candidates[rng.integers(len(candidates))])
    return np.array(is_open, dtype=bool).reshape(D, D)


def reduce_dead_ends(grid: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Phase 2: open a random closed neighbour of a random dead end, until the
    number of dead ends is at most half of what it was at the start."""
    grid = grid.copy()
    flat = grid.ravel()  # a view, so writes go through to `grid`
    nbrs = grid_neighbors(grid.shape[0])
    ends = dead_ends(grid)
    target = len(ends) / 2
    while len(ends) > target:
        d = int(ends[rng.integers(len(ends))])
        # Every dead end has at least one closed in-bounds neighbour: it has
        # 2-4 neighbours on the grid and only one of them is open.
        closed = [n for n in nbrs[d] if not flat[n]]
        flat[closed[rng.integers(len(closed))]] = True
        ends = dead_ends(grid)
    return grid


class Ship:
    """A ship layout plus the adjacency lists the planners need."""

    def __init__(self, grid: np.ndarray):
        self.grid = np.asarray(grid, dtype=bool)
        if self.grid.ndim != 2 or self.grid.shape[0] != self.grid.shape[1]:
            raise ValueError("ship grid must be square")
        self.D = self.grid.shape[0]
        self.open_flat = self.grid.ravel()
        self.open_cells = np.flatnonzero(self.open_flat)
        is_open = self.open_flat.tolist()
        self.neighbors: list[list[int]] = [
            [n for n in nbrs if is_open[n]] if is_open[i] else []
            for i, nbrs in enumerate(grid_neighbors(self.D))
        ]

    @classmethod
    def generate(cls, D: int, rng: np.random.Generator) -> "Ship":
        return cls(generate_layout(D, rng))

    @property
    def n_open(self) -> int:
        return len(self.open_cells)

    def coords(self, cell: int) -> tuple[int, int]:
        return divmod(cell, self.D)

    def index(self, r: int, c: int) -> int:
        return r * self.D + c

    def distances_from(self, source: int) -> list[float]:
        """BFS distance from `source` to every cell through open cells
        (inf for blocked/unreachable cells)."""
        dist = [float("inf")] * (self.D * self.D)
        dist[source] = 0
        frontier = deque([source])
        while frontier:
            cur = frontier.popleft()
            d = dist[cur] + 1
            for n in self.neighbors[cur]:
                if dist[n] == float("inf"):
                    dist[n] = d
                    frontier.append(n)
        return dist

    def render(self, marks: dict[int, str] | None = None) -> str:
        """ASCII picture: '#' blocked, '.' open, plus any single-char marks."""
        marks = marks or {}
        rows = []
        for r in range(self.D):
            row = []
            for c in range(self.D):
                i = r * self.D + c
                row.append(marks.get(i, "." if self.open_flat[i] else "#"))
            rows.append("".join(row))
        return "\n".join(rows)

    def __str__(self) -> str:
        return self.render()
