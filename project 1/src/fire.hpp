// fire.hpp: the fire.
//
// THE RULE (from the assignment)
//   Every time step, each open cell that is not burning catches fire with
//   probability 1 - (1 - q)^K, where K = how many of its 4 neighbours are
//   burning and q is the ship's "flammability". More burning neighbours
//   means a higher chance. Blocked cells never burn.
//
// SYNCHRONOUS UPDATE (the TA's feedback)
//   All cells are updated from the fire as it was at the START of the step.
//   A cell that catches fire during step t cannot spread fire until step
//   t + 1. fire_step() does this by computing every new ignition first and
//   only adding them to the fire afterwards.
//
// ONE FIRE PER TRIAL, SHARED BY ALL BOTS
//   The fire never reacts to the bot. So for each trial we generate one fire
//   "trajectory" and replay it for every bot. All four bots then face the
//   exact same fire, which makes comparisons between bots fair and much
//   less noisy. The trajectory stores, for every cell, the time step at
//   which it caught fire. "Is cell c burning at time t?" is then just
//   ignite_time[c] <= t. Bots are only ever shown the present, never the
//   future.
#pragma once

#include <array>    // std::array: a fixed-size array that knows its size
#include <vector>

#include "common.hpp"
#include "ship.hpp"

// Ignition time of a cell that hasn't caught fire (yet).
constexpr int NOT_YET = INF;

// Lookup table: entry K is 1 - (1 - q)^K for K = 0..4, the chance that a
// cell with K burning neighbours catches fire this step.
std::array<double, 5> spread_probabilities(double q);

// One synchronous fire update: returns the mask of cells that ignite this
// step (it does not modify `burning`; the caller adds them afterwards).
Mask fire_step(const Mask& burning, const Mask& open_grid, int D,
               const std::array<double, 5>& probs, Rng& rng);

// One realisation of the fire, generated lazily: only as many steps are
// simulated as anyone has asked about.
//
// This is a `class` with PRIVATE data: outside code can only use the public
// member functions below, which keeps the fire's internal state consistent
// (nobody can, say, change ignite_time_ without updating burning_).
class FireTrajectory {
public:
    // A new random fire that starts at `origin`. The generator is taken BY
    // VALUE: the trajectory keeps its own copy and draws from it as it goes.
    FireTrajectory(const Ship& ship, double q, int origin, Rng rng);

    // A second constructor (C++ allows several, as long as their parameter
    // lists differ; this is called OVERLOADING). This one builds a fire
    // whose ignition times are already known (-1 = never), so nothing is
    // simulated. Use it to replay a fire that was recorded earlier, for
    // example to run the bots on exactly the same fire again (see the tests).
    FireTrajectory(const Ship& ship, double q, const std::vector<int>& ignite_times);

    // Simulate until `t` fire updates have happened (no-op if already there).
    void advance_to(int t);

    // Which cells are burning after `t` fire updates (1 = burning).
    Mask burning_at(int t);

    // Is one particular cell burning after `t` fire updates?
    bool is_burning(int cell, int t);

    // Read-only access to the ignition times (the oracle and tests use it).
    // Returning `const std::vector<int>&` gives the caller a read-only view
    // of our vector instead of copying it.
    const std::vector<int>& ignite_times() const { return ignite_time_; }

private:
    // A trailing underscore is a common naming convention for private members.
    int D_ = 0;
    Mask open_;                        // copy of the ship's open cells
    double q_ = 0.0;
    Rng rng_;                          // this fire's own random generator
    std::array<double, 5> probs_{};    // spread_probabilities(q_)
    Mask burning_;                     // cells burning at time t_
    std::vector<int> ignite_time_;     // ignition step per cell, NOT_YET if not burning yet
    int t_ = 0;                        // how many updates have been simulated
    bool replay_ = false;              // true: times were given, never simulate
};
