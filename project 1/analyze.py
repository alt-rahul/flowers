"""Summarise experiment CSVs into tables and plots.

    python analyze.py results/main.csv.gz --out results
    python analyze.py results/tuning_bot4.csv --out results/tuning --no-plots

Writes summary.csv (one row per bot and q), summary.md (tables for the
writeup) and, unless --no-plots, PNG charts.
"""
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


def bot_label(spec):
    """'bot4:penalty=5' -> 'Bot 4 (penalty=5)'; 'bot4_forecast' -> 'Bot 4 (forecast)'."""
    name, _, args = spec.partition(":")
    if name == "bot4_forecast":
        label = "Bot 4 (forecast)"
    else:
        label = f"Bot {name[3:]}" if name.startswith("bot") else name
    return f"{label} ({args})" if args else label


def wilson(k, n, z=1.96):
    """95% Wilson score interval for a binomial proportion."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def load(paths):
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
                # Columns added later; older CSVs (e.g. the tuning runs) lack them.
                r["fireproof"] = int(r["fireproof"]) if r.get("fireproof") else None
                r["deviations"] = int(r["deviations"]) if r.get("deviations") else None
                rows.append(r)
    return rows


def summarize(rows):
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


def paired_difference(rows, a, b):
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


def has_diagnostics(rows):
    return all(r["fireproof"] is not None and r["deviations"] is not None for r in rows)


def trial_types(rows, qs):
    """Per q, the shares of trials that are a certain win from the start
    (a fireproof path exists), contested (winnable, but only by deciding
    well), and impossible (not even a clairvoyant bot wins)."""
    first = rows[0]["bot"]
    out = {}
    for q in qs:
        rs = [r for r in rows if r["bot"] == first and r["q"] == q]
        n = len(rs)
        certain = sum(r["fireproof"] for r in rs)
        possible = sum(r["oracle_success"] for r in rs)
        out[q] = (certain / n, (possible - certain) / n, (n - possible) / n, n)
    return out


def contested_stats(rows, bots, qs):
    """Success rate (with 95% CI) on contested trials only, per (bot, q)."""
    out = {}
    for b in bots:
        for q in qs:
            rs = [r for r in rows if r["bot"] == b and r["q"] == q
                  and r["oracle_success"] and not r["fireproof"]]
            if rs:
                k = sum(r["success"] for r in rs)
                out[(b, q)] = (k / len(rs), wilson(k, len(rs)), len(rs))
    return out


def divergence(rows, bots, qs):
    """Share of trials in which each bot makes at least one move that Bot 2's
    rule (step along a shortest fire-free path) could not have made."""
    out = {}
    for b in bots:
        for q in qs:
            rs = [r for r in rows if r["bot"] == b and r["q"] == q]
            if rs:
                k = sum(r["deviations"] > 0 for r in rs)
                out[(b, q)] = (k / len(rs), wilson(k, len(rs)))
    return out


def divergence_outcomes(rows, bot, base="bot2"):
    """Pooled over q: outcomes of `bot` vs `base` on the same trials, split
    by whether `bot` ever left Bot 2's rule."""
    by = defaultdict(dict)
    for r in rows:
        by[(r["q"], r["trial"])][r["bot"]] = r
    out = {True: Counter(), False: Counter()}
    for v in by.values():
        if bot in v and base in v:
            out[v[bot]["deviations"] > 0][(v[bot]["success"], v[base]["success"])] += 1
    return out


def write_summary_csv(path, bots, qs, stats):
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


def markdown_tables(rows, bots, qs, stats, base=None):
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

    if has_diagnostics(rows):
        lines.append(diagnostic_tables(rows, bots, qs))

    lines.append("\n### Thinking time (one core; time spent inside the bot's own code)\n")
    lines.append("| | " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * (len(bots) + 1) + "|")
    per_trial, per_move = [], []
    for b in bots:
        rs = [r for r in rows if r["bot"] == b]
        per_trial.append(np.mean([r["ms"] for r in rs]))
        per_move.append(1000 * sum(r["ms"] for r in rs) / max(1, sum(r["steps"] for r in rs)))
    lines.append("| ms per trial | " + " | ".join(f"{m:.1f}" for m in per_trial) + " |")
    lines.append("| µs per move | " + " | ".join(f"{m:.0f}" for m in per_move) + " |")
    return "\n".join(lines) + "\n"


