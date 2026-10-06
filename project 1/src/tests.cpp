// tests.cpp: checks that everything works.
//
// Run with `make test` (or ./bin/tests after `make`). Each test function
// calls check(condition, description); every failed check is printed, and
// the program exits with code 1 if anything failed.
//
// Real projects usually use a testing library (GoogleTest, Catch2, ...).
// We use a tiny hand-made check() instead, so there is nothing to install.
#include <algorithm>
#include <cmath>
#include <functional>
#include <iostream>
#include <queue>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "bots.hpp"
#include "fire.hpp"
#include "planners.hpp"
#include "planning.hpp"
#include "ship.hpp"
#include "simulation.hpp"

// ---- A minimal test framework ---------------------------------------------

int checks_run = 0;
int checks_failed = 0;

void check(bool ok, const std::string& what) {
    checks_run += 1;
    if (!ok) {
        checks_failed += 1;
        std::cout << "  FAILED: " << what << "\n";
    }
}

// A seeded generator, so every test run sees the same random ships and fires.
Rng make_rng(unsigned a, unsigned b = 0) {
    std::seed_seq seq{a, b};
    return Rng(seq);
}

// A random trial for the bot tests.
Trial make_trial(int D, double q, unsigned seed, int i) {
    Rng rng = make_rng(seed, static_cast<unsigned>(i));
    return Trial::generate(D, q, rng);
}

// A ship that is one corridor along the top row: cells 0 .. n-1.
Ship corridor_ship(int n) {
    Mask grid(n * n, 0);
    for (int c = 0; c < n; ++c) grid[c] = 1;
    return Ship(grid, n);
}

// A mask with just the given cells set, e.g. fire_at(ship, {11}).
Mask fire_at(const Ship& ship, const std::vector<int>& cells) {
    Mask burning(ship.D * ship.D, 0);
    for (int c : cells) burning[c] = 1;
    return burning;
}

bool is_valid_path(const Ship& ship, const Path& path, int start, int goal) {
    if (path.empty() || path.front() != start || path.back() != goal) return false;
    for (size_t i = 0; i + 1 < path.size(); ++i) {
        const std::vector<int>& nb = ship.neighbors[path[i]];
        if (std::find(nb.begin(), nb.end(), path[i + 1]) == nb.end()) return false;
    }
    return true;
}

// Pick `count` different random open cells.
std::vector<int> pick_cells(const Ship& ship, Rng& rng, int count) {
    std::vector<int> cells = ship.open_cells;
    for (int i = 0; i < count; ++i) {
        std::swap(cells[i], cells[random_int(rng, i, static_cast<int>(cells.size()))]);
    }
    return std::vector<int>(cells.begin(), cells.begin() + count);
}

// ---- Ship ---------------------------------------------------------------------

// Phase 1 grows a tree (n cells joined by n - 1 adjacencies) and stops only
// when no blocked cell has exactly one open neighbour.
void test_maze_phase_is_a_maximal_tree() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed);
        const int D = 25;
        Mask grid = grow_maze(D, rng);
        int open = 0, pairs = 0;
        for (int r = 0; r < D; ++r) {
            for (int c = 0; c < D; ++c) {
                int cell = r * D + c;
                if (!grid[cell]) continue;
                open += 1;
                if (r + 1 < D && grid[cell + D]) pairs += 1;   // count each pair once:
                if (c + 1 < D && grid[cell + 1]) pairs += 1;   // only down and right
            }
        }
        check(pairs == open - 1, "phase 1 should produce a tree");
        std::vector<int> count = count_neighbors(grid, D);
        bool candidate_left = false;
        for (int cell = 0; cell < D * D; ++cell) {
            if (!grid[cell] && count[cell] == 1) candidate_left = true;
        }
        check(!candidate_left, "phase 1 should stop only when nothing can be opened");
    }
}

