"""How well do Bot 4's fire forecasts match the real fire?

For random ships and fire origins, compare each forecast's p_t(c) with the
fraction of Monte Carlo fire runs (the real spread rule) in which cell c is
burning after t updates. Prints the bias and mean absolute error per q and
draws one reliability diagram per forecast (forecast vs observed frequency).

    python forecast_check.py --D 50 --out results/forecast_calibration.png
"""
from __future__ import annotations

import argparse

import numpy as np

from analyze import COLORS, GRID, INK, INK_2, MARKERS, SURFACE
from fire import fire_step, spread_probabilities
from forecast import FORECASTS
from ship import Ship


def monte_carlo(ship: Ship, q: float, origin: int, horizon: int, runs: int,
                rng: np.random.Generator) -> np.ndarray:
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


def main() -> None:
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

    titles = {"meanfield": "Naive mean-field", "dmp": "Message passing (used by Bot 4)"}
    bins = np.linspace(0, 1, 11)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.6), dpi=150, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    print(f"{'forecast':>10} {'q':>5} {'bias (forecast - real)':>24} {'mean abs error':>15}")
    for ax, kind in zip(axes, ["meanfield", "dmp"]):
        ax.plot([0, 1], [0, 1], color=INK_2, linewidth=1, zorder=1)
        for i, q in enumerate(qs):
            pred, real = [], []
            for ship, origin, freq in cases[q]:
                burning = np.zeros(ship.D * ship.D, dtype=bool)
                burning[origin] = True
                forecast = FORECASTS[kind](ship, q, burning)
                for t in range(1, args.horizon + 1):
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
        ax.set_xlabel("Forecast probability a cell is burning", color=INK_2)
        ax.set_title(titles[kind], loc="left", color=INK, fontsize=11, pad=8)
    axes[0].set_ylabel("Observed frequency (Monte Carlo)", color=INK_2)
    axes[0].legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper left")
    fig.suptitle("Fire forecasts vs the real fire", x=0.01, ha="left", color=INK,
                 fontsize=13, fontweight="bold")
    fig.text(0.01, 0.905, "On the diagonal = calibrated; below it = forecast more pessimistic "
             "than reality.", color=INK_2, fontsize=9.5)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(args.out, facecolor=SURFACE)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
