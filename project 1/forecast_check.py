"""How well do the fire predictions match the real fire?

For random ships and fire origins, compare each model's p_t(c), the chance
that cell c is burning after t updates, with the fraction of Monte Carlo fire
runs (the real spread rule) in which it is. Prints the bias and mean absolute
error per q and draws one reliability diagram per model (predicted vs
observed frequency). The models:

    race        Bot 4's: the fire must travel d cells (maze distance) and
                advances one cell per step with probability q, so
                p_t(c) = P(Binomial(t, q) >= d)
    dmp         message passing (the earlier, forecast-based Bot 4)
    meanfield   the naive forecast that message passing replaced

    python forecast_check.py --D 50 --out results/forecast_calibration.png
"""
import argparse

import numpy as np

from analyze import COLORS, GRID, INK, INK_2, MARKERS, SURFACE
from fire import fire_step, spread_probabilities
from forecast import FORECASTS
from ship import Ship


def monte_carlo(ship, q, origin, horizon, runs, rng):
    """freq[t, c] = fraction of runs where cell c burns after t updates."""
    probs = spread_probabilities(q)
    freq = np.zeros((horizon + 1, ship.D * ship.D))
    for _ in range(runs):
        burning = np.zeros((ship.D, ship.D), dtype=bool)
        burning.flat[origin] = True
        freq[0] += burning.ravel()
        for t in range(1, horizon + 1):
            burning |= fire_step(burning, ship.grid, probs, rng)
            freq[t] += burning.ravel()
    return freq / runs


def race_probabilities(ship, q, origin, horizon):
    """p[t, c] = P(Binomial(t, q) >= d(c)), d = maze distance from the origin."""
    dist = np.array(ship.distances_from(origin))
    reachable = np.isfinite(dist)
    d = np.where(reachable, dist, 0).astype(int)
    p = np.zeros((horizon + 1, ship.D * ship.D))
    pmf = np.zeros(horizon + 2)
    pmf[0] = 1.0
    for t in range(horizon + 1):
        if t > 0:
            pmf[1:] = pmf[1:] * (1 - q) + pmf[:-1] * q
            pmf[0] *= 1 - q
        at_least = np.cumsum(pmf[::-1])[::-1]        # at_least[j] = P(at least j advances)
        p[t] = np.where(reachable & (d <= t), at_least[np.minimum(d, t)], 0.0)
    return p


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--qs", default="0.1,0.3,0.5,0.8")
    parser.add_argument("--ships", type=int, default=10)
    parser.add_argument("--runs", type=int, default=400)
    parser.add_argument("--horizon", type=int, default=40)
    parser.add_argument("--out", default="results/forecast_calibration.png")
    args = parser.parse_args()

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(2026)
    qs = [float(x) for x in args.qs.split(",")]
    # Same ships, origins and Monte Carlo runs for both forecasts.
    cases = {q: [] for q in qs}
    for q in qs:
        for _ in range(args.ships):
            ship = Ship.generate(args.D, rng)
            origin = int(rng.choice(ship.open_cells))
            cases[q].append((ship, origin, monte_carlo(ship, q, origin, args.horizon,
                                                       args.runs, rng)))

    titles = {"race": "Race model (Bot 4)", "dmp": "Message passing (earlier Bot 4)",
              "meanfield": "Naive mean-field"}
    bins = np.linspace(0, 1, 11)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.6), dpi=150, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    print(f"{'model':>10} {'q':>5} {'bias (predicted - real)':>24} {'mean abs error':>15}")
    for ax, kind in zip(axes, ["race", "dmp", "meanfield"]):
        ax.plot([0, 1], [0, 1], color=INK_2, linewidth=1, zorder=1)
        for i, q in enumerate(qs):
            pred, real = [], []
            for ship, origin, freq in cases[q]:
                burning = np.zeros(ship.D * ship.D, dtype=bool)
                burning[origin] = True
                if kind == "race":
                    race = race_probabilities(ship, q, origin, args.horizon)
                else:
                    forecast = FORECASTS[kind](ship, q, burning)
                for t in range(1, args.horizon + 1):
                    if kind == "race":
                        p = race[t][ship.open_cells]
                    else:
                        p = forecast.prob_at(t)[ship.open_cells]
                    f = freq[t][ship.open_cells]
                    # Skip cells that are certain either way; they say nothing.
                    keep = (p > 1e-3) | (f > 0)
                    pred.append(p[keep])
                    real.append(f[keep])
            pred, real = np.concatenate(pred), np.concatenate(real)
            print(f"{kind:>10} {q:5.2f} {np.mean(pred - real):+24.3f} "
                  f"{np.mean(np.abs(pred - real)):15.3f}")
            idx = np.clip(np.digitize(pred, bins) - 1, 0, len(bins) - 2)
            used = [b for b in range(len(bins) - 1) if (idx == b).any()]
            ax.plot([pred[idx == b].mean() for b in used], [real[idx == b].mean() for b in used],
                    color=COLORS[i % 4], marker=MARKERS[i % 4], linewidth=2, markersize=5,
                    markeredgecolor=SURFACE, markeredgewidth=1.2, label=f"q = {q:g}", zorder=3)
        ax.set_facecolor(SURFACE)
        ax.grid(True, color=GRID, linewidth=0.8)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(GRID)
        ax.tick_params(colors=INK_2, labelsize=9, length=0)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("Predicted probability a cell is burning", color=INK_2)
        ax.set_title(titles[kind], loc="left", color=INK, fontsize=11, pad=8)
    axes[0].set_ylabel("Observed frequency (Monte Carlo)", color=INK_2)
    axes[0].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    fig.suptitle("Fire predictions vs the real fire", x=0.01, ha="left", color=INK,
                 fontsize=13, fontweight="bold")
    fig.text(0.01, 0.905, "On the diagonal = calibrated. Above it = optimistic (the fire comes "
             "more often than predicted); below it = pessimistic (predicts fire that doesn't "
             "come).", color=INK_2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
