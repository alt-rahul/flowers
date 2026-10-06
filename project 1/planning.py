"""Search algorithms shared by the bots' planners (see planners.py).

    bfs_path         shortest path avoiding some cells (Bots 1, 2, 3)
    astar_path       cheapest path when cells have different costs (Bot 4)
    manhattan_distances  the A* heuristic used by Bot 4
    bfs_distances    distance from one cell to every other, avoiding some cells
    fire_distances   how soon the fire could possibly reach each cell
    fireproof_path   a path the fire provably cannot catch (certain-win check)
    with_neighbors   the fire plus every cell next to it (Bot 3's buffer)
    risk_astar       the search used by the earlier, forecast-based Bot 4
"""
import heapq
import math
from collections import deque


def bfs_path(neighbors, start, goal, blocked):
    """Shortest path from `start` to `goal` (both included) that avoids every
    cell with blocked[cell] True. The start cell is never treated as blocked,
    since the bot is already standing on it. Returns None if no path exists.

    `blocked` should be a Python list rather than a numpy array: indexing a
    list from Python is several times faster than indexing numpy scalars.
    """
    if start == goal:
        return [start]
    parent = {start: start}
    frontier = deque([start])
    while frontier:
        cur = frontier.popleft()
        for n in neighbors[cur]:
            if n in parent or blocked[n]:
                continue
            parent[n] = cur
            if n == goal:
                path = [n]
                while n != start:
                    n = parent[n]
                    path.append(n)
                path.reverse()
                return path
            frontier.append(n)
    return None


def bfs_distances(neighbors, source, blocked):
    """Distance from `source` to every cell, avoiding blocked cells (inf if
    unreachable). The source itself is never treated as blocked."""
    dist = [math.inf] * len(blocked)
    dist[source] = 0
    frontier = deque([source])
    while frontier:
        cur = frontier.popleft()
        d = dist[cur] + 1
        for n in neighbors[cur]:
            if dist[n] == math.inf and not blocked[n]:
                dist[n] = d
                frontier.append(n)
    return dist


def fire_distances(neighbors, burning, n_cells):
    """Fewest fire updates needed to reach each cell from the cells burning
    now (multi-source BFS; inf if unreachable). The fire advances at most one
    cell per update, so a cell at distance d cannot be burning until at least
    d more updates have happened, whatever q is."""
    dist = [math.inf] * n_cells
    frontier = deque()
    for c in burning:
        dist[c] = 0
        frontier.append(c)
    while frontier:
        cur = frontier.popleft()
        d = dist[cur] + 1
        for n in neighbors[cur]:
            if dist[n] == math.inf:
                dist[n] = d
                frontier.append(n)
    return dist


def fireproof_path(neighbors, start, goal, fire_dist):
    """Shortest path the fire cannot catch even if it spreads at every chance
    (as if q = 1), or None if there is no such path.

    Entering cell c on move k is safe for sure if fire_dist[c] > k: the bot
    stands there during the k-th fire update, and the fire needs at least
    fire_dist[c] updates to arrive. The button only needs fire_dist >= k,
    because it is pressed before the fire moves. A bot that follows such a
    path is certain to win, so whether one exists can be decided with one BFS
    and no simulation. Reaching a cell earlier only helps, so a plain BFS
    that visits each cell at its earliest possible time is enough.
    """
    if start == goal:
        return [start]
    parent = {start: start}
    frontier = [start]
    k = 0
    while frontier:
        k += 1
        nxt = []
        for cur in frontier:
            for n in neighbors[cur]:
                if n in parent:
                    continue
                if n == goal:
                    if fire_dist[n] >= k:
                        parent[n] = cur
                        path = [n]
                        while n != start:
                            n = parent[n]
                            path.append(n)
                        path.reverse()
                        return path
                    continue
                parent[n] = cur  # never safe later either, so don't revisit
                if fire_dist[n] > k:
                    nxt.append(n)
        frontier = nxt
    return None


def with_neighbors(mask, D):
    """Flat mask of the cells in `mask` plus their up/down/left/right neighbours."""
    m = mask.reshape(D, D)
    out = m.copy()
    out[1:, :] |= m[:-1, :]
    out[:-1, :] |= m[1:, :]
    out[:, 1:] |= m[:, :-1]
    out[:, :-1] |= m[:, 1:]
    return out.ravel()


