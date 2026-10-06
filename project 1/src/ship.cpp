// ship.cpp: definitions for ship.hpp.
// Read ship.hpp first: it explains what each function is for.
#include "ship.hpp"

#include <deque>       // std::deque: double-ended queue, used as the BFS queue
#include <stdexcept>   // std::invalid_argument, an exception type

Adjacency grid_neighbors(int D) {
    // `Adjacency nbrs(D * D);` creates a vector of D*D empty inner vectors.
    Adjacency nbrs(D * D);
    for (int r = 0; r < D; ++r) {
        for (int c = 0; c < D; ++c) {
            // A REFERENCE (`&`) is another name for an existing object. Here
            // `cell` IS nbrs[r * D + c], so push_back adds to that inner vector.
            std::vector<int>& cell = nbrs[r * D + c];
            if (r > 0) cell.push_back((r - 1) * D + c);      // above
            if (r < D - 1) cell.push_back((r + 1) * D + c);  // below
            if (c > 0) cell.push_back(r * D + c - 1);        // left
            if (c < D - 1) cell.push_back(r * D + c + 1);    // right
        }
    }
    return nbrs;  // returning a vector is cheap: C++ moves it, it doesn't copy it
}

std::vector<int> count_neighbors(const Mask& mask, int D) {
    // `const Mask& mask`: pass by CONST REFERENCE. The function reads the
    // caller's mask directly (no copy, so it's fast) and promises not to
    // change it. This is the usual way to pass big objects you only read.
    std::vector<int> count(D * D, 0);  // D*D zeros
    for (int r = 0; r < D; ++r) {
        for (int c = 0; c < D; ++c) {
            int n = 0;
            if (r > 0 && mask[(r - 1) * D + c]) ++n;
            if (r < D - 1 && mask[(r + 1) * D + c]) ++n;
            if (c > 0 && mask[r * D + c - 1]) ++n;
            if (c < D - 1 && mask[r * D + c + 1]) ++n;
            count[r * D + c] = n;
        }
    }
    return count;
}

std::vector<int> dead_ends(const Mask& grid, int D) {
    std::vector<int> count = count_neighbors(grid, D);
    std::vector<int> ends;
    for (int cell = 0; cell < D * D; ++cell) {
        if (grid[cell] && count[cell] == 1) ends.push_back(cell);
    }
    return ends;
}

Mask generate_layout(int D, Rng& rng) {
    return reduce_dead_ends(grow_maze(D, rng), D, rng);
}

Mask grow_maze(int D, Rng& rng) {
    // Exceptions: `throw` stops the function and reports an error to whoever
    // called it. Nothing after the `throw` line runs.
    if (D < 3) throw std::invalid_argument("D must be at least 3 so the ship has an interior");

    Mask is_open(D * D, 0);   // start with every cell blocked

    // Open a random INTERIOR cell (rows and columns 1..D-2).
    int r = random_int(rng, 1, D - 1);
    int c = random_int(rng, 1, D - 1);
    is_open[r * D + c] = 1;

    // Then follow the assignment's steps literally:
    //   1. find every blocked cell with exactly one open neighbour,
    //   2. pick one of them at random and open it,
    //   3. repeat until there are none left.
    // Rescanning the whole grid every round is O(D^4) in total. For a 50 x 50
    // ship that is about 15 milliseconds, which is fine, so we keep the code
    // simple instead of updating the candidate list incrementally (opening a
    // cell only changes its 4 neighbours' counts, so that would be O(D^2)).
    while (true) {
        std::vector<int> count = count_neighbors(is_open, D);
        std::vector<int> candidates;
        for (int cell = 0; cell < D * D; ++cell) {
            if (!is_open[cell] && count[cell] == 1) candidates.push_back(cell);
        }
        if (candidates.empty()) break;   // nothing left to open: phase 1 is done
        int pick = random_int(rng, 0, static_cast<int>(candidates.size()));
        // static_cast<int>(...) converts the vector's size (an unsigned type)
        // to a plain int explicitly, so the compiler doesn't warn about mixing them.
        is_open[candidates[pick]] = 1;
    }
    return is_open;
}

Mask reduce_dead_ends(Mask grid, int D, Rng& rng) {
    const Adjacency nbrs = grid_neighbors(D);
    std::vector<int> ends = dead_ends(grid, D);
    const double target = ends.size() / 2.0;   // "cut by at least half"
    while (ends.size() > target) {
        int d = ends[random_int(rng, 0, static_cast<int>(ends.size()))];
        // Every dead end has at least one blocked in-bounds neighbour (it has
        // 2-4 neighbours on the grid and only one of them is open), so
        // `closed` is never empty.
        std::vector<int> closed;
        for (int n : nbrs[d]) {
            if (!grid[n]) closed.push_back(n);
        }
        grid[closed[random_int(rng, 0, static_cast<int>(closed.size()))]] = 1;
        ends = dead_ends(grid, D);   // recount after each change
    }
    return grid;
}

// ---- Ship member functions ------------------------------------------------
// `Ship::` in front of a name means "the member of Ship called ...".

// The part after the colon is the MEMBER INITIALIZER LIST: it sets the
// members directly before the constructor body runs. std::move hands over
// the vector's memory instead of copying it.
Ship::Ship(Mask open_grid, int side) : D(side), grid(std::move(open_grid)) {
    for (int cell = 0; cell < D * D; ++cell) {
        if (grid[cell]) open_cells.push_back(cell);
    }
    const Adjacency all = grid_neighbors(D);
    neighbors.assign(D * D, {});   // D*D empty lists
    for (int cell = 0; cell < D * D; ++cell) {
        if (!grid[cell]) continue;               // blocked cells keep an empty list
        for (int n : all[cell]) {
            if (grid[n]) neighbors[cell].push_back(n);
        }
    }
}

Ship Ship::generate(int D, Rng& rng) {
    return Ship(generate_layout(D, rng), D);
}

int Ship::n_open() const {
    return static_cast<int>(open_cells.size());
}

std::pair<int, int> Ship::coords(int cell) const {
    return {cell / D, cell % D};   // integer division and remainder
}

int Ship::index(int r, int c) const {
    return r * D + c;
}

std::vector<int> Ship::distances_from(int source) const {
    // Breadth-first search (BFS): explore cells in order of distance from
    // the source using a first-in-first-out queue. The first time a cell is
    // reached, it is reached along a shortest path.
    std::vector<int> dist(D * D, INF);
    dist[source] = 0;
    std::deque<int> frontier = {source};
    while (!frontier.empty()) {
        int cur = frontier.front();
        frontier.pop_front();
        int d = dist[cur] + 1;
        for (int n : neighbors[cur]) {
            if (dist[n] == INF) {   // not reached yet
                dist[n] = d;
                frontier.push_back(n);
            }
        }
    }
    return dist;
}

std::string Ship::render() const {
    std::string out;
    for (int r = 0; r < D; ++r) {
        for (int c = 0; c < D; ++c) out += grid[r * D + c] ? '.' : '#';  // ?: is "if ? then : else"
        out += '\n';
    }
    return out;
}
