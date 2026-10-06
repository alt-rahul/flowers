// analyze.cpp: turn experiment CSVs into summary tables (Markdown).
//
//     ./bin/analyze results/main.csv --out results/summary.md --table results/summary.csv
//     ./bin/analyze part1.csv part2.csv          (several files: their rows are combined)
//
// Prints (or writes to --out) these tables, all built from the CSV columns
// that bin/experiments writes:
//   1. success rate per (bot, q) with a 95% confidence interval, next to the
//      clairvoyant bound
//   2. Bot 4 minus every other bot, paired by trial, with a 95% interval
//   3. trial types: certain win / contested / impossible
//   4. success on contested trials only
//   5. how often each bot leaves Bot 2's rule, and what that wins or loses
//   6. why bots fail, and how many failures were avoidable
//   7. thinking time
// --table also writes the numbers behind table 1 as a CSV, for plotting in a
// spreadsheet or any other tool.
//
// C++ IDEAS USED HERE
//   * std::map<Key, Value> as a dictionary, with std::pair / std::tuple keys
//     (pairs and tuples compare element by element, so they can be keys).
//   * Reading a file line by line with std::getline.
//   * snprintf to format numbers ("%.1f" = one decimal place).
#include <algorithm>
#include <cmath>
#include <cstdio>     // std::snprintf
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

// One CSV row: one bot on one trial.
struct Row {
    int D = 0;
    double q = 0.0;
    int trial = 0;
    std::string bot;
    int success = 0;
    std::string reason;
    int steps = 0;
    int deviations = 0;
    double ms = 0.0;
    int oracle_success = 0;
    int fireproof = 0;
};

// Identifies a trial: (D, q, trial index).
using TrialKey = std::tuple<int, double, int>;

// ---- reading CSV files ------------------------------------------------------

// Split one CSV line into fields. A field wrapped in double quotes may
// contain commas (bot specs like "bot4:threshold=0.5,penalty=50" are).
std::vector<std::string> split_csv_line(const std::string& line) {
    std::vector<std::string> fields;
    std::string current;
    bool in_quotes = false;
    for (char ch : line) {
        if (ch == '"') {
            in_quotes = !in_quotes;
        } else if (ch == ',' && !in_quotes) {
            fields.push_back(current);
            current.clear();
        } else if (ch != '\r') {
            current += ch;
        }
    }
    fields.push_back(current);
    return fields;
}

// Read every row of one CSV file and add it to `rows`. Columns are found by
// name from the header line, so their order doesn't matter.
void read_csv(const std::string& path, std::vector<Row>& rows) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open " + path);
    std::string line;
    std::getline(in, line);
    std::vector<std::string> header = split_csv_line(line);
    std::map<std::string, int> col;   // column name -> position
    for (size_t i = 0; i < header.size(); ++i) col[header[i]] = static_cast<int>(i);
    for (const char* name : {"D", "q", "trial", "bot", "success", "reason", "steps", "deviations",
                             "ms", "oracle_success", "fireproof"}) {
        if (col.count(name) == 0) throw std::runtime_error(path + " has no column " + name);
    }
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        std::vector<std::string> f = split_csv_line(line);
        Row r;
        r.D = std::stoi(f[col["D"]]);
        r.q = std::stod(f[col["q"]]);
        r.trial = std::stoi(f[col["trial"]]);
        r.bot = f[col["bot"]];
        r.success = std::stoi(f[col["success"]]);
        r.reason = f[col["reason"]];
        r.steps = std::stoi(f[col["steps"]]);
        r.deviations = std::stoi(f[col["deviations"]]);
        r.ms = std::stod(f[col["ms"]]);
        r.oracle_success = std::stoi(f[col["oracle_success"]]);
        r.fireproof = std::stoi(f[col["fireproof"]]);
        rows.push_back(r);
    }
}

// ---- statistics ---------------------------------------------------------------

// 95% Wilson score interval for a proportion k / n. Better than the usual
// p ± 1.96 * sqrt(p(1-p)/n) when p is near 0 or 1, which happens a lot here.
std::pair<double, double> wilson(int k, int n) {
    if (n == 0) return {0.0, 0.0};
    const double z = 1.96;
    double p = static_cast<double>(k) / n;
    double centre = (p + z * z / (2 * n)) / (1 + z * z / n);
    double half = z * std::sqrt(p * (1 - p) / n + z * z / (4.0 * n * n)) / (1 + z * z / n);
    return {centre - half, centre + half};
}

