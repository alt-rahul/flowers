// fire.cpp: definitions for fire.hpp.
#include "fire.hpp"

#include <cmath>   // std::pow

std::array<double, 5> spread_probabilities(double q) {
    std::array<double, 5> probs{};
    for (int k = 0; k < 5; ++k) probs[k] = 1.0 - std::pow(1.0 - q, k);
    return probs;
}

Mask fire_step(const Mask& burning, const Mask& open_grid, int D,
               const std::array<double, 5>& probs, Rng& rng) {
    // K for every cell, counted from the fire as it was at the START of the
    // step. Nothing is changed until all ignitions have been decided: that
    // is what makes the update synchronous.
    std::vector<int> k = count_neighbors(burning, D);
    Mask ignite(D * D, 0);
    for (int cell = 0; cell < D * D; ++cell) {
        // Draw a random number for EVERY cell, even walls and burning cells,
        // so each step uses the generator the same way whatever the fire
        // looks like. (Skipping draws would make one cell's roll depend on
        // which other cells happen to be burning.)
        double roll = random_unit(rng);
        if (open_grid[cell] && !burning[cell] && roll < probs[k[cell]]) ignite[cell] = 1;
    }
    return ignite;
}

// Member initializer list (after the colon): sets members before the body.
FireTrajectory::FireTrajectory(const Ship& ship, double q, int origin, Rng rng)
    : D_(ship.D), open_(ship.grid), q_(q), rng_(rng), probs_(spread_probabilities(q)),
      burning_(ship.D * ship.D, 0), ignite_time_(ship.D * ship.D, NOT_YET) {
    burning_[origin] = 1;
    ignite_time_[origin] = 0;
}

FireTrajectory::FireTrajectory(const Ship& ship, double q, const std::vector<int>& ignite_times)
    : D_(ship.D), open_(ship.grid), q_(q), probs_(spread_probabilities(q)),
      burning_(ship.D * ship.D, 0), ignite_time_(ship.D * ship.D, NOT_YET), replay_(true) {
    // `size_t` is the unsigned integer type C++ uses for sizes and indexes.
    for (size_t cell = 0; cell < ignite_times.size(); ++cell) {
        if (ignite_times[cell] >= 0) ignite_time_[cell] = ignite_times[cell];
    }
}

void FireTrajectory::advance_to(int t) {
    if (replay_) {                 // nothing to simulate: the times are known
        if (t > t_) t_ = t;
        return;
    }
    while (t_ < t) {
        Mask fresh = fire_step(burning_, open_, D_, probs_, rng_);
        t_ += 1;
        for (int cell = 0; cell < D_ * D_; ++cell) {
            if (fresh[cell]) {     // only now are the new ignitions added
                burning_[cell] = 1;
                ignite_time_[cell] = t_;
            }
        }
    }
}

Mask FireTrajectory::burning_at(int t) {
    advance_to(t);
    Mask out(ignite_time_.size(), 0);
    for (size_t c = 0; c < ignite_time_.size(); ++c) out[c] = ignite_time_[c] <= t;
    return out;
}

bool FireTrajectory::is_burning(int cell, int t) {
    advance_to(t);
    return ignite_time_[cell] <= t;
}
