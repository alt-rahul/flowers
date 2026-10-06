// experiments.cpp: the experiment runner.
//
// Runs every bot on many random trials and writes one CSV row per
// (trial, bot). bin/analyze turns the CSV into tables.
//
// Examples (from the project folder, after `make`):
//     ./bin/experiments --D 50 --q 0:1:0.05 --trials 1000 --out results/main.csv
//     ./bin/experiments --q 0.3,0.4 --bots bot3 bot4:threshold=0.4 --out tune.csv
//     ./bin/analyze results/main.csv --out results/summary.md
//
// Every bot runs on the same trial (same ship, start cells and fire), so
// differences between bots are paired comparisons. Each trial's random seed
// depends only on (seed, q, trial index), so any row can be reproduced.
//
// Besides each bot's result, every row records facts about the trial:
//   oracle_success, oracle_steps   could a clairvoyant bot win, and how fast?
//   fireproof                      was it a certain win from the start?
//   bot_to_button, fire_to_button, fire_to_bot   maze distances at the start
// and about the bot:
//   deviations                     moves Bot 2's rule could not have made
//   ms                             time spent inside the bot's own code
//
// This runner is single-threaded to keep the code simple. To use several
// cores, start several runs at once on different q values (each writing its
// own CSV) and pass all the CSV files to bin/analyze.
#include <algorithm>   // std::max
#include <cmath>       // std::round, std::llround
#include <fstream>     // std::ofstream: writing files
#include <iostream>    // std::cout, std::cerr: printing to the terminal
#include <sstream>     // std::ostringstream: building strings like printing
#include <string>
#include <vector>

#include "bots.hpp"
#include "simulation.hpp"

// The command-line settings, with their defaults.
struct Settings {
    int D = 50;
    std::string q_text;                // "start:stop:step" or "q1,q2,..."
    int trials = 500;
    int first_trial = 0;
    std::vector<std::string> bots = {"bot1", "bot2", "bot3", "bot4"};
    unsigned seed = 440;
    std::string out;
};

// Turn "0:1:0.05" into 0, 0.05, ..., 1 (stop included), or "0.1,0.3" into
// 0.1, 0.3. Values are rounded to 6 decimals, so 0.1 + 2 * 0.05 comes out
// as 0.2 and not 0.20000000000000001.
std::vector<double> parse_qs(const std::string& text) {
    std::vector<double> qs;
    if (text.find(':') != std::string::npos) {
        size_t a = text.find(':');
        size_t b = text.find(':', a + 1);
        double start = std::stod(text.substr(0, a));
        double stop = std::stod(text.substr(a + 1, b - a - 1));
        double step = std::stod(text.substr(b + 1));
        int n = static_cast<int>(std::round((stop - start) / step));
        for (int i = 0; i <= n; ++i) qs.push_back(std::round((start + i * step) * 1e6) / 1e6);
    } else {
        std::stringstream parts(text);
        std::string piece;
        while (std::getline(parts, piece, ',')) qs.push_back(std::stod(piece));
    }
    return qs;
}

// A random generator for trial number `trial` at flammability `q`.
// std::seed_seq mixes several numbers into one good starting state, so
// nearby inputs (trial 7 and trial 8) still give unrelated random streams.
Rng trial_rng(unsigned seed, double q, int trial) {
    unsigned q_key = static_cast<unsigned>(std::llround(q * 1000000));
    std::seed_seq seq{seed, q_key, static_cast<unsigned>(trial)};
    return Rng(seq);
}

// Short number formatting for the CSV: 0.3 rather than 0.300000.
std::string number(double x) {
    std::ostringstream s;
    s.precision(10);
    s << x;
    return s.str();
}

// A CSV field that contains a comma (e.g. "bot4:threshold=0.5,penalty=50")
// must be wrapped in double quotes, or the comma would split it into two columns.
std::string csv_field(const std::string& text) {
    if (text.find(',') == std::string::npos) return text;
    return "\"" + text + "\"";
}

// The word after a flag such as "--D". `int& i` is a reference, so moving i
// forward here also moves it forward in the caller's loop.
std::string next_word(int argc, char** argv, int& i) {
    if (i + 1 >= argc) throw std::invalid_argument(std::string("missing value after ") + argv[i]);
    i += 1;
    return argv[i];
}

