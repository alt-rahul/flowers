// common.hpp: small definitions shared by every other file.
//
// C++ BASICS USED HERE
//   * A ".hpp" file is a HEADER. It holds declarations (names and types) that
//     several ".cpp" files need to know about. Each .cpp file says
//     `#include "common.hpp"`, which literally pastes this file's text in.
//   * `#pragma once` tells the compiler to paste a header only once per .cpp
//     file, even if it is included through several routes.
//   * `using Name = Type;` creates a short alias for a long type name. It is
//     not a new type, just a nickname (like `typedef`).
#pragma once

#include <limits>   // std::numeric_limits: the largest int, infinity, etc.
#include <random>   // std::mt19937_64 and the distributions
#include <vector>   // std::vector: a resizable array

// A Mask is one true/false flag per cell, indexed by flat cell id
// (cell = row * D + col), e.g. "is this cell open?" or "is it burning?".
// We store each flag in an `unsigned char` (one byte, 0 or 1).
// Why not std::vector<bool>? The standard library packs vector<bool> into
// single bits, which makes it slower and behave unlike every other vector,
// so most C++ programmers avoid it.
using Mask = std::vector<unsigned char>;

// A path is a list of flat cell ids, from the start cell to the goal cell.
// An EMPTY path means "no path exists". A real path always has at least one
// cell, so empty is never ambiguous.
using Path = std::vector<int>;

// The adjacency list: neighbors[cell] = the open cells next to `cell`.
// A vector of vectors (a list of lists).
using Adjacency = std::vector<std::vector<int>>;

// The random number generator: the 64-bit "Mersenne Twister", a standard,
// well-tested generator. Seeding it with the same number always reproduces
// the same sequence, which makes every experiment repeatable.
using Rng = std::mt19937_64;

// "Infinity" for integer distances: the largest int. Used for "unreachable".
// `constexpr` means the value is fixed at compile time, like a #define but
// with a type.
constexpr int INF = std::numeric_limits<int>::max();

// "Infinity" for costs, which are doubles. Unlike INF above, this is a real
// IEEE infinity: anything + COST_INF is still COST_INF.
constexpr double COST_INF = std::numeric_limits<double>::infinity();

// A random integer in [lo, hi), i.e. lo included, hi excluded.
// `inline` is required for a function defined in a header, otherwise every
// .cpp file that includes the header would define its own copy and the
// linker would complain about duplicates.
// `Rng& rng` is a REFERENCE: the function uses the caller's generator itself,
// not a copy. That matters: a copy would hand out the same numbers again.
inline int random_int(Rng& rng, int lo, int hi) {
    std::uniform_int_distribution<int> dist(lo, hi - 1);  // this one includes both ends
    return dist(rng);
}

// A random double in [0, 1).
inline double random_unit(Rng& rng) {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    return dist(rng);
}
