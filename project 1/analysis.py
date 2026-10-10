import matplotlib
matplotlib.use("Agg")   # saves the charts as files instead of opening a window for each one
import matplotlib.pyplot as plt
import pandas as pd

from bots import PENALTY

# this file takes all the results that experiments.py saved and turns them into the charts and tables
# that are used in the writeup, you run it with "python analysis.py" once experiments.py is done.
# the charts get saved in the plots folder and the tables get saved in results/summary.md

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
# each bot always has the same color in every chart so it's easy to follow a bot from one chart to the next,
# these colors were picked so they're still easy to tell apart for someone who is colorblind
COLORS = {"bot1": "#2a78d6", "bot2": "#eb6834", "bot3": "#1baf7a", "bot4": "#4a3aa7"}
# for the chart where the lines are different q values (not bots), the lines go from
# light gray for the smallest q to black for the biggest q
GRAYS = ["#9a9a9a", "#5c5c5c", "#1e1e1e"]

report = []   # every line of results/summary.md, it gets written to the file at the very end


# gets one column of the results (like "success") for one bot at one q, as a list sorted by the trial number
# so that the same index in two lists is always the same trial (same ship and same fire)
def column(results, q, bot, name):
    rows = results[(results["q"] == q) & (results["bot"] == bot)]
    rows = rows.sort_values("trial")
    return list(rows[name])


# calculates the mean (the average) of a list of numbers
def mean(values):
    return sum(values) / len(values)


# the success rate of a bot at q (a success is 1 and a failure is 0, so the mean is the success rate)
def success_rate(results, q, bot):
    return mean(column(results, q, bot, "success"))


# compares two bots on the exact same trials: for every trial, bot_a's result minus bot_b's result
# gives 1 (only bot_a won), -1 (only bot_b won) or 0 (both won or both lost), the mean of that is
# how much better bot_a did. this is much more exact than comparing two separate success rates
def paired_difference(results, q, bot_a, bot_b):
    a = column(results, q, bot_a, "success")
    b = column(results, q, bot_b, "success")
    diffs = []
    for i in range(len(a)):
        diffs.append(a[i] - b[i])
    return mean(diffs)


# the average of one column (like "close_calls") for one bot at one q. if only_wins is True it only uses
# the trials the bot won, since the victory margin only exists when the bot wins
def average(results, q, bot, name, only_wins=False):
    rows = results[(results["q"] == q) & (results["bot"] == bot)]
    if only_wins:
        rows = rows[rows["success"] == 1]
    return rows[name].mean()


# every q uses the same 200 ships with the same fire seed, so for every ship we can find the lowest q where
# the bot first loses it, which I call its "breaking point". a ship the bot never loses gets None
def breaking_points(results, qs, bot):
    points = {}   # trial -> breaking point
    for trial in sorted(results["trial"].unique()):
        points[trial] = None
    for q in qs:   # qs goes from the smallest q to the biggest, so the first loss we find is the lowest q
        rows = results[(results["q"] == q) & (results["bot"] == bot)]
        trials = list(rows["trial"])
        successes = list(rows["success"])
        for i in range(len(trials)):
            if successes[i] == 0 and points[trials[i]] is None:
                points[trials[i]] = q
    return points


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
            rate = success_rate(results, q, bot)
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


