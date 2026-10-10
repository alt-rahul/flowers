import matplotlib
matplotlib.use("Agg")   # saves the charts as files instead of opening a window for each one
import matplotlib.pyplot as plt
import pandas as pd

from bots import PENALTY

# this file draws the charts that are used in the writeup from the results that experiments.py saved,
# you run it with "python analysis.py" once experiments.py is done. the charts get saved in the plots folder,
# and the numbers behind the close calls, changes of mind and failure reasons charts get saved as csv files
# in the results folder

BOTS = ["bot1", "bot2", "bot3", "bot4"]
NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
# each bot always has the same color in every chart so it's easy to follow a bot from one chart to the next,
# these colors were picked so they're still easy to tell apart for someone who is colorblind
COLORS = {"bot1": "#2a78d6", "bot2": "#eb6834", "bot3": "#1baf7a", "bot4": "#4a3aa7"}
# the reasons a bot can fail, and the names that show up in the chart for them
REASONS = ["entered_fire", "caught", "button_burned", "trapped"]
REASON_LABELS = ["walked\ninto fire", "fire spread\nonto bot", "button\nburned first", "cut off\nfrom button"]
# for the chart where the lines are different q values (not bots), the lines go from
# light gray for the smallest q to black for the biggest q
GRAYS = ["#9a9a9a", "#5c5c5c", "#1e1e1e"]


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# the average of one column (like "success") for one bot at every q, as a list in the same order as qs
def average_by_q(results, bot, column, qs):
    values = []
    for q in qs:
        rows = results[(results["q"] == q) & (results["bot"] == bot)]
        values.append(rows[column].mean())
    return values


# draws one line for every bot, with q along the bottom and the average of one column going up, every line
# chart in the writeup is drawn by this one function so they all look the same. scale multiplies every value
# (100 turns a success rate into a %, or a count per run into a count per 100 runs). it also returns the numbers
# it drew as a table, one row for each q and one column for each bot
def line_chart(results, qs, bots, column, scale, ylabel, title, filename):
    table = pd.DataFrame({"q": qs})
    plt.figure(figsize=(8, 5))
    for bot in bots:
        values = []
        for value in average_by_q(results, bot, column, qs):
            values.append(round(scale * value, 2))
        table[NAMES[bot]] = values
        plt.plot(qs, values, marker="o", markersize=3, color=COLORS[bot], label=NAMES[bot])
    plt.xlabel("Flammability q")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid()
    save_chart(filename)
    return table


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


# one small bar chart for each bot showing why it failed, as a % of all of that bot's failures (over every q),
# it also returns those %s as a table, one row for each reason and one column for each bot
def plot_failure_reasons(results):
    table = pd.DataFrame({"reason": REASONS})
    plt.figure(figsize=(10, 7))
    for i in range(len(BOTS)):
        bot = BOTS[i]
        failures = results[(results["bot"] == bot) & (results["success"] == 0)]
        shares = []
        for reason in REASONS:
            count = len(failures[failures["reason"] == reason])
            shares.append(round(100 * count / len(failures), 1))
        table[NAMES[bot]] = shares
        plt.subplot(2, 2, i + 1)   # 2 rows and 2 columns of charts, this is chart number i + 1
        plt.bar(REASON_LABELS, shares, color=COLORS[bot])
        plt.ylim(0, 60)
        plt.ylabel("Share of failures (%)")
        plt.title(NAMES[bot])
    plt.tight_layout()
    save_chart("failure_reasons.png")
    return table


# reads the results and draws the six charts
def main():
    results = pd.read_csv("results/main.csv")
    qs = sorted(results["q"].unique())

    plot_heat_cost()
    plot_think_time(results)
    line_chart(results, qs, BOTS, "success", 100, "Success rate (%)", "Success rate vs flammability q",
               "success_rate.png")
    close_calls = line_chart(results, qs, BOTS, "close_calls", 100, "Close calls per 100 runs",
                             "How often a bot ends a move right next to the fire", "close_calls.png")
    close_calls.to_csv("results/close_calls_by_q.csv", index=False)
    # bot1 never plans again, so it never changes its mind and it's left out
    change_plan = line_chart(results, qs, ["bot2", "bot3", "bot4"], "change_plan", 1, "Changes of mind per run",
                             "How often a bot switches to a different route", "change_plan.png")
    change_plan.to_csv("results/change_plan_by_q.csv", index=False)
    failure_reasons = plot_failure_reasons(results)
    failure_reasons.to_csv("results/failure_reasons.csv", index=False)
    print("Charts saved in plots/")


if __name__ == "__main__":
    main()
