"""Extra charts for the writeup (plain matplotlib).

    python figures.py --out results

Draws:
    ship_phases.png    one ship after phase 1 and after phase 2, dead ends marked
    danger_radius.png  how far from the fire Bot 4's predicted fire reaches, for several q
    ship_size.png      Bot 4's success rate on ships of size D = 25, 50 and 100
    head_to_head.png   per q, trials Bot 4 won that Bot 2 / Bot 3 lost, and the reverse
    tuning.png         every Bot 4 setting tried, against the chosen one
"""
import argparse
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")   # draw straight to PNG files, no window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from analyze import BOT_COLORS, BOT_MARKERS, load, wilson
from planners import danger_radius
from ship import Ship


def save(path):
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def ship_phases(path, D=30, seed=3):
    """The same ship after phase 1 (a tree, lots of dead ends) and after phase 2
    (dead ends halved, loops added)."""
    rng = np.random.default_rng(seed)
    ship = Ship(D)
    ship.grow_maze(rng)
    after_phase1 = [[ship.grid[r][c].is_open for c in range(D)] for r in range(D)]
    ends1 = set(ship.dead_ends())
    ship.reduce_dead_ends(rng)
    ends2 = set(ship.dead_ends())

    def picture(phase):
        # 0 wall, 1 open, 2 dead end, 3 opened in phase 2
        rows = []
        for r in range(D):
            row = []
            for c in range(D):
                if phase == 1:
                    is_open = after_phase1[r][c]
                    ends = ends1
                else:
                    is_open = ship.grid[r][c].is_open
                    ends = ends2
                if not is_open:
                    row.append(0)
                elif (r, c) in ends:
                    row.append(2)
                elif phase == 2 and not after_phase1[r][c]:
                    row.append(3)
                else:
                    row.append(1)
            rows.append(row)
        return rows

    colors = ListedColormap(["black", "white", "#eb6834", "#2a78d6"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.4))
    axes[0].imshow(picture(1), cmap=colors, vmin=0, vmax=3)
    axes[0].set_title(f"After phase 1: {len(ends1)} dead ends")
    axes[1].imshow(picture(2), cmap=colors, vmin=0, vmax=3)
    axes[1].set_title(f"After phase 2: {len(ends2)} dead ends")
    for ax in axes:
        ax.axis("off")
    fig.legend(handles=[Patch(color="#eb6834", label="dead end"),
                        Patch(color="#2a78d6", label="opened in phase 2")],
               loc="lower center", ncol=2, frameon=False)
    save(path)


def danger_radius_chart(path, qs=(0.1, 0.2, 0.3, 0.5, 0.8), threshold=0.6, max_k=40):
    """For a cell the bot reaches in k moves: the largest fire distance d at
    which Bot 4 still predicts the fire gets there first. Bot 3's buffer is
    d <= 1 whatever k is."""
    plt.figure(figsize=(8, 5))
    shades = plt.cm.Purples(np.linspace(0.45, 1.0, len(qs)))   # one hue, light to dark
    ks = list(range(max_k + 1))
    for q, shade in zip(qs, shades):
        radius = danger_radius(q, threshold, max_k)
        plt.plot(ks, radius, drawstyle="steps-post", color=shade, linewidth=2,
                 label=f"Bot 4, q = {q:g}")
    plt.axhline(1, color="#1baf7a", linestyle="--", linewidth=2,
                label="Bot 3's buffer (d = 1 at every k)")
    plt.xlabel("Moves the bot needs to reach the cell (k)")
    plt.ylabel("Largest fire distance d treated as fire")
    plt.title("Which cells Bot 4 treats as predicted fire (threshold 0.6)")
    plt.legend()
    plt.grid(alpha=0.3)
    save(path)


