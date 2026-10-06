"""Show one of Bot 4's real decisions: what it forecast and which path it chose.

Replays Bot 4 on a trial until the first move where its plan is longer than
the shortest fire-free path (the shortest path is what Bot 2 would take), so
the bot is genuinely trading length for safety. Then it draws the fire
forecast at two future times with both paths on top, and prints the numbers
Bot 4 compared.

    python decision.py --D 50 --q 0.3 --trial 5 --out results/decision_example.png
"""
from __future__ import annotations

import argparse
import math

import numpy as np

from analyze import INK, INK_2, SURFACE
from bots import Bot4
from experiments import trial_rng
from forecast import MessagePassingForecast
from planning import bfs_path, fire_distances, fireproof_path, risk_astar
from simulation import Trial

BLOCKED = "#383835"


def path_numbers(path, button, forecast, w):
    """Steps, summed risk, cost, riskiest non-button cell, and the chance the
    button is burning when the path reaches it."""
    risks = [forecast.risk_at(k - 1 if c == button else k)[c]
             for k, c in enumerate(path[1:], start=1)]
    steps = len(path) - 1
    worst = max((-math.expm1(-forecast.risk_at(k)[c]) for k, c in enumerate(path[1:-1], 1)),
                default=0.0)
    return {"steps": steps, "risk": sum(risks), "cost": steps + w * sum(risks),
            "worst_cell": worst, "button": float(forecast.prob_at(steps - 1)[button])}


def find_decision(trial: Trial, w: float):
    """Replay Bot 4 until it first prefers a longer path; return the state."""
    ship, button = trial.ship, trial.button
    heuristic = ship.distances_from(button)
    pos, t = trial.bot_start, 0
    while True:
        burning = trial.fire.burning_at(t)
        fire_dist = fire_distances(ship.neighbors, np.flatnonzero(burning).tolist(), len(burning))
        if fireproof_path(ship.neighbors, pos, button, fire_dist) is not None:
            return None  # Bot 4 commits to a certain win from here on
        forecast = MessagePassingForecast(ship, trial.q, burning)
        plan = risk_astar(ship.neighbors, pos, button, heuristic, forecast.risk_at, w)
        short = bfs_path(ship.neighbors, pos, button, burning.tolist())
        if plan is None or short is None:
            return None
        if len(plan) > len(short):
            return t, pos, burning, forecast, plan, short
        pos, t = plan[1], t + 1
        if pos == button or trial.fire.is_burning(pos, t):
            return None


def draw(trial, t, pos, forecast, plan, short, nums, out, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb

    from matplotlib.colors import LinearSegmentedColormap

    ship, D = trial.ship, trial.ship.D
    # The darkest tenth of "Oranges" is nearly black; drop it so burning cells
    # stay distinct from walls.
    cmap = LinearSegmentedColormap.from_list(
        "fire", plt.get_cmap("Oranges")(np.linspace(0, 0.9, 256)))
    horizons = [(10, "10 steps ahead"),
                (nums["short"]["steps"] - 1, "when the shortest path would reach the button")]
    # Zoom to the part of the ship that matters: both paths plus everywhere
    # the forecast gives the fire a real chance by the later horizon.
    later = forecast.prob_at(horizons[-1][0]).reshape(D, D)
    cells = [ship.coords(c) for c in plan + short] + list(zip(*np.nonzero(later > 0.05)))
    rows, cols = zip(*cells)
    r0, r1 = max(min(rows) - 3, 0), min(max(rows) + 3, D - 1)
    c0, c1 = max(min(cols) - 3, 0), min(max(cols) + 3, D - 1)
    fig, axes = plt.subplots(1, 2, figsize=(11, 6.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    for ax, (h, label) in zip(axes, horizons):
        p = forecast.prob_at(h).reshape(D, D)
        img = cmap(p)[:, :, :3]
        img[~ship.grid] = to_rgb(BLOCKED)
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
        ax.set_title(f"Forecast {label}", loc="left", color=INK, fontsize=10.5)
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9,
               labelcolor=INK)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    cbar = fig.colorbar(sm, cax=fig.add_axes([0.915, 0.2, 0.012, 0.6]))
    cbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_label("Forecast chance the cell is burning", color=INK_2, fontsize=9)
    cbar.ax.tick_params(colors=INK_2, labelsize=8)
    s, b = nums["short"], nums["plan"]
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.01, 0.915,
             f"Shortest path: {s['steps']} steps, summed risk {s['risk']:.2f}, button "
             f"{s['button']:.0%} likely burning on arrival.   Bot 4's plan: {b['steps']} steps, "
             f"summed risk {b['risk']:.2f}, button {b['button']:.0%}.",
             color=INK_2, fontsize=9)
    fig.subplots_adjust(left=0.01, right=0.895, top=0.86, bottom=0.1, wspace=0.05)
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--q", type=float, required=True)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--out", default="decision.png")
    args = parser.parse_args()

    w = Bot4().risk_weight
    trial = Trial.generate(args.D, args.q, trial_rng(args.seed, args.q, args.trial))
    found = find_decision(trial, w)
    if found is None:
        raise SystemExit("Bot 4 never preferred a longer path on this trial")
    t, pos, burning, forecast, plan, short = found
    nums = {"short": path_numbers(short, trial.button, forecast, w),
            "plan": path_numbers(plan, trial.button, forecast, w)}
    for name in ("short", "plan"):
        n = nums[name]
        print(f"{name:5s}: {n['steps']} steps, summed risk {n['risk']:.3f}, cost {n['cost']:.1f}, "
              f"riskiest cell {n['worst_cell']:.2f}, button burning on arrival {n['button']:.2f}")
    title = (f"Bot 4's decision at move {t + 1}: trial {args.trial}, q = {args.q:g}, "
             f"D = {args.D}")
    draw(trial, t, pos, forecast, plan, short, nums, args.out, title)
    print(f"move {t + 1} -> {args.out}")


if __name__ == "__main__":
    main()
