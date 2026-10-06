"""Show one of Bot 4's real decisions: what it predicted and which path it chose.

Replays Bot 4 on a trial until the first move where its plan is longer than
the shortest fire-free path (the shortest path is what Bot 2 would take), so
the bot is genuinely trading length for safety. Then it draws the ship at
that moment, with the burning cells, the cells Bot 4 predicted would be on
fire, and both paths on top, and prints the numbers Bot 4 compared.

    python decision.py --D 50 --q 0.3 --trial 5 --out results/examples/decision.png
"""
import argparse

import numpy as np

from analyze import INK, INK_2, SURFACE
from bots import make_bot
from experiments import trial_rng
from planners import avoid_fire, avoid_predicted_fire, predicted_fire
from simulation import Trial

BLOCKED = "#383835"
BURNING = "#d03b00"
PREDICTED = "#f6b26b"
OPEN = "#f4f3ef"


def path_numbers(path, danger, penalty):
    """Steps, predicted-fire cells on the path, and the A* cost Bot 4 gives it."""
    steps = len(path) - 1
    flagged = sum(1 for c in path[1:] if danger[c])
    return {"steps": steps, "flagged": flagged, "cost": steps + penalty * flagged}


def find_decision(trial, options):
    """Replay Bot 4 until it first prefers a longer path; return the state."""
    ship, button, q = trial.ship, trial.button, trial.q
    pos, t = trial.bot_start, 0
    while True:
        burning = trial.fire.burning_at(t)
        plan = avoid_predicted_fire(ship, pos, button, burning, q, **options)
        short = avoid_fire(ship, pos, button, burning, q)
        if plan is None or short is None:
            return None
        if len(plan) > len(short):
            return t, pos, burning, plan, short
        pos, t = plan[1], t + 1
        if pos == button or trial.fire.is_burning(pos, t):
            return None


def draw(trial, pos, burning, danger, plan, short, nums, out, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb
    from matplotlib.patches import Patch

    ship, D = trial.ship, trial.ship.D
    # Colour every cell: wall, open, predicted fire or burning.
    img = np.zeros((D, D, 3))
    img[ship.grid] = to_rgb(OPEN)
    img[~ship.grid] = to_rgb(BLOCKED)
    img[np.array(danger).reshape(D, D)] = to_rgb(PREDICTED)
    img[burning.reshape(D, D)] = to_rgb(BURNING)

    # Zoom to the part of the ship that matters: both paths and the fire.
    cells = [ship.coords(c) for c in plan + short] + list(zip(*np.nonzero(burning.reshape(D, D))))
    rows, cols = zip(*cells)
    r0, r1 = max(min(rows) - 3, 0), min(max(rows) + 3, D - 1)
    c0, c1 = max(min(cols) - 3, 0), min(max(cols) + 3, D - 1)

    fig, ax = plt.subplots(figsize=(7.5, 7.5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.imshow(img, interpolation="nearest")
    for path, style, name in [(short, (0, (3, 2)), "shortest fire-free path (Bot 2's choice)"),
                              (plan, "-", "Bot 4's plan")]:
        rc = np.array([ship.coords(c) for c in path])
        ax.plot(rc[:, 1], rc[:, 0], color=SURFACE, linewidth=4.5, solid_capstyle="round")
        ax.plot(rc[:, 1], rc[:, 0], color=INK, linewidth=2, linestyle=style,
                solid_capstyle="round", label=name)
    for cell, marker, color, name in [(pos, "o", INK, "bot now"),
                                      (trial.button, "*", "#008300", "button")]:
        r, c = ship.coords(cell)
        ax.plot(c, r, marker=marker, markersize=15 if marker == "*" else 10, color=color,
                markeredgecolor=SURFACE, markeredgewidth=1.5, linestyle="none", label=name)
    ax.set_xlim(c0 - 0.5, c1 + 0.5)
    ax.set_ylim(r1 + 0.5, r0 - 0.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    handles, labels = ax.get_legend_handles_labels()
    handles += [Patch(color=BURNING), Patch(color=PREDICTED)]
    labels += ["burning now", "predicted fire (Bot 4 adds the penalty)"]
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=9,
               labelcolor=INK)
    s, b = nums["short"], nums["plan"]
    fig.suptitle(title, x=0.02, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.02, 0.925,
             f"Shortest path: {s['steps']} steps, {s['flagged']} predicted-fire cells, "
             f"cost {s['cost']:g}.   Bot 4's plan: {b['steps']} steps, "
             f"{b['flagged']} predicted-fire cells, cost {b['cost']:g}.",
             color=INK_2, fontsize=9)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.12)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--q", type=float, required=True)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--bot", default="bot4", help="a Bot 4 spec, e.g. bot4:threshold=0.5")
    parser.add_argument("--out", default="decision.png")
    args = parser.parse_args()

    options = make_bot(args.bot).options
    threshold = options.get("threshold", 0.6)
    penalty = options.get("penalty", 20.0)
    trial = Trial.generate(args.D, args.q, trial_rng(args.seed, args.q, args.trial))
    found = find_decision(trial, options)
    if found is None:
        raise SystemExit("Bot 4 never preferred a longer path on this trial")
    t, pos, burning, plan, short = found
    lookahead = options.get("lookahead", True)
    fire_metric = options.get("fire_metric", "maze")
    danger = predicted_fire(trial.ship, pos, trial.button, burning, trial.q, threshold,
                            lookahead, fire_metric)
    nums = {"short": path_numbers(short, danger, penalty),
            "plan": path_numbers(plan, danger, penalty)}
    for name in ("short", "plan"):
        n = nums[name]
        print(f"{name:5s}: {n['steps']} steps, {n['flagged']} predicted-fire cells, "
              f"cost {n['cost']:g}")
    title = (f"Bot 4's decision at move {t + 1}: trial {args.trial}, q = {args.q:g}, "
             f"D = {args.D}")
    draw(trial, pos, burning, danger, plan, short, nums, args.out, title)
    print(f"move {t + 1} -> {args.out}")


if __name__ == "__main__":
    main()