def ship_size_chart(path, main_rows, size_rows):
    """Bot 4's success rate (95% CI) against q for each ship size."""
    groups = defaultdict(list)
    size_qs = {r["q"] for r in size_rows}
    for r in main_rows + size_rows:
        if r["bot"] == "bot4" and r["q"] in size_qs:
            groups[(r["D"], r["q"])].append(r["success"])
    plt.figure(figsize=(8, 5))
    shades = plt.cm.Purples([0.5, 0.75, 1.0])
    for D, shade in zip(sorted({d for d, q in groups}), shades):
        qs = sorted(q for d, q in groups if d == D)
        rates, low, high = [], [], []
        for q in qs:
            wins = groups[(D, q)]
            rate = sum(wins) / len(wins)
            lo, hi = wilson(sum(wins), len(wins))
            rates.append(rate)
            low.append(rate - lo)
            high.append(hi - rate)
        plt.errorbar(qs, rates, yerr=[low, high], marker="o", markersize=4, capsize=2,
                     color=shade, label=f"D = {D}")
    plt.xlabel("Flammability q")
    plt.ylabel("Bot 4's success rate")
    plt.title("Bot 4 on three ship sizes (95% CI)")
    plt.legend()
    plt.grid(alpha=0.3)
    save(path)


def head_to_head_chart(path, rows):
    """Per q, out of every 1,000 trials: how many Bot 4 won while the rival
    lost, and how many the rival won while Bot 4 lost."""
    by_trial = defaultdict(dict)
    for r in rows:
        by_trial[(r["q"], r["trial"])][r["bot"]] = r["success"]
    qs = sorted({q for q, t in by_trial})
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    for ax, rival in zip(axes, ["bot2", "bot3"]):
        won, lost = [], []
        for q in qs:
            results = [v for (qq, t), v in by_trial.items() if qq == q]
            won.append(1000 * sum(v["bot4"] and not v[rival] for v in results) / len(results))
            lost.append(1000 * sum(v[rival] and not v["bot4"] for v in results) / len(results))
        name = f"Bot {rival[3:]}"
        ax.plot(qs, won, marker=BOT_MARKERS["bot4"], markersize=4, color=BOT_COLORS["bot4"],
                label=f"Bot 4 won, {name} lost")
        ax.plot(qs, lost, marker=BOT_MARKERS[rival], markersize=4, color=BOT_COLORS[rival],
                label=f"{name} won, Bot 4 lost")
        ax.set_title(f"Bot 4 against {name}, same trials")
        ax.set_xlabel("Flammability q")
        ax.grid(alpha=0.3)
        ax.legend()
    axes[0].set_ylabel("Trials per 1,000")
    save(path)


def tuning_chart(path, rows, chosen="bot4:threshold=0.6,penalty=20"):
    """Every setting tried in tuning: success minus the chosen setting's on
    the same trials, pooled over q, in points with a 95% CI."""
    by_trial = defaultdict(dict)
    for r in rows:
        by_trial[(r["q"], r["trial"])][r["bot"]] = r["success"]
    variants = [
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
    plt.figure(figsize=(8, 5.5))
    for y, (spec, label) in enumerate(variants):
        diffs = np.array([v[spec] - v[chosen] for v in by_trial.values()], dtype=float)
        mean = 100 * diffs.mean()
        half = 100 * 1.96 * diffs.std(ddof=1) / math.sqrt(len(diffs))
        bot = spec.split(":")[0]
        plt.errorbar(mean, y, xerr=half, marker=BOT_MARKERS[bot], markersize=6, capsize=3,
                     color=BOT_COLORS[bot])
    plt.axvline(0, color="black", linewidth=1)
    plt.yticks(range(len(variants)), [label for spec, label in variants])
    plt.gca().invert_yaxis()
    plt.xlabel("Success rate minus the chosen Bot 4 (θ = 0.6, λ = 20), in points")
    plt.title("Bot 4 tuning: 4,000 separate trials, 95% CI")
    plt.grid(alpha=0.3, axis="x")
    save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="results")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    ship_phases(os.path.join(args.out, "ship_phases.png"))
    danger_radius_chart(os.path.join(args.out, "danger_radius.png"))
    main_rows = load(["results/main.csv.gz"])
    ship_size_chart(os.path.join(args.out, "ship_size.png"), main_rows,
                    load(["results/size.csv.gz"]))
    head_to_head_chart(os.path.join(args.out, "head_to_head.png"), main_rows)
    tuning_chart(os.path.join(args.out, "tuning.png"), load(["results/tuning.csv.gz"]))
    print(f"charts written to {args.out}")


if __name__ == "__main__":
    main()
