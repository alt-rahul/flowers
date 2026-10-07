"""The ship: a D x D grid of Tile objects, and how to generate one.

HOW A SHIP IS STORED
    ship.grid[r][c] is the Tile at row r, column c (a list of lists).
    A position is a (row, col) tuple, e.g. (3, 7).

    Each Tile knows:
        is_open     open floor (True) or wall (False)
        on_fire     burning right now
        has_bot     the bot is standing here
        has_button  the button is here
        neighbors   the positions of the OPEN tiles next to it
                    (up, down, left, right; no diagonals)

    Walls never change after the ship is generated, so each tile's list of
    open neighbours is worked out once, at the end of Ship.generate().

This file knows nothing about bots or how the fire spreads, so later projects
can reuse it.
"""


class Tile:
    """One cell of the ship."""

    def __init__(self):
        self.is_open = False
        self.on_fire = False
        self.has_bot = False
        self.has_button = False
        self.neighbors = []   # positions of the open tiles next to this one


def grid_neighbors(D, r, c):
    """The positions next to (r, c) that are inside the grid: up, down, left,
    right. Walls are ignored here; this is just the geometry of the grid."""
    out = []
    if r > 0:
        out.append((r - 1, c))   # up
    if r < D - 1:
        out.append((r + 1, c))   # down
    if c > 0:
        out.append((r, c - 1))   # left
    if c < D - 1:
        out.append((r, c + 1))   # right
    return out


