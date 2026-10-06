// simulation.hpp: running a bot on a trial, plus the clairvoyant bound.
//
// A TRIAL is one complete setup: a ship, a flammability q, the bot's start
// cell, the button cell, the fire's first cell, and the fire's (lazily
// generated) future. Every bot is run on the same Trial, so all bots face the
// exact same fire.
//
// ONE TIME STEP (the order the assignment specifies)
//   1. The bot decides where to go and moves there.
//   2. If it moved into a burning cell, it fails ("entered_fire").
//   3. If it is on the button, it presses it and wins ("success").
//   4. Otherwise the fire advances one step.
//   5. If the fire reached the bot's cell, it fails ("caught").
//   6. If the fire reached the button, nobody can press it any more: the
//      trial ends as a certain loss ("button_burned").
//   A bot that reports NO_ROUTE ends the trial too ("trapped"): every route
//   to the button already runs through fire, and fire never goes out.
#pragma once

#include <map>
#include <string>
#include <vector>

#include "bots.hpp"
#include "common.hpp"
#include "fire.hpp"
#include "ship.hpp"

// How a run ended.
const std::string SUCCESS = "success";
const std::string ENTERED_FIRE = "entered_fire";
const std::string CAUGHT = "caught";
const std::string BUTTON_BURNED = "button_burned";
const std::string TRAPPED = "trapped";
const std::string TIMEOUT = "timeout";   // safety cap; never happens in practice

struct Trial {
    Ship ship;
    double q;
    int bot_start;
    int button;
    int fire_start;
    FireTrajectory fire;
    // Cache for distances_to_button(): time t -> distances. std::map is a
    // sorted dictionary: it stores (key, value) pairs and finds a key fast.
    std::map<int, std::vector<int>> to_button;

    // A constructor that fills in every member.
    Trial(Ship ship_, double q_, int bot_start_, int button_, int fire_start_, FireTrajectory fire_);

    // A random trial: generate a ship, then pick three DIFFERENT random open
    // cells for the bot, the button and the fire.
    static Trial generate(int D, double q, Rng& rng);

    // Safety cap on the number of steps in one run.
    int max_steps() const;

    // Is this trial a CERTAIN win from the start? True if some path to the
    // button stays ahead of even the fastest possible fire (q = 1). Decided
    // with two BFSs and no simulation.
    bool fireproof() const;

    // Distance to the button through cells not burning after t updates
    // (used to detect moves Bot 2's rule couldn't make). Cached per t
    // because every bot on this trial asks about the same fire.
    // Returns a reference into the cache: std::map never moves its stored
    // values, so the reference stays valid.
    const std::vector<int>& distances_to_button(int t);
};

// The result of one bot on one trial.
struct Outcome {
    bool success = false;
    std::string reason;
    int steps = 0;
    Path path;              // cells visited (only filled if asked)
    int deviations = 0;     // moves Bot 2's rule could not have made
    double think_ms = 0.0;  // time spent inside the bot's own reset()/act()
};

// Run one bot on one trial. The trial is passed by (non-const) reference
// because running a bot may make the fire simulate further ahead.
// Default arguments (`= false`) let callers leave them out.
Outcome run_bot(Trial& trial, Bot& bot, bool record_path = false, bool count_deviations = false);

// The clairvoyant bound: the fewest steps in which a bot that knew the fire's
// ENTIRE future could press the button, or -1 if no sequence of moves could
// win.
int oracle_steps(Trial& trial);
