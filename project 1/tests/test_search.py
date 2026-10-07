import heapq
import math

import numpy as np

from search import a_star, bfs, distance_map, manhattan_distance
from ship import generate_ship


def two_random_tiles(ship):
    cells = ship.open_cells()
    np.random.shuffle(cells)
    return cells[0], cells[1]


def is_valid_path(ship, path, start, goal, restricted):
    if path[0] != start or path[-1] != goal:
        return False
    for i in range(len(path) - 1):
        if path[i + 1] not in ship.neighbors(path[i]):
            return False
        if path[i + 1] in restricted:
            return False
    return True


def test_bfs_finds_a_shortest_path():
    for seed in range(10):
        ship = generate_ship(20, seed)
        start, goal = two_random_tiles(ship)
        path = bfs(ship, start, goal, set())
        assert is_valid_path(ship, path, start, goal, set())
        assert len(path) - 1 == distance_map(ship, [start], set())[goal[0]][goal[1]]


def test_bfs_avoids_restricted_tiles():
    for i in range(30):
        ship = generate_ship(15, i)
        start, goal = two_random_tiles(ship)
        restricted = set()
        for pos in ship.open_cells():
            if np.random.random() < 0.2 and pos != goal:
                restricted.add(pos)
        path = bfs(ship, start, goal, restricted)
        if path is not None:
            assert is_valid_path(ship, path, start, goal, restricted)


def all_ones(D):
    cost = []
    for r in range(D):
        cost.append([1.0] * D)
    return cost


def test_a_star_with_equal_costs_finds_a_shortest_path():
    for seed in range(10):
        ship = generate_ship(20, seed)
        start, goal = two_random_tiles(ship)
        cost = all_ones(ship.D)
        path = a_star(ship, start, goal, cost)
        assert is_valid_path(ship, path, start, goal, set())
        assert len(path) - 1 == distance_map(ship, [start], set())[goal[0]][goal[1]]


def cheapest_cost(ship, start, goal, cost):
    """Plain uniform cost search (no heuristic), to check A* against."""
    best = {start: 0.0}
    fringe = [(0.0, start)]
    while len(fringe) > 0:
        g, curr = heapq.heappop(fringe)
        if curr == goal:
            return g
        for child in ship.neighbors(curr):
            step = cost[child[0]][child[1]]
            if step != math.inf and (child not in best or g + step < best[child]):
                best[child] = g + step
                heapq.heappush(fringe, (best[child], child))
    return None


def test_a_star_finds_the_cheapest_path():
    for seed in range(10):
        ship = generate_ship(20, seed)
        start, goal = two_random_tiles(ship)
        # Costs like Bot 4's: mostly 1, some 21, a few that can't be entered.
        cost = all_ones(ship.D)
        for r in range(ship.D):
            for c in range(ship.D):
                roll = np.random.random()
                if roll < 0.05:
                    cost[r][c] = math.inf
                elif roll < 0.3:
                    cost[r][c] = 21.0
        cost[goal[0]][goal[1]] = 1.0
        path = a_star(ship, start, goal, cost)
        expected = cheapest_cost(ship, start, goal, cost)
        if expected is None:
            assert path is None
        else:
            assert is_valid_path(ship, path, start, goal, set())
            total = 0
            for r, c in path[1:]:
                total += cost[r][c]
            assert total == expected


def test_manhattan_distance_never_overestimates():
    ship = generate_ship(20, 1)
    goal = ship.open_cells()[0]
    dist = distance_map(ship, [goal], set())
    for r, c in ship.open_cells():
        assert manhattan_distance((r, c), goal) <= dist[r][c]
