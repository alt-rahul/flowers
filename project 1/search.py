"""The search algorithms, written from the lecture pseudocode.

fringe:      the states still to explore
closed_set:  the states already explored
prev:        prev[child] = the state we reached the child from (prev[start] = None)

A state is a tile position (row, col).
"""
import heapq
import math
from collections import deque


def follow_prev(prev, goal):
    """Rebuild the path by following prev back from the goal to the start."""
    path = []
    state = goal
    while state is not None:
        path.append(state)
        state = prev[state]
    path.reverse()
    return path


def bfs(ship, start, goal, restricted):
    """Shortest path from start to goal that never enters a restricted tile,
    or None if there isn't one.

    GraphSearch with a queue as the fringe. One extra check compared to the
    notes: a child that is already in prev is already on the fringe, so it
    isn't added again."""
    fringe = deque([start])
    closed_set = set()
    prev = {start: None}
    while len(fringe) > 0:
        current_state = fringe.popleft()
        if current_state == goal:
            return follow_prev(prev, goal)
        for child in ship.neighbors(current_state):
            if child not in restricted and child not in closed_set and child not in prev:
                fringe.append(child)
                prev[child] = current_state
        closed_set.add(current_state)
    return None


def distance_map(ship, starts, restricted):
    """dist[r][c] = the number of moves from the nearest tile in starts to
    (r, c), never entering a restricted tile (math.inf if it can't be reached).

    The same BFS with no goal: it runs until the fringe is empty. For the fire,
    starts is every burning tile at once."""
    dist = [[math.inf] * ship.D for r in range(ship.D)]
    fringe = deque()
    for r, c in starts:
        dist[r][c] = 0
        fringe.append((r, c))
    while len(fringe) > 0:
        current_state = fringe.popleft()
        r, c = current_state
        for child in ship.neighbors(current_state):
            cr, cc = child
            if dist[cr][cc] == math.inf and child not in restricted:
                dist[cr][cc] = dist[r][c] + 1
                fringe.append(child)
    return dist


def manhattan_distance(a, b):
    """The number of moves from a to b if there were no walls."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def a_star(ship, start, goal, cost):
    """Cheapest path from start to goal, where stepping onto tile (r, c) costs
    cost[r][c] (math.inf means never step there). Returns None if there is no path.

    Uniform cost search with priority = g + h, where g = dist[state] is the
    cheapest cost found so far and h is the Manhattan distance to the goal.
    Like the A* in the notes there is no closed list: when a child gets a
    cheaper dist it is just added to the fringe again."""
    fringe = [(manhattan_distance(start, goal), 0.0, start)]   # (priority, g, state)
    prev = {start: None}
    dist = {start: 0.0}
    while len(fringe) > 0:
        priority, g, curr = heapq.heappop(fringe)
        if curr == goal:
            return follow_prev(prev, goal)
        for child in ship.neighbors(curr):
            cr, cc = child
            if cost[cr][cc] == math.inf:
                continue
            dist_to_child = dist[curr] + cost[cr][cc]
            if child not in dist or dist_to_child < dist[child]:
                dist[child] = dist_to_child
                prev[child] = curr
                priority = dist[child] + manhattan_distance(child, goal)
                heapq.heappush(fringe, (priority, dist[child], child))
    return None


def fireproof_path(ship, start, goal, fire_dist):
    """A path the fire can't catch even if it spreads at every chance (q = 1),
    or None. fire_dist is the fire's distance map.

    BFS one move at a time: on move k the bot can enter tile c only if
    fire_dist[c] > k, and the button only if fire_dist >= k (it is pressed
    before the fire moves). Reaching a tile earlier is never worse, so each
    tile only has to be looked at once."""
    if start == goal:
        return [start]
    prev = {start: None}
    fringe = [start]   # the tiles reached in k - 1 moves
    k = 0
    while len(fringe) > 0:
        k += 1
        next_fringe = []   # the tiles reached in k moves
        for current_state in fringe:
            for child in ship.neighbors(current_state):
                if child in prev:
                    continue
                cr, cc = child
                if child == goal:
                    if fire_dist[cr][cc] >= k:
                        prev[child] = current_state
                        return follow_prev(prev, goal)
                    continue
                prev[child] = current_state
                if fire_dist[cr][cc] > k:
                    next_fringe.append(child)
        fringe = next_fringe
    return None