void test_dead_ends_cut_at_least_in_half() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed);
        const int D = 30;
        Mask maze = grow_maze(D, rng);
        Mask ship = reduce_dead_ends(maze, D, rng);
        check(dead_ends(ship, D).size() * 2 <= dead_ends(maze, D).size(),
              "phase 2 should at least halve the dead ends");
        bool only_opened = true;
        for (int cell = 0; cell < D * D; ++cell) {
            if (maze[cell] && !ship[cell]) only_opened = false;
        }
        check(only_opened, "phase 2 should only open cells");
    }
}

void test_all_open_cells_connected() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed);
        Ship ship = Ship::generate(30, rng);
        std::vector<int> dist = ship.distances_from(ship.open_cells[0]);
        bool all_reached = true;
        for (int c : ship.open_cells) {
            if (dist[c] == INF) all_reached = false;
        }
        check(all_reached, "every open cell should be reachable");
    }
}

void test_generation_is_reproducible() {
    Rng a = make_rng(42);
    Rng b = make_rng(42);
    check(generate_layout(20, a) == generate_layout(20, b), "same seed, same ship");
}

void test_neighbors_are_open_and_adjacent() {
    Rng rng = make_rng(3);
    Ship ship = Ship::generate(15, rng);
    for (int cell = 0; cell < ship.D * ship.D; ++cell) {
        if (!ship.grid[cell]) {
            check(ship.neighbors[cell].empty(), "blocked cells have no neighbour list");
            continue;
        }
        for (int n : ship.neighbors[cell]) {
            int dr = std::abs(n / ship.D - cell / ship.D);
            int dc = std::abs(n % ship.D - cell % ship.D);
            check(ship.grid[n] && dr + dc == 1, "neighbours must be open and adjacent");
        }
    }
}

// ---- Fire ---------------------------------------------------------------------

void test_spread_probabilities() {
    std::array<double, 5> p = spread_probabilities(0.3);
    for (int k = 0; k < 5; ++k) {
        check(std::abs(p[k] - (1 - std::pow(0.7, k))) < 1e-12, "1 - (1 - q)^K");
    }
}

// With q = 1 every cell next to the fire must ignite, but a cell that ignites
// this step must not pass the fire on until the next step. So after t updates
// exactly the cells within distance t of the origin are burning.
void test_update_is_synchronous() {
    Ship ship = corridor_ship(15);
    FireTrajectory fire(ship, 1.0, 7, make_rng(0));
    for (int t = 1; t < 8; ++t) {
        Mask burning = fire.burning_at(t);
        bool exact = true;
        for (int cell = 0; cell < 15 * 15; ++cell) {
            bool expected = cell < 15 && std::abs(cell - 7) <= t;
            if (static_cast<bool>(burning[cell]) != expected) exact = false;
        }
        check(exact, "fire should advance exactly one cell per step at q = 1");
    }
}

void test_no_spread_when_q_is_zero() {
    Ship ship = corridor_ship(15);
    FireTrajectory fire(ship, 0.0, 7, make_rng(0));
    Mask burning = fire.burning_at(50);
    int count = 0;
    for (unsigned char b : burning) count += b;
    check(count == 1, "fire should not spread when q = 0");
}

void test_fire_stays_on_open_cells() {
    Rng rng = make_rng(1);
    Ship ship = Ship::generate(20, rng);
    FireTrajectory fire(ship, 0.7, ship.open_cells[0], make_rng(1));
    Mask burning = fire.burning_at(60);
    bool ok = true;
    for (int cell = 0; cell < 20 * 20; ++cell) {
        if (burning[cell] && !ship.grid[cell]) ok = false;
    }
    check(ok, "walls never burn");
}

