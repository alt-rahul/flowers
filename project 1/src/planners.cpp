// planners.cpp: definitions for planners.hpp. Read planners.hpp first: it
// explains the idea behind each planner.
#include "planners.hpp"

#include <cmath>   // std::pow
#include <map>     // std::map: a sorted dictionary
#include <tuple>   // std::tuple: a fixed-size bundle of values, usable as a map key

#include "planning.hpp"

// ---- Bots 1-3 -----------------------------------------------------------------
//
// The parameters q and options are unnamed here, (double, const BotOptions&):
// these planners don't use them, and leaving the names out tells the
// compiler (and the reader) so, without an "unused parameter" warning.

Path avoid_fire(const Ship& ship, int pos, int button, const Mask& burning, double,
                const BotOptions&) {
    return bfs_path(ship.neighbors, pos, button, burning);
}

Path avoid_fire_and_neighbors(const Ship& ship, int pos, int button, const Mask& burning,
                              double q, const BotOptions& options) {
    Mask buffer = with_neighbors(burning, ship.D);   // fire + every cell next to it
    Path path = bfs_path(ship.neighbors, pos, button, buffer);
    if (path.empty()) {
        // No route avoids the buffer: reuse Bot 2's planner.
        path = avoid_fire(ship, pos, button, burning, q, options);
    }
    return path;
}

// ---- Bot 4 --------------------------------------------------------------------

const std::vector<int>& danger_radius(double q, double threshold, int max_steps) {
    // A STATIC LOCAL VARIABLE is created the first time the function runs and
    // then kept between calls (it lives as long as the program). We use it as
    // a cache: the key is (q, threshold, max_steps), the value is the table.
    // Without it, every move of every trial would rebuild the same table.
    static std::map<std::tuple<double, double, int>, std::vector<int>> cache;
    std::tuple<double, double, int> key(q, threshold, max_steps);
    if (cache.count(key) > 0) return cache[key];

    // Build the binomial distribution one step at a time:
    //     pmf[j] = P(exactly j advances so far)
    // Each extra step, every outcome either stays where it was (chance 1 - q)
    // or moves up by one advance (chance q).
    std::vector<double> pmf(max_steps + 1, 0.0);
    pmf[0] = 1.0;                                  // after 0 steps: 0 advances, for sure
    std::vector<int> radius(max_steps + 1);
    std::vector<double> at_least(max_steps + 1);
    for (int k = 0; k <= max_steps; ++k) {
        if (k > 0) {
            // Go from the top down, so pmf[j - 1] is still last step's value
            // when we use it.
            for (int j = max_steps; j >= 1; --j) pmf[j] = pmf[j] * (1 - q) + pmf[j - 1] * q;
            pmf[0] = pmf[0] * (1 - q);
        }
        // at_least[d] = P(at least d advances) = pmf[d] + pmf[d + 1] + ...,
        // summed from the top down.
        double total = 0.0;
        for (int d = max_steps; d >= 0; --d) {
            total += pmf[d];
            at_least[d] = total;
        }
        // at_least only shrinks as d grows, so the largest d that passes is
        // the last one before the first failure.
        int largest = -1;
        for (int d = 0; d <= max_steps && at_least[d] > threshold; ++d) largest = d;
        radius[k] = largest;
    }
    cache[key] = radius;
    return cache[key];   // a reference into the cache: valid for the whole program
}

double fire_arrival_probability(int k, int d, double q) {
    // P(Binomial(k, q) >= d) = sum over j = d .. k of C(k, j) q^j (1 - q)^(k - j).
    double total = 0.0;
    for (int j = d; j <= k; ++j) {
        // C(k, j) = k! / (j! (k - j)!), built as a running product so no
        // factorial overflows.
        double choose = 1.0;
        for (int i = 1; i <= j; ++i) choose = choose * (k - j + i) / i;
        total += choose * std::pow(q, j) * std::pow(1 - q, k - j);
    }
    return total;
}

Mask predicted_fire(const Ship& ship, int pos, int button, const Mask& burning, double q,
                    const BotOptions& options) {
    const int D = ship.D;
    const int n_cells = D * D;
    Mask danger(n_cells, 0);

    if (!options.lookahead) {
        // The literal one-step rule. Only cells touching the fire can ever
        // pass it, which makes it a thinner version of Bot 3's buffer.
        std::vector<int> k = count_neighbors(burning, D);
        for (int c : ship.open_cells) {
            if (!burning[c] && 1 - std::pow(1 - q, k[c]) > options.threshold) danger[c] = 1;
        }
        return danger;
    }

    std::vector<int> fire_cells;
    for (int c = 0; c < n_cells; ++c) {
        if (burning[c]) fire_cells.push_back(c);
    }
    // How far the fire must travel to each cell: through the maze, or (for
    // comparison) straight across the grid as if there were no walls.
    std::vector<int> fire_dist;
    if (options.fire_metric == "maze") {
        fire_dist = fire_distances(ship.neighbors, fire_cells, n_cells);
    } else {
        fire_dist = fire_distances(grid_neighbors(D), fire_cells, n_cells);
    }
    std::vector<int> bot_dist = bfs_distances(ship.neighbors, pos, burning);
    const std::vector<int>& radius = danger_radius(q, options.threshold, n_cells);

    for (int c : ship.open_cells) {
        if (burning[c] || bot_dist[c] == INF) continue;
        // How many fire updates happen before the bot stands on c: one per
        // move, except that the button is pressed before the fire moves.
        int steps = (c == button) ? bot_dist[c] - 1 : bot_dist[c];
        if (steps < 0) continue;   // only when the bot is already on the button
        if (fire_dist[c] <= radius[steps]) danger[c] = 1;
    }
    return danger;
}

Path avoid_predicted_fire(const Ship& ship, int pos, int button, const Mask& burning, double q,
                          const BotOptions& options) {
    Mask danger = predicted_fire(ship, pos, button, burning, q, options);
    std::vector<double> step_cost(ship.D * ship.D);
    for (int c = 0; c < ship.D * ship.D; ++c) {
        if (burning[c]) {
            step_cost[c] = COST_INF;
        } else if (danger[c]) {
            step_cost[c] = 1.0 + options.penalty;
        } else {
            step_cost[c] = 1.0;
        }
    }
    std::vector<int> heuristic = manhattan_distances(ship.D, button);
    return astar_path(ship.neighbors, pos, button, step_cost, heuristic);
}