// Mean of a list of numbers and the half-width of its 95% interval.
std::pair<double, double> mean_and_halfwidth(const std::vector<double>& x) {
    if (x.empty()) return {0.0, 0.0};
    double sum = 0.0;
    for (double v : x) sum += v;
    double mean = sum / x.size();
    if (x.size() < 2) return {mean, 0.0};
    double squares = 0.0;
    for (double v : x) squares += (v - mean) * (v - mean);
    double sd = std::sqrt(squares / (x.size() - 1));
    return {mean, 1.96 * sd / std::sqrt(static_cast<double>(x.size()))};
}

// ---- formatting ---------------------------------------------------------------

// A number with a fixed number of decimals, e.g. fixed(0.12345, 3) = "0.123".
std::string fixed(double x, int decimals) {
    char buffer[64];
    std::snprintf(buffer, sizeof(buffer), "%.*f", decimals, x);
    return buffer;
}

// A proportion as a percentage, e.g. percent(0.123) = "12.3%".
std::string percent(double x, int decimals = 1) {
    return fixed(100 * x, decimals) + "%";
}

// q without trailing zeros: 0.3 rather than 0.300000.
std::string q_text(double q) {
    std::ostringstream s;
    s << q;
    return s.str();
}

// "bot4:threshold=0.5" -> "Bot 4 (threshold=0.5)".
std::string label(const std::string& spec) {
    std::string name = spec, args;
    size_t colon = spec.find(':');
    if (colon != std::string::npos) {
        name = spec.substr(0, colon);
        args = spec.substr(colon + 1);
    }
    std::string out = name.rfind("bot", 0) == 0 ? "Bot " + name.substr(3) : name;
    return args.empty() ? out : out + " (" + args + ")";
}

// The header and divider of a Markdown table.
std::string table_header(const std::vector<std::string>& columns) {
    std::string top = "|", rule = "|";
    for (const std::string& c : columns) {
        top += " " + c + " |";
        rule += "---|";
    }
    return top + "\n" + rule + "\n";
}

// ---- main ---------------------------------------------------------------------

