// planning.hpp: the search algorithms the planners use.
//
// WHAT'S IN HERE
//   bfs_path             shortest path that avoids some cells (Bots 1, 2, 3)
//   astar_path           cheapest path when cells have different costs (Bot 4)
//   manhattan_distances  the A* heuristic Bot 4 uses
//   bfs_distances        distance from one cell to all others, avoiding some cells
//   fire_distances       how soon the fire could POSSIBLY reach each cell
//   fireproof_path       a path the fire provably cannot catch (certain-win check)
//   with_neighbors       "the fire plus every cell next to it" (Bot 3's buffer)
//
// KEY FACTS THAT MAKE THESE ALGORITHMS CORRECT
//   1. The fire only grows. A burning cell never stops burning.
//   2. The fire moves at most ONE cell per step, whatever q is.
#pragma once

#include <vector>

#include "common.hpp"

// Shortest path from `start` to `goal` (both included) that never enters a
// cell with blocked[cell] == 1. The start cell is never treated as blocked:
// the bot is already standing there. Returns an EMPTY path if there is none.
Path bfs_path(const Adjacency& neighbors, int start, int goal, const Mask& blocked);

// Cheapest path from `start` to `goal` (both included), where ENTERING cell c
// costs step_cost[c] (COST_INF = never enter). `heuristic[c]` estimates the
// cost still to go from c; it must never overestimate it. Returns an empty
// path if every route is impassable.
Path astar_path(const Adjacency& neighbors, int start, int goal,
                const std::vector<double>& step_cost, const std::vector<int>& heuristic);

// |row - goal row| + |col - goal col| for every cell of a D x D grid: the
// number of moves to `goal` if there were no walls at all.
std::vector<int> manhattan_distances(int D, int goal);

// Number of moves from `source` to every cell, avoiding blocked cells
// (INF if unreachable). The source itself is never treated as blocked.
std::vector<int> bfs_distances(const Adjacency& neighbors, int source, const Mask& blocked);

// Multi-source BFS from every burning cell: the fewest fire updates needed
// to reach each cell (INF if unreachable). Because the fire moves at most
// one cell per update, a cell at distance d CANNOT be burning before d more
// updates have happened, no matter what q is.
std::vector<int> fire_distances(const Adjacency& neighbors, const std::vector<int>& burning_cells,
                                int n_cells);

// The shortest path that stays ahead of even the fastest possible fire
// (as if q = 1), or an empty path if there is none. If such a path exists,
// a bot that follows it is CERTAIN to win.
Path fireproof_path(const Adjacency& neighbors, int start, int goal,
                    const std::vector<int>& fire_dist);

// The cells in `mask` plus their up/down/left/right neighbours.
Mask with_neighbors(const Mask& mask, int D);
