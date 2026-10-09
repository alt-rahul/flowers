"""Turns the experiment results into the tables and charts in the writeup.

    python analysis.py

Reads results/main.csv, results/tuning.csv and results/size.csv, saves the
charts in plots/ and the tables in results/summary.md.
"""
import math

import matplotlib
matplotlib.use("Agg")   # save charts to files without opening a window
import matplotlib.pyplot as plt
import pandas as pd

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
COLORS = {"bot1": "blue", "bot2": "orange", "bot3": "green", "bot4": "red"}

REASONS = ["entered_fire", "caught", "button_burned", "trapped"]
REASON_NAMES = {"entered_fire": "walked into fire", "caught": "fire spread onto bot",
                "button_burned": "button burned first", "trapped": "cut off from button"}

report = []   # the lines of results/summary.md


def column(results, q, bot, name):
    """One column of the results (for example "success") for one bot at one q,
    as a list in trial order."""
    rows = results[(results["q"] == q) & (results["bot"] == bot)]
    rows = rows.sort_values("trial")
    return list(rows[name])


def mean_and_error(values):
    """The mean of a list of numbers, and the size of its 95% confidence interval."""
    n = len(values)
    mean = sum(values) / n
    total = 0
    for value in values:
        total += (value - mean) ** 2
    standard_deviation = math.sqrt(total / (n - 1))
    error = 1.96 * standard_deviation / math.sqrt(n)
    return mean, error


def success_rate(results, q, bot):
    """The bot's success rate at q, and the size of its 95% confidence interval."""
    return mean_and_error(column(results, q, bot, "success"))


def paired_difference(results, q, bot_a, bot_b):
    """bot_a's success rate minus bot_b's on the same trials, and the size of
    its 95% confidence interval. Both bots faced the same fire on every trial,
    so each trial gives a difference of -1, 0 or 1."""
    a = column(results, q, bot_a, "success")
    b = column(results, q, bot_b, "success")
    diffs = []
    for i in range(len(a)):
        diffs.append(a[i] - b[i])
    return mean_and_error(diffs)


def certain_win_share(results, q):
    """The share of trials at q that were a certain win from the start."""
    certain = column(results, q, "bot1", "fireproof")
    return sum(certain) / len(certain)


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------- charts ----

def plot_success_rate(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        rates = []
        for q in qs:
            rate, error = success_rate(results, q, bot)
            rates.append(100 * rate)
        plt.plot(qs, rates, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])

    certain = []
    for q in qs:
        certain.append(100 * certain_win_share(results, q))
    plt.plot(qs, certain, "k--", label="Certain win from the start")

    plt.xlabel("Flammability q")
    plt.ylabel("Success rate (%)")
    plt.title("Success rate vs flammability q")
    plt.legend()
    plt.grid()
    save_chart("success_rate.png")