class Ship:
    """A D x D grid of tiles. Build a random one with Ship.generate(D, rng)."""

    def __init__(self, D):
        self.D = D
        self.grid = [[Tile() for c in range(D)] for r in range(D)]   # every tile starts as a wall

    @classmethod
    def generate(cls, D, rng):
        """A random ship, built with the two phases from the assignment.
        `rng` is a seeded numpy random generator, so the same seed always
        gives the same ship."""
        ship = cls(D)
        ship.grow_maze(rng)          # phase 1
        ship.reduce_dead_ends(rng)   # phase 2
        ship.find_neighbors()
        return ship

    @classmethod
    def from_rows(cls, rows):
        """A ship drawn as text, one string per row: '#' is a wall, anything
        else is open. Handy for tests, e.g. Ship.from_rows(["#.#", "...", "#.#"])."""
        ship = cls(len(rows))
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                ship.grid[r][c].is_open = ch != "#"
        ship.find_neighbors()
        return ship

    # ---- looking things up --------------------------------------------------

    def tile(self, pos):
        """The Tile at position (r, c)."""
        r, c = pos
        return self.grid[r][c]

    def neighbors(self, pos):
        """Positions of the open tiles next to `pos`."""
        return self.tile(pos).neighbors

    def open_cells(self):
        """Positions of every open tile, row by row."""
        return [(r, c) for r in range(self.D) for c in range(self.D) if self.grid[r][c].is_open]

    def fire_cells(self):
        """The set of positions that are on fire right now."""
        return {(r, c) for r in range(self.D) for c in range(self.D) if self.grid[r][c].on_fire}

    def count_open_neighbors(self, pos):
        r, c = pos
        return sum(1 for nr, nc in grid_neighbors(self.D, r, c) if self.grid[nr][nc].is_open)

    def is_dead_end(self, pos):
        """An open tile with exactly one open neighbour."""
        return self.tile(pos).is_open and self.count_open_neighbors(pos) == 1

    def dead_ends(self):
        """Positions of every dead end, row by row."""
        return [(r, c) for r in range(self.D) for c in range(self.D) if self.is_dead_end((r, c))]

    # ---- generation ---------------------------------------------------------

    def grow_maze(self, rng):
        """Phase 1: open a random interior tile, then keep opening a random
        wall that has exactly one open neighbour (a "candidate"), until there
        are none left.

        Every new tile touches exactly one open tile when it opens, so the open
        tiles form a tree: exactly one route between any two of them, and lots
        of dead ends (a "perfect maze").

        Instead of rescanning the whole grid for candidates every round (about
        D^4 work), we keep the list of candidates up to date: opening a tile
        only changes the open-neighbour counts of the 4 tiles around it.
        """
        D = self.D
        if D < 3:
            raise ValueError("D must be at least 3 so the ship has an interior")
        open_count = [[0] * D for r in range(D)]   # open neighbours of each tile
        candidates = []    # walls with exactly one open neighbour
        where = {}         # position -> its index in `candidates`

        def add(pos):
            where[pos] = len(candidates)
            candidates.append(pos)

        def remove(pos):
            # Take a position out of the middle of the list quickly: move the
            # last entry into its slot, then shorten the list by one.
            i = where.pop(pos)
            last = candidates.pop()
            if i < len(candidates):
                candidates[i] = last
                where[last] = i

        def open_tile(pos):
            r, c = pos
            self.grid[r][c].is_open = True
            if pos in where:                 # it was a candidate; not any more
                remove(pos)
            for nr, nc in grid_neighbors(D, r, c):
                open_count[nr][nc] += 1
                if not self.grid[nr][nc].is_open:
                    if open_count[nr][nc] == 1:     # a wall with exactly 1 open neighbour
                        add((nr, nc))
                    elif open_count[nr][nc] == 2:   # now 2 open neighbours: not a candidate
                        remove((nr, nc))

        # A random interior tile: rows and columns 1 .. D-2.
        r, c = rng.integers(1, D - 1, size=2)
        open_tile((int(r), int(c)))
        while candidates:
            open_tile(candidates[rng.integers(len(candidates))])

    def reduce_dead_ends(self, rng):
        """Phase 2: pick a random dead end and open a random wall next to it,
        until at most half of the original dead ends are left. This adds loops,
        so there are often several routes between two tiles: that is what gives
        the bots choices to make.

        Opening a tile can only change whether that tile and the tiles next to
        it are dead ends, so only those are rechecked after each opening.
        """
        D = self.D
        ends = set(self.dead_ends())
        target = len(ends) / 2
        while len(ends) > target:
            in_order = sorted(ends)                # row by row, like dead_ends()
            r, c = in_order[rng.integers(len(in_order))]
            walls = [(nr, nc) for nr, nc in grid_neighbors(D, r, c) if not self.grid[nr][nc].is_open]
            nr, nc = walls[rng.integers(len(walls))]
            self.grid[nr][nc].is_open = True
            for pos in [(nr, nc)] + grid_neighbors(D, nr, nc):
                if self.is_dead_end(pos):
                    ends.add(pos)
                else:
                    ends.discard(pos)

    def find_neighbors(self):
        """Give every open tile the list of open tiles next to it."""
        for r in range(self.D):
            for c in range(self.D):
                tile = self.grid[r][c]
                if tile.is_open:
                    tile.neighbors = [(nr, nc) for nr, nc in grid_neighbors(self.D, r, c)
                                      if self.grid[nr][nc].is_open]
                else:
                    tile.neighbors = []

    # ---- per-trial state ----------------------------------------------------

    def clear(self):
        """Remove the bot, the button and the fire, keeping the walls."""
        for row in self.grid:
            for tile in row:
                tile.on_fire = False
                tile.has_bot = False
                tile.has_button = False

    def render(self):
        """ASCII picture: '#' wall, '.' open, 'B' bot, 'X' button, 'F' fire."""
        lines = []
        for row in self.grid:
            line = ""
            for tile in row:
                if tile.has_bot:
                    line += "B"
                elif tile.has_button:
                    line += "X"
                elif tile.on_fire:
                    line += "F"
                else:
                    line += "." if tile.is_open else "#"
            lines.append(line)
        return "\n".join(lines)

    def __str__(self):
        """print(ship) shows the ASCII picture."""
        return self.render()