// A cell with K burning neighbours should ignite with chance 1 - (1 - q)^K.
void test_ignition_rate_matches_formula() {
    const double q = 0.2;
    const int trials = 40000;
    Mask grid(9, 1);   // a 3 x 3 grid, all open; the centre is cell 4
    std::array<double, 5> probs = spread_probabilities(q);
    Rng rng = make_rng(5);
    // Each inner list says which cells are burning around the centre.
    std::vector<std::vector<int>> setups = {{1}, {1, 3}, {1, 3, 5, 7}};
    for (const std::vector<int>& burning_cells : setups) {
        Mask burning(9, 0);
        for (int c : burning_cells) burning[c] = 1;
        int hits = 0;
        for (int i = 0; i < trials; ++i) hits += fire_step(burning, grid, 3, probs, rng)[4];
        double expected = 1 - std::pow(1 - q, static_cast<double>(burning_cells.size()));
        double tolerance = 4 * std::sqrt(expected * (1 - expected) / trials);   // 4 standard errors
        check(std::abs(static_cast<double>(hits) / trials - expected) < tolerance,
              "ignition frequency should match 1 - (1 - q)^K");
    }
}

// A recorded fire, rebuilt with the "replay" constructor, burns exactly the
// same cells at the same times.
void test_recorded_fire_replays_exactly() {
    Rng rng = make_rng(9);
    Ship ship = Ship::generate(20, rng);
    FireTrajectory fire(ship, 0.4, ship.open_cells[5], make_rng(9));
    fire.advance_to(40);
    std::vector<int> times = fire.ignite_times();
    for (int& t : times) {
        if (t == NOT_YET) t = -1;   // the replay constructor's "never"
    }
    FireTrajectory replay(ship, 0.4, times);
    bool same = true;
    for (int t = 0; t <= 40; ++t) {
        if (fire.burning_at(t) != replay.burning_at(t)) same = false;
    }
    check(same, "a replayed fire should match the original");
}

// ---- Search -------------------------------------------------------------------

void test_bfs_path_is_shortest() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed);
        Ship ship = Ship::generate(20, rng);
        std::vector<int> c = pick_cells(ship, rng, 2);
        Path path = bfs_path(ship.neighbors, c[0], c[1], Mask(ship.D * ship.D, 0));
        check(is_valid_path(ship, path, c[0], c[1]), "BFS path should be a valid path");
        check(static_cast<int>(path.size()) - 1 == ship.distances_from(c[0])[c[1]],
              "BFS path should be a shortest path");
    }
}

void test_bfs_path_avoids_blocked_cells() {
    Rng rng = make_rng(0);
    for (int i = 0; i < 30; ++i) {
        Ship ship = Ship::generate(15, rng);
        std::vector<int> c = pick_cells(ship, rng, 2);
        Mask blocked(ship.D * ship.D, 0);
        for (int cell = 0; cell < ship.D * ship.D; ++cell) blocked[cell] = random_unit(rng) < 0.2;
        blocked[c[1]] = 0;
        Path path = bfs_path(ship.neighbors, c[0], c[1], blocked);
        if (path.empty()) continue;
        bool avoids = true;
        for (size_t k = 1; k < path.size(); ++k) {
            if (blocked[path[k]]) avoids = false;
        }
        check(is_valid_path(ship, path, c[0], c[1]) && avoids, "BFS should avoid blocked cells");
    }
}

void test_with_neighbors() {
    Mask mask(25, 0);
    mask[12] = 1;   // centre of a 5 x 5 grid
    Mask out = with_neighbors(mask, 5);
    Mask expected(25, 0);
    for (int c : {7, 11, 12, 13, 17}) expected[c] = 1;
    check(out == expected, "with_neighbors should add the four neighbours");
}

// With every step costing 1, the cheapest path is a shortest path.
void test_astar_with_unit_costs_finds_shortest_paths() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed);
        Ship ship = Ship::generate(20, rng);
        std::vector<int> c = pick_cells(ship, rng, 2);
        std::vector<double> cost(ship.D * ship.D, 1.0);
        Path path = astar_path(ship.neighbors, c[0], c[1], cost, manhattan_distances(ship.D, c[1]));
        check(is_valid_path(ship, path, c[0], c[1]), "A* path should be valid");
        check(static_cast<int>(path.size()) - 1 == ship.distances_from(c[0])[c[1]],
              "A* with unit costs should find a shortest path");
    }
}

