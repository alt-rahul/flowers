// bots.hpp: the bots. One Bot class, and a table saying how each bot is built.
//
// A BOT IS JUST
//   a name        e.g. "Bot 2"
//   a planner     a function from planners.hpp that returns a path
//   replan        true: ask the planner again every step
//                 false: plan once at the start, then follow that plan
//   options       settings passed to the planner (e.g. Bot 4's threshold)
//
// THE SIMULATOR TALKS TO EVERY BOT THE SAME WAY
//   bot.reset(ship, button, q)   once, when a trial starts
//   bot.act(pos, burning)        every step; returns the next cell, or
//                                NO_ROUTE if no route to the button avoids
//                                the fire
//   Because the fire never shrinks, NO_ROUTE means the bot can never win, so
//   the simulator ends the trial ("trapped").
//
// C++ IDEA: FUNCTION POINTERS
//   A function's name, used without (), is its ADDRESS in memory. A variable
//   that holds such an address is a FUNCTION POINTER, and calling it runs
//   whichever function it points to. So the Bot class doesn't need to know
//   anything about BFS or A*: it stores "the planner to call" and calls it.
//   The type of a function pointer spells out what the function takes and
//   returns; the `using Planner = ...` line below gives that long type a name.
#pragma once

#include <string>

#include "common.hpp"
#include "planners.hpp"
#include "ship.hpp"

// act()'s answer when no fire-free route to the button exists.
constexpr int NO_ROUTE = -1;

// "Pointer to a function that takes (ship, pos, button, burning, q, options)
// and returns a Path". Every planner in planners.hpp has exactly this shape.
using Planner = Path (*)(const Ship& ship, int pos, int button, const Mask& burning, double q,
                         const BotOptions& options);

class Bot {
public:
    // Build a bot from its parts. Most code calls make_bot() below instead.
    Bot(const std::string& name, Planner planner, bool replan, const BotOptions& options);

    // Forget everything from the previous trial.
    void reset(const Ship& ship, int button, double q);

    // Return the next cell to move to, or NO_ROUTE if there is no route.
    int act(int pos, const Mask& burning);

    // The bot's parts. They are public so that tests and the experiment
    // runner can read them (e.g. bot.name).
    std::string name;
    Planner planner;
    bool replan;
    BotOptions options;

private:
    // `const Ship*` is a pointer to a ship we may read but not change. We use
    // a pointer (not a copy) because the ship belongs to the trial, which
    // outlives the bot's use of it. nullptr = "points to nothing yet".
    const Ship* ship_ = nullptr;
    int button_ = -1;
    double q_ = 0.0;
    Path path_;          // the plan being followed; empty = no plan yet
    bool planned_ = false;
    int k_ = 0;          // index of the bot's current cell in path_
};

// Build a bot from a text spec such as "bot3" or "bot4:threshold=0.5,penalty=50".
// Options after the colon go into the bot's BotOptions. Throws
// std::invalid_argument for an unknown bot or option.
Bot make_bot(const std::string& spec);
