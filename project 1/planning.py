"""Search algorithms the bots' planners use (see planners.py).

    bfs_path           shortest path avoiding some tiles (Bots 1, 2, 3)
    astar_path         cheapest path when tiles have different costs (Bot 4)
    manhattan_distance the A* heuristic h(n) Bot 4 uses
    bfs_distances      distance from one tile to every other, avoiding some tiles
    fire_distances     how soon the fire could possibly reach each tile
    fireproof_path     a path the fire provably cannot catch (certain-win check)
    with_neighbors     some tiles plus every tile next to them (Bot 3's buffer)

The searches follow the pseudocode from lecture: a fringe of states still to
explore, a closed set of states already explored, and prev[child] = the state
we reached the child from (prev[start] = None), which is followed backwards to
rebuild the path at the end. A state is a tile position (row, col).

"Restricted" tiles are given as a set of positions. Distance maps are 2D
lists: dist[r][c], with math.inf meaning "can't get there".
"""
import heapq
import math
from collections import deque

from ship import grid_neighbors


def follow_prev(prev, goal):
    """Rebuild the path to `goal`: follow prev back until we reach the start
    (whose prev is None), then reverse."""
    path = []
    state = goal
    while state is not None:
        path.append(state)
        state = prev[state]
    path.reverse()
    return path


def bfs_path(ship, start, goal, restricted):
    """Shortest path from `start` to `goal` (both included) that never enters a
    tile in `restricted`. Returns None if there is no such path.

    GraphSearch with a queue as the fringe (BFS): the oldest state comes off
    first, so states come off in order of distance from the start, and the
    first time the goal comes off it is along a shortest path.

    One addition to the notes: a child that is already in prev has already
    been added to the fringe, so it isn't added again. That way every tile is
    on the fringe at most once and keeps the first tile it was reached from."""
    fringe = deque([start])
    closed_set = set()
    prev = {start: None}
    while fringe:
        current_state = fringe.popleft()
        if current_state == goal:
            return follow_prev(prev, goal)
        for child in ship.neighbors(current_state):
            if child not in restricted and child not in closed_set and child not in prev:
                fringe.append(child)
                prev[child] = current_state
        closed_set.add(current_state)
    return None


def bfs_distances(ship, start, restricted=None):
    """dist[r][c] = the number of moves from `start` to (r, c), avoiding the
    tiles in `restricted` (math.inf if it can't be reached).

    The same BFS as bfs_path, but with no goal: it runs until the fringe is
    empty and records dist[child] = dist[current_state] + 1. A tile whose dist
    is no longer math.inf has already been added to the fringe."""
    if restricted is None:
        restricted = set()
    dist = [[math.inf] * ship.D for r in range(ship.D)]
    dist[start[0]][start[1]] = 0
    fringe = deque([start])
    while fringe:
        current_state = fringe.popleft()
        r, c = current_state
        for child in ship.neighbors(current_state):
            cr, cc = child
            if dist[cr][cc] == math.inf and child not in restricted:
                dist[cr][cc] = dist[r][c] + 1
                fringe.append(child)
    return dist


def fire_distances(ship, fire_cells, ignore_walls=False):
    """dist[r][c] = how many updates the fire needs, at the very least, to reach
    (r, c) from the tiles burning now. A BFS that starts with every burning
    tile on the fringe at once.

    The fire moves at most one tile per update, whatever q is, so a tile at
    distance d cannot be burning until at least d more updates have happened.

    With ignore_walls=True the BFS also crosses walls, which gives the plain
    Manhattan distance to the nearest fire (only used to compare variants of
    Bot 4)."""
    D = ship.D
    dist = [[math.inf] * D for r in range(D)]
    fringe = deque()
    for r, c in fire_cells:
        dist[r][c] = 0
        fringe.append((r, c))
    while fringe:
        r, c = fringe.popleft()
        if ignore_walls:
            children = grid_neighbors(D, r, c)
        else:
            children = ship.neighbors((r, c))
        for cr, cc in children:
            if dist[cr][cc] == math.inf:
                dist[cr][cc] = dist[r][c] + 1
                fringe.append((cr, cc))
    return dist


def fireproof_path(ship, start, goal, fire_dist):
    """The shortest path the fire cannot catch even if it spreads at every
    chance (as if q = 1), or None if there is no such path.

    Entering tile (r, c) on move k is safe for sure if fire_dist[r][c] > k: the
    bot stands there while the fire makes its k-th update, and the fire needs at
    least fire_dist[r][c] updates to arrive. The button only needs >= k,
    because it is pressed before the fire moves.

    A BFS that goes one move (k) at a time: `fringe` holds the tiles reached
    in k - 1 moves, `next_fringe` collects the ones reached in k. Reaching a
    tile earlier is never worse, so each tile is looked at once: if it isn't
    safe the first time we can reach it, it never will be."""
    if start == goal:
        return [start]
    prev = {start: None}
    fringe = [start]
    k = 0
    while fringe:
        k += 1
        next_fringe = []
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
                prev[child] = current_state   # seen: never safe later either
                if fire_dist[cr][cc] > k:
                    next_fringe.append(child)
        fringe = next_fringe
    return None


def with_neighbors(ship, cells):
    """The set of `cells` plus every tile next to one of them."""
    out = set(cells)
    for r, c in cells:
        out.update(grid_neighbors(ship.D, r, c))
    return out


def manhattan_distance(a, b):
    """|row difference| + |column difference|: the number of moves from a to b
    if there were no walls. Removing the walls is a relaxation of the problem,
    so this never overestimates the real distance (it is admissible)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_path(ship, start, goal, cost):
    """Cheapest path from `start` to `goal` (both included) with A*, where
    entering tile (r, c) costs cost[r][c] (math.inf = never enter). Returns
    None if every route is impassable.

    This is uniform cost search with priority(n) = f(n) = g(n) + h(n):
        g(n) = dist[n], the cheapest cost found so far from the start to n
        h(n) = manhattan_distance(n, goal), an estimate of the cost still to go
    Every step costs at least 1 and h drops by at most 1 per step, so
    h(n) <= cost(n, n') + h(n'): h is consistent, hence admissible, and the
    first time the goal comes off the fringe its path is the cheapest one.
    With h = 0 this would be plain uniform cost search.

    The fringe is a heap of (priority, g, position) tuples. Python's heapq
    has no add_or_update, so when a child gets a cheaper dist it is simply
    added again; the old copy has a higher priority, and when it comes off
    later it changes nothing. Tuples are compared one entry at a time, so ties
    in priority are broken by g and then by position, which makes the search
    give the same path every time."""
    fringe = [(manhattan_distance(start, goal), 0.0, start)]
    prev = {start: None}
    dist = {start: 0.0}
    while fringe:
        priority, g, curr = heapq.heappop(fringe)
        if curr == goal:
            return follow_prev(prev, goal)
        for child in ship.neighbors(curr):
            cr, cc = child
            if cost[cr][cc] == math.inf:      # not a valid child (burning)
                continue
            dist_to_child = dist[curr] + cost[cr][cc]
            if child not in dist or dist_to_child < dist[child]:
                dist[child] = dist_to_child
                prev[child] = curr
                heapq.heappush(fringe, (dist[child] + manhattan_distance(child, goal),
                                        dist[child], child))
    return None
