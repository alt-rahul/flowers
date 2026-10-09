from ship import Ship


# a small ship drawn by hand, only used by the tests: '#' is a wall, '.' is open
def ship_from_rows(rows):
    ship = Ship(len(rows))
    for r in range(len(rows)):
        for c in range(len(rows[r])):
            ship.grid[r][c].is_open = rows[r][c] != "#"
    ship.find_neighbors()
    return ship
