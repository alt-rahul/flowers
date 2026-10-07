"""Turns the experiment results into the tables and charts in the writeup.

    python analysis.py

Reads results/main.csv.gz, results/size.csv.gz and results/tuning.csv.gz,
saves the charts in plots/ and the tables in results/summary.md.
"""
import csv
import gzip
import math

import matplotlib
matplotlib.use("Agg")   # save charts to files without opening a window
import matplotlib.pyplot as plt
import numpy as np

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
COLORS = {"bot1": "#2a78d6", "bot2": "#eb6834", "bot3": "#1baf7a", "bot4": "#4a3aa7"}
MARKERS = {"bot1": "o", "bot2": "s", "bot3": "^", "bot4": "D"}

REASONS = ["entered_fire", "caught", "button_burned", "trapped"]
REASON_NAMES = {"entered_fire": "walked into fire", "caught": "fire spread onto bot",
                "button_burned": "button burned first", "trapped": "cut off from button"}
REASON_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]

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
    """bot_a's success rate minus bot_b's on the same trials, with a 95%
    confidence interval. Both bots faced the same fire on every trial."""
    diffs = []
    for results in trials[q].values():
        diffs.append(results[bot_a]["success"] - results[bot_b]["success"])
    mean = np.mean(diffs)
    error = 1.96 * np.std(diffs, ddof=1) / math.sqrt(len(diffs))
    return mean, error


def certain_win_share(trials, q):
    count = 0
    for results in trials[q].values():
        count += results["bot1"]["fireproof"]
    return count / len(trials[q])


