// simulation.cpp: definitions for simulation.hpp.
#include "simulation.hpp"

#include <chrono>      // std::chrono: clocks, for timing the bots
#include <stdexcept>
#include <utility>     // std::swap, std::move

#include "planning.hpp"

Trial::Trial(Ship ship_, double q_, int bot_start_, int button_, int fire_start_, FireTrajectory fire_)
    : ship(std::move(ship_)), q(q_), bot_start(bot_start_), button(button_),
      fire_start(fire_start_), fire(std::move(fire_)) {}

Trial Trial::generate(int D, double q, Rng& rng) {
    Ship ship = Ship::generate(D, rng);

    // Pick 3 distinct open cells: shuffle just the first three positions of a
    // copy of the list (a partial Fisher-Yates shuffle). Each pick swaps a
    // random not-yet-picked cell into position i.
    std::vector<int> cells = ship.open_cells;
    for (int i = 0; i < 3; ++i) {
        int j = random_int(rng, i, static_cast<int>(cells.size()));
        std::swap(cells[i], cells[j]);
    }
    int bot = cells[0];
    int button = cells[1];
    int fire_start = cells[2];

    // The fire gets its own copy of the generator, in its current state, and
    // draws from it whenever it needs to simulate further.
    FireTrajectory fire(ship, q, fire_start, rng);
    return Trial(ship, q, bot, button, fire_start, fire);
}

int Trial::max_steps() const {
    return 10 * ship.n_open();
}

bool Trial::fireproof() const {
    std::vector<int> fire_dist = fire_distances(ship.neighbors, {fire_start}, ship.D * ship.D);
    return !fireproof_path(ship.neighbors, bot_start, button, fire_dist).empty();
}

const std::vector<int>& Trial::distances_to_button(int t) {
    if (to_button.count(t) == 0) {
        to_button[t] = bfs_distances(ship.neighbors, button, fire.burning_at(t));
    }
    return to_button[t];
}

// Was moving from `from` to `to` a move Bot 2's rule could make, i.e. a step
// along SOME shortest path to the button? `dist` holds distances to the
// button through unburnt cells. If the bot's own cell can't reach the button
// (INF), any move to a cell that CAN reach it counts as a deviation, and a
// move to another cut-off cell doesn't (infinity minus 1 is still infinity).
static bool is_deviation(const std::vector<int>& dist, int from, int to) {
    if (dist[from] == INF) return dist[to] != INF;
    return dist[to] != dist[from] - 1;
}

Outcome run_bot(Trial& trial, Bot& bot, bool record_path, bool count_deviations) {
    Outcome out;
    int pos = trial.bot_start;
    out.path.push_back(pos);

    // Timing: steady_clock is a clock that never jumps (good for measuring).
    // duration<double, std::milli> converts a time difference to milliseconds.
    using Clock = std::chrono::steady_clock;
    auto t0 = Clock::now();   // `auto`: let the compiler work out the type
    bot.reset(trial.ship, trial.button, trial.q);
    out.think_ms += std::chrono::duration<double, std::milli>(Clock::now() - t0).count();

    int t = 0;   // number of fire updates so far
    while (t < trial.max_steps()) {
        Mask burning = trial.fire.burning_at(t);

        // 1. The bot decides (timed).
        t0 = Clock::now();
        int next = bot.act(pos, burning);
        out.think_ms += std::chrono::duration<double, std::milli>(Clock::now() - t0).count();

        if (next == NO_ROUTE) {
            out.reason = TRAPPED;
            out.steps = t;
            return out;
        }

        // Safety check: a bot may only stay or step to an open neighbour.
        bool legal = (next == pos);
        for (int n : trial.ship.neighbors[pos]) {
            if (n == next) legal = true;
        }
        if (!legal) throw std::runtime_error(bot.name + " made an illegal move");

        if (count_deviations && is_deviation(trial.distances_to_button(t), pos, next)) {
            out.deviations += 1;
        }

        // 2-3. The bot moves.
        pos = next;
        if (record_path) out.path.push_back(pos);
        if (burning[pos]) {
            out.reason = ENTERED_FIRE;
            out.steps = t + 1;
            return out;
        }
        if (pos == trial.button) {
            out.success = true;
            out.reason = SUCCESS;
            out.steps = t + 1;
            return out;
        }

        // 4-6. The fire advances, then check the bot and the button.
        t += 1;
        if (trial.fire.is_burning(pos, t)) {
            out.reason = CAUGHT;
            out.steps = t;
            return out;
        }
        if (trial.fire.is_burning(trial.button, t)) {
            out.reason = BUTTON_BURNED;
            out.steps = t;
            return out;
        }
    }
    out.reason = TIMEOUT;
    out.steps = t;
    return out;
}

int oracle_steps(Trial& trial) {
    // A BFS in which cell n may be entered on move k+1 only if it is not
    // burning after k+1 fire updates (the button: after k updates, since it
    // is pressed before the fire moves). Because the fire only grows,
    // reaching a cell as early as possible is always best, so each cell only
    // needs to be visited once.
    const Adjacency& neighbors = trial.ship.neighbors;
    std::vector<char> seen(neighbors.size(), 0);
    seen[trial.bot_start] = 1;
    std::vector<int> frontier = {trial.bot_start};
    int k = 0;
    while (!frontier.empty() && k < trial.max_steps()) {
        trial.fire.advance_to(k + 1);   // make sure the fire is known that far ahead
        const std::vector<int>& ignite = trial.fire.ignite_times();
        std::vector<int> next;
        for (int c : frontier) {
            for (int n : neighbors[c]) {
                if (seen[n]) continue;
                if (n == trial.button) {
                    if (ignite[n] > k) return k + 1;   // reached the button in time
                } else if (ignite[n] > k + 1) {
                    seen[n] = 1;
                    next.push_back(n);
                }
            }
        }
        frontier = next;
        k += 1;
    }
    return -1;   // no sequence of moves wins
}
