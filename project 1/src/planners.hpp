// planners.hpp: one function per way of choosing a path.
//
// EVERY PLANNER HAS THE SAME SHAPE
//   Path planner(ship, pos, button, burning, q, options)
//   It gets the ship, the bot's position, the button, the cells burning right
//   now and the flammability q, and returns a path from `pos` to `button`
//   (an empty path if no route avoids the fire). A Bot (bots.hpp) just calls
//   its planner and walks along the result, so the four bots differ only in
//   which planner they use and whether they replan:
//
//     Bot 1  avoid_fire, planned once at the start (only the first fire cell
//            is burning then) and never again
//     Bot 2  avoid_fire, replanned every step
//     Bot 3  avoid_fire_and_neighbors, replanned every step; when no path
//            avoids the fire's neighbours it falls back to avoid_fire
//     Bot 4  avoid_predicted_fire, replanned every step (A*, see below)
//
// BOT 4'S IDEA: A RACE BETWEEN THE BOT AND THE FIRE
//   The bot moves one cell per step. Along a single route, the fire's front
//   moves one cell per step with probability q (the next cell has one
//   burning neighbour, which gets one q-coin per step). So in k steps the
//   front advances Binomial(k, q) cells. For every cell we compare
//       k = how many steps the bot needs to get there (BFS from the bot)
//       d = how many cells the fire must travel to get there (BFS from the fire)
//   If P(the fire advances at least d cells in k steps) > threshold, we
//   assume the cell WILL be on fire by the time we arrive: "predicted fire".
//
//   Then Bot 4 runs A* from the bot to the button where entering a cell costs
//       infinity       if it is burning right now (never entered)
//       1 + penalty    if it is predicted fire
//       1              otherwise
//   with the Manhattan distance to the button as the heuristic. So the bot
//   takes a detour around predicted fire when the detour is shorter than the
//   penalty, and goes through it only when every alternative is worse.
//
//   Along one route the race is exact. The real fire can also arrive by
//   other routes (loops, other burning cells), which only makes it faster,
//   so the real probability is never lower than the race's: the model is a
//   slightly optimistic lower bound.
#pragma once

#include <string>
#include <vector>

#include "common.hpp"
#include "ship.hpp"

// Settings a planner may use. Bots 1-3 ignore them; Bot 4 reads all four.
// The values after `=` are the defaults, so `BotOptions options;` gives the
// standard Bot 4.
struct BotOptions {
    double threshold = 0.6;            // "predicted fire" if P(fire first) > threshold
    double penalty = 20.0;             // extra cost of stepping into predicted fire
    bool lookahead = true;             // false: only look one step ahead (for comparison)
    std::string fire_metric = "maze";  // "manhattan": ignore walls when measuring the fire's distance
};

// Bots 1 and 2: shortest path to the button that never enters a burning cell.
Path avoid_fire(const Ship& ship, int pos, int button, const Mask& burning, double q,
                const BotOptions& options);

// Bot 3: shortest path that avoids the fire AND every cell next to it; if no
// such path exists, fall back to avoid_fire (Bot 2's planner).
Path avoid_fire_and_neighbors(const Ship& ship, int pos, int button, const Mask& burning,
                              double q, const BotOptions& options);

// Bot 4: A* with burning cells impassable and predicted-fire cells costing
// 1 + penalty, guided by the Manhattan distance to the button.
Path avoid_predicted_fire(const Ship& ship, int pos, int button, const Mask& burning, double q,
                          const BotOptions& options);

// The cells Bot 4 treats as "will be on fire" (1 = predicted fire).
// With options.lookahead = false it uses the literal one-step rule instead:
// a cell is predicted fire if it catches fire NEXT step with probability
// above the threshold, i.e. 1 - (1 - q)^K > threshold, K = burning neighbours.
Mask predicted_fire(const Ship& ship, int pos, int button, const Mask& burning, double q,
                    const BotOptions& options);

// radius[k] = the largest fire distance d for which
//     P(the fire advances at least d cells in k steps) > threshold,
// when the fire's advance in k steps is Binomial(k, q); k = 0 .. max_steps.
// A cell the bot reaches in k steps, and the fire must travel d cells to
// reach, is predicted fire exactly when d <= radius[k]. (-1 if even d = 0
// fails, which only happens when threshold >= 1.)
// The table is computed once per (q, threshold, max_steps) and remembered.
const std::vector<int>& danger_radius(double q, double threshold, int max_steps);

// P(Binomial(k, q) >= d), written out as a sum. The bot uses danger_radius
// (faster); the tests use this to check it.
double fire_arrival_probability(int k, int d, double q);
