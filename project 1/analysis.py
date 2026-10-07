"""Turns the experiment results into the tables and charts in the writeup.

    python analysis.py

Reads the results in results/, saves the charts in plots/ and the tables in
results/summary.md.
"""
import csv
import gzip
import math

import matplotlib
matplotlib.use("Agg")   # save charts to files without opening a window
import matplotlib.pyplot as plt

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
COLORS = {"bot1": "blue", "bot2": "orange", "bot3": "green", "bot4": "red"}

REASONS = ["entered_fire", "caught", "button_burned", "trapped"]
REASON_NAMES = {"entered_fire": "walked into fire", "caught": "fire spread onto bot",
                "button_burned": "button burned first", "trapped": "cut off from button"}

report = []   # the lines of results/summary.md


def load(path, D):
    """trials[q][trial number][bot] = that bot's row, for ships of size D."""
    trials = {}
    with gzip.open(path, "rt") as f:
        for row in csv.DictReader(f):
            if int(row["D"]) != D:
                continue
            row["success"] = int(row["success"])
            row["steps"] = int(row["steps"])
            row["deviations"] = int(row["deviations"])
            row["ms"] = float(row["ms"])
            row["fireproof"] = int(row["fireproof"])
            q = float(row["q"])
            number = int(row["trial"])
            if q not in trials:
                trials[q] = {}
            if number not in trials[q]:
                trials[q][number] = {}
            trials[q][number][row["bot"]] = row
    return trials


def success_rate(trials, q, bot):
    """The bot's success rate at q, and the size of its 95% confidence interval."""
    wins = 0
    for results in trials[q].values():
        wins += results[bot]["success"]
    n = len(trials[q])
    rate = wins / n
    error = 1.96 * math.sqrt(rate * (1 - rate) / n)
    return rate, error


def paired_difference(trials, q, bot_a, bot_b):
    """bot_a's success rate minus bot_b's on the same trials, and the size of
    its 95% confidence interval. Both bots faced the same fire on every trial,
    so each trial gives a difference of -1, 0 or 1."""
    diffs = []
    for results in trials[q].values():
        diffs.append(results[bot_a]["success"] - results[bot_b]["success"])
    n = len(diffs)
    mean = sum(diffs) / n
    total = 0
    for d in diffs:
        total += (d - mean) ** 2
    standard_deviation = math.sqrt(total / (n - 1))
    error = 1.96 * standard_deviation / math.sqrt(n)
    return mean, error


def certain_win_share(trials, q):
    """The share of trials at q that were a certain win from the start."""
    count = 0
    for results in trials[q].values():
        count += results["bot1"]["fireproof"]
    return count / len(trials[q])


def failure_counts(trials, bot):
    """How many times the bot failed for each reason, over every q."""
    counts = {}
    for reason in REASONS:
        counts[reason] = 0
    for q in trials:
        for results in trials[q].values():
            reason = results[bot]["reason"]
            if reason in counts:
                counts[reason] += 1
    return counts


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------- charts ----

def plot_success_rate(trials):
    qs = sorted(trials)
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        rates = []
        for q in qs:
            rate, error = success_rate(trials, q, bot)
            rates.append(100 * rate)
        plt.plot(qs, rates, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])

    certain = []
    for q in qs:
        certain.append(100 * certain_win_share(trials, q))
    plt.plot(qs, certain, "k--", label="Certain win from the start")

    plt.xlabel("Flammability q")
    plt.ylabel("Success rate (%)")
    plt.title("Success rate vs flammability q")
    plt.legend()
    plt.grid()
    save_chart("success_rate.png")


def plot_bot4_advantage(trials):
    qs = sorted(trials)
    plt.figure(figsize=(8, 5))
    for bot in ["bot1", "bot2", "bot3"]:
        diffs = []
        for q in qs:
            diff, error = paired_difference(trials, q, "bot4", bot)
            diffs.append(100 * diff)
        plt.plot(qs, diffs, marker="o", markersize=3, color=COLORS[bot],
                 label="Bot 4 minus " + NAMES[bot])
    plt.axhline(0, color="black")
    plt.xlabel("Flammability q")
    plt.ylabel("Difference in success rate (points)")
    plt.title("How much better Bot 4 does, on the same trials")
    plt.legend()
    plt.grid()
    save_chart("bot4_advantage.png")