# how many moves per run a bot ends up right next to a burning cell, on average, at every q
def plot_close_calls(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        values = []
        for q in qs:
            values.append(average(results, q, bot, "close_calls"))
        plt.plot(qs, values, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Close calls per run")
    plt.title("How often a bot ends a move right next to the fire")
    plt.legend()
    plt.grid()
    save_chart("close_calls.png")


# how many times per run a bot throws away its plan for a different route, on average, at every q
# (bot1 never plans again, so it's always 0 and it's left out)
def plot_mind_changes(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in ["bot2", "bot3", "bot4"]:
        values = []
        for q in qs:
            values.append(average(results, q, bot, "mind_changes"))
        plt.plot(qs, values, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Changes of mind per run")
    plt.title("How often a bot switches to a different route")
    plt.legend()
    plt.grid()
    save_chart("mind_changes.png")


# when a bot wins, how many moves the fire still needed to reach the button, on average, at every q.
# a small number means it was a narrow escape
def plot_victory_margin(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        values = []
        for q in qs:
            values.append(average(results, q, bot, "victory_margin", only_wins=True))
        plt.plot(qs, values, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Moves the fire still needed to reach the button")
    plt.title("How close the fire was when the button got pressed")
    plt.legend()
    plt.grid()
    save_chart("victory_margin.png")


# for every q, the % of ships a bot has won at every q up to that one (it hasn't hit its breaking point yet).
# this line can only go down, and where it ends at q = 1 is the % of ships the bot never loses
def plot_breaking_point(results, qs):
    plt.figure(figsize=(8, 5))
    for bot in BOTS:
        points = breaking_points(results, qs, bot)
        unbeaten = []
        for q in qs:
            count = 0
            for trial in points:
                if points[trial] is None or points[trial] > q:
                    count += 1
            unbeaten.append(100 * count / len(points))
        plt.plot(qs, unbeaten, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel("Ships never lost up to this q (%)")
    plt.title("How much fire a bot can handle on the same ship")
    plt.legend()
    plt.grid()
    save_chart("breaking_point.png")


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

# every bot's success rate at every q
def table_success_rates(results, qs):
    report.append("## Success rate (%)\n")
    report.append("| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 |")
    report.append("|---|---|---|---|---|")
    for q in qs:
        line = f"| {q:g} |"
        for bot in BOTS:
            rate = success_rate(results, q, bot)
            line += f" {100 * rate:.1f}% |"
        report.append(line)


# bot4's success rate minus every other bot's on the same trials, at every q
def table_differences(results, qs):
    report.append("\n## Bot 4 minus each other bot, same trials (percentage points)\n")
    report.append("| q | vs Bot 1 | vs Bot 2 | vs Bot 3 |")
    report.append("|---|---|---|---|")
    for q in qs:
        line = f"| {q:g} |"
        for bot in ["bot1", "bot2", "bot3"]:
            diff = paired_difference(results, q, "bot4", bot)
            line += f" {100 * diff:+.1f} |"
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


# the new metrics for every bot at every 0.1 of q: close calls per run, changes of mind per run and the
# victory margin, all as one dataframe that also gets saved to results/new_metrics.csv
def new_metrics_table(results, qs):
    rows = []
    for q in qs:
        for bot in BOTS:
            rows.append([q, NAMES[bot], round(100 * success_rate(results, q, bot), 1),
                         round(average(results, q, bot, "close_calls"), 2),
                         round(average(results, q, bot, "mind_changes"), 2),
                         round(average(results, q, bot, "victory_margin", only_wins=True), 1)])
    return pd.DataFrame(rows, columns=["q", "bot", "success rate (%)", "close calls per run",
                                       "changes of mind per run", "victory margin (moves)"])


# for every bot: how many ships it never loses at any q, and the average breaking point of the ships it does lose
def breaking_point_table(results, qs):
    rows = []
    for bot in BOTS:
        points = breaking_points(results, qs, bot)
        lost = []
        never = 0
        for trial in points:
            if points[trial] is None:
                never += 1
            else:
                lost.append(points[trial])
        rows.append([NAMES[bot], never, len(lost), round(mean(lost), 2)])
    return pd.DataFrame(rows, columns=["bot", "ships never lost", "ships lost at some q", "average breaking point q"])


# every tuning setting's success rate minus the chosen bot4's (penalty 10) over all the tuning trials
def tuning_difference(tuning, bot):
    diffs = []
    for q in sorted(tuning["q"].unique()):
        a = column(tuning, q, bot, "success")
        b = column(tuning, q, TUNING_CHOSEN, "success")
        for i in range(len(a)):
            diffs.append(a[i] - b[i])
    return 100 * mean(diffs)


# the tuning results as a table: every setting's success rate and how far it is from the chosen bot4
def table_tuning(tuning):
    report.append("\n## Bot 4 tuning (800 separate trials)\n")
    report.append("| Bot | Success | Minus the chosen Bot 4 (points) |")
    report.append("|---|---|---|")
    for bot, label in TUNING_LABELS:
        rows = tuning[tuning["bot"] == bot]
        difference = tuning_difference(tuning, bot)
        label = label.replace("\n", " ")
        report.append(f"| {label} | {100 * rows['success'].mean():.2f}% | {difference:+.2f} |")


# reads the results, makes every chart and every table, and saves the tables in results/summary.md
# and the two new dataframes in results/new_metrics.csv and results/breaking_point.csv
def main():
    results = pd.read_csv("results/main.csv")
    tuning = pd.read_csv("results/tuning.csv")
    qs = sorted(results["q"].unique())

    plot_success_rate(results, qs)
    plot_heat_cost()
    plot_divergence(results, qs)
    plot_close_calls(results, qs)
    plot_mind_changes(results, qs)
    plot_victory_margin(results, qs)
    plot_breaking_point(results, qs)
    plot_tuning(tuning)

    new_metrics = new_metrics_table(results, qs)
    new_metrics.to_csv("results/new_metrics.csv", index=False)
    breaking = breaking_point_table(results, qs)
    breaking.to_csv("results/breaking_point.csv", index=False)

    report.append("# Results\n")
    report.append(f"Main run: D = 50, {len(results) // 4} trials (results/main.csv).\n")
    table_success_rates(results, qs)
    table_differences(results, qs)
    table_divergence(results, qs)
    report.append("\n## New metrics (every q, also in results/new_metrics.csv)\n")
    report.append("```\n" + new_metrics.to_string(index=False) + "\n```")
    report.append("\n## Breaking point (also in results/breaking_point.csv)\n")
    report.append("```\n" + breaking.to_string(index=False) + "\n```")
    table_tuning(tuning)

    with open("results/summary.md", "w") as f:
        f.write("\n".join(report) + "\n")
    print("\n".join(report))
    print("\nCharts saved in plots/, tables in results/summary.md")


if __name__ == "__main__":
    main()