def save_chart(name):
    plt.savefig(f"plots/{name}", dpi=120, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------- charts ----

def plot_centerpiece(trials):
    qs = sorted(trials)

    # The q values where Bot 4 beats both Bot 2 and Bot 3 with 95% confidence.
    ahead = []
    for q in qs:
        diff2, error2 = paired_difference(trials, q, "bot4", "bot2")
        diff3, error3 = paired_difference(trials, q, "bot4", "bot3")
        if diff2 - error2 > 0 and diff3 - error3 > 0:
            ahead.append(q)

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 9), sharex=True)
    for bot in BOTS:
        rates = [success_rate(trials, q, bot)[0] for q in qs]
        top.plot(qs, rates, marker=MARKERS[bot], markersize=4, color=COLORS[bot], label=NAMES[bot])
    top.plot(qs, [certain_win_share(trials, q) for q in qs], "k--", label="Certain win from the start")
    top.axvspan(min(ahead), max(ahead), color="grey", alpha=0.15,
                label="Bot 4 ahead of Bots 2 and 3 (95%)")
    top.set_ylabel("Success rate")
    top.set_title("Success rate vs flammability q")
    top.legend()
    top.grid(alpha=0.3)

    for bot in ["bot1", "bot2", "bot3"]:
        diffs = []
        errors = []
        for q in qs:
            diff, error = paired_difference(trials, q, "bot4", bot)
            diffs.append(100 * diff)
            errors.append(100 * error)
        bottom.errorbar(qs, diffs, yerr=errors, marker=MARKERS[bot], markersize=4, capsize=2,
                        color=COLORS[bot], label=f"Bot 4 minus {NAMES[bot]}")
    bottom.axhline(0, color="black", linewidth=1)
    bottom.axvspan(min(ahead), max(ahead), color="grey", alpha=0.15)
    bottom.set_xlabel("Flammability q")
    bottom.set_ylabel("Difference (points)")
    bottom.set_title("Bot 4's advantage on the same trials (95% CI)")
    bottom.legend()
    bottom.grid(alpha=0.3)
    fig.tight_layout()
    save_chart("centerpiece.png")


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
            shares.append(count / len(trials[q]))
        plt.plot(qs, shares, marker=MARKERS[bot], markersize=4, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Share of trials")
    plt.title("How often a bot leaves Bot 2's rule at least once")
    plt.legend()
    plt.grid(alpha=0.3)
    save_chart("divergence.png")


def plot_failure_reasons(trials, low_q, high_q):
    """Why each bot fails, as a share of all trials with low_q <= q <= high_q."""
    plt.figure(figsize=(8, 5))
    bottoms = [0.0, 0.0, 0.0, 0.0]
    for i in range(len(REASONS)):
        reason = REASONS[i]
        heights = []
        for bot in BOTS:
            failed = 0
            total = 0
            for q in trials:
                if low_q <= q <= high_q:
                    for results in trials[q].values():
                        total += 1
                        if results[bot]["reason"] == reason:
                            failed += 1
            heights.append(failed / total)
        plt.bar([NAMES[bot] for bot in BOTS], heights, bottom=bottoms, color=REASON_COLORS[i],
                edgecolor="white", linewidth=1.5, label=REASON_NAMES[reason])
        for j in range(len(BOTS)):
            bottoms[j] += heights[j]
    plt.ylabel("Share of all trials")
    plt.title(f"Why bots fail (q = {low_q:g} to {high_q:g})")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    save_chart("failure_reasons.png")


def plot_head_to_head(trials):
    """Per q, out of every 1,000 trials: how many Bot 4 won while the other
    bot lost, and the other way round."""
    qs = sorted(trials)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, other in zip(axes, ["bot2", "bot3"]):
        bot4_won = []
        other_won = []
        for q in qs:
            a = 0
            b = 0
            for results in trials[q].values():
                if results["bot4"]["success"] and not results[other]["success"]:
                    a += 1
                if results[other]["success"] and not results["bot4"]["success"]:
                    b += 1
            bot4_won.append(1000 * a / len(trials[q]))
            other_won.append(1000 * b / len(trials[q]))
        ax.plot(qs, bot4_won, marker=MARKERS["bot4"], markersize=4, color=COLORS["bot4"],
                label=f"Bot 4 won, {NAMES[other]} lost")
        ax.plot(qs, other_won, marker=MARKERS[other], markersize=4, color=COLORS[other],
                label=f"{NAMES[other]} won, Bot 4 lost")
        ax.set_title(f"Bot 4 against {NAMES[other]}, same trials")
        ax.set_xlabel("Flammability q")
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("Trials per 1,000")
    save_chart("head_to_head.png")


def plot_ship_size(trials_by_size):
    """Bot 4's success rate on each ship size."""
    plt.figure(figsize=(8, 5))
    shades = ["#9a91d0", "#6c5fc0", "#4a3aa7"]
    sizes = sorted(trials_by_size)
    for i in range(len(sizes)):
        D = sizes[i]
        qs = sorted(trials_by_size[25])   # the q values every size was run at
        rates = []
        errors = []
        for q in qs:
            rate, error = success_rate(trials_by_size[D], q, "bot4")
            rates.append(rate)
            errors.append(error)
        plt.errorbar(qs, rates, yerr=errors, marker="o", markersize=4, capsize=2,
                     color=shades[i], label=f"D = {D}")
    plt.xlabel("Flammability q")
    plt.ylabel("Bot 4's success rate")
    plt.title("Bot 4 on three ship sizes (95% CI)")
    plt.legend()
    plt.grid(alpha=0.3)
    save_chart("ship_size.png")


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
    """The variant's success rate minus the chosen Bot 4's, over every tuning trial."""
    diffs = []
    for q in tuning:
        for results in tuning[q].values():
            diffs.append(results[variant]["success"] - results[TUNING_CHOSEN]["success"])
    mean = 100 * np.mean(diffs)
    error = 100 * 1.96 * np.std(diffs, ddof=1) / math.sqrt(len(diffs))
    return mean, error


def plot_tuning(tuning):
    plt.figure(figsize=(8, 5.5))
    for y in range(len(TUNING_VARIANTS)):
        variant, label = TUNING_VARIANTS[y]
        mean, error = tuning_difference(tuning, variant)
        bot = variant[:4]   # "bot2", "bot3" or "bot4"
        plt.errorbar(mean, y, xerr=error, marker=MARKERS[bot], markersize=6, capsize=3, color=COLORS[bot])
    plt.axvline(0, color="black", linewidth=1)
    plt.yticks(range(len(TUNING_VARIANTS)), [label for variant, label in TUNING_VARIANTS])
    plt.gca().invert_yaxis()
    plt.xlabel("Success rate minus the chosen Bot 4 (θ = 0.6, λ = 20), in points")
    plt.title("Bot 4 tuning: 4,000 separate trials, 95% CI")
    plt.grid(alpha=0.3, axis="x")
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
    report.append("| Bot | Failures | " + " | ".join(REASON_NAMES[reason] for reason in REASONS)
                  + " | another bot won the same trial |")
    report.append("|---|---|---|---|---|---|---|")
    for bot in BOTS:
        counts = {}
        for reason in REASONS:
            counts[reason] = 0
        failures = 0
        saved = 0   # failures where another bot won, so a better decision existed
        for q in trials:
            for results in trials[q].values():
                if results[bot]["success"]:
                    continue
                failures += 1
                if results[bot]["reason"] in counts:
                    counts[results[bot]["reason"]] += 1
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
            answer = "yes" if left else "no"
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
    for variant, label in [(TUNING_CHOSEN, "θ = 0.6, λ = 20 (chosen)")] + TUNING_VARIANTS:
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

    plot_centerpiece(trials)
    plot_divergence(trials)
    plot_failure_reasons(trials, 0.2, 0.6)
    plot_head_to_head(trials)
    plot_ship_size(trials_by_size)
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
