"""The ship: a D x D grid of Tile objects, and how to generate one.

A position is a (row, col) tuple, and ship.grid[r][c] is the tile at row r,
column c.
"""


class Tile:
    def __init__(self):
        self.is_open = False
        self.on_fire = False
        self.has_bot = False
        self.has_button = False
        self.neighbors = []   # positions of the open tiles next to this one


def grid_neighbors(D, r, c):
    """The positions up, down, left and right of (r, c) that are inside the grid."""
    neighbors = []
    if r > 0:
        neighbors.append((r - 1, c))
    if r < D - 1:
        neighbors.append((r + 1, c))
    if c > 0:
        neighbors.append((r, c - 1))
    if c < D - 1:
        neighbors.append((r, c + 1))
    return neighbors


def remove_from_list(items, item):
    """Remove item from the list by moving the last item into its place."""
    i = items.index(item)
    items[i] = items[-1]
    items.pop()


class Ship:
    def __init__(self, D):
        self.D = D
        self.grid = [[Tile() for c in range(D)] for r in range(D)]   # every tile starts blocked

    def tile(self, pos):
        r, c = pos
        return self.grid[r][c]

    def neighbors(self, pos):
        return self.tile(pos).neighbors

    def open_cells(self):
        cells = []
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].is_open:
                    cells.append((r, c))
        return cells

    def fire_cells(self):
        fire = set()
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].on_fire:
                    fire.add((r, c))
        return fire

    def count_open_neighbors(self, r, c):
        count = 0
        for nr, nc in grid_neighbors(self.D, r, c):
            if self.grid[nr][nc].is_open:
                count += 1
        return count

    def dead_ends(self):
        """Open tiles with exactly one open neighbour."""
        ends = []
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].is_open and self.count_open_neighbors(r, c) == 1:
                    ends.append((r, c))
        return ends

    def grow_maze(self, rng):
        """Phase 1: open a random interior tile, then keep opening a random
        blocked tile that has exactly one open neighbour until there are none."""
        candidates = []   # blocked tiles with exactly one open neighbour

        r, c = rng.integers(1, self.D - 1, size=2)   # rows and columns 1 to D-2
        r, c = int(r), int(c)
        while True:
            self.grid[r][c].is_open = True
            if (r, c) in candidates:
                remove_from_list(candidates, (r, c))

            # Opening (r, c) only changes the tiles next to it.
            for nr, nc in grid_neighbors(self.D, r, c):
                if not self.grid[nr][nc].is_open:
                    count = self.count_open_neighbors(nr, nc)
                    if count == 1:
                        candidates.append((nr, nc))
                    elif count == 2:
                        remove_from_list(candidates, (nr, nc))

            if len(candidates) == 0:
                break
            r, c = candidates[rng.integers(len(candidates))]

    def reduce_dead_ends(self, rng):
        """Phase 2: open a random blocked tile next to a random dead end, until
        at most half of the original dead ends are left."""
        ends = self.dead_ends()
        target = len(ends) / 2
        while len(ends) > target:
            r, c = ends[rng.integers(len(ends))]
            blocked = []
            for nr, nc in grid_neighbors(self.D, r, c):
                if not self.grid[nr][nc].is_open:
                    blocked.append((nr, nc))
            nr, nc = blocked[rng.integers(len(blocked))]
            self.grid[nr][nc].is_open = True
            ends = self.dead_ends()

    def find_neighbors(self):
        """Save each open tile's open neighbours. Walls never change after the
        ship is built, so this only has to be done once."""
        for r in range(self.D):
            for c in range(self.D):
                tile = self.grid[r][c]
                tile.neighbors = []
                if tile.is_open:
                    for nr, nc in grid_neighbors(self.D, r, c):
                        if self.grid[nr][nc].is_open:
                            tile.neighbors.append((nr, nc))

    def clear(self):
        """Take away the bot, the button and the fire, keeping the walls."""
        for row in self.grid:
            for tile in row:
                tile.on_fire = False
                tile.has_bot = False
                tile.has_button = False


def generate_ship(D, rng):
    ship = Ship(D)
    ship.grow_maze(rng)
    ship.reduce_dead_ends(rng)
    ship.find_neighbors()
    return ship


def ship_from_rows(rows):
    """A small hand-drawn ship for the tests: '#' is a wall, '.' is open."""
    ship = Ship(len(rows))
    for r in range(len(rows)):
        for c in range(len(rows[r])):
            ship.grid[r][c].is_open = rows[r][c] != "#"
    ship.find_neighbors()
    return ship