// Cheapest cost from start to goal by plain Dijkstra (no heuristic), or -1
// if the goal can't be reached. A slower, simpler algorithm to compare with.
double dijkstra_cost(const Ship& ship, int start, int goal, const std::vector<double>& cost) {
    std::vector<double> best(ship.D * ship.D, COST_INF);
    // A min-heap of (cost so far, cell). std::pair compares the first value
    // first, then the second, so the cheapest pair comes out first.
    std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>,
                        std::greater<std::pair<double, int>>> heap;
    best[start] = 0.0;
    heap.push({0.0, start});
    while (!heap.empty()) {
        std::pair<double, int> top = heap.top();
        heap.pop();
        double g = top.first;
        int cell = top.second;
        if (cell == goal) return g;
        if (g > best[cell]) continue;
        for (int n : ship.neighbors[cell]) {
            if (cost[n] == COST_INF) continue;
            if (g + cost[n] < best[n]) {
                best[n] = g + cost[n];
                heap.push({best[n], n});
            }
        }
    }
    return -1.0;
}

// With mixed costs (like Bot 4's: mostly 1, some 21, a few impassable),
// A* must find a path exactly as cheap as Dijkstra's.
void test_astar_finds_the_cheapest_path() {
    for (unsigned seed = 0; seed < 10; ++seed) {
        Rng rng = make_rng(seed, 1);
        Ship ship = Ship::generate(20, rng);
        std::vector<int> c = pick_cells(ship, rng, 2);
        std::vector<double> cost(ship.D * ship.D);
        for (double& x : cost) {
            double roll = random_unit(rng);
            x = roll < 0.05 ? COST_INF : (roll < 0.3 ? 21.0 : 1.0);
        }
        cost[c[1]] = 1.0;
        Path path = astar_path(ship.neighbors, c[0], c[1], cost, manhattan_distances(ship.D, c[1]));
        double expected = dijkstra_cost(ship, c[0], c[1], cost);
        if (expected < 0) {
            check(path.empty(), "A* should find no path when Dijkstra finds none");
            continue;
        }
        double total = 0.0;
        for (size_t k = 1; k < path.size(); ++k) total += cost[path[k]];
        check(is_valid_path(ship, path, c[0], c[1]), "A* path should be valid");
        check(std::abs(total - expected) < 1e-9, "A* should find the cheapest path");
    }
}

// The heuristic must never overestimate the real distance.
void test_manhattan_never_overestimates() {
    Rng rng = make_rng(1);
    Ship ship = Ship::generate(20, rng);
    int goal = ship.open_cells[0];
    std::vector<int> h = manhattan_distances(ship.D, goal);
    std::vector<int> dist = ship.distances_from(goal);
    bool ok = true;
    for (int c : ship.open_cells) {
        if (h[c] > dist[c]) ok = false;
    }
    check(ok, "Manhattan distance should never exceed the maze distance");
}

// ---- Bot 4's race model --------------------------------------------------------

// The lookup table must agree with the binomial formula for every (k, d).
void test_danger_radius_matches_the_binomial_formula() {
    for (double q : {0.1, 0.3, 0.7}) {
        for (double threshold : {0.3, 0.6, 0.9}) {
            const std::vector<int>& radius = danger_radius(q, threshold, 40);
            bool ok = true;
            for (int k = 0; k <= 40; ++k) {
                for (int d = 1; d <= k + 1; ++d) {
                    double p = fire_arrival_probability(k, d, q);
                    if (std::abs(p - threshold) < 1e-9) continue;   // skip exact ties
                    if ((d <= radius[k]) != (p > threshold)) ok = false;
                }
            }
            check(ok, "danger_radius should match P(Binomial(k, q) >= d) > threshold");
        }
    }
}

