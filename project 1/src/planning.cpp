// planning.cpp: definitions for planning.hpp.
#include "planning.hpp"

#include <algorithm>   // std::reverse
#include <cstdlib>     // std::abs
#include <deque>       // std::deque, used as a first-in-first-out queue
#include <functional>  // std::greater
#include <queue>       // std::priority_queue

// Rebuild a path from a "parent" table: parent[cell] = the cell we came from.
// Walk backwards from the goal to the start, then reverse.
// `static` here means this helper is private to this .cpp file.
static Path follow_parents(const std::vector<int>& parent, int start, int goal) {
    Path path;
    int cell = goal;
    path.push_back(cell);
    while (cell != start) {
        cell = parent[cell];
        path.push_back(cell);
    }
    std::reverse(path.begin(), path.end());   // begin()/end() mark the whole vector
    return path;
}

Path bfs_path(const Adjacency& neighbors, int start, int goal, const Mask& blocked) {
    if (start == goal) return {start};   // `{start}` builds a one-element vector

    // parent[c] = -1 means "not reached yet". Reaching a cell for the first
    // time records where we came from.
    std::vector<int> parent(neighbors.size(), -1);
    parent[start] = start;
    std::deque<int> frontier;
    frontier.push_back(start);
    while (!frontier.empty()) {
        int cur = frontier.front();
        frontier.pop_front();
        for (int n : neighbors[cur]) {
            if (parent[n] != -1 || blocked[n]) continue;   // seen already, or not allowed
            parent[n] = cur;
            if (n == goal) return follow_parents(parent, start, goal);
            frontier.push_back(n);
        }
    }
    return {};   // an empty path: the goal can't be reached
}

// ---- A* -------------------------------------------------------------------
//
// A* IN ONE PARAGRAPH
//   Like Dijkstra's algorithm, A* repeatedly takes the cheapest-looking cell
//   off a priority queue and expands it (looks at its neighbours).
//   "Cheapest-looking" is f = g + h: g is the cheapest known cost from the
//   start, h is a guess of the cost still to go. If h never overestimates,
//   the first time the goal comes off the queue we have the cheapest path.
//   With h = 0 this is exactly Dijkstra's algorithm; a good h just makes the
//   search look towards the goal first, so it expands fewer cells.

// One entry in the priority queue: a struct with named fields.
struct QueueEntry {
    double f;   // g + h: estimated total cost of a path through `cell`
    double g;   // cost of the best path found so far from the start to `cell`
    int cell;
};

// The priority queue needs to know how to order entries: smallest f first,
// ties broken by smaller g, then by smaller cell id. A fixed tie-break makes
// the search deterministic: the same input always gives the same path.
// `a > b` here means "a should come out of the queue AFTER b".
bool operator>(const QueueEntry& a, const QueueEntry& b) {
    if (a.f != b.f) return a.f > b.f;
    if (a.g != b.g) return a.g > b.g;
    return a.cell > b.cell;
}

Path astar_path(const Adjacency& neighbors, int start, int goal,
                const std::vector<double>& step_cost, const std::vector<int>& heuristic) {
    if (start == goal) return {start};

    std::vector<double> best(neighbors.size(), COST_INF);   // cheapest known cost to each cell
    std::vector<int> parent(neighbors.size(), -1);
    Mask done(neighbors.size(), 0);                          // cells whose cost is final

    // std::priority_queue normally pops the LARGEST element first. Giving it
    // std::greater<QueueEntry> (which uses our operator>) makes it pop the
    // SMALLEST, i.e. a min-heap.
    std::priority_queue<QueueEntry, std::vector<QueueEntry>, std::greater<QueueEntry>> heap;
    best[start] = 0.0;
    heap.push({static_cast<double>(heuristic[start]), 0.0, start});   // fields in order: f, g, cell

    while (!heap.empty()) {
        QueueEntry entry = heap.top();
        heap.pop();
        int cell = entry.cell;
        double g = entry.g;
        // A cell can be pushed more than once (each time a cheaper way to
        // reach it is found). Only the first, cheapest copy counts.
        if (done[cell]) continue;
        if (cell == goal) return follow_parents(parent, start, goal);
        done[cell] = 1;
        for (int n : neighbors[cell]) {
            double cost = step_cost[n];
            if (cost == COST_INF || done[n]) continue;   // impassable, or already final
            double new_g = g + cost;
            if (new_g < best[n]) {
                best[n] = new_g;
                parent[n] = cell;
                heap.push({new_g + heuristic[n], new_g, n});
            }
        }
    }
    return {};   // every route is impassable
}