def diagnostic_tables(rows, bots, qs):
    lines = []
    types = trial_types(rows, qs)
    lines.append("\n### Trial types: certain from the start, contested, or impossible\n")
    lines.append("Certain = a path exists that even the fastest possible fire (q = 1) "
                 "cannot catch, found with two BFSs and no simulation. Impossible = not "
                 "even the clairvoyant bot wins. Contested = everything else.\n")
    lines.append("| q | trials | certain win | contested | impossible |")
    lines.append("|---|---|---|---|---|")
    for q in qs:
        c, m, i, n = types[q]
        lines.append(f"| {q:g} | {n} | {c:.1%} | {m:.1%} | {i:.1%} |")

    cont = contested_stats(rows, bots, qs)
    lines.append("\n### Success rate on contested trials only\n")
    lines.append("| q | contested trials | " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * (len(bots) + 2) + "|")
    for q in qs:
        n = next((cont[(b, q)][2] for b in bots if (b, q) in cont), 0)
        cells = [f"{cont[(b, q)][0]:.3f}" if (b, q) in cont else "" for b in bots]
        lines.append(f"| {q:g} | {n} | " + " | ".join(cells) + " |")

    others = [b for b in bots if b not in ("bot1", "bot2")]
    if "bot2" in bots and others:
        div = divergence(rows, others, qs)
        lines.append("\n### How often a bot leaves Bot 2's rule\n")
        lines.append("Share of trials with at least one move that is not a step along a "
                     "shortest fire-free path (Bot 2 never makes such a move).\n")
        lines.append("| q | " + " | ".join(bot_label(b) for b in others) + " |")
        lines.append("|---" * (len(others) + 1) + "|")
        for q in qs:
            lines.append(f"| {q:g} | " + " | ".join(
                f"{div[(b, q)][0]:.1%}" for b in others if (b, q) in div) + " |")
        lines.append("\nOutcomes on the same trials, pooled over q:\n")
        lines.append("| Bot | left Bot 2's rule? | trials | won, Bot 2 lost | Bot 2 won, lost "
                     "| both won | both lost |")
        lines.append("|---|---|---|---|---|---|---|")
        for b in others:
            out = divergence_outcomes(rows, b)
            for dev in (True, False):
                c = out[dev]
                lines.append(f"| {bot_label(b)} | {'yes' if dev else 'no'} | {sum(c.values())} "
                             f"| {c[(1, 0)]} | {c[(0, 1)]} | {c[(1, 1)]} | {c[(0, 0)]} |")
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
    key, ci = ("rate_given_winnable", "ci_given_winnable") if conditional else ("rate", "ci")
    if not conditional:
        o = [next(stats[(b, q)] for b in bots if (b, q) in stats) for q in qs]
        ax.plot(qs, [s["oracle_rate"] for s in o], color=REFERENCE, linewidth=1.5,
                linestyle=(0, (4, 3)), label="Clairvoyant bound", zorder=4)
    # The bots' curves sit close together, so overlapping CI bands would blur
    # into one; the widest half-width goes in the subtitle instead and the
    # paired-difference chart shows which gaps are real.
    half = max((s[ci][1] - s[ci][0]) / 2 for s in stats.values() if not math.isnan(s[ci][0]))
    lowest = 1.0
    for i, b in enumerate(bots):
        pts = [stats[(b, q)] for q in qs if (b, q) in stats]
        y = [s[key] for s in pts]
        lowest = min(lowest, min(y))
        ax.plot([s["q"] for s in pts], y, color=COLORS[i % len(COLORS)], linewidth=2,
                solid_capstyle="round", zorder=3, marker=MARKERS[i % len(MARKERS)],
                markersize=5, markeredgecolor=SURFACE, markeredgewidth=1.2,
                label=bot_label(b))
    ax.set_xlim(min(qs), max(qs))
    if conditional:
        ax.set_ylim(math.floor((lowest - 0.01) * 50) / 50, 1.005)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        _style(ax, "Success on winnable trials",
               "Only trials a clairvoyant bot could win. The y-axis starts above zero. "
               f"95% CIs within ±{half:.1%}.", "Success rate")
    else:
        ax.set_ylim(0, 1.02)
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
        _style(ax, "Success rate by flammability",
               f"Share of trials where the bot pressed the button. 95% CIs within ±{half:.1%}.",
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


def _significant_span(rows, qs, base="bot4", rivals=("bot2", "bot3")):
    """Smallest and largest q at which `base` beats every rival with 95%
    confidence (paired by trial), or None."""
    diffs = [paired_difference(rows, base, r) for r in rivals]
    sig = [q for q in qs if all(q in d and d[q][0] - d[q][1] > 0 for d in diffs)]
    return (min(sig), max(sig), sig) if sig else None


def plot_centerpiece(path, rows, bots, qs, stats):
    """Top: success rate of every bot (and the clairvoyant bound) against q.
    Bottom: Bot 4's paired advantage over each other bot, on the same x-axis.
    The shaded band is where Bot 4 beats both Bot 2 and Bot 3 with 95%
    confidence."""
    import matplotlib.pyplot as plt

    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.5, 8), dpi=150, sharex=True,
                                      gridspec_kw={"height_ratios": [3, 2]})
    fig.patch.set_facecolor(SURFACE)
    span = _significant_span(rows, qs)
    for ax in (top, bottom):
        if span:
            ax.axvspan(span[0], span[1], color=GRID, alpha=0.6, linewidth=0, zorder=0)

    o = [next(stats[(b, q)] for b in bots if (b, q) in stats) for q in qs]
    top.plot(qs, [s["oracle_rate"] for s in o], color=REFERENCE, linewidth=1.5,
             linestyle=(0, (4, 3)), label="Clairvoyant bound", zorder=4)
    for i, b in enumerate(bots):
        pts = [stats[(b, q)] for q in qs if (b, q) in stats]
        top.plot([s["q"] for s in pts], [s["rate"] for s in pts], color=COLORS[i], linewidth=2,
                 marker=MARKERS[i], markersize=4.5, markeredgecolor=SURFACE,
                 markeredgewidth=1, label=bot_label(b), zorder=3)
    top.set_ylim(0.4, 1.01)
    top.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    half = max((s["ci"][1] - s["ci"][0]) / 2 for s in stats.values())
    _style(top, "Success rate by flammability",
           f"All four bots on the same trials. 95% CIs within ±{half:.1%}. "
           "The y-axis starts at 40%.", "Success rate", xlabel="")
    top.legend(frameon=False, fontsize=9, labelcolor=INK, loc="lower left")
    if span:
        inside = [q for q in qs if span[0] <= q <= span[1]]
        note = "95% confidence" if len(span[2]) == len(inside) else \
            f"95% confidence at {len(span[2])} of these {len(inside)} q values"
        top.text((span[0] + span[1]) / 2, 0.985, f"Bot 4 ahead of Bots 2 and 3\n({note})",
                 ha="center", va="top", fontsize=8.5, color=INK_2)
        if span[1] < max(qs):
            top.text((span[1] + max(qs)) / 2, 0.44, "All bots tie:\nthe start decides",
                     ha="center", va="bottom", fontsize=8.5, color=INK_2)

    bottom.axhline(0, color=INK_2, linewidth=1, zorder=2)
    base = "bot4"
    for i, b in enumerate(bots):
        if b == base:
            continue
        d = paired_difference(rows, base, b)
        x = [q for q in qs if q in d]
        y = np.array([d[q][0] for q in x])
        h = np.array([d[q][1] for q in x])
        bottom.fill_between(x, y - h, y + h, color=COLORS[i], alpha=0.12, linewidth=0, zorder=1)
        bottom.plot(x, y, color=COLORS[i], linewidth=2, marker=MARKERS[i], markersize=4.5,
                    markeredgecolor=SURFACE, markeredgewidth=1, zorder=3,
                    label=f"Bot 4 minus {bot_label(b)}")
    bottom.set_xlim(min(qs), max(qs))
    bottom.yaxis.set_major_formatter(lambda v, _: "0" if abs(v) < 1e-9 else f"{v * 100:+.0f} pts")
    _style(bottom, "Bot 4's advantage on the same trials",
           "Paired difference in success rate. Above zero = Bot 4 better. Bands: 95% CI.",
           "Difference")
    bottom.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_versions(path, rows, qs, stats):
    """The two Bot 4 designs side by side. Top: how far each bot falls short
    of the clairvoyant bound. Bottom: the new Bot 4 minus the earlier,
    forecast-based one, paired by trial. Colors match the main charts; the
    earlier Bot 4 is the neutral dashed line."""
    import matplotlib.pyplot as plt

    from matplotlib.ticker import MaxNLocator

    series = [("bot2", COLORS[1], MARKERS[1], "-"), ("bot3", COLORS[2], MARKERS[2], "-"),
              ("bot4", COLORS[3], MARKERS[3], "-"), ("bot4_forecast", REFERENCE, "v", (0, (4, 2)))]
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8.5, 7.5), dpi=150, sharex=True,
                                      gridspec_kw={"height_ratios": [3, 2]})
    fig.patch.set_facecolor(SURFACE)
    for b, color, marker, style in series:
        x = [q for q in qs if (b, q) in stats]
        y = [100 * (stats[(b, q)]["oracle_rate"] - stats[(b, q)]["rate"]) for q in x]
        top.plot(x, y, color=color, linewidth=2, linestyle=style, marker=marker, markersize=4.5,
                 markeredgecolor=SURFACE, markeredgewidth=1, label=bot_label(b), zorder=3)
    top.set_ylim(bottom=0)
    top.yaxis.set_major_locator(MaxNLocator(integer=True))
    top.yaxis.set_major_formatter(lambda v, _: f"{v:.0f} pts")
    _style(top, "How far each bot falls below the clairvoyant bound",
           "Clairvoyant success rate minus the bot's, on the same trials. Lower is better.",
           "Shortfall", xlabel="")
    top.legend(frameon=False, fontsize=9, labelcolor=INK, loc="upper right")

    d = paired_difference(rows, "bot4", "bot4_forecast")
    x = [q for q in qs if q in d]
    y = np.array([d[q][0] for q in x])
    h = np.array([d[q][1] for q in x])
    bottom.axhline(0, color=INK_2, linewidth=1, zorder=2)
    bottom.fill_between(x, y - h, y + h, color=COLORS[3], alpha=0.15, linewidth=0, zorder=1)
    bottom.plot(x, y, color=COLORS[3], linewidth=2, marker=MARKERS[3], markersize=4.5,
                markeredgecolor=SURFACE, markeredgewidth=1, zorder=3,
                label="Bot 4 minus Bot 4 (forecast)")
    bottom.set_xlim(min(qs), max(qs))
    bottom.yaxis.set_major_formatter(lambda v, _: "0" if abs(v) < 1e-9 else f"{v * 100:+.1f} pts")
    _style(bottom, "New Bot 4 vs the earlier one, same trials",
           "Paired difference in success rate. Below zero = the earlier Bot 4 was better. "
           "Band: 95% CI.", "Difference")
    bottom.legend(frameon=False, fontsize=9, labelcolor=INK, loc="lower right")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_trial_types(path, qs, types):
    """How many trials are decided at the start, contested, or impossible."""
    import matplotlib.pyplot as plt

    certain = np.array([types[q][0] for q in qs])
    winnable = certain + np.array([types[q][1] for q in qs])
    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    ax.fill_between(qs, certain, winnable, color=GRID, linewidth=0, zorder=1)
    ax.plot(qs, winnable, color=INK, linewidth=2, zorder=3)
    ax.plot(qs, certain, color=INK_2, linewidth=2, linestyle=(0, (4, 3)), zorder=3)
    i = len(qs) // 4
    ax.text(qs[i], winnable[i] + 0.03, "Clairvoyant bot can win", color=INK, fontsize=9.5)
    ax.text(qs[-1], certain[-1] - 0.04, "Certain win from the start", color=INK_2,
            fontsize=9.5, ha="right", va="top")
    mid = len(qs) // 3
    ax.text(qs[mid], (certain[mid] + winnable[mid]) / 2, "Contested:\ndecisions matter here",
            color=INK, fontsize=10, ha="center", va="center", fontweight="bold")
    ax.text(qs[-1], 0.97, "No bot can win above the top line", color=INK_2, fontsize=9,
            ha="right", va="top")
    ax.set_xlim(min(qs), max(qs))
    ax.set_ylim(0, 1.0)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    _style(ax, "Which trials can a bot's decisions change?",
           "Share of trials. A certain win is found with two BFSs: some path stays ahead "
           "of even a q = 1 fire.", "Share of trials")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_contested(path, bots, qs, cont, min_trials=50):
    """Success rate restricted to contested trials, where bots can differ."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    lowest, half = 1.0, 0.0
    for i, b in enumerate(bots):
        pts = [(q, cont[(b, q)]) for q in qs if (b, q) in cont and cont[(b, q)][2] >= min_trials]
        x = [q for q, _ in pts]
        y = [c[0] for _, c in pts]
        lowest = min([lowest] + y)
        half = max([half] + [(c[1][1] - c[1][0]) / 2 for _, c in pts])
        ax.plot(x, y, color=COLORS[i], linewidth=2, marker=MARKERS[i], markersize=5,
                markeredgecolor=SURFACE, markeredgewidth=1.2, label=bot_label(b), zorder=3)
    ax.set_xlim(min(qs), max(qs))
    ax.set_ylim(math.floor((lowest - 0.02) * 20) / 20, 1.005)
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    _style(ax, "Success on contested trials",
           f"Trials that are winnable but not certain from the start (q values with at least "
           f"{min_trials} such trials). 95% CIs within ±{half:.1%}.", "Success rate")
    _legend(ax, loc="lower left")
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def plot_divergence(path, bots, qs, div):
    """How often Bots 3 and 4 make a move Bot 2's rule could not."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MultipleLocator

    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    for i, b in enumerate(bots):
        if b in ("bot1", "bot2"):
            continue
        x = [q for q in qs if (b, q) in div]
        ax.plot(x, [div[(b, q)][0] for q in x], color=COLORS[i], linewidth=2,
                marker=MARKERS[i], markersize=5, markeredgecolor=SURFACE,
                markeredgewidth=1.2, label=bot_label(b), zorder=3)
    ax.set_xlim(min(qs), max(qs))
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MultipleLocator(0.05))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    _style(ax, "How often a bot decides differently from Bot 2",
           "Share of trials with at least one move off every shortest fire-free path. "
           "Bot 2 is 0% by definition.", "Share of trials")
    _legend(ax, loc="upper left")
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


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--out", default="results")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--base", help="bot the others are compared with (default: last)")
    parser.add_argument("--D", type=int, help="only use trials on ships of this size")
    parser.add_argument("--bots", nargs="+", help="only these bots, in this order")
    parser.add_argument("--versions", action="store_true",
                        help="only draw the Bot 4 vs Bot 4 (forecast) chart")
    parser.add_argument("--failure-q", default="0.2:0.6",
                        help="q range pooled in the failure chart (default 0.2:0.6)")
    args = parser.parse_args()

    rows = load(args.csv)
    if args.D is not None:
        rows = [r for r in rows if r["D"] == args.D]
    if args.bots:
        rows = [r for r in rows if r["bot"] in args.bots]
    bots, qs, stats = summarize(rows)
    if args.bots:
        bots = [b for b in args.bots if b in bots]
    os.makedirs(args.out, exist_ok=True)
    write_summary_csv(os.path.join(args.out, "summary.csv"), bots, qs, stats)
    md = markdown_tables(rows, bots, qs, stats, args.base)
    with open(os.path.join(args.out, "summary.md"), "w") as f:
        f.write(md)
    print(md)
    if args.no_plots:
        return
    if args.versions:
        import matplotlib
        matplotlib.use("Agg")
        plot_versions(os.path.join(args.out, "bot4_versions.png"), rows, qs, stats)
        return
    if len(bots) > len(COLORS):
        # The palette has one color per bot; never cycle colors.
        print(f"skipping charts: {len(bots)} bots but only {len(COLORS)} series colors")
        return
    import matplotlib
    matplotlib.use("Agg")
    if "bot4" in bots and has_diagnostics(rows):
        plot_centerpiece(os.path.join(args.out, "centerpiece.png"), rows, bots, qs, stats)
        plot_trial_types(os.path.join(args.out, "trial_types.png"), qs, trial_types(rows, qs))
        plot_contested(os.path.join(args.out, "success_contested.png"), bots, qs,
                       contested_stats(rows, bots, qs))
        plot_divergence(os.path.join(args.out, "divergence.png"), bots, qs,
                        divergence(rows, bots, qs))
    else:
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
