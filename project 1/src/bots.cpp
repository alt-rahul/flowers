// bots.cpp: definitions for bots.hpp.
#include "bots.hpp"

#include <cctype>      // std::tolower
#include <stdexcept>   // std::invalid_argument

// The part after the colon is the MEMBER INITIALIZER LIST: it sets each
// member directly before the constructor body runs.
Bot::Bot(const std::string& name_, Planner planner_, bool replan_, const BotOptions& options_)
    : name(name_), planner(planner_), replan(replan_), options(options_) {}

void Bot::reset(const Ship& ship, int button, double q) {
    ship_ = &ship;   // remember WHERE the ship is (its address), not a copy
    button_ = button;
    q_ = q;
    path_.clear();
    planned_ = false;
    k_ = 0;
}

int Bot::act(int pos, const Mask& burning) {
    if (replan || !planned_) {
        // `planner(...)` calls whichever function the pointer points to.
        // `*ship_` follows the pointer to the Ship itself.
        path_ = planner(*ship_, pos, button_, burning, q_, options);
        planned_ = true;
        k_ = 0;
        if (path_.empty()) return NO_ROUTE;
    }
    if (path_.empty()) return NO_ROUTE;   // a bot that never replans keeps its (missing) plan
    k_ += 1;
    return path_[k_];   // path_[0] is where we stand; the next cell is the move
}

// ---- make_bot ---------------------------------------------------------------

// Lower-case copy of a string ("True" -> "true"). `static` keeps this helper
// private to this file.
static std::string lower(std::string s) {
    for (char& ch : s) ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    return s;
}

Bot make_bot(const std::string& spec) {
    // Split "name:key=value,key=value" into the name and the options.
    std::string name = spec;
    std::string option_text;
    size_t colon = spec.find(':');   // std::string::npos means "not found"
    if (colon != std::string::npos) {
        name = spec.substr(0, colon);
        option_text = spec.substr(colon + 1);
    }

    // Start from the defaults, then override whatever the spec says.
    BotOptions options;
    size_t begin = 0;
    while (begin < option_text.size()) {
        size_t comma = option_text.find(',', begin);
        if (comma == std::string::npos) comma = option_text.size();
        std::string item = option_text.substr(begin, comma - begin);
        begin = comma + 1;
        size_t eq = item.find('=');
        if (eq == std::string::npos) throw std::invalid_argument("bad bot option: " + item);
        std::string key = item.substr(0, eq);
        std::string value = item.substr(eq + 1);
        if (key == "threshold") options.threshold = std::stod(value);   // text -> double
        else if (key == "penalty") options.penalty = std::stod(value);
        else if (key == "lookahead") options.lookahead = lower(value) == "true";
        else if (key == "fire_metric") options.fire_metric = value;
        else throw std::invalid_argument("unknown bot option: " + key);
    }

    // How each bot is built: (display name, planner, replan every step?).
    // Writing a function's name without () passes its address.
    if (name == "bot1") return Bot("Bot 1", avoid_fire, false, options);
    if (name == "bot2") return Bot("Bot 2", avoid_fire, true, options);
    if (name == "bot3") return Bot("Bot 3", avoid_fire_and_neighbors, true, options);
    if (name == "bot4") return Bot("Bot 4", avoid_predicted_fire, true, options);
    throw std::invalid_argument("unknown bot: " + name);
}
