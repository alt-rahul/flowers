"""Ship layout generation.

WHAT THIS FILE DOES
    Builds the D x D "ship": a maze of open cells (corridors and rooms) and
    blocked cells (walls), following the two-phase procedure in the project
    spec. It knows nothing about fire or bots, so later projects can reuse it.

HOW A SHIP IS STORED
    * `grid`: a D x D numpy array of booleans, True = open. numpy arrays are
      like a contiguous C array plus whole-array operations that run in C.
    * Cells also have a single integer id, the "flat index" i = r * D + c
      (row-major, exactly like flattening a 2D C array). The path planners use
      these ints because Python compares and hashes plain ints much faster
      than (row, col) tuples. The fire code uses the 2D array, because numpy
      can update the whole grid in a handful of operations.
    * `neighbors[i]`: the open cells next to cell i (up/down/left/right only,
      no diagonals). This adjacency list is what every search algorithm walks.
"""
# Lets type hints like `list[int] | None` work on older Python versions.
# Type hints are documentation only: Python does not enforce them.
from collections import deque     # double-ended queue, like std::deque (BFS frontier)
from functools import lru_cache   # memoization decorator: caches a function's results

import numpy as np


# @lru_cache means: the first call for a given D computes the answer, later
# calls with the same D return the cached result instantly. Every ship of
# size D has the same grid geometry, so this is computed once per D.
@lru_cache(maxsize=None)
def grid_neighbors(D):
    """For every cell (by flat index), the flat indices of its up/down/left/
    right neighbours that are inside the grid. Walls are ignored here; this is
    pure geometry. Returned as tuples (immutable) so the cached copy can't be
    modified by accident."""
    nbrs = []
    for r in range(D):              # range(D) = 0, 1, ..., D-1
        for c in range(D):
            cell = []
            if r > 0:
                cell.append((r - 1) * D + c)   # cell above
            if r < D - 1:
                cell.append((r + 1) * D + c)   # cell below
            if c > 0:
                cell.append(r * D + c - 1)     # cell to the left
            if c < D - 1:
                cell.append(r * D + c + 1)     # cell to the right
            nbrs.append(tuple(cell))
    return tuple(nbrs)


def count_neighbors(mask):
    """Given a 2D boolean mask (e.g. "is open" or "is burning"), return a 2D
    array counting how many of each cell's 4 neighbours are True.

    This is the "shifted slice" trick used all over the project. Example:
        count[1:, :] += mask[:-1, :]
    means "for every row r >= 1, add mask[r-1] (the row above) to count[r]".
    In C++ that is:
        for (r = 1; r < D; ++r) for (c = 0; c < D; ++c) count[r][c] += mask[r-1][c];
    The four lines below do above / below / left / right in four whole-array
    operations instead of a Python loop over D*D cells.
    """
    count = np.zeros(mask.shape, dtype=np.int8)   # small ints are enough (max 4)
    count[1:, :] += mask[:-1, :]    # neighbour above
    count[:-1, :] += mask[1:, :]    # neighbour below
    count[:, 1:] += mask[:, :-1]    # neighbour to the left
    count[:, :-1] += mask[:, 1:]    # neighbour to the right
    return count


def dead_ends(grid):
    """Flat indices of all dead ends: open cells with exactly one open
    neighbour. `&` is element-wise AND on boolean arrays, and
    np.flatnonzero returns the flat indices of the True entries."""
    return np.flatnonzero(grid & (count_neighbors(grid) == 1))


def generate_layout(D, rng):
    """Generate a D x D layout following the project's procedure: grow a maze
    (phase 1), then knock out about half of its dead ends (phase 2).

    `rng` is a seeded random number generator. Passing it in (instead of
    using a global one) makes every ship reproducible from its seed."""
    return reduce_dead_ends(grow_maze(D, rng), rng)


def grow_maze(D, rng):
    """Phase 1 of the spec: open a random interior cell, then repeatedly open
    a random blocked cell that has exactly one open neighbour, until no such
    cell is left.

    Result: a "perfect maze". Because every new cell touched exactly one open
    cell when it was opened, the open cells form a tree: one route between
    any two cells, and lots of dead ends.

    Efficiency: rescanning the whole grid for candidates every iteration
    would cost O(D^2) per step and O(D^4) overall. Instead we keep the set of
    candidates up to date incrementally: opening a cell only changes the
    open-neighbour counts of its own 4 neighbours. The candidates are stored
    in a list plus a dict mapping cell -> position in the list, which allows
    O(1) random choice and O(1) removal. Total cost: O(D^2).
    """
    if D < 3:
        raise ValueError("D must be at least 3 so the ship has an interior")
    nbrs = grid_neighbors(D)
    is_open = [False] * (D * D)     # Python list of D*D False values
    open_count = [0] * (D * D)      # open_count[i] = number of open neighbours of i
    candidates = []   # blocked cells with exactly one open neighbour
    where = {}        # cell -> its position in `candidates` (like std::unordered_map)

    # Small helper functions defined inside grow_maze. They can read and
    # modify the lists above (Python closures), like C++ lambdas capturing
    # by reference.
    def add(cell):
        where[cell] = len(candidates)
        candidates.append(cell)

    def remove(cell):
        # O(1) removal from the middle of a vector: move the last element
        # into the hole, then pop the last slot. Order doesn't matter because
        # we always pick a random candidate anyway.
        i = where.pop(cell)          # look up and delete the cell's position
        last = candidates.pop()      # remove the last element
        if i < len(candidates):      # if the removed cell wasn't the last one...
            candidates[i] = last     # ...fill its hole with the old last element
            where[last] = i

    def open_cell(cell):
        is_open[cell] = True
        if cell in where:            # it was a candidate; it isn't any more
            remove(cell)
        for n in nbrs[cell]:
            open_count[n] += 1
            if not is_open[n]:
                if open_count[n] == 1:     # blocked with exactly 1 open neighbour: new candidate
                    add(n)
                elif open_count[n] == 2:   # now has 2 open neighbours: no longer a candidate
                    remove(n)

    # Start from a random interior cell: rows and columns 1..D-2, so the
    # first cell is not on the outer edge. (integers(1, D-1) excludes D-1.)
    r, c = rng.integers(1, D - 1, size=2)
    open_cell(int(r) * D + int(c))
    while candidates:                # a non-empty list counts as True
        open_cell(candidates[rng.integers(len(candidates))])
    # Convert the Python list into a D x D numpy array.
    return np.array(is_open, dtype=bool).reshape(D, D)


