import numpy as np

from bots import bot2_path, bot3_path, bot4_path, heat_map
from fire import spread_fire
from search import bfs
from ship import generate_ship, check_neighbors
from helpers import ship_from_rows


def corridor():
    """A ship that is one corridor along the top row: (0, 0) to (0, 11)."""
    rows = ["#" * 12] * 12
    rows[0] = "." * 12
    return ship_from_rows(rows)


def start_fire(ship, cells):
    ship.clear()
    for pos in cells:
        ship.tile(pos).on_fire = True


def test_bot3_falls_back_to_bot2():
    # The fire sits in a pocket right next to the only corridor, so every
    # route passes next to it.
    ship = ship_from_rows(["#######",
                           "#######",
                           "###.###",
                           ".......",
                           "#######",
                           "#######",
                           "#######"])
    start_fire(ship, [(2, 3)])
    path = bot3_path(ship, (3, 0), (3, 6))
    assert path == bot2_path(ship, (3, 0), (3, 6))
    assert (3, 3) in path


def test_bot3_avoids_the_tiles_next_to_the_fire_when_it_can():
    for i in range(20):
        ship = generate_ship(20, i)
        cells = ship.open_cells()
        np.random.shuffle(cells)
        start, button, fire = cells[0], cells[1], cells[2]
        start_fire(ship, [fire])
        buffer = {fire}
        for n in check_neighbors(ship.D, fire[0], fire[1]):
            buffer.add(n)
        path = bot3_path(ship, start, button)
        if bfs(ship, start, button, buffer) is not None:
            for pos in path[1:]:
                assert pos not in buffer


def test_heat_is_1_next_to_the_fire_and_drops_by_q():
    ship = corridor()
    start_fire(ship, [(0, 11)])
    heat = heat_map(ship, 0.3)
    assert heat[0][11] == 0                     # burning: no heat, it costs BURNING_COST instead
    assert heat[0][10] == 1                     # next to the fire
    assert abs(heat[0][9] - 0.3) < 1e-9         # one tile further: times q
    assert abs(heat[0][8] - 0.09) < 1e-9        # two tiles further: times q again


def test_a_fast_fire_makes_more_heat_than_a_slow_one():
    ship = generate_ship(20, 1)
    start_fire(ship, [ship.open_cells()[0]])
    slow = heat_map(ship, 0.2)
    fast = heat_map(ship, 0.8)
    for r, c in ship.open_cells():
        assert fast[r][c] >= slow[r][c]


def example_ship():
    """Two routes of 12 moves from (0, 0) to the button at (4, 8): along the
    top, or along the bottom, which passes 2 tiles under the fire at (2, 4)."""
    ship = ship_from_rows(["B........",
                           ".#######.",
                           ".###F###.",
                           ".###.###.",
                           "........X",
                           "#########",
                           "#########",
                           "#########",
                           "#########"])
    start_fire(ship, [(2, 4)])
    return ship


def test_bot4_goes_around_the_heat_when_the_way_around_is_short():
    ship = example_ship()
    plan = bot4_path(ship, (0, 0), (4, 8), 0.3)
    assert (0, 8) in plan          # along the top
    assert (4, 4) not in plan      # not under the fire


def test_bot4_goes_through_the_heat_when_the_way_around_is_long():
    ship = example_ship()
    plan = bot4_path(ship, (4, 2), (4, 8), 0.3)
    assert len(plan) - 1 == 6      # straight along the bottom
    assert (4, 4) in plan


def test_bot4_never_plans_through_fire():
    for i in range(20):
        ship = generate_ship(20, 300 + i)
        cells = ship.open_cells()
        np.random.shuffle(cells)
        start, button, fire = cells[0], cells[1], cells[2]
        start_fire(ship, [fire])
        for t in range(8):
            spread_fire(ship, 0.5)
        if ship.tile(start).on_fire or ship.tile(button).on_fire:
            continue
        plan = bot4_path(ship, start, button, 0.5)
        if bot2_path(ship, start, button) is None:
            assert plan is None    # every route runs through fire: trapped
        else:
            for pos in plan:
                assert not ship.tile(pos).on_fire


def test_bot4_without_a_penalty_takes_a_shortest_path():
    for i in range(20):
        ship = generate_ship(20, 200 + i)
        cells = ship.open_cells()
        np.random.shuffle(cells)
        start, button, fire = cells[0], cells[1], cells[2]
        start_fire(ship, [fire])
        for t in range(5):
            spread_fire(ship, 0.3)
        if ship.tile(start).on_fire or ship.tile(button).on_fire:
            continue
        shortest = bot2_path(ship, start, button)
        plan = bot4_path(ship, start, button, 0.3, 0)
        if shortest is None:
            assert plan is None
        else:
            assert len(plan) == len(shortest)