// Along a corridor the fire really does advance one cell per step with
// probability q, so the race model should match how often the real fire
// (simulated many times) has reached each cell.
void test_race_model_matches_the_real_fire_on_a_corridor() {
    const double q = 0.3;
    const int runs = 4000;
    Ship ship = corridor_ship(15);
    std::vector<int> ds = {1, 3, 6, 10};
    std::vector<int> ts = {5, 10, 20};
    // hits[i][j] = in how many runs cell ds[i] is burning after ts[j] updates.
    std::vector<std::vector<int>> hits(ds.size(), std::vector<int>(ts.size(), 0));
    for (int run = 0; run < runs; ++run) {
        FireTrajectory fire(ship, q, 0, make_rng(11, static_cast<unsigned>(run)));
        for (size_t i = 0; i < ds.size(); ++i) {
            for (size_t j = 0; j < ts.size(); ++j) hits[i][j] += fire.is_burning(ds[i], ts[j]);
        }
    }
    for (size_t i = 0; i < ds.size(); ++i) {
        for (size_t j = 0; j < ts.size(); ++j) {
            double expected = fire_arrival_probability(ts[j], ds[i], q);
            double seen = static_cast<double>(hits[i][j]) / runs;
            double tolerance = 4 * std::sqrt(expected * (1 - expected) / runs) + 1e-3;
            check(std::abs(seen - expected) < tolerance,
                  "on a corridor the race model should match the real fire");
        }
    }
}

// On a real ship the fire can also arrive by other routes, which only makes
// it faster: the real chance is never below the race model's (up to noise).
void test_race_model_never_overestimates_the_fire() {
    const double q = 0.4;
    const int runs = 2000;
    Rng rng = make_rng(12);
    Ship ship = Ship::generate(15, rng);
    int origin = ship.open_cells[ship.n_open() / 2];
    std::vector<int> dist = ship.distances_from(origin);
    std::vector<int> ts = {5, 10, 20};
    std::vector<std::vector<int>> hits(ts.size(), std::vector<int>(ship.D * ship.D, 0));
    for (int run = 0; run < runs; ++run) {
        FireTrajectory fire(ship, q, origin, make_rng(13, static_cast<unsigned>(run)));
        for (size_t j = 0; j < ts.size(); ++j) {
            Mask burning = fire.burning_at(ts[j]);
            for (int c : ship.open_cells) hits[j][c] += burning[c];
        }
    }
    bool ok = true;
    for (size_t j = 0; j < ts.size(); ++j) {
        for (int c : ship.open_cells) {
            double model = fire_arrival_probability(ts[j], dist[c], q);
            double seen = static_cast<double>(hits[j][c]) / runs;
            double tolerance = 4 * std::sqrt(model * (1 - model) / runs) + 0.01;
            if (seen < model - tolerance) ok = false;
        }
    }
    check(ok, "the race model should never predict more fire than really comes");
}

// Corridor 0..11, fire at 11, q = 0.5, threshold 0.6.
void test_predicted_fire_is_not_a_fixed_buffer() {
    Ship ship = corridor_ship(12);
    Mask burning = fire_at(ship, {11});
    BotOptions options;   // threshold 0.6
    // Bot at 9: cell 10 is next to the fire, but the bot gets there in one
    // step and the fire needs a successful advance first (chance 0.5 < 0.6).
    Mask near = predicted_fire(ship, 9, -1, burning, 0.5, options);
    check(!near[10], "a cell the bot reaches first should not be predicted fire");
    // Bot at 0: it needs 10 steps to reach cell 10, by which time the fire
    // has almost surely got there; it reaches cell 5 in 5 steps, but the fire
    // needs 6 advances in 5 steps, which is impossible.
    Mask far = predicted_fire(ship, 0, -1, burning, 0.5, options);
    check(far[10], "a cell the fire reaches first should be predicted fire");
    check(!far[5], "a cell the fire can't reach in time should not be predicted fire");
}

