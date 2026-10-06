// ship.hpp: the ship layout.
//
// WHAT THIS PART OF THE PROJECT DOES
//   Builds the D x D ship: a maze of open cells (corridors) and blocked cells
//   (walls), using the two-phase procedure from the assignment:
//     Phase 1 (grow_maze): start from one random interior cell and keep
//       opening random blocked cells that touch exactly one open cell. This
//       grows a "perfect maze", a tree with exactly one route between any
//       two cells.
//     Phase 2 (reduce_dead_ends): open random walls next to dead ends until
//       at most half of the dead ends remain. This adds loops, so there are
//       often several routes between two cells, which gives bots choices.
//
// HOW CELLS ARE NAMED
//   Every cell has one integer id, its "flat index": cell = row * D + col.
//   This is exactly how a 2D array is laid out in memory in C/C++
//   (row-major order). Row and column come back with row = cell / D and
//   col = cell % D.
//
// HEADER vs SOURCE
//   This header only DECLARES things: it says what exists and what types
//   go in and out. The matching ship.cpp DEFINES them (contains the code).
//   Other files include this header to call the functions without needing
//   to see their code.
#pragma once

#include <string>
#include <utility>   // std::pair
#include <vector>

#include "common.hpp"

// For every cell of a D x D grid (walls ignored), the flat ids of its
// up/down/left/right neighbours that lie inside the grid. The loop is fast,
// so callers simply recompute it when they need it.
Adjacency grid_neighbors(int D);

// For a mask (e.g. open cells, burning cells), count how many of each cell's
// 4 neighbours are set.
std::vector<int> count_neighbors(const Mask& mask, int D);

// Flat ids of all dead ends: open cells with exactly one open neighbour.
std::vector<int> dead_ends(const Mask& grid, int D);

// The full generation procedure: phase 1 then phase 2.
Mask generate_layout(int D, Rng& rng);

// Phase 1, done literally as the assignment describes it.
Mask grow_maze(int D, Rng& rng);

// Phase 2. Takes `grid` BY VALUE (no &), which means the function gets its
// own copy to modify, and the caller's grid is left alone.
Mask reduce_dead_ends(Mask grid, int D, Rng& rng);

// A finished ship plus the lookup tables the rest of the code needs.
//
// `struct` and `class` are almost the same thing in C++; the only difference
// is that struct members are public by default. A struct with public data
// is the simplest way to bundle related values together, which is all we
// need here.
struct Ship {
    int D = 0;                    // side length of the grid
    Mask grid;                    // grid[cell] = 1 if open, 0 if blocked
    std::vector<int> open_cells;  // flat ids of all open cells, ascending
    Adjacency neighbors;          // neighbors[cell] = OPEN neighbours of cell ([] if blocked)

    // Default constructor: an empty ship. Needed so that other structs can
    // hold a Ship member before it is filled in.
    Ship() = default;

    // Build a Ship from an existing layout. `explicit` stops C++ from
    // silently converting a Mask into a Ship behind your back.
    explicit Ship(Mask open_grid, int side);

    // Generate a random ship. `static` means you call it on the type, not on
    // an object: Ship s = Ship::generate(50, rng);
    static Ship generate(int D, Rng& rng);

    // `const` after a member function's parameter list promises that the
    // function does not change the Ship. The compiler enforces it.
    int n_open() const;
    std::pair<int, int> coords(int cell) const;   // flat id -> (row, col)
    int index(int r, int c) const;                // (row, col) -> flat id

    // Breadth-first search from `source`: number of moves to every cell
    // through open cells (INF if unreachable).
    std::vector<int> distances_from(int source) const;

    // ASCII picture: '#' blocked, '.' open. Handy for debugging.
    std::string render() const;
};