std::vector<int> manhattan_distances(int D, int goal) {
    int goal_row = goal / D;
    int goal_col = goal % D;
    std::vector<int> h(D * D);
    for (int r = 0; r < D; ++r) {
        for (int c = 0; c < D; ++c) {
            h[r * D + c] = std::abs(r - goal_row) + std::abs(c - goal_col);
        }
    }
    return h;
}

// ---- distance maps and the certain-win check -------------------------------

std::vector<int> bfs_distances(const Adjacency& neighbors, int source, const Mask& blocked) {
    std::vector<int> dist(blocked.size(), INF);
    dist[source] = 0;
    std::deque<int> frontier;
    frontier.push_back(source);
    while (!frontier.empty()) {
        int cur = frontier.front();
        frontier.pop_front();
        int d = dist[cur] + 1;
        for (int n : neighbors[cur]) {
            if (dist[n] == INF && !blocked[n]) {
                dist[n] = d;
                frontier.push_back(n);
            }
        }
    }
    return dist;
}

std::vector<int> fire_distances(const Adjacency& neighbors, const std::vector<int>& burning_cells,
                                int n_cells) {
    // Same as BFS, but starting from ALL burning cells at once (each at
    // distance 0). Walls still stop the fire; nothing else does.
    std::vector<int> dist(n_cells, INF);
    std::deque<int> frontier;
    for (int c : burning_cells) {
        dist[c] = 0;
        frontier.push_back(c);
    }
    while (!frontier.empty()) {
        int cur = frontier.front();
        frontier.pop_front();
        int d = dist[cur] + 1;
        for (int n : neighbors[cur]) {
            if (dist[n] == INF) {
                dist[n] = d;
                frontier.push_back(n);
            }
        }
    }
    return dist;
}

Path fireproof_path(const Adjacency& neighbors, int start, int goal,
                    const std::vector<int>& fire_dist) {
    // When is entering cell c on move k CERTAINLY safe?
    //   The bot stands on c while the fire makes its k-th update. The fire
    //   needs at least fire_dist[c] updates to arrive. So c is safe for sure
    //   if fire_dist[c] > k.
    //   The button is pressed BEFORE the fire moves, so it only needs
    //   fire_dist[button] >= k.
    // We BFS one layer (one move) at a time, so we always know k. Arriving
    // somewhere earlier is never worse, so each cell is visited at most once.
    if (start == goal) return {start};
    std::vector<int> parent(neighbors.size(), -1);
    parent[start] = start;
    std::vector<int> frontier = {start};
    int k = 0;
    while (!frontier.empty()) {
        k += 1;                       // the move number for cells found in this round
        std::vector<int> next;
        for (int cur : frontier) {
            for (int n : neighbors[cur]) {
                if (parent[n] != -1) continue;
                if (n == goal) {
                    if (fire_dist[n] >= k) {
                        parent[n] = cur;
                        return follow_parents(parent, start, goal);
                    }
                    continue;         // too late for the button now, and it only gets later
                }
                parent[n] = cur;      // mark as seen: if it isn't safe now, it never will be
                if (fire_dist[n] > k) next.push_back(n);
            }
        }
        frontier = next;
    }
    return {};
}

Mask with_neighbors(const Mask& mask, int D) {
    Mask out = mask;   // `=` on a vector makes a full copy
    for (int r = 0; r < D; ++r) {
        for (int c = 0; c < D; ++c) {
            if (!mask[r * D + c]) continue;
            if (r > 0) out[(r - 1) * D + c] = 1;
            if (r < D - 1) out[(r + 1) * D + c] = 1;
            if (c > 0) out[r * D + c - 1] = 1;
            if (c < D - 1) out[r * D + c + 1] = 1;
        }
    }
    return out;
}