// At q = 1 the fire advances every step, so a cell is predicted fire exactly
// when the fire is at most as far from it as the bot is.
void test_predicted_fire_is_exact_when_q_is_one() {
    Rng rng = make_rng(3);
    for (int i = 0; i < 10; ++i) {
        Ship ship = Ship::generate(20, rng);
        std::vector<int> c = pick_cells(ship, rng, 2);
        int start = c[0], fire = c[1];
        Mask burning = fire_at(ship, {fire});
        Mask danger = predicted_fire(ship, start, -1, burning, 1.0, BotOptions());
        std::vector<int> from_fire = ship.distances_from(fire);
        std::vector<int> from_bot = bfs_distances(ship.neighbors, start, burning);
        bool ok = true;
        for (int cell : ship.open_cells) {
            if (cell == fire || from_bot[cell] == INF) continue;
            if (static_cast<bool>(danger[cell]) != (from_fire[cell] <= from_bot[cell])) ok = false;
        }
        check(ok, "at q = 1, predicted fire = the fire gets there no later than the bot");
    }
}

// The literal one-step rule can only flag cells touching the fire.
void test_one_step_rule_only_flags_cells_next_to_the_fire() {
    BotOptions options;
    options.lookahead = false;
    for (int i = 0; i < 10; ++i) {
        Trial trial = make_trial(20, 0.9, 4, i);
        Mask burning = trial.fire.burning_at(5);
        Mask danger = predicted_fire(trial.ship, trial.bot_start, trial.button, burning, 0.9, options);
        Mask touching = with_neighbors(burning, trial.ship.D);
        bool ok = true;
        for (int c = 0; c < trial.ship.D * trial.ship.D; ++c) {
            if (danger[c] && !touching[c]) ok = false;
        }
        check(ok, "the one-step rule should only flag cells next to the fire");
    }
}

// ---- Planners and bots ----------------------------------------------------------

// A corridor with a side pocket: the fire sits in the pocket, right next to
// the corridor cell the bot must pass through.
void test_bot3_falls_back_to_bot2_when_the_buffer_blocks_every_route() {
    Mask grid(7 * 7, 0);
    for (int c = 0; c < 7; ++c) grid[3 * 7 + c] = 1;   // the corridor (row 3)
    grid[2 * 7 + 3] = 1;                               // the pocket
    Ship ship(grid, 7);
    Mask burning = fire_at(ship, {ship.index(2, 3)});
    int start = ship.index(3, 0), button = ship.index(3, 6);
    Path path = avoid_fire_and_neighbors(ship, start, button, burning, 0.3, BotOptions());
    check(path == avoid_fire(ship, start, button, burning, 0.3, BotOptions()),
          "Bot 3 should fall back to Bot 2's path");
    check(std::find(path.begin(), path.end(), ship.index(3, 3)) != path.end(),
          "the fallback path walks past the fire");
}

void test_bot3_avoids_the_buffer_when_it_can() {
    Rng rng = make_rng(0);
    for (int i = 0; i < 20; ++i) {
        Ship ship = Ship::generate(20, rng);
        std::vector<int> c = pick_cells(ship, rng, 3);
        Mask burning = fire_at(ship, {c[2]});
        Mask buffer = with_neighbors(burning, ship.D);
        Path path = avoid_fire_and_neighbors(ship, c[0], c[1], burning, 0.3, BotOptions());
        if (path.empty() || bfs_path(ship.neighbors, c[0], c[1], buffer).empty()) continue;
        bool avoids = true;
        for (size_t k = 1; k < path.size(); ++k) {
            if (buffer[path[k]]) avoids = false;
        }
        check(avoids, "Bot 3 should avoid the fire's neighbours when it can");
    }
}

void test_bot1_plans_once_and_never_replans() {
    for (int i = 0; i < 20; ++i) {
        Trial trial = make_trial(20, 0.5, 1, i);
        Path plan = bfs_path(trial.ship.neighbors, trial.bot_start, trial.button,
                             trial.fire.burning_at(0));
        Bot bot = make_bot("bot1");
        Outcome out = run_bot(trial, bot, true);
        if (plan.empty()) continue;
        bool follows = out.path.size() <= plan.size() &&
                       std::equal(out.path.begin(), out.path.end(), plan.begin());
        check(follows, "Bot 1 should follow its first plan to the end");
    }
}