// Read the command line. argv[] holds the words typed after the program name.
// (std::stoi / std::stoul / std::stod convert text to int / unsigned / double.)
Settings parse_args(int argc, char** argv) {
    Settings s;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--D") s.D = std::stoi(next_word(argc, argv, i));
        else if (arg == "--q") s.q_text = next_word(argc, argv, i);
        else if (arg == "--trials") s.trials = std::stoi(next_word(argc, argv, i));
        else if (arg == "--first-trial") s.first_trial = std::stoi(next_word(argc, argv, i));
        else if (arg == "--seed") s.seed = static_cast<unsigned>(std::stoul(next_word(argc, argv, i)));
        else if (arg == "--out") s.out = next_word(argc, argv, i);
        else if (arg == "--bots") {
            // Every following word up to the next --flag is a bot spec.
            s.bots.clear();
            while (i + 1 < argc && std::string(argv[i + 1]).rfind("--", 0) != 0) {
                s.bots.push_back(argv[++i]);
            }
        } else {
            throw std::invalid_argument("unknown argument: " + arg);
        }
    }
    if (s.q_text.empty() || s.out.empty()) {
        throw std::invalid_argument("usage: experiments --q <qs> --out <file.csv> "
                                    "[--D 50] [--trials 500] [--first-trial 0] "
                                    "[--bots bot1 bot2 ...] [--seed 440]");
    }
    return s;
}

// `main` is where every C++ program starts. argc = number of words on the
// command line, argv = the words themselves.
int main(int argc, char** argv) {
    // try / catch: if anything inside `try` throws an exception, jump to
    // `catch`, print the message and exit with an error code.
    try {
        Settings s = parse_args(argc, argv);
        std::vector<double> qs = parse_qs(s.q_text);

        // Does the output file already exist (so we shouldn't repeat the header)?
        bool new_file = !std::ifstream(s.out).good();
        std::ofstream csv(s.out, std::ios::app);   // open for appending
        if (!csv) throw std::runtime_error("cannot open " + s.out);
        if (new_file) {
            csv << "D,q,trial,bot,success,reason,steps,deviations,ms,oracle_success,"
                   "oracle_steps,fireproof,bot_to_button,fire_to_button,fire_to_bot\n";
        }

        const int total = static_cast<int>(qs.size()) * s.trials;
        int done = 0;
        for (double q : qs) {
            for (int i = s.first_trial; i < s.first_trial + s.trials; ++i) {
                Rng rng = trial_rng(s.seed, q, i);
                Trial trial = Trial::generate(s.D, q, rng);

                // Facts about the trial itself, shared by every bot's row.
                int best = oracle_steps(trial);
                std::vector<int> from_button = trial.ship.distances_from(trial.button);
                std::vector<int> from_fire = trial.ship.distances_from(trial.fire_start);
                std::ostringstream common;
                common << (best >= 0 ? 1 : 0) << ','
                       << (best >= 0 ? std::to_string(best) : "") << ','
                       << (trial.fireproof() ? 1 : 0) << ','
                       << from_button[trial.bot_start] << ','
                       << from_button[trial.fire_start] << ','
                       << from_fire[trial.bot_start];

                for (const std::string& spec : s.bots) {
                    Bot bot = make_bot(spec);
                    Outcome out = run_bot(trial, bot, false, true);
                    std::ostringstream ms;
                    ms.setf(std::ios::fixed);
                    ms.precision(3);
                    ms << out.think_ms;
                    csv << s.D << ',' << number(q) << ',' << i << ',' << csv_field(spec) << ','
                        << (out.success ? 1 : 0) << ',' << out.reason << ',' << out.steps << ','
                        << out.deviations << ',' << ms.str() << ',' << common.str() << '\n';
                }

                done += 1;
                if (done % std::max(1, total / 20) == 0 || done == total) {
                    std::cout << done << "/" << total << " trials" << std::endl;
                }
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;   // a non-zero exit code tells the shell something went wrong
    }
    return 0;
}