def plot_ship_size(trials_by_size):
    qs = sorted(trials_by_size[25])   # the q values every size was run at
    plt.figure(figsize=(8, 5))
    for D in [25, 50, 100]:
        rates = []
        for q in qs:
            rate, error = success_rate(trials_by_size[D], q, "bot4")
            rates.append(100 * rate)
        plt.plot(qs, rates, marker="o", label=f"D = {D}")
    plt.xlabel("Flammability q")
    plt.ylabel("Bot 4's success rate (%)")
    plt.title("Bot 4 on three ship sizes")
    plt.legend()
    plt.grid()
    save_chart("ship_size.png")


def plot_divergence(trials):
    """How often Bots 3 and 4 make at least one move Bot 2's rule couldn't."""
    qs = sorted(trials)
    plt.figure(figsize=(8, 5))
    for bot in ["bot3", "bot4"]:
        shares = []
        for q in qs:
            count = 0
            for results in trials[q].values():
                if results[bot]["deviations"] > 0:
                    count += 1
            shares.append(100 * count / len(trials[q]))
        plt.plot(qs, shares, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Trials (%)")
    plt.title("How often a bot makes a move Bot 2 wouldn't")
    plt.legend()
    plt.grid()
    save_chart("divergence.png")


def plot_failure_reasons(trials):
    """One bar chart per bot: how its failures break down."""
    labels = ["walked\ninto fire", "fire spread\nonto bot", "button\nburned first", "cut off\nfrom button"]
    plt.figure(figsize=(10, 7))
    for i in range(len(BOTS)):
        bot = BOTS[i]
        counts = failure_counts(trials, bot)
        failures = 0
        for reason in REASONS:
            failures += counts[reason]
        shares = []
        for reason in REASONS:
            shares.append(100 * counts[reason] / failures)
        plt.subplot(2, 2, i + 1)
        plt.bar(labels, shares, color=COLORS[bot])
        plt.ylim(0, 60)
        plt.ylabel("Share of failures (%)")
        plt.title(NAMES[bot])
    plt.tight_layout()
    save_chart("failure_reasons.png")


def plot_head_to_head(trials):
    """Out of every 1,000 trials at each q: how many Bot 4 won while Bot 3
    lost, and how many Bot 3 won while Bot 4 lost."""
    qs = sorted(trials)
    bot4_won = []
    bot3_won = []
    for q in qs:
        a = 0
        b = 0
        for results in trials[q].values():
            if results["bot4"]["success"] and not results["bot3"]["success"]:
                a += 1
            if results["bot3"]["success"] and not results["bot4"]["success"]:
                b += 1
        bot4_won.append(1000 * a / len(trials[q]))
        bot3_won.append(1000 * b / len(trials[q]))
    plt.figure(figsize=(8, 5))
    plt.plot(qs, bot4_won, marker="o", markersize=3, color=COLORS["bot4"], label="Bot 4 won, Bot 3 lost")
    plt.plot(qs, bot3_won, marker="o", markersize=3, color=COLORS["bot3"], label="Bot 3 won, Bot 4 lost")
    plt.xlabel("Flammability q")
    plt.ylabel("Trials per 1,000")
    plt.title("Bot 4 against Bot 3, on the same trials")
    plt.legend()
    plt.grid()
    save_chart("head_to_head.png")


# The Bot 4 settings tried in tuning, as they are named in results/tuning.csv.gz.
TUNING_CHOSEN = "bot4:threshold=0.6,penalty=20"
TUNING_VARIANTS = [
    ("bot2", "Bot 2"),
    ("bot3", "Bot 3"),
    ("bot4:threshold=0.4,penalty=5", "θ = 0.4, λ = 5"),
    ("bot4:threshold=0.4,penalty=20", "θ = 0.4, λ = 20"),
    ("bot4:threshold=0.4,penalty=100", "θ = 0.4, λ = 100"),
    ("bot4:threshold=0.6,penalty=5", "θ = 0.6, λ = 5"),
    ("bot4:threshold=0.6,penalty=100", "θ = 0.6, λ = 100"),
    ("bot4:penalty=1000", "θ = 0.6, λ = 1000"),
    ("bot4:threshold=0.8,penalty=5", "θ = 0.8, λ = 5"),
    ("bot4:threshold=0.8,penalty=20", "θ = 0.8, λ = 20"),
    ("bot4:threshold=0.8,penalty=100", "θ = 0.8, λ = 100"),
    ("bot4:lookahead=false", "one-step 60% rule"),
    ("bot4:fire_metric=manhattan", "Manhattan fire distance"),
]


def tuning_difference(tuning, variant):
    """The variant's success rate minus the chosen Bot 4's over every tuning
    trial, in points, and the size of its 95% confidence interval."""
    diffs = []
    for q in tuning:
        for results in tuning[q].values():
            diffs.append(results[variant]["success"] - results[TUNING_CHOSEN]["success"])
    n = len(diffs)
    mean = sum(diffs) / n
    total = 0
    for d in diffs:
        total += (d - mean) ** 2
    error = 1.96 * math.sqrt(total / (n - 1)) / math.sqrt(n)
    return 100 * mean, 100 * error


def plot_tuning(tuning):
    labels = []
    diffs = []
    for variant, label in TUNING_VARIANTS:
        mean, error = tuning_difference(tuning, variant)
        labels.append(label)
        diffs.append(mean)
    plt.figure(figsize=(8, 5))
    plt.barh(labels, diffs)
    plt.axvline(0, color="black")
    plt.xlabel("Success rate minus the chosen Bot 4 (θ = 0.6, λ = 20), in points")
    plt.title("Bot 4 tuning on 4,000 separate trials")
    save_chart("tuning.png")


# ------------------------------------------------------------- tables ----

def table_success_rates(trials):
    report.append("## Success rate (95% CI) and certain wins\n")
    report.append("| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 | Certain wins |")
    report.append("|---|---|---|---|---|---|")
    for q in sorted(trials):
        line = f"| {q:g} |"
        for bot in BOTS:
            rate, error = success_rate(trials, q, bot)
            line += f" {100 * rate:.1f}% ± {100 * error:.1f} |"
        line += f" {100 * certain_win_share(trials, q):.1f}% |"
        report.append(line)


def table_differences(trials):
    report.append("\n## Bot 4 minus each other bot, same trials (points, 95% CI)\n")
    report.append("| q | vs Bot 1 | vs Bot 2 | vs Bot 3 |")
    report.append("|---|---|---|---|")
    for q in sorted(trials):
        line = f"| {q:g} |"
        for bot in ["bot1", "bot2", "bot3"]:
            diff, error = paired_difference(trials, q, "bot4", bot)
            line += f" {100 * diff:+.1f} ± {100 * error:.1f} |"
        report.append(line)


def table_certain_wins(trials):
    report.append("\n## Certain wins: how many of them each bot won\n")
    report.append("| Bot | Certain-win trials won |")
    report.append("|---|---|")
    for bot in BOTS:
        won = 0
        total = 0
        for q in trials:
            for results in trials[q].values():
                if results[bot]["fireproof"]:
                    total += 1
                    won += results[bot]["success"]
        report.append(f"| {NAMES[bot]} | {won} of {total} |")


def table_failures(trials):
    report.append("\n## Why bots fail (all q, share of each bot's failures)\n")
    report.append("| Bot | Failures | walked into fire | fire spread onto bot | button burned first "
                  "| cut off from button | another bot won the same trial |")
    report.append("|---|---|---|---|---|---|---|")
    for bot in BOTS:
        counts = failure_counts(trials, bot)
        failures = 0
        saved = 0   # failures where another bot won, so a better decision existed
        for q in trials:
            for results in trials[q].values():
                if results[bot]["success"]:
                    continue
                failures += 1
                for other in BOTS:
                    if other != bot and results[other]["success"]:
                        saved += 1
                        break
        line = f"| {NAMES[bot]} | {failures} |"
        for reason in REASONS:
            line += f" {100 * counts[reason] / failures:.0f}% |"
        line += f" {100 * saved / failures:.1f}% |"
        report.append(line)


def table_head_to_head(trials):
    report.append("\n## Bot 4 head to head, same trials\n")
    report.append("| q range | Bot 4 lost, Bot 3 won | Bot 4 won, Bot 3 lost "
                  "| Bot 4 lost, Bot 2 won | Bot 4 won, Bot 2 lost |")
    report.append("|---|---|---|---|---|")
    for low_q, high_q in [(0, 0.2), (0.225, 0.7), (0.75, 1)]:
        line = f"| {low_q:g} to {high_q:g} |"
        for other in ["bot3", "bot2"]:
            lost = 0
            won = 0
            for q in trials:
                if low_q <= q <= high_q:
                    for results in trials[q].values():
                        if results[other]["success"] and not results["bot4"]["success"]:
                            lost += 1
                        if results["bot4"]["success"] and not results[other]["success"]:
                            won += 1
            line += f" {lost} | {won} |"
        report.append(line)


def table_divergence(trials):
    report.append("\n## Outcomes against Bot 2, split by whether the bot ever left Bot 2's rule\n")
    report.append("| Bot | Left Bot 2's rule? | Trials | Won where Bot 2 lost | Lost where Bot 2 won |")
    report.append("|---|---|---|---|---|")
    for bot in ["bot3", "bot4"]:
        for left in [True, False]:
            count = 0
            won = 0
            lost = 0
            for q in trials:
                for results in trials[q].values():
                    if (results[bot]["deviations"] > 0) != left:
                        continue
                    count += 1
                    if results[bot]["success"] and not results["bot2"]["success"]:
                        won += 1
                    if results["bot2"]["success"] and not results[bot]["success"]:
                        lost += 1
            if left:
                answer = "yes"
            else:
                answer = "no"
            report.append(f"| {NAMES[bot]} | {answer} | {count} | {won} | {lost} |")


def table_thinking_time(trials):
    report.append("\n## Thinking time (time spent deciding, as recorded in the results)\n")
    report.append("| | Bot 1 | Bot 2 | Bot 3 | Bot 4 |")
    report.append("|---|---|---|---|---|")
    per_move = "| µs per move |"
    per_trial = "| ms per trial |"
    for bot in BOTS:
        total_ms = 0.0
        total_steps = 0
        count = 0
        for q in trials:
            for results in trials[q].values():
                total_ms += results[bot]["ms"]
                total_steps += results[bot]["steps"]
                count += 1
        per_move += f" {1000 * total_ms / total_steps:.0f} |"
        per_trial += f" {total_ms / count:.1f} |"
    report.append(per_move)
    report.append(per_trial)


def table_ship_size(trials_by_size):
    report.append("\n## Ship size: Bot 4's success rate, and Bot 4 minus Bot 3 (points)\n")
    report.append("| q | D = 25 | D = 50 | D = 100 | minus Bot 3, D = 25 | D = 50 | D = 100 |")
    report.append("|---|---|---|---|---|---|---|")
    for q in sorted(trials_by_size[25]):
        line = f"| {q:g} |"
        for D in [25, 50, 100]:
            rate, error = success_rate(trials_by_size[D], q, "bot4")
            line += f" {100 * rate:.1f}% |"
        for D in [25, 50, 100]:
            diff, error = paired_difference(trials_by_size[D], q, "bot4", "bot3")
            line += f" {100 * diff:+.1f} ± {100 * error:.1f} |"
        report.append(line)


def table_tuning(tuning):
    report.append("\n## Bot 4 tuning (4,000 separate trials, seed 7)\n")
    report.append("| Bot | Success | Minus the chosen Bot 4 (points) |")
    report.append("|---|---|---|")
    variants = [(TUNING_CHOSEN, "θ = 0.6, λ = 20 (chosen)")] + TUNING_VARIANTS
    for variant, label in variants:
        wins = 0
        count = 0
        for q in tuning:
            for results in tuning[q].values():
                wins += results[variant]["success"]
                count += 1
        mean, error = tuning_difference(tuning, variant)
        report.append(f"| {label} | {100 * wins / count:.2f}% | {mean:+.2f} ± {error:.2f} |")


def main():
    trials = load("results/main.csv.gz", 50)
    trials_by_size = {
        25: load("results/size.csv.gz", 25),
        50: trials,
        100: load("results/size.csv.gz", 100),
    }
    tuning = load("results/tuning.csv.gz", 50)

    plot_success_rate(trials)
    plot_bot4_advantage(trials)
    plot_ship_size(trials_by_size)
    plot_divergence(trials)
    plot_failure_reasons(trials)
    plot_head_to_head(trials)
    plot_tuning(tuning)

    report.append("# Results\n")
    report.append("Main run: D = 50, 83,000 trials (results/main.csv.gz).\n")
    table_success_rates(trials)
    table_differences(trials)
    table_certain_wins(trials)
    table_failures(trials)
    table_head_to_head(trials)
    table_divergence(trials)
    table_thinking_time(trials)
    table_ship_size(trials_by_size)
    table_tuning(tuning)

    with open("results/summary.md", "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nCharts saved in plots/, tables in results/summary.md")


if __name__ == "__main__":
    main()