def reduce_dead_ends(grid, rng):
    """Phase 2 of the spec: pick a random dead end, open one of its blocked
    neighbours at random, and repeat until at most half of the original dead
    ends are left. This adds loops to the maze, so there are often several
    routes between two cells: that is what gives the bots choices to make.

    (Opening a cell can create a new dead end, so the count doesn't always
    drop by one, but the loop always finishes: eventually enough cells open.)
    """
    grid = grid.copy()               # don't modify the caller's array
    flat = grid.ravel()  # a 1D view of the same memory, so writes go through to `grid`
    nbrs = grid_neighbors(grid.shape[0])
    ends = dead_ends(grid)
    target = len(ends) / 2
    while len(ends) > target:
        d = int(ends[rng.integers(len(ends))])
        # Every dead end has at least one closed in-bounds neighbour: it has
        # 2-4 neighbours on the grid and only one of them is open.
        # (List comprehension: "the list of n in nbrs[d] where flat[n] is False".)
        closed = [n for n in nbrs[d] if not flat[n]]
        flat[closed[rng.integers(len(closed))]] = True
        ends = dead_ends(grid)       # recount (cheap: a few numpy operations)
    return grid


class Ship:
    """A finished ship layout plus the lookup structures the rest of the code
    needs. Build one with `Ship.generate(D, rng)`."""

    def __init__(self, grid):
        # `self` is Python's explicit version of C++'s `this`.
        self.grid = np.asarray(grid, dtype=bool)
        if self.grid.ndim != 2 or self.grid.shape[0] != self.grid.shape[1]:
            raise ValueError("ship grid must be square")
        self.D = self.grid.shape[0]
        self.open_flat = self.grid.ravel()              # same data, indexed by flat id
        self.open_cells = np.flatnonzero(self.open_flat)  # flat ids of all open cells
        is_open = self.open_flat.tolist()  # plain Python list: faster to index in loops
        # Adjacency list: neighbors[i] = open neighbours of cell i, or [] if i
        # is blocked. Like a std::vector<std::vector<int>>.
        self.neighbors = [
            [n for n in nbrs if is_open[n]] if is_open[i] else []
            for i, nbrs in enumerate(grid_neighbors(self.D))   # enumerate gives (index, item)
        ]

    # A classmethod is a static factory: Ship.generate(50, rng) returns a new Ship.
    @classmethod
    def generate(cls, D, rng):
        return cls(generate_layout(D, rng))

    # @property lets you write ship.n_open (no parentheses) for a computed value.
    @property
    def n_open(self):
        return len(self.open_cells)

    def coords(self, cell):
        """Flat index -> (row, col). divmod returns (quotient, remainder)."""
        return divmod(cell, self.D)

    def index(self, r, c):
        """(row, col) -> flat index."""
        return r * self.D + c

    def distances_from(self, source):
        """Breadth-first search (BFS) from `source`: the number of moves to
        reach every cell through open cells (inf for blocked or unreachable
        cells). BFS explores cells in order of distance, so the first time a
        cell is reached is along a shortest path.

        Used for Bot 4's A* heuristic (distance to the button) and for the
        distance columns in the experiment CSV."""
        dist = [float("inf")] * (self.D * self.D)
        dist[source] = 0
        frontier = deque([source])           # FIFO queue of cells to expand
        while frontier:
            cur = frontier.popleft()
            d = dist[cur] + 1
            for n in self.neighbors[cur]:
                if dist[n] == float("inf"):  # not reached yet
                    dist[n] = d
                    frontier.append(n)
        return dist

    def render(self, marks=None):
        """ASCII picture for debugging: '#' blocked, '.' open, plus any
        single-character marks, e.g. {bot_cell: 'B', button: 'X'}."""
        marks = marks or {}       # `or` gives {} when marks is None
        rows = []
        for r in range(self.D):
            row = []
            for c in range(self.D):
                i = r * self.D + c
                # dict.get(key, default): the mark if there is one, else '.' or '#'
                row.append(marks.get(i, "." if self.open_flat[i] else "#"))
            rows.append("".join(row))
        return "\n".join(rows)

    def __str__(self):
        """Called by print(ship), like overloading operator<< in C++."""
        return self.render()
