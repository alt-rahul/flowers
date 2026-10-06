"""Summarise experiment CSVs into tables and plots.

    python analyze.py results/main.csv.gz --out results
    python analyze.py results/tuning_bot4.csv --out results/tuning --no-plots

Writes summary.csv (one row per bot and q), summary.md (tables for the
writeup) and, unless --no-plots, PNG charts.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import math
import os
from collections import Counter, defaultdict

import numpy as np

REASONS = ["entered_fire", "caught", "button_burned", "trapped", "timeout"]
REASON_LABELS = {
    "entered_fire": "walked into fire",
    "caught": "fire spread onto bot",
    "button_burned": "button burned first",
    "trapped": "cut off from button",
    "timeout": "timed out",
}

# Categorical slots 1-4 of the validated reference palette, assigned to bots
# in fixed order; the clairvoyant bound is a neutral reference line.
COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
MARKERS = ["o", "s", "^", "D"]
REFERENCE = "#52514e"
SURFACE = "#fcfcfb"
GRID = "#e4e3df"
INK = "#0b0b0b"
INK_2 = "#52514e"


def bot_label(spec: str) -> str:
    """'bot4:risk_weight=10' -> 'Bot 4 (risk_weight=10)'."""
    name, _, args = spec.partition(":")
    label = f"Bot {name[3:]}" if name.startswith("bot") else name
    return f"{label} ({args})" if args else label


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def load(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt", newline="") as f:
            for r in csv.DictReader(f):
                r["D"] = int(r["D"])
                r["q"] = float(r["q"])
                r["trial"] = int(r["trial"])
                r["success"] = int(r["success"])
                r["oracle_success"] = int(r["oracle_success"])
                r["steps"] = int(r["steps"])
                r["ms"] = float(r["ms"])
                rows.append(r)
    return rows


def summarize(rows: list[dict]) -> tuple[list[str], list[float], dict]:
    bots = list(dict.fromkeys(r["bot"] for r in rows))
    qs = sorted({r["q"] for r in rows})
    groups = defaultdict(list)
    for r in rows:
        groups[(r["bot"], r["q"])].append(r)
    stats = {}
    for (bot, q), rs in groups.items():
        n = len(rs)
        wins = sum(r["success"] for r in rs)
        winnable = [r for r in rs if r["oracle_success"]]
        wins_winnable = sum(r["success"] for r in winnable)
        failures = [r for r in rs if not r["success"]]
        stats[(bot, q)] = {
            "bot": bot, "q": q, "n": n, "wins": wins, "rate": wins / n,
            "ci": wilson(wins, n),
            "oracle_rate": len(winnable) / n,
            "oracle_ci": wilson(len(winnable), n),
            "winnable": len(winnable),
            "rate_given_winnable": wins_winnable / len(winnable) if winnable else math.nan,
            "ci_given_winnable": wilson(wins_winnable, len(winnable)),
            "reasons": Counter(r["reason"] for r in failures),
            "avoidable": Counter(r["reason"] for r in failures if r["oracle_success"]),
            "ms": float(np.mean([r["ms"] for r in rs])),
        }
    return bots, qs, stats


def paired_difference(rows: list[dict], a: str, b: str) -> dict[float, tuple[float, float, int]]:
    """Mean of success(a) - success(b) over shared trials, with a 95% CI
    half-width, per q. Pairing on the same trials removes most of the noise."""
    by_trial = defaultdict(dict)
    for r in rows:
        by_trial[(r["q"], r["trial"])][r["bot"]] = r["success"]
    diffs = defaultdict(list)
    for (q, _), res in by_trial.items():
        if a in res and b in res:
            diffs[q].append(res[a] - res[b])
    out = {}
    for q, d in diffs.items():
        d = np.array(d, dtype=float)
        half = 1.96 * d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 1 else math.nan
        out[q] = (float(d.mean()), half, len(d))
    return out


def write_summary_csv(path: str, bots, qs, stats) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bot", "q", "trials", "success_rate", "ci_low", "ci_high",
                    "clairvoyant_rate", "success_given_winnable", "mean_ms_per_trial"]
                   + [f"fail_{r}" for r in REASONS] + [f"avoidable_{r}" for r in REASONS])
        for bot in bots:
            for q in qs:
                s = stats.get((bot, q))
                if s is None:
                    continue
                w.writerow([bot, q, s["n"], f"{s['rate']:.4f}", f"{s['ci'][0]:.4f}",
                            f"{s['ci'][1]:.4f}", f"{s['oracle_rate']:.4f}",
                            f"{s['rate_given_winnable']:.4f}", f"{s['ms']:.2f}"]
                           + [s["reasons"][r] for r in REASONS]
                           + [s["avoidable"][r] for r in REASONS])


def markdown_tables(rows, bots, qs, stats, base=None) -> str:
    lines = []
    D = sorted({r["D"] for r in rows})
    n = sorted({s["n"] for s in stats.values()})
    lines.append(f"Ship size D = {', '.join(map(str, D))}; trials per (bot, q): "
                 f"{n[0]}" + (f" to {n[-1]}" if n[-1] != n[0] else "") + ".\n")

    lines.append("### Success rate (95% CI)\n")
    lines.append("| q | " + " | ".join(bot_label(b) for b in bots) + " | Clairvoyant bound |")
    lines.append("|---" * (len(bots) + 2) + "|")
    for q in qs:
        cells = []
        for b in bots:
            s = stats.get((b, q))
            cells.append("" if s is None else
                         f"{s['rate']:.3f} ({s['ci'][0]:.3f}-{s['ci'][1]:.3f})")
        o = next(stats[(b, q)] for b in bots if (b, q) in stats)
        lines.append(f"| {q:g} | " + " | ".join(cells) + f" | {o['oracle_rate']:.3f} |")

    lines.append("\n### Success rate among winnable trials (clairvoyant bot could win)\n")
    lines.append("| q | " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * (len(bots) + 1) + "|")
    for q in qs:
        cells = [f"{stats[(b, q)]['rate_given_winnable']:.3f}" if (b, q) in stats else ""
                 for b in bots]
        lines.append(f"| {q:g} | " + " | ".join(cells) + " |")

    if len(bots) > 1:
        base = base or bots[-1]
        lines.append(f"\n### Paired difference: {bot_label(base)} minus each other bot "
                     "(same trials; +0.010 = 1 point better)\n")
        others = [b for b in bots if b != base]
        lines.append("| q | " + " | ".join(f"vs {bot_label(b)}" for b in others) + " |")
        lines.append("|---" * (len(others) + 1) + "|")
        diffs = {b: paired_difference(rows, base, b) for b in others}
        for q in qs:
            cells = []
            for b in others:
                d = diffs[b].get(q)
                cells.append("" if d is None else f"{d[0]:+.3f} ± {d[1]:.3f}")
            lines.append(f"| {q:g} | " + " | ".join(cells) + " |")

    lines.append("\n### Why bots fail (all q pooled; share of failures, "
                 "and how many a clairvoyant bot could have avoided)\n")
    lines.append("| Bot | failures | " + " | ".join(REASON_LABELS[r] for r in REASONS[:4])
                 + " | avoidable |")
    lines.append("|---" * 7 + "|")
    for b in bots:
        reasons, avoidable = Counter(), Counter()
        for q in qs:
            if (b, q) in stats:
                reasons += stats[(b, q)]["reasons"]
                avoidable += stats[(b, q)]["avoidable"]
        total = sum(reasons.values())
        if total == 0:
            continue
        cells = [f"{reasons[r] / total:.0%}" for r in REASONS[:4]]
        lines.append(f"| {bot_label(b)} | {total} | " + " | ".join(cells)
                     + f" | {sum(avoidable.values()) / total:.0%} |")

    lines.append("\n### Mean wall-clock time per trial (ms, one core)\n")
    lines.append("| " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * len(bots) + "|")
    ms = [np.mean([stats[(b, q)]["ms"] for q in qs if (b, q) in stats]) for b in bots]
    lines.append("| " + " | ".join(f"{m:.1f}" for m in ms) + " |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- plots ---

def _style(ax, title, subtitle, ylabel, xlabel="Flammability q"):
    ax.set_facecolor(SURFACE)
    ax.grid(True, color=GRID, linewidth=0.8, linestyle="-")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9, length=0)
    ax.set_xlabel(xlabel, color=INK_2, fontsize=10)
    ax.set_ylabel(ylabel, color=INK_2, fontsize=10)
    ax.set_title(title, loc="left", color=INK, fontsize=13, fontweight="bold", pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK_2, fontsize=9.5, va="bottom")


def _legend(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=9, labelcolor=INK, **kw)
    return leg


def plot_success(path, bots, qs, stats, conditional=False):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    if not conditional:
        o = [next(stats[(b, q)] for b in bots if (b, q) in stats) for q in qs]
        ax.plot(qs, [s["oracle_rate"] for s in o], color=REFERENCE, linewidth=1.5,
                linestyle=(0, (4, 3)), label="Clairvoyant bound", zorder=2)
    for i, b in enumerate(bots):
        pts = [stats[(b, q)] for q in qs if (b, q) in stats]
        x = [s["q"] for s in pts]
        key, ci = ("rate_given_winnable", "ci_given_winnable") if conditional else ("rate", "ci")
        y = [s[key] for s in pts]
        lo = [s[ci][0] for s in pts]
        hi = [s[ci][1] for s in pts]
        color = COLORS[i % len(COLORS)]
        ax.fill_between(x, lo, hi, color=color, alpha=0.12, linewidth=0, zorder=1)
        ax.plot(x, y, color=color, linewidth=2, solid_capstyle="round", zorder=3,
                marker=MARKERS[i % len(MARKERS)], markersize=5, markeredgecolor=SURFACE,
                markeredgewidth=1.2, label=bot_label(b))
    ax.set_xlim(min(qs), max(qs))
    ax.set_ylim(0, 1.02)
    if conditional:
        _style(ax, "Success on winnable trials",
               "Share of trials won, counting only those a clairvoyant bot could win. "
               "Bands: 95% CI.", "Success rate")
    else:
        _style(ax, "Success rate by flammability",
               "Share of trials where the bot pressed the button. Bands: 95% CI.",
               "Success rate")
    _legend(ax, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_differences(path, rows, bots, qs):
    """Paired difference of the last bot (Bot 4) against every other bot."""
    import matplotlib.pyplot as plt

    base = bots[-1]
    others = bots[:-1]
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.axhline(0, color=INK_2, linewidth=1, zorder=2)
    for i, b in enumerate(others):
        d = paired_difference(rows, base, b)
        x = [q for q in qs if q in d]
        y = np.array([d[q][0] for q in x])
        h = np.array([d[q][1] for q in x])
        color = COLORS[i % len(COLORS)]
        ax.fill_between(x, y - h, y + h, color=color, alpha=0.12, linewidth=0, zorder=1)
        ax.plot(x, y, color=color, linewidth=2, marker=MARKERS[i % len(MARKERS)],
                markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.2, zorder=3,
                label=f"{bot_label(base)} minus {bot_label(b)}")
    ax.set_xlim(min(qs), max(qs))
    _style(ax, f"How much {bot_label(base)} gains on the same trials",
           "Difference in success rate, paired by trial. Above 0 = better. Bands: 95% CI.",
           "Difference in success rate")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:+.2f}")
    _legend(ax, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_failures(path, bots, qs, stats):
    """Stacked bars: why each bot failed, pooled over the given q values,
    split into failures a clairvoyant bot could have avoided or not."""
    import matplotlib.pyplot as plt

    # Palette slots 5-8, so failure reasons never share a color with a bot.
    shades = {"entered_fire": "#e34948", "caught": "#4a3aa7",
              "button_burned": "#008300", "trapped": "#e87ba4"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), dpi=150, sharey=True)
    fig.patch.set_facecolor(SURFACE)
    totals = {b: sum(stats[(b, q)]["n"] for q in qs if (b, q) in stats) for b in bots}
    for ax, (kind, title) in zip(axes, [("avoidable", "Avoidable"), ("unavoidable", "Unavoidable")]):
        x = np.arange(len(bots))
        bottom = np.zeros(len(bots))
        for reason in REASONS[:4]:
            vals = []
            for b in bots:
                c = 0
                for q in qs:
                    if (b, q) not in stats:
                        continue
                    s = stats[(b, q)]
                    av = s["avoidable"][reason]
                    c += av if kind == "avoidable" else s["reasons"][reason] - av
                vals.append(c / totals[b])
            vals = np.array(vals)
            ax.bar(x, vals, bottom=bottom, width=0.55, color=shades[reason],
                   edgecolor=SURFACE, linewidth=1.5, label=REASON_LABELS[reason])
            bottom += vals
        for xi, v in zip(x, bottom):
            ax.text(xi, v + 0.004, f"{v:.1%}", ha="center", va="bottom", color=INK, fontsize=9)
        ax.set_xticks(x, [bot_label(b) for b in bots])
        _style(ax, title, "Clairvoyant bot could win" if kind == "avoidable"
               else "No sequence of moves wins", "Share of all trials" if kind == "avoidable" else "",
               xlabel="")
        ax.grid(axis="x", visible=False)
    axes[0].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9,
               labelcolor=INK)
    q_range = f"q = {min(qs):g} to {max(qs):g}"
    fig.suptitle(f"Why bots fail ({q_range})", x=0.01, ha="left", color=INK,
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=(0, 0.07, 1, 0.97))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--out", default="results")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--base", help="bot the others are compared with (default: last)")
    parser.add_argument("--failure-q", default="0.2:0.6",
                        help="q range pooled in the failure chart (default 0.2:0.6)")
    args = parser.parse_args()

    rows = load(args.csv)
    bots, qs, stats = summarize(rows)
    os.makedirs(args.out, exist_ok=True)
    write_summary_csv(os.path.join(args.out, "summary.csv"), bots, qs, stats)
    md = markdown_tables(rows, bots, qs, stats, args.base)
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(md)
    print(md)
    if args.no_plots:
        return
    if len(bots) > len(COLORS):
        # The palette has one color per bot; never cycle colors.
        print(f"skipping charts: {len(bots)} bots but only {len(COLORS)} series colors")
        return
    import matplotlib
    matplotlib.use("Agg")
    plot_success(os.path.join(args.out, "success_rate.png"), bots, qs, stats)
    plot_success(os.path.join(args.out, "success_given_winnable.png"), bots, qs, stats,
                 conditional=True)
    if len(bots) > 1:
        plot_differences(os.path.join(args.out, "bot4_paired_gain.png"), rows, bots, qs)
    lo, hi = (float(x) for x in args.failure_q.split(":"))
    plot_failures(os.path.join(args.out, "failure_reasons.png"), bots,
                  [q for q in qs if lo <= q <= hi], stats)


if __name__ == "__main__":
    main()
