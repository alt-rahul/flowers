import math

import matplotlib
matplotlib.use("Agg")   # saves the charts as files instead of opening a window for each one
import matplotlib.pyplot as plt
import pandas as pd

from bots import PENALTY
from search import map_distance
from simulation import setup_trial

# this file takes all the results that experiments.py saved and turns them into the charts and tables
# that are used in the writeup, you run it with "python analysis.py" once experiments.py is done.
# the charts get saved in the plots folder and the tables get saved in results/summary.md

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
# each bot always has the same color in every chart so it's easy to follow a bot from one chart to the next,
# these colors were picked so they're still easy to tell apart for someone who is colorblind
COLORS = {"bot1": "#2a78d6", "bot2": "#eb6834", "bot3": "#1baf7a", "bot4": "#4a3aa7"}
# for the charts where the lines are different q values or ship sizes (not bots), the lines go from
# light gray for the smallest one to black for the biggest one
GRAYS = ["#9a9a9a", "#5c5c5c", "#1e1e1e"]

# the reasons a bot can fail, and the names that show up in the charts for them
REASONS = ["entered_fire", "caught", "button_burned", "trapped"]
REASON_NAMES = {"entered_fire": "walked into fire", "caught": "fire spread onto bot",
                "button_burned": "button burned first", "trapped": "cut off from button"}

report = []   # every line of results/summary.md, it gets written to the file at the very end


# gets one column of the results (like "success") for one bot at one q, as a list sorted by the trial number
# so that the same index in two lists is always the same trial (same ship and same fire)
def column(results, q, bot, name):
    rows = results[(results["q"] == q) & (results["bot"] == bot)]
    rows = rows.sort_values("trial")
    return list(rows[name])


# calculates the mean of a list of numbers and how big its 95% confidence interval is, the interval tells us
# how sure we can be about the mean: the real value is within mean +- error 95% of the time
def mean_and_error(values):
    n = len(values)
    mean = sum(values) / n
    total = 0
    for value in values:
        total += (value - mean) ** 2
    standard_deviation = math.sqrt(total / (n - 1))
    error = 1.96 * standard_deviation / math.sqrt(n)
    return mean, error


# the success rate of a bot at q (a success is 1 and a failure is 0, so the mean is the success rate)
def success_rate(results, q, bot):
    return mean_and_error(column(results, q, bot, "success"))


# compares two bots on the exact same trials: for every trial, bot_a's result minus bot_b's result
# gives 1 (only bot_a won), -1 (only bot_b won) or 0 (both won or both lost), the mean of that is
# how much better bot_a did. this is much more exact than comparing two separate success rates
def paired_difference(results, q, bot_a, bot_b):
    a = column(results, q, bot_a, "success")
    b = column(results, q, bot_b, "success")
    diffs = []
    for i in range(len(a)):
        diffs.append(a[i] - b[i])
    return mean_and_error(diffs)


# at q, counts how many trials bot4 won while the other bot lost, and how many the other bot won while bot4 lost
def head_to_head(results, q, other):
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


# counts how many times the bot failed for each reason, over every q
def failure_counts(results, bot):
    rows = results[results["bot"] == bot]
    counts = {}
    for reason in REASONS:
        counts[reason] = len(rows[rows["reason"] == reason])
    return counts


# the head start of a trial is how many more moves the fire needs to reach the button than the bot does
# (the fire's distance to the button minus the bot's distance to the button), so a positive head start
# means the bot started closer to the button than the fire. the results don't save the distances so this
# builds the ship of every trial again to measure it, which takes a couple of minutes
def head_starts(trials):
    heads = {}
    for trial in range(trials):
        ship, bot_start, button, fire_start = setup_trial(50, trial)
        dist = map_distance(ship, [button], set())   # every cell's distance to the button
        heads[trial] = dist[fire_start[0]][fire_start[1]] - dist[bot_start[0]][bot_start[1]]
    return heads


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------- charts ----