def manhattan_distances(D, goal):
    """|row - goal row| + |col - goal col| for every cell: the number of moves
    from each cell to `goal` if there were no walls at all.

    Walls can only make a route longer and every move costs at least 1, so
    this never overestimates the real remaining cost. That makes it a valid
    (admissible and consistent) A* heuristic."""
    gr, gc = divmod(goal, D)
    return [abs(r - gr) + abs(c - gc) for r in range(D) for c in range(D)]


def astar_path(neighbors, start, goal, step_cost, heuristic):
    """Cheapest path from `start` to `goal` (both included) with A*, where
    entering cell c costs step_cost[c] (math.inf = impassable). Returns None if
    every route is impassable.

    A* always expands the cell with the smallest f = g + h, where g is the
    cheapest known cost from the start and h = heuristic[cell] estimates the
    cost still to go. As long as h never overestimates (and every step costs
    at least as much as h can drop, which holds for Manhattan distance with
    step costs >= 1), the first time the goal is taken off the heap its path
    is the cheapest one. With h = 0 this is Dijkstra's algorithm, and with all
    step costs equal to 1 it finds the same path lengths as BFS.
    """
    if start == goal:
        return [start]
    best = {start: 0.0}                 # cheapest known cost to reach each cell
    parent = {}
    done = set()              # cells whose cheapest cost is final
    heap = [(heuristic[start], 0.0, start)]   # (f, g, cell); heapq pops the smallest
    while heap:
        _, g, cell = heapq.heappop(heap)
        if cell in done:
            continue                    # an outdated heap entry
        if cell == goal:
            path = [cell]
            while cell != start:
                cell = parent[cell]
                path.append(cell)
            path.reverse()
            return path
        done.add(cell)
        for n in neighbors[cell]:
            cost = step_cost[n]
            if cost == math.inf or n in done:
                continue
            new_g = g + cost
            if new_g < best.get(n, math.inf):
                best[n] = new_g
                parent[n] = cell
                heapq.heappush(heap, (new_g + heuristic[n], new_g, n))
    return None


def risk_astar(neighbors, start, goal, heuristic, risk_at, risk_weight):
    """Used by the earlier, forecast-based Bot 4 (planners.forecast_astar).

    A* over (cell, time) states where entering a cell costs
    ``1 + risk_weight * risk``, and the risk depends on *when* the bot gets
    there.

    `risk_at(t)` is a flat float array whose entry c is the risk of standing
    in cell c after t fire updates (inf for cells that are already burning,
    which makes them impassable). Moving into an ordinary cell on move t+1
    means the bot is standing there while the fire makes its (t+1)-th update,
    so it is charged risk_at(t+1). The button is pressed before the fire
    updates, so entering it on move t+1 is charged risk_at(t).

    `heuristic` must be admissible and consistent for unit step costs; the
    BFS distance to the goal through open cells (ignoring fire) is both,
    because every move costs at least 1.

    Pruning: the fire only grows, so the risk of every cell is non-decreasing
    in time. Arriving at a cell earlier and no more expensively is therefore
    never worse, and a state (c, t) can be skipped once some (c, t') with
    t' <= t has been expanded (states of the same cell come off the heap in
    order of cost, since they share the same heuristic value). Waiting in
    place is never useful for the same reason, so it is not considered.
    """
    if start == goal:
        return [start]
    push, pop, inf = heapq.heappush, heapq.heappop, math.inf
    best_g = {(start, 0): 0.0}
    parent = {}
    expanded_at = {}  # cell -> earliest time it was expanded
    heap = [(heuristic[start], heuristic[start], 0.0, 0, start)]
    while heap:
        _, _, g, t, cell = pop(heap)
        if g > best_g[(cell, t)]:
            continue  # stale heap entry
        if cell == goal:
            path = [cell]
            state = (cell, t)
            while state in parent:
                state = parent[state]
                path.append(state[0])
            path.reverse()
            return path
        prev = expanded_at.get(cell)
        if prev is not None and prev <= t:
            continue  # dominated by an earlier, cheaper arrival
        expanded_at[cell] = t
        # .item() on the few cells we touch is much cheaper than converting
        # whole layers to Python lists.
        risk_now = risk_at(t).item
        risk_next = risk_at(t + 1).item
        for n in neighbors[cell]:
            r = risk_now(n) if n == goal else risk_next(n)
            if r == inf:
                continue
            ng = g + 1.0 + risk_weight * r
            key = (n, t + 1)
            old = best_g.get(key)
            if old is None or ng < old:
                best_g[key] = ng
                parent[key] = (cell, t)
                h = heuristic[n]
                push(heap, (ng + h, h, ng, t + 1, n))
    return None