void test_bot2_never_deviates_from_its_own_rule() {
    for (double q : {0.2, 0.5}) {
        for (int i = 0; i < 30; ++i) {
            Trial trial = make_trial(20, q, 7, i);
            Bot bot = make_bot("bot2");
            check(run_bot(trial, bot, false, true).deviations == 0, "Bot 2 never leaves its own rule");
        }
    }
}

// With no penalty every step costs 1, so A* only ever takes steps along a
// shortest fire-free path: never a move Bot 2's rule couldn't make.
void test_bot4_without_penalty_behaves_like_bot2() {
    for (int i = 0; i < 30; ++i) {
        Trial trial = make_trial(20, 0.3, 4, i);
        Bot bot = make_bot("bot4:penalty=0");
        check(run_bot(trial, bot, false, true).deviations == 0,
              "Bot 4 with no penalty should never leave Bot 2's rule");
    }
}

void test_no_bot_beats_the_clairvoyant_bound() {
    for (double q : {0.0, 0.2, 0.5, 1.0}) {
        for (int i = 0; i < 40; ++i) {
            Trial trial = make_trial(20, q, 2, i);
            int best = oracle_steps(trial);
            for (std::string spec : {"bot1", "bot2", "bot3", "bot4"}) {
                Bot bot = make_bot(spec);
                Outcome out = run_bot(trial, bot, true);
                check(out.path.front() == trial.bot_start, "paths start at the bot");
                check(out.reason != ENTERED_FIRE || spec == "bot1", "only Bot 1 walks into fire");
                if (out.success) {
                    check(best >= 0 && out.steps >= best, spec + " must not beat the clairvoyant bot");
                    check(out.path.back() == trial.button, "a win ends on the button");
                }
            }
        }
    }
}

void test_everyone_wins_without_fire_spread() {
    for (int i = 0; i < 20; ++i) {
        Trial trial = make_trial(20, 0.0, 3, i);
        bool reachable = !bfs_path(trial.ship.neighbors, trial.bot_start, trial.button,
                                   trial.fire.burning_at(0)).empty();
        for (std::string spec : {"bot1", "bot2", "bot3", "bot4"}) {
            Bot bot = make_bot(spec);
            Outcome out = run_bot(trial, bot);
            check(out.reason == (reachable ? SUCCESS : TRAPPED), spec + " should win when q = 0");
        }
    }
}