int main(int argc, char** argv) {
    try {
        std::vector<std::string> inputs;
        std::string out_path, table_path, base;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if ((arg == "--out" || arg == "--table" || arg == "--base") && i + 1 < argc) {
                std::string value = argv[++i];
                if (arg == "--out") out_path = value;
                else if (arg == "--table") table_path = value;
                else base = value;
            } else {
                inputs.push_back(arg);
            }
        }
        if (inputs.empty()) {
            std::cerr << "usage: analyze results.csv [more.csv ...] [--out summary.md] "
                         "[--table summary.csv] [--base bot4]\n";
            return 1;
        }

        std::vector<Row> rows;
        for (const std::string& path : inputs) read_csv(path, rows);
        if (rows.empty()) throw std::runtime_error("no rows to analyse");

        // Bots in the order they first appear; q values sorted (std::set
        // keeps its elements sorted and unique).
        std::vector<std::string> bots;
        std::set<double> q_set;
        std::set<int> d_set;
        for (const Row& r : rows) {
            if (std::find(bots.begin(), bots.end(), r.bot) == bots.end()) bots.push_back(r.bot);
            q_set.insert(r.q);
            d_set.insert(r.D);
        }
        std::vector<double> qs(q_set.begin(), q_set.end());
        if (base.empty()) {
            base = std::find(bots.begin(), bots.end(), "bot4") != bots.end() ? "bot4" : bots.back();
        }

        // Index the rows two ways: by (bot, q), and by trial then bot.
        // Storing positions (ints) into `rows` avoids copying rows around.
        std::map<std::pair<std::string, double>, std::vector<int>> by_bot_q;
        std::map<TrialKey, std::map<std::string, int>> by_trial;
        for (size_t i = 0; i < rows.size(); ++i) {
            const Row& r = rows[i];
            by_bot_q[{r.bot, r.q}].push_back(static_cast<int>(i));
            by_trial[TrialKey(r.D, r.q, r.trial)][r.bot] = static_cast<int>(i);
        }

        std::ostringstream md;   // the Markdown report, built up like printing
        md << "Ship size D =";
        for (int D : d_set) md << " " << D;
        md << "; " << by_trial.size() << " trials; bots:";
        for (const std::string& b : bots) md << " " << label(b) << ";";
        md << "\n\n";

        // 1. Success rate with 95% interval, and the clairvoyant bound.
        md << "### Success rate (95% CI)\n\n";
        std::vector<std::string> cols = {"q", "trials"};
        for (const std::string& b : bots) cols.push_back(label(b));
        cols.push_back("Clairvoyant bound");
        md << table_header(cols);
        std::ostringstream table_csv;
        table_csv << "bot,q,trials,success_rate,ci_low,ci_high,clairvoyant_rate\n";
        for (double q : qs) {
            std::string line = "| " + q_text(q) + " | ";
            int n_trials = 0;
            double bound = 0.0;
            std::string cells;
            for (const std::string& b : bots) {
                const std::vector<int>& idx = by_bot_q[{b, q}];
                int n = static_cast<int>(idx.size()), wins = 0, winnable = 0;
                for (int i : idx) {
                    wins += rows[i].success;
                    winnable += rows[i].oracle_success;
                }
                if (n == 0) {
                    cells += " |";
                    continue;
                }
                std::pair<double, double> ci = wilson(wins, n);
                double rate = static_cast<double>(wins) / n;
                n_trials = n;
                bound = static_cast<double>(winnable) / n;
                cells += " " + percent(rate) + " (" + percent(ci.first) + "-" + percent(ci.second) + ") |";
                table_csv << b << "," << q_text(q) << "," << n << "," << fixed(rate, 4) << ","
                          << fixed(ci.first, 4) << "," << fixed(ci.second, 4) << ","
                          << fixed(bound, 4) << "\n";
            }
            md << line << n_trials << " |" << cells << " " << percent(bound) << " |\n";
        }

        // 2. Paired differences: base minus each other bot, trial by trial.
        std::vector<std::string> others;
        for (const std::string& b : bots) {
            if (b != base) others.push_back(b);
        }
        if (!others.empty()) {
            md << "\n### " << label(base) << " minus each other bot, same trials "
               << "(points; 95% CI)\n\n";
            cols = {"q"};
            for (const std::string& b : others) cols.push_back("vs " + label(b));
            md << table_header(cols);
            for (double q : qs) {
                md << "| " << q_text(q) << " |";
                for (const std::string& b : others) {
                    std::vector<double> diffs;
                    for (const auto& entry : by_trial) {
                        if (std::get<1>(entry.first) != q) continue;
                        const std::map<std::string, int>& m = entry.second;
                        if (m.count(base) && m.count(b)) {
                            diffs.push_back(rows[m.at(base)].success - rows[m.at(b)].success);
                        }
                    }
                    std::pair<double, double> d = mean_and_halfwidth(diffs);
                    md << " " << (d.first >= 0 ? "+" : "") << fixed(100 * d.first, 1) << " ± "
                       << fixed(100 * d.second, 1) << " |";
                }
                md << "\n";
            }
        }

        // 3. Trial types. These are facts about the trial, the same in every
        // bot's row, so read them from any one row per trial.
        md << "\n### Trial types\n\nCertain = some path stays ahead of even the fastest "
              "possible fire; impossible = not even the clairvoyant bot wins; contested = "
              "everything else.\n\n";
        md << table_header({"q", "trials", "certain win", "contested", "impossible"});
        for (double q : qs) {
            int n = 0, certain = 0, impossible = 0;
            for (const auto& entry : by_trial) {
                if (std::get<1>(entry.first) != q) continue;
                const Row& r = rows[entry.second.begin()->second];
                n += 1;
                certain += r.fireproof;
                impossible += 1 - r.oracle_success;
            }
            md << "| " << q_text(q) << " | " << n << " | " << percent(1.0 * certain / n) << " | "
               << percent(1.0 * (n - certain - impossible) / n) << " | "
               << percent(1.0 * impossible / n) << " |\n";
        }

        // 4. Success on contested trials only.
        md << "\n### Success on contested trials only\n\n";
        cols = {"q", "contested trials"};
        for (const std::string& b : bots) cols.push_back(label(b));
        md << table_header(cols);
        for (double q : qs) {
            std::string cells;
            int contested = 0;
            for (const std::string& b : bots) {
                int n = 0, wins = 0;
                for (int i : by_bot_q[{b, q}]) {
                    if (rows[i].oracle_success && !rows[i].fireproof) {
                        n += 1;
                        wins += rows[i].success;
                    }
                }
                contested = n;
                cells += " " + (n > 0 ? percent(1.0 * wins / n) : std::string("")) + " |";
            }
            md << "| " << q_text(q) << " | " << contested << " |" << cells << "\n";
        }

        // 5. Leaving Bot 2's rule. A deviation is a move that is not a step
        // along some shortest fire-free path; Bot 2 never makes one.
        bool has_bot2 = std::find(bots.begin(), bots.end(), "bot2") != bots.end();
        std::vector<std::string> deciders;
        for (const std::string& b : bots) {
            if (b != "bot1" && b != "bot2") deciders.push_back(b);
        }
        if (has_bot2 && !deciders.empty()) {
            md << "\n### How often a bot leaves Bot 2's rule (share of trials)\n\n";
            cols = {"q"};
            for (const std::string& b : deciders) cols.push_back(label(b));
            md << table_header(cols);
            for (double q : qs) {
                md << "| " << q_text(q) << " |";
                for (const std::string& b : deciders) {
                    const std::vector<int>& idx = by_bot_q[{b, q}];
                    int left = 0;
                    for (int i : idx) left += rows[i].deviations > 0;
                    md << " " << percent(idx.empty() ? 0.0 : 1.0 * left / idx.size()) << " |";
                }
                md << "\n";
            }
            md << "\nOutcomes on the same trials, all q pooled:\n\n";
            md << table_header({"Bot", "left Bot 2's rule?", "trials", "won, Bot 2 lost",
                                "Bot 2 won, lost", "both won", "both lost"});
            for (const std::string& b : deciders) {
                for (int left = 1; left >= 0; --left) {
                    // counts[a][c]: this bot's success a, Bot 2's success c.
                    int counts[2][2] = {{0, 0}, {0, 0}};
                    int n = 0;
                    for (const auto& entry : by_trial) {
                        const std::map<std::string, int>& m = entry.second;
                        if (!m.count(b) || !m.count("bot2")) continue;
                        const Row& r = rows[m.at(b)];
                        if ((r.deviations > 0) != (left == 1)) continue;
                        n += 1;
                        counts[r.success][rows[m.at("bot2")].success] += 1;
                    }
                    md << "| " << label(b) << " | " << (left ? "yes" : "no") << " | " << n << " | "
                       << counts[1][0] << " | " << counts[0][1] << " | " << counts[1][1] << " | "
                       << counts[0][0] << " |\n";
                }
            }
        }

        // 6. Why bots fail, all q pooled.
        const std::vector<std::string> reasons = {"entered_fire", "caught", "button_burned", "trapped"};
        md << "\n### Why bots fail (all q pooled; share of failures)\n\n"
           << "Avoidable = the clairvoyant bot would have won that trial.\n\n";
        md << table_header({"Bot", "failures", "walked into fire", "fire spread onto bot",
                            "button burned first", "cut off from button", "avoidable"});
        for (const std::string& b : bots) {
            std::map<std::string, int> count;
            int failures = 0, avoidable = 0;
            for (const Row& r : rows) {
                if (r.bot != b || r.success) continue;
                failures += 1;
                count[r.reason] += 1;
                avoidable += r.oracle_success;
            }
            if (failures == 0) continue;
            md << "| " << label(b) << " | " << failures << " |";
            for (const std::string& reason : reasons) md << " " << percent(1.0 * count[reason] / failures, 0) << " |";
            md << " " << percent(1.0 * avoidable / failures, 0) << " |\n";
        }

        // 7. Thinking time.
        md << "\n### Thinking time (time spent inside the bot's own code)\n\n";
        cols = {""};
        for (const std::string& b : bots) cols.push_back(label(b));
        md << table_header(cols);
        std::string per_trial = "| ms per trial |", per_move = "| µs per move |";
        for (const std::string& b : bots) {
            double ms = 0.0;
            long long steps = 0;
            int n = 0;
            for (const Row& r : rows) {
                if (r.bot != b) continue;
                ms += r.ms;
                steps += r.steps;
                n += 1;
            }
            per_trial += " " + fixed(ms / std::max(1, n), 2) + " |";
            per_move += " " + fixed(1000 * ms / std::max(1LL, steps), 1) + " |";
        }
        md << per_trial << "\n" << per_move << "\n";

        // Write everything out.
        if (out_path.empty()) {
            std::cout << md.str();
        } else {
            std::ofstream(out_path) << md.str();
            std::cout << "wrote " << out_path << "\n";
        }
        if (!table_path.empty()) {
            std::ofstream(table_path) << table_csv.str();
            std::cout << "wrote " << table_path << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
