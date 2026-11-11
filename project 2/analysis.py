import matplotlib
matplotlib.use("Agg")   # saves the charts as files instead of opening a window for each one
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments import average

# this file draws the charts that are used in the writeup from the tables that experiments.py saved,
# run this after you run experiments and the charts get saved in the plots folder

# the same colors as project 1: my strategies are purple like bot 4 was, the baseline is blue
COLORS = {"baseline": "#2a78d6", "mine (normal)": "#4a3aa7", "mine": "#4a3aa7", "mine (free moves)": "#1baf7a"}
GRAYS = ["#9a9a9a", "#5c5c5c", "#1e1e1e"]


def save_chart(name):
    plt.savefig("plots/" + name, dpi=120, bbox_inches="tight")
    plt.close()


# draws one line for every strategy in the table, with k or alpha along the bottom and the average cost going up
# (ylabel says what the cost is, since when moving is free only the detector counts).
# for alpha the x axis is on a log scale since the values go from 0.01 to 3, and log_y does the same for the cost
# when the baseline costs are way bigger than mine
def line_chart(table, strategies, xlabel, ylabel, title, filename, log_x=False, log_y=False):
    x = table.columns[0]
    plt.figure(figsize=(8, 5))
    for strategy in strategies:
        # my free moves line is dashed so it's easy to tell apart from my normal strategy
        style = "--" if strategy == "mine (free moves)" else "-"
        plt.plot(table[x], table[strategy], style, marker="o", markersize=4, color=COLORS[strategy], label=strategy)
    if log_x:
        plt.xscale("log")
    if log_y:
        plt.yscale("log")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid()
    save_chart(filename)


# shows how alpha changes the type B detector: the chance of a ping based on how far away the LostBot is,
# for a small, a medium and a big alpha. the dashed line is a 50/50 chance
def plot_ping_chance():
    distances = np.arange(1, 31)
    alphas = [0.05, 0.2, 1.0]
    plt.figure(figsize=(8, 5))
    for i in range(len(alphas)):
        chances = np.exp(-alphas[i] * (distances - 1))
        plt.plot(distances, chances, marker="o", markersize=3, color=GRAYS[i], label=f"alpha = {alphas[i]}")
    plt.axhline(0.5, color="black", linestyle="--", label="a 50/50 chance")
    plt.xlabel("Distance between the two bots (d)")
    plt.ylabel("Chance of a ping")
    plt.title("How alpha changes the type B detector")
    plt.legend()
    plt.grid()
    save_chart("ping_chance.png")


# a bar chart of where the cost goes (moves vs detector uses) for each strategy, at the k and alpha where my
# strategies did best. for each strategy there are two bars next to each other: the cost of moving and the
# cost of running the detector
def plot_cost_breakdown(results, best_k, best_alpha):
    labels = []
    move_costs = []
    reading_costs = []
    for detector, setting in [("A", best_k), ("B", best_alpha)]:
        for strategy in ["baseline", "mine"]:
            labels.append(f"Type {detector}\n{strategy}")
            move_costs.append(average(results, detector, setting, strategy, False, "moves"))
            reading_costs.append(0.5 * average(results, detector, setting, strategy, False, "readings"))
    x = np.arange(len(labels))
    plt.figure(figsize=(8, 5))
    plt.bar(x - 0.2, move_costs, width=0.4, color="#5c5c5c", label="moves")
    plt.bar(x + 0.2, reading_costs, width=0.4, color="#9a9a9a", label="1/2 x detector uses")
    plt.xticks(x, labels)
    plt.ylabel("Average cost")
    plt.title(f"Where the cost goes (k = {best_k}, alpha = {best_alpha})")
    plt.legend()
    save_chart("cost_breakdown.png")


# the k (or alpha) in the first column of the table where my strategy had the lowest average cost
def lowest_setting(table):
    settings = list(table[table.columns[0]])
    costs = list(table["mine"])
    best = 0
    for i in range(len(costs)):
        if costs[i] < costs[best]:
            best = i
    return settings[best]


# reads the tables and draws every chart
def main():
    results = pd.read_csv("results/main.csv").values.tolist()   # every search as a list, like in experiments.py
    type_a = pd.read_csv("results/type_a_cost.csv")
    type_b = pd.read_csv("results/type_b_cost.csv")
    type_a_free = pd.read_csv("results/type_a_free_moves.csv")
    type_b_free = pd.read_csv("results/type_b_free_moves.csv")

    plot_ping_chance()
    cost = "Average cost (moves + 1/2 detector uses)"
    free_cost = "Average cost (1/2 detector uses, moving is free)"
    line_chart(type_a, ["baseline", "mine"], "k (the square is 2k + 1 by 2k + 1)", cost,
               "Type A: cost of finding the LostBot vs k", "cost_vs_k.png")
    line_chart(type_b, ["baseline", "mine"], "alpha", cost, "Type B: cost of finding the LostBot vs alpha",
               "cost_vs_alpha.png", log_x=True, log_y=True)
    free_strategies = ["baseline", "mine (normal)", "mine (free moves)"]
    line_chart(type_a_free, free_strategies, "k (the square is 2k + 1 by 2k + 1)", free_cost,
               "Type A when moving is free", "free_moves_k.png")
    line_chart(type_b_free, free_strategies, "alpha", free_cost, "Type B when moving is free",
               "free_moves_alpha.png", log_x=True)

    # the k and alpha where my strategy had the lowest average cost
    best_k = int(lowest_setting(type_a))
    best_alpha = lowest_setting(type_b)
    plot_cost_breakdown(results, best_k, best_alpha)


if __name__ == "__main__":
    main()