// `bool threw = false; try { ... } catch (...) { threw = true; }` is the
// usual way to check that something throws an exception.
void test_make_bot_parses_options() {
    Bot bot = make_bot("bot4:threshold=0.5,penalty=50,lookahead=false,fire_metric=manhattan");
    check(bot.name == "Bot 4", "bot4 spec");
    check(bot.options.threshold == 0.5 && bot.options.penalty == 50.0, "numeric options");
    check(!bot.options.lookahead && bot.options.fire_metric == "manhattan", "other options");
    check(!make_bot("bot1").replan && make_bot("bot2").replan, "only Bot 1 plans once");
    check(make_bot("bot3").planner == avoid_fire_and_neighbors, "Bot 3's planner");
    bool threw = false;
    try {
        make_bot("bot9");
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    check(threw, "an unknown bot should throw an exception");
    threw = false;
    try {
        make_bot("bot4:speed=3");
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    check(threw, "an unknown option should throw an exception");
}

// ---- Certain wins ---------------------------------------------------------------

// At q = 1 the fire spreads at every chance, so "some path outruns the
// fastest possible fire" must agree exactly with the clairvoyant bot.
void test_fireproof_matches_clairvoyant_when_fire_is_fastest() {
    for (int i = 0; i < 60; ++i) {
        Trial trial = make_trial(20, 1.0, 5, i);
        check(trial.fireproof() == (oracle_steps(trial) >= 0), "fireproof == clairvoyant win at q = 1");
    }
}

void test_fireproof_trials_are_always_winnable() {
    for (double q : {0.1, 0.4, 0.7}) {
        for (int i = 0; i < 40; ++i) {
            Trial trial = make_trial(20, q, 6, i);
            if (trial.fireproof()) check(oracle_steps(trial) >= 0, "a certain win must be winnable");
        }
    }
}

// ---- main: run every test ------------------------------------------------------

int main() {
    // A list of (name, function) pairs. `void (*)()` is the type "pointer to
    // a function that takes nothing and returns nothing" (see bots.hpp for
    // more on function pointers).
    struct Test {
        std::string name;
        void (*run)();
    };
    std::vector<Test> tests = {
        {"maze phase is a maximal tree", test_maze_phase_is_a_maximal_tree},
        {"dead ends cut at least in half", test_dead_ends_cut_at_least_in_half},
        {"all open cells connected", test_all_open_cells_connected},
        {"generation is reproducible", test_generation_is_reproducible},
        {"neighbours are open and adjacent", test_neighbors_are_open_and_adjacent},
        {"spread probabilities", test_spread_probabilities},
        {"fire update is synchronous", test_update_is_synchronous},
        {"no spread when q is zero", test_no_spread_when_q_is_zero},
        {"fire stays on open cells", test_fire_stays_on_open_cells},
        {"ignition rate matches formula", test_ignition_rate_matches_formula},
        {"recorded fire replays exactly", test_recorded_fire_replays_exactly},
        {"BFS path is shortest", test_bfs_path_is_shortest},
        {"BFS path avoids blocked cells", test_bfs_path_avoids_blocked_cells},
        {"with_neighbors", test_with_neighbors},
        {"A* with unit costs finds shortest paths", test_astar_with_unit_costs_finds_shortest_paths},
        {"A* finds the cheapest path", test_astar_finds_the_cheapest_path},
        {"Manhattan never overestimates", test_manhattan_never_overestimates},
        {"danger radius matches the binomial formula", test_danger_radius_matches_the_binomial_formula},
        {"race model matches the real fire on a corridor", test_race_model_matches_the_real_fire_on_a_corridor},
        {"race model never overestimates the fire", test_race_model_never_overestimates_the_fire},
        {"predicted fire is not a fixed buffer", test_predicted_fire_is_not_a_fixed_buffer},
        {"predicted fire is exact when q = 1", test_predicted_fire_is_exact_when_q_is_one},
        {"one-step rule only flags cells next to the fire", test_one_step_rule_only_flags_cells_next_to_the_fire},
        {"Bot 3 falls back to Bot 2", test_bot3_falls_back_to_bot2_when_the_buffer_blocks_every_route},
        {"Bot 3 avoids the buffer when it can", test_bot3_avoids_the_buffer_when_it_can},
        {"Bot 1 plans once", test_bot1_plans_once_and_never_replans},
        {"Bot 2 never deviates", test_bot2_never_deviates_from_its_own_rule},
        {"Bot 4 without penalty behaves like Bot 2", test_bot4_without_penalty_behaves_like_bot2},
        {"no bot beats the clairvoyant bound", test_no_bot_beats_the_clairvoyant_bound},
        {"everyone wins without fire spread", test_everyone_wins_without_fire_spread},
        {"make_bot parses options", test_make_bot_parses_options},
        {"fireproof matches clairvoyant at q = 1", test_fireproof_matches_clairvoyant_when_fire_is_fastest},
        {"fireproof trials are winnable", test_fireproof_trials_are_always_winnable},
    };
    for (const Test& test : tests) {
        int failed_before = checks_failed;
        test.run();
        std::cout << (checks_failed == failed_before ? "ok    " : "FAIL  ") << test.name << "\n";
    }
    std::cout << "\n" << checks_run << " checks, " << checks_failed << " failed\n";
    return checks_failed == 0 ? 0 : 1;
}
