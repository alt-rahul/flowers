import matplotlib
matplotlib.use("Agg")   # saves the charts as files instead of opening a window for each one
import matplotlib.pyplot as plt
import pandas as pd

from bots import PENALTY

# this file takes all the results that experiments.py saved and turns them into the tables and charts
# that are used in the writeup, you run it with "python analysis.py" once experiments.py is done.
# every table gets saved as a csv file in the results folder (so the numbers in the writeup can be read
# straight off them) and every chart gets saved in the plots folder

NAMES = {"bot1": "Bot 1", "bot2": "Bot 2", "bot3": "Bot 3", "bot4": "Bot 4"}
# each bot always has the same color in every chart so it's easy to follow a bot from one chart to the next,
# these colors were picked so they're still easy to tell apart for someone who is colorblind
COLORS = {"Bot 1": "#2a78d6", "Bot 2": "#eb6834", "Bot 3": "#1baf7a", "Bot 4": "#4a3aa7"}
# for the chart where the lines are different q values (not bots), the lines go from
# light gray for the smallest q to black for the biggest q
GRAYS = ["#9a9a9a", "#5c5c5c", "#1e1e1e"]

# the settings that were tried in the tuning run, the way they are named in results/tuning.csv, and the name
# that shows up in the chart. bot4 with a penalty of 10 is the one I ended up using
TUNING_LABELS = {
    "bot2": "Bot 2",
    "bot3": "Bot 3",
    "bot4 penalty=5": "Bot 4\npenalty 5",
    "bot4 penalty=10": "Bot 4\npenalty 10",
    "bot4 penalty=20": "Bot 4\npenalty 20",
    "bot4 penalty=30": "Bot 4\npenalty 30",
}


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# ------------------------------------------------------------- tables ----

# the average of one column (like "close_calls") for every bot at every q, as a table with
# one row for each q and one column for each bot
def by_q(results, column):
    table = results.pivot_table(index="q", columns="bot", values=column)
    table.columns = [NAMES[bot] for bot in table.columns]
    return table


# every q uses the same 200 ships with the same fire seed, so for every ship we can find the lowest q where
# a bot first loses it, which I call its "breaking point". one row for each ship and one column for each bot,
# and a ship the bot never loses is left empty
def breaking_points(results):
    losses = results[results["success"] == 0]
    table = losses.pivot_table(index="trial", columns="bot", values="q", aggfunc="min")
    table = table.reindex(sorted(results["trial"].unique()))   # adds back the ships no bot ever loses, as empty rows
    table.columns = [NAMES[bot] for bot in table.columns]
    return table


# for every bot: how many ships it never loses at any q, and its average breaking point on the ships that every
# bot loses at some q (using the same ships for every bot keeps it fair)
def breaking_point_summary(points):
    lost_by_all = points.dropna()   # dropna removes the ships that some bot never loses
    rows = []
    for name in points.columns:
        rows.append([name, points[name].isna().sum(), round(lost_by_all[name].mean(), 3)])
    return pd.DataFrame(rows, columns=["bot", "ships never lost",
                                       f"average breaking point on the {len(lost_by_all)} ships every bot loses"])


# for every q, the % of ships a bot has won at every q up to that one (it hasn't hit its breaking point yet)
def unbeaten_by_q(points, qs):
    table = pd.DataFrame(index=qs)
    for name in points.columns:
        values = []
        for q in qs:
            lost = (points[name] <= q).sum()   # ships already lost at this q or before (empty ones never count)
            values.append(100 * (len(points) - lost) / len(points))
        table[name] = values
    return table


# ------------------------------------------------------------- charts ----

# draws one line for every column of the table (one column per bot) with q along the bottom,
# every line chart in the writeup is drawn by this one function so they all look the same
def line_chart(table, ylabel, title, filename):
    plt.figure(figsize=(8, 5))
    for name in table.columns:
        plt.plot(table.index, table[name], marker="o", markersize=3, color=COLORS[name], label=name)
    plt.xlabel("Flammability q")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid()
    save_chart(filename)


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


# the success rate of every setting in the tuning run (800 trials that the main run never uses),
# bot2 and bot3 are there so we can compare against them
def plot_tuning(overall):
    labels = []
    colors = []
    for name in overall.index:
        labels.append(TUNING_LABELS[name])
        colors.append(COLORS[NAMES[name[:4]]])   # the first 4 letters are the bot's name, like "bot4"
    plt.figure(figsize=(8, 5))
    plt.bar(labels, overall, color=colors)
    for i in range(len(overall)):
        plt.text(i, overall.iloc[i], f"{overall.iloc[i]:.1f}%", ha="center", va="bottom")   # the number on top of each bar
    plt.ylim(0, 100)
    plt.ylabel("Success rate (%)")
    plt.title("Tuning Bot 4's penalty on 800 separate trials")
    save_chart("tuning.png")


# reads the results, makes every table (saved as csv files) and draws every chart from those tables
def main():
    results = pd.read_csv("results/main.csv")
    tuning = pd.read_csv("results/tuning.csv")
    size = pd.read_csv("results/size.csv")
    qs = sorted(results["q"].unique())

    # success rate (%) of every bot at every q (experiments.py already saved it as results/success_by_q.csv)
    success = 100 * by_q(results, "success")

    # the two things counted during every run (close calls per 100 runs, since they are rare)
    close_calls = (100 * by_q(results, "close_calls")).round(1)
    change_plan = by_q(results, "change_plan").round(2)[["Bot 2", "Bot 3", "Bot 4"]]   # bot1 is always 0
    close_calls.to_csv("results/close_calls_by_q.csv")
    change_plan.to_csv("results/change_plan_by_q.csv")

    # breaking points
    points = breaking_points(results)
    points.to_csv("results/breaking_point_by_ship.csv")
    breaking_point_summary(points).to_csv("results/breaking_point_summary.csv", index=False)
    unbeaten = unbeaten_by_q(points, qs)

    # time to decide one move (ms), the total thinking time divided by the total number of moves
    think_time = (results.groupby("bot")["ms"].sum() / results.groupby("bot")["steps"].sum()).round(2)
    think_time.to_csv("results/think_time.csv", header=["ms per move"])

    # tuning: the success rate (%) of every setting at every q, and over all of the tuning trials
    tuning_table = (100 * tuning.pivot_table(index="bot", columns="q", values="success")).round(1)
    tuning_table["all q"] = (100 * tuning.groupby("bot")["success"].mean()).round(2)
    tuning_table = tuning_table.reindex(list(TUNING_LABELS))   # puts the settings in the order of TUNING_LABELS
    tuning_table.to_csv("results/tuning_by_q.csv")

    # ship size: bot4's success rate (%) at each q on the 25, 50 and 100 ships
    size_table = (100 * size.pivot_table(index="q", columns="D", values="success")).round(1)
    size_table[50] = success["Bot 4"]   # the 50 by 50 ship comes from the main run
    size_table = size_table[[25, 50, 100]]
    size_table.to_csv("results/size_by_q.csv")

    line_chart(success, "Success rate (%)", "Success rate vs flammability q", "success_rate.png")
    plot_heat_cost()
    line_chart(close_calls, "Close calls per 100 runs", "How often a bot ends a move right next to the fire",
               "close_calls.png")
    line_chart(change_plan, "Changes of mind per run", "How often a bot switches to a different route",
               "change_plan.png")
    line_chart(unbeaten, "Ships never lost up to this q (%)", "How much fire a bot can handle on the same ship",
               "breaking_point.png")
    plot_tuning(tuning_table["all q"])
    print("Tables saved in results/, charts saved in plots/")


if __name__ == "__main__":
    main()