def plot_bot4_advantage(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in ["bot1", "bot2", "bot3"]:
        diffs = []
        for q in qs:
            diff, error = paired_difference(results, q, "bot4", bot)
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


def plot_divergence(results, qs):
    """How often Bots 3 and 4 make at least one move Bot 2's rule couldn't."""
    plt.figure(figsize=(8, 5))
    for bot in ["bot3", "bot4"]:
        shares = []
        for q in qs:
            deviations = column(results, q, bot, "deviations")
            count = 0
            for d in deviations:
                if d > 0:
                    count += 1
            shares.append(100 * count / len(deviations))
        plt.plot(qs, shares, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Trials (%)")
    plt.title("How often a bot makes a move Bot 2 wouldn't")
    plt.legend()
    plt.grid()
    save_chart("divergence.png")


def failure_counts(results, bot):
    """How many times the bot failed for each reason, over every q."""
    rows = results[results["bot"] == bot]
    counts = {}
    for reason in REASONS:
        counts[reason] = len(rows[rows["reason"] == reason])
    return counts


def plot_failure_reasons(results):
    """One bar chart per bot: how its failures break down."""
    labels = ["walked\ninto fire", "fire spread\nonto bot", "button\nburned first", "cut off\nfrom button"]
    plt.figure(figsize=(10, 7))
    for i in range(len(BOTS)):
        bot = BOTS[i]
        counts = failure_counts(results, bot)
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


def head_to_head(results, q, other):
    """At q: how many trials Bot 4 won while `other` lost, and the reverse."""
    bot4 = column(results, q, "bot4", "success")
    rival = column(results, q, other, "success")
    bot4_won = 0
    other_won = 0
    for i in range(len(bot4)):
        if bot4[i] == 1 and rival[i] == 0:
            bot4_won += 1
        if rival[i] == 1 and bot4[i] == 0:
            other_won += 1
    return bot4_won, other_won


def plot_head_to_head(results, qs):
    """Out of every 1,000 trials at each q: how many Bot 4 won while Bot 3
    lost, and how many Bot 3 won while Bot 4 lost."""
    bot4_won = []
    bot3_won = []
    for q in qs:
        a, b = head_to_head(results, q, "bot3")
        n = len(column(results, q, "bot4", "success"))
        bot4_won.append(1000 * a / n)
        bot3_won.append(1000 * b / n)
    plt.figure(figsize=(8, 5))
    plt.plot(qs, bot4_won, marker="o", markersize=3, color=COLORS["bot4"], label="Bot 4 won, Bot 3 lost")
    plt.plot(qs, bot3_won, marker="o", markersize=3, color=COLORS["bot3"], label="Bot 3 won, Bot 4 lost")
    plt.xlabel("Flammability q")
    plt.ylabel("Trials per 1,000")
    plt.title("Bot 4 against Bot 3, on the same trials")
    plt.legend()
    plt.grid()
    save_chart("head_to_head.png")


def plot_ship_size(results, size):
    """Bot 4's success rate at each q, on ships of size 25, 50 and 100.
    D = 50 comes from the main run, the others from the ship size run."""
    qs = sorted(size["q"].unique())
    plt.figure(figsize=(8, 5))
    for D in [25, 50, 100]:
        if D == 50:
            rows = results
        else:
            rows = size[size["D"] == D]
        rates = []
        for q in qs:
            successes = column(rows, q, "bot4", "success")
            rates.append(100 * sum(successes) / len(successes))
        plt.plot(qs, rates, marker="o", label=f"D = {D}")
    plt.xlabel("Flammability q")
    plt.ylabel("Bot 4's success rate (%)")
    plt.title("Bot 4 on three ship sizes")
    plt.legend()
    plt.grid()
    save_chart("ship_size.png")


# The bots tried in tuning, as they are named in results/tuning.csv.
TUNING_CHOSEN = "bot4 penalty=10"
TUNING_LABELS = [
    ("bot2", "Bot 2"),
    ("bot3", "Bot 3"),
    ("bot4 penalty=5", "penalty 5"),
    ("bot4 penalty=20", "penalty 20"),
    ("bot4 penalty=30", "penalty 30"),
]


def tuning_difference(tuning, bot):
    """The bot's success rate minus the chosen Bot 4's over every tuning
    trial, in points, and the size of its 95% confidence interval."""
    diffs = []
    for q in sorted(tuning["q"].unique()):
        a = column(tuning, q, bot, "success")
        b = column(tuning, q, TUNING_CHOSEN, "success")
        for i in range(len(a)):
            diffs.append(a[i] - b[i])
    mean, error = mean_and_error(diffs)
    return 100 * mean, 100 * error


def plot_tuning(tuning):
    labels = []
    diffs = []
    for bot, label in TUNING_LABELS:
        mean, error = tuning_difference(tuning, bot)
        labels.append(label)
        diffs.append(mean)
    plt.figure(figsize=(8, 5))
    plt.barh(labels, diffs)
    plt.axvline(0, color="black")
    plt.xlabel("Success rate minus the chosen Bot 4 (penalty 10), in points")
    plt.title("Bot 4 tuning on 800 separate trials")
    save_chart("tuning.png")


# ------------------------------------------------------------- tables ----

def table_success_rates(results, qs):
    report.append("## Success rate (95% CI) and certain wins\n")
    report.append("| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 | Certain wins |")
    report.append("|---|---|---|---|---|---|")
    for q in qs:
        line = f"| {q:g} |"
        for bot in BOTS:
            rate, error = success_rate(results, q, bot)
            line += f" {100 * rate:.1f}% ± {100 * error:.1f} |"
        line += f" {100 * certain_win_share(results, q):.1f}% |"
        report.append(line)


def table_differences(results, qs):
    report.append("\n## Bot 4 minus each other bot, same trials (points, 95% CI)\n")
    report.append("| q | vs Bot 1 | vs Bot 2 | vs Bot 3 |")
    report.append("|---|---|---|---|")
    for q in qs:
        line = f"| {q:g} |"
        for bot in ["bot1", "bot2", "bot3"]:
            diff, error = paired_difference(results, q, "bot4", bot)
            line += f" {100 * diff:+.1f} ± {100 * error:.1f} |"
        report.append(line)


def table_certain_wins(results):
    report.append("\n## Certain wins: how many of them each bot won\n")
    report.append("| Bot | Certain-win trials won |")
    report.append("|---|---|")
    for bot in BOTS:
        rows = results[(results["bot"] == bot) & (results["fireproof"] == 1)]
        won = rows["success"].sum()
        report.append(f"| {NAMES[bot]} | {won} of {len(rows)} |")


def table_failures(results, qs):
    report.append("\n## Why bots fail (all q, share of each bot's failures)\n")
    report.append("| Bot | Failures | walked into fire | fire spread onto bot | button burned first "
                  "| cut off from button | another bot won the same trial |")
    report.append("|---|---|---|---|---|---|---|")
    for bot in BOTS:
        counts = failure_counts(results, bot)
        failures = 0
        saved = 0   # failures where another bot won, so a better decision existed
        for q in qs:
            success = {}
            for b in BOTS:
                success[b] = column(results, q, b, "success")
            for i in range(len(success[bot])):
                if success[bot][i] == 1:
                    continue
                failures += 1
                for other in BOTS:
                    if other != bot and success[other][i] == 1:
                        saved += 1
                        break
        line = f"| {NAMES[bot]} | {failures} |"
        for reason in REASONS:
            line += f" {100 * counts[reason] / failures:.0f}% |"
        line += f" {100 * saved / failures:.1f}% |"
        report.append(line)


def table_head_to_head(results, qs):
    report.append("\n## Bot 4 head to head, same trials\n")
    report.append("| q range | Bot 4 lost, Bot 3 won | Bot 4 won, Bot 3 lost "
                  "| Bot 4 lost, Bot 2 won | Bot 4 won, Bot 2 lost |")
    report.append("|---|---|---|---|---|")
    for low_q, high_q in [(0, 0.2), (0.225, 0.7), (0.75, 1)]:
        line = f"| {low_q:g} to {high_q:g} |"
        for other in ["bot3", "bot2"]:
            lost = 0
            won = 0
            for q in qs:
                if q >= low_q and q <= high_q:
                    bot4_won, other_won = head_to_head(results, q, other)
                    won += bot4_won
                    lost += other_won
            line += f" {lost} | {won} |"
        report.append(line)


def table_divergence(results, qs):
    report.append("\n## Outcomes against Bot 2, split by whether the bot ever left Bot 2's rule\n")
    report.append("| Bot | Left Bot 2's rule? | Trials | Won where Bot 2 lost | Lost where Bot 2 won |")
    report.append("|---|---|---|---|---|")
    for bot in ["bot3", "bot4"]:
        for left in [True, False]:
            count = 0
            won = 0
            lost = 0
            for q in qs:
                deviations = column(results, q, bot, "deviations")
                success = column(results, q, bot, "success")
                bot2_success = column(results, q, "bot2", "success")
                for i in range(len(deviations)):
                    if (deviations[i] > 0) != left:
                        continue
                    count += 1
                    if success[i] == 1 and bot2_success[i] == 0:
                        won += 1
                    if bot2_success[i] == 1 and success[i] == 0:
                        lost += 1
            if left:
                answer = "yes"
            else:
                answer = "no"
            report.append(f"| {NAMES[bot]} | {answer} | {count} | {won} | {lost} |")


def table_tuning(tuning):
    report.append("\n## Bot 4 tuning (800 separate trials)\n")
    report.append("| Bot | Success | Minus the chosen Bot 4 (points) |")
    report.append("|---|---|---|")
    for bot, label in [(TUNING_CHOSEN, "penalty 10 (chosen)")] + TUNING_LABELS:
        rows = tuning[tuning["bot"] == bot]
        mean, error = tuning_difference(tuning, bot)
        report.append(f"| {label} | {100 * rows['success'].mean():.2f}% | {mean:+.2f} ± {error:.2f} |")


def main():
    results = pd.read_csv("results/main.csv")
    tuning = pd.read_csv("results/tuning.csv")
    size = pd.read_csv("results/size.csv")
    qs = sorted(results["q"].unique())

    plot_success_rate(results, qs)
    plot_bot4_advantage(results, qs)
    plot_divergence(results, qs)
    plot_failure_reasons(results)
    plot_head_to_head(results, qs)
    plot_tuning(tuning)
    plot_ship_size(results, size)

    report.append("# Results\n")
    report.append(f"Main run: D = 50, {len(results) // 4} trials (results/main.csv).\n")
    table_success_rates(results, qs)
    table_differences(results, qs)
    table_certain_wins(results)
    table_failures(results, qs)
    table_head_to_head(results, qs)
    table_divergence(results, qs)
    table_tuning(tuning)

    with open("results/summary.md", "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nCharts saved in plots/, tables in results/summary.md")


if __name__ == "__main__":
    main()