# the main chart: every bot's success rate at every q, all on the same axes so they're easy to compare
def plot_success_rate(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        rates = []
        for q in qs:
            rate, error = success_rate(results, q, bot)
            rates.append(100 * rate)
        plt.plot(qs, rates, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Success rate (%)")
    plt.title("Success rate vs flammability q")
    plt.legend()
    plt.grid()
    save_chart("success_rate.png")


# shows how bot4's heat map works: how much it costs bot4 to step on a cell based on how far the fire has to
# travel to get there (d), for a slow, a medium and a fast fire. the cost is 1 + PENALTY * q ** (d - 1),
# and a cell that is far from the fire costs about 1 (the dashed line), same as a normal move
def plot_heat_cost():
    distances = list(range(1, 11))   # d = 1 to 10
    qs = [0.2, 0.5, 0.8]
    plt.figure(figsize=(8, 5))
    for i in range(len(qs)):
        q = qs[i]
        costs = []
        for d in distances:
            costs.append(1 + PENALTY * q ** (d - 1))
        plt.plot(distances, costs, marker="o", color=GRAYS[i], label=f"q = {q}")
    plt.axhline(1, color="black", linestyle="--", label="a normal move")
    plt.xticks(distances)
    plt.ylim(0, 12)
    plt.xlabel("How far the fire has to travel to reach the cell (d)")
    plt.ylabel("Cost of stepping on the cell")
    plt.title("What a cell costs Bot 4")
    plt.legend()
    plt.grid()
    save_chart("heat_cost.png")


# how long each bot takes to decide on one move, on average, which is the total time the bot spent
# thinking divided by the total number of moves it made (bot1 only plans once so it barely thinks at all)
def plot_think_time(results):
    labels = []
    times = []
    colors = []
    for bot in BOTS:
        rows = results[results["bot"] == bot]
        labels.append(NAMES[bot])
        times.append(rows["ms"].sum() / rows["steps"].sum())
        colors.append(COLORS[bot])
    plt.figure(figsize=(8, 5))
    plt.bar(labels, times, color=colors)
    for i in range(len(times)):
        plt.text(i, times[i], f"{times[i]:.2f} ms", ha="center", va="bottom")   # the number on top of each bar
    plt.ylabel("Time to decide one move (ms)")
    plt.title("How long each bot thinks before each move")
    save_chart("think_time.png")


# compares bot4 and bot2 on the exact same trials (same ship and same fire): at each q it shows the % of
# trials where bot4 won but bot2 lost, and the % of trials where bot2 won but bot4 lost. when the bot4
# line is above the bot2 line, bot4 is doing better at that q
def plot_bot4_vs_bot2(results, qs):
    bot4_only = []
    bot2_only = []
    for q in qs:
        bot4_won, bot2_won = head_to_head(results, q, "bot2")
        trials = len(column(results, q, "bot4", "success"))
        bot4_only.append(100 * bot4_won / trials)
        bot2_only.append(100 * bot2_won / trials)
    plt.figure(figsize=(8, 5))
    plt.plot(qs, bot4_only, marker="o", markersize=3, color=COLORS["bot4"], label="Bot 4 won, Bot 2 lost")
    plt.plot(qs, bot2_only, marker="o", markersize=3, color=COLORS["bot2"], label="Bot 2 won, Bot 4 lost")
    plt.xlabel("Flammability q")
    plt.ylabel("Trials (%)")
    plt.title("Trials that only one of Bot 4 and Bot 2 won")
    plt.legend()
    plt.grid()
    save_chart("bot4_vs_bot2.png")


# bot2's success rate based on its head start, for a slow, a medium and the fastest fire. the head starts
# are put into groups of 10 moves (-10 to -1, 0 to 9, 10 to 19 and so on) and a group needs at least 10
# trials to be shown, otherwise the point is too noisy to mean anything
def plot_head_start(results, heads):
    qs = [0.2, 0.5, 1.0]
    plt.figure(figsize=(8, 5))
    for i in range(len(qs)):
        q = qs[i]
        rows = results[(results["q"] == q) & (results["bot"] == "bot2")]
        trials = list(rows["trial"])
        successes = list(rows["success"])
        wins = {}     # group -> how many trials in that group bot2 won
        counts = {}   # group -> how many trials are in that group
        for j in range(len(trials)):
            group = (heads[trials[j]] // 10) * 10
            if group not in counts:
                counts[group] = 0
                wins[group] = 0
            counts[group] += 1
            wins[group] += successes[j]
        middles = []
        rates = []
        for group in sorted(counts):
            if counts[group] >= 10:
                middles.append(group + 4.5)   # the middle of the group, for example 4.5 for 0 to 9
                rates.append(100 * wins[group] / counts[group])
        plt.plot(middles, rates, marker="o", color=GRAYS[i], label=f"q = {q}")
    plt.axvline(0, color="black")   # left of this line the fire started closer to the button than the bot
    plt.xlabel("Head start: the fire's distance to the button minus the bot's (moves)")
    plt.ylabel("Bot 2's success rate (%)")
    plt.title("Starting closer to the button than the fire")
    plt.legend()
    plt.grid()
    save_chart("head_start.png")


# bot4's success rate on the three ship sizes, D = 50 comes from the main run and the others come from the
# ship size run
def plot_ship_size(results, size):
    qs = sorted(size["q"].unique())
    sizes = [25, 50, 100]
    plt.figure(figsize=(8, 5))
    for i in range(len(sizes)):
        D = sizes[i]
        if D == 50:
            rows = results
        else:
            rows = size[size["D"] == D]
        rates = []
        for q in qs:
            successes = column(rows, q, "bot4", "success")
            rates.append(100 * sum(successes) / len(successes))
        plt.plot(qs, rates, marker="o", color=GRAYS[i], label=f"D = {D}")
    plt.xlabel("Flammability q")
    plt.ylabel("Bot 4's success rate (%)")
    plt.title("Bot 4 on three ship sizes")
    plt.legend()
    plt.grid()
    save_chart("ship_size.png")


# how often bot3 and bot4 make at least one move that bot2's rule couldn't have made (a move that isn't
# along a shortest path that avoids the fire), this is how we check if they really decide differently
def plot_divergence(results, qs):
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


# one small bar chart for each bot showing why it failed, as a % of all of that bot's failures
def plot_failure_reasons(results):
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
        plt.subplot(2, 2, i + 1)   # 2 rows and 2 columns of charts, this is chart number i + 1
        plt.bar(labels, shares, color=COLORS[bot])
        plt.ylim(0, 60)
        plt.ylabel("Share of failures (%)")
        plt.title(NAMES[bot])
    plt.tight_layout()
    save_chart("failure_reasons.png")


# the bots that were tried in the tuning run, the way they are named in results/tuning.csv, and the name
# that shows up in the chart. bot4 with a penalty of 10 is the one I ended up using
TUNING_CHOSEN = "bot4 penalty=10"
TUNING_LABELS = [
    ("bot2", "Bot 2"),
    ("bot3", "Bot 3"),
    ("bot4 penalty=5", "Bot 4\npenalty 5"),
    ("bot4 penalty=10", "Bot 4\npenalty 10"),
    ("bot4 penalty=20", "Bot 4\npenalty 20"),
    ("bot4 penalty=30", "Bot 4\npenalty 30"),
]


# the success rate of every setting in the tuning run (800 trials that the main run never uses),
# bot2 and bot3 are there so we can compare against them
def plot_tuning(tuning):
    labels = []
    rates = []
    colors = []
    for bot, label in TUNING_LABELS:
        rows = tuning[tuning["bot"] == bot]
        labels.append(label)
        rates.append(100 * rows["success"].mean())
        colors.append(COLORS[bot[:4]])   # the first 4 letters are the bot's name, like "bot4"
    plt.figure(figsize=(8, 5))
    plt.bar(labels, rates, color=colors)
    for i in range(len(rates)):
        plt.text(i, rates[i], f"{rates[i]:.1f}%", ha="center", va="bottom")   # the number on top of each bar
    plt.ylim(0, 100)
    plt.ylabel("Success rate (%)")
    plt.title("Tuning Bot 4's penalty on 800 separate trials")
    save_chart("tuning.png")


# ------------------------------------------------------------- tables ----

# every bot's success rate at every q, with its 95% confidence interval
def table_success_rates(results, qs):
    report.append("## Success rate (95% CI)\n")
    report.append("| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |")
    report.append("|---|---|---|---|---|")
    for q in qs:
        line = f"| {q:g} |"
        for bot in BOTS:
            rate, error = success_rate(results, q, bot)
            line += f" {100 * rate:.1f}% ± {100 * error:.1f} |"
        report.append(line)


# bot4's success rate minus every other bot's on the same trials, at every q
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


# why each bot fails, and how many of its failures could have been saved: if another bot won the same
# trial (same ship and same fire) then there was a better set of moves the bot could've made
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


# for low, middle and high q: how many trials bot4 lost that bot3 or bot2 won, and the other way around
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


# splits the trials by whether bot3 or bot4 ever made a move bot2's rule couldn't have made, and for each
# group counts the trials it won where bot2 lost and the trials it lost where bot2 won
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


# every tuning setting's success rate minus the chosen bot4's (penalty 10) over all the tuning trials
def tuning_difference(tuning, bot):
    diffs = []
    for q in sorted(tuning["q"].unique()):
        a = column(tuning, q, bot, "success")
        b = column(tuning, q, TUNING_CHOSEN, "success")
        for i in range(len(a)):
            diffs.append(a[i] - b[i])
    mean, error = mean_and_error(diffs)
    return 100 * mean, 100 * error


# the tuning results as a table: every setting's success rate and how far it is from the chosen bot4
def table_tuning(tuning):
    report.append("\n## Bot 4 tuning (800 separate trials)\n")
    report.append("| Bot | Success | Minus the chosen Bot 4 (points) |")
    report.append("|---|---|---|")
    for bot, label in TUNING_LABELS:
        rows = tuning[tuning["bot"] == bot]
        mean, error = tuning_difference(tuning, bot)
        label = label.replace("\n", " ")
        report.append(f"| {label} | {100 * rows['success'].mean():.2f}% | {mean:+.2f} ± {error:.2f} |")


# reads the results, makes every chart and every table, and saves the tables in results/summary.md
def main():
    results = pd.read_csv("results/main.csv")
    tuning = pd.read_csv("results/tuning.csv")
    size = pd.read_csv("results/size.csv")
    qs = sorted(results["q"].unique())

    plot_success_rate(results, qs)
    plot_heat_cost()
    plot_think_time(results)
    plot_bot4_vs_bot2(results, qs)
    plot_ship_size(results, size)
    plot_divergence(results, qs)
    plot_failure_reasons(results)
    plot_tuning(tuning)
    print("Measuring every trial's head start (this takes a couple of minutes)...")
    plot_head_start(results, head_starts(200))

    report.append("# Results\n")
    report.append(f"Main run: D = 50, {len(results) // 4} trials (results/main.csv).\n")
    table_success_rates(results, qs)
    table_differences(results, qs)
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
