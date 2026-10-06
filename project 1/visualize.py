"""Draw what happened on one trial, for one or more bots, side by side.

Trials are numbered exactly as in experiments.py, so a row in a results CSV
can be replayed by passing the same D, q, seed and trial index:

    python visualize.py --D 50 --q 0.3 --trial 17 --bots bot3 bot4 --out trial17.png

Or search for the first trial matching a pattern of outcomes (1 = success,
0 = failure, "oracle" = whether a clairvoyant bot could win):

    python visualize.py --D 50 --q 0.3 --where bot3=0 bot4=1 --bots bot3 bot4 --out case.png
"""
import argparse

import numpy as np

from analyze import INK, INK_2, SURFACE, bot_label
from bots import make_bot
from experiments import trial_rng
from simulation import Trial, oracle_steps, run_bot

BLOCKED = "#383835"
OPEN = SURFACE


def find_trial(D, q, seed, where, limit=5000):
    for i in range(limit):
        trial = Trial.generate(D, q, trial_rng(seed, q, i))
        ok = True
        for spec, want in where.items():
            got = oracle_steps(trial) is not None if spec == "oracle" else \
                run_bot(trial, make_bot(spec)).success
            if int(got) != want:
                ok = False
                break
        if ok:
            return i
    raise SystemExit(f"no trial among the first {limit} matches {where}")


def draw(trial, specs, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import to_rgb

    ship = trial.ship
    D = ship.D
    fig, axes = plt.subplots(1, len(specs), figsize=(5.2 * len(specs), 5.8), dpi=150,
                             squeeze=False)
    fig.patch.set_facecolor(SURFACE)
    fire_cmap = plt.get_cmap("Oranges")
    for ax, spec in zip(axes[0], specs):
        out = run_bot(trial, make_bot(spec), record_path=True)
        end = out.steps
        ignite = trial.fire.ignite_time.reshape(D, D)
        img = np.zeros((D, D, 3))
        img[ship.grid] = to_rgb(OPEN)
        img[~ship.grid] = to_rgb(BLOCKED)
        burning = ignite <= end
        if end > 0:
            # Earlier ignitions darker, so the direction of spread is visible.
            shade = 0.85 - 0.6 * ignite[burning] / end
            img[burning] = fire_cmap(shade)[:, :3]
        else:
            img[burning] = fire_cmap(0.85)[:3]
        ax.imshow(img, interpolation="nearest")
        rc = np.array([ship.coords(c) for c in out.path])
        ax.plot(rc[:, 1], rc[:, 0], color=SURFACE, linewidth=4, solid_capstyle="round")
        ax.plot(rc[:, 1], rc[:, 0], color=INK, linewidth=2, solid_capstyle="round")
        for cell, marker, color, label in [
            (trial.bot_start, "o", INK, "bot start"),
            (trial.button, "*", "#008300", "button"),
            (trial.fire_start, "X", "#e34948", "fire origin"),
        ]:
            r, c = ship.coords(cell)
            ax.plot(c, r, marker=marker, markersize=15 if marker == "*" else 11, color=color,
                    markeredgecolor=SURFACE, markeredgewidth=1.5, linestyle="none", label=label)
        r, c = ship.coords(out.path[-1])
        ax.plot(c, r, marker="o", markersize=8, markerfacecolor=SURFACE,
                markeredgecolor=INK, markeredgewidth=2, linestyle="none", label="bot end")
        verdict = "success" if out.success else out.reason.replace("_", " ")
        ax.set_title(f"{bot_label(spec)}: {verdict} after {out.steps} steps",
                     color=INK, fontsize=10.5, loc="left")
        ax.set_xticks([])
        ax.set_yticks([])
        for s in ax.spines.values():
            s.set_visible(False)
    handles, labels = axes[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9,
               labelcolor=INK)
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=12, fontweight="bold")
    fig.text(0.01, 0.905, "Fire shown at the moment each bot's run ended; darker = burned earlier.",
             color=INK_2, fontsize=9)
    fig.tight_layout(rect=(0, 0.06, 1, 0.9))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--q", type=float, required=True)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--trial", type=int)
    parser.add_argument("--where", nargs="*", default=[], help="e.g. bot3=0 bot4=1 oracle=1")
    parser.add_argument("--bots", nargs="+", default=["bot1", "bot2", "bot3", "bot4"])
    parser.add_argument("--out", default="trial.png")
    args = parser.parse_args()

    where = {k: int(v) for k, v in (w.split("=") for w in args.where)}
    i = args.trial if args.trial is not None else find_trial(args.D, args.q, args.seed, where)
    trial = Trial.generate(args.D, args.q, trial_rng(args.seed, args.q, i))
    best = oracle_steps(trial)
    bound = f"clairvoyant bot wins in {best} steps" if best else "no bot could win"
    draw(trial, args.bots, args.out, f"Trial {i}, D = {args.D}, q = {args.q:g} ({bound})")
    print(f"trial {i} -> {args.out}")


if __name__ == "__main__":
    main()
