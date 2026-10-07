"""Draw what happened on one trial, for one or more bots, side by side.

Trials are numbered exactly as in experiments.py, so a row in a results CSV
can be replayed by passing the same D, q, seed and trial index:

    python visualize.py --D 50 --q 0.3 --trial 17 --bots bot3 bot4 --out trial17.png

Or search for the first trial matching a pattern of outcomes (1 = success,
0 = failure):

    python visualize.py --D 50 --q 0.3 --where bot3=0 bot4=1 --bots bot3 bot4 --out case.png
"""
import argparse

import matplotlib
matplotlib.use("Agg")   # draw straight to PNG files, no window
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from analyze import bot_label
from bots import make_bot
from experiments import trial_rng
from simulation import Trial, fire_history, run_bot


def find_trial(D, q, seed, where, limit=5000):
    for i in range(limit):
        trial = Trial.generate(D, q, trial_rng(seed, q, i))
        ok = True
        for spec, want in where.items():
            if int(run_bot(trial, make_bot(spec)).success) != want:
                ok = False
                break
        if ok:
            return i
    raise SystemExit(f"no trial among the first {limit} matches {where}")


def draw(trial, specs, path, title):
    """One picture per bot: walls black, floor white, the tiles that burned
    by the end of that bot's run orange, and the bot's path in blue."""
    ship = trial.ship
    colors = ListedColormap(["black", "white", "orange"])   # 0 wall, 1 floor, 2 fire
    fig, axes = plt.subplots(1, len(specs), figsize=(5 * len(specs), 5.5), squeeze=False)
    for ax, spec in zip(axes[0], specs):
        out = run_bot(trial, make_bot(spec), record_path=True)
        burned = fire_history(trial, out.steps)
        picture = []
        for r in range(ship.D):
            row = []
            for c in range(ship.D):
                if not ship.grid[r][c].is_open:
                    row.append(0)
                elif burned[r][c] is not None:
                    row.append(2)
                else:
                    row.append(1)
            picture.append(row)
        ax.imshow(picture, cmap=colors, vmin=0, vmax=2)
        ax.plot([c for r, c in out.path], [r for r, c in out.path], color="blue", linewidth=2)
        ax.plot(trial.bot_start[1], trial.bot_start[0], "bo", markersize=8, label="bot start")
        ax.plot(trial.button[1], trial.button[0], "g*", markersize=14, label="button")
        ax.plot(trial.fire_start[1], trial.fire_start[0], "rx", markersize=10, mew=3,
                label="fire start")
        verdict = "success" if out.success else out.reason.replace("_", " ")
        ax.set_title(f"{bot_label(spec)}: {verdict} after {out.steps} steps")
        ax.axis("off")
    axes[0][0].legend(loc="upper left", fontsize=8)
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--q", type=float, required=True)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--trial", type=int)
    parser.add_argument("--where", nargs="*", default=[], help="e.g. bot3=0 bot4=1")
    parser.add_argument("--bots", nargs="+", default=["bot1", "bot2", "bot3", "bot4"])
    parser.add_argument("--out", default="trial.png")
    args = parser.parse_args()

    where = {k: int(v) for k, v in (w.split("=") for w in args.where)}
    i = args.trial if args.trial is not None else find_trial(args.D, args.q, args.seed, where)
    trial = Trial.generate(args.D, args.q, trial_rng(args.seed, args.q, i))
    draw(trial, args.bots, args.out, f"Trial {i}, D = {args.D}, q = {args.q:g}")
    print(f"trial {i} -> {args.out}")


if __name__ == "__main__":
    main()
