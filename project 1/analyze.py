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

import matplotlib
matplotlib.use("Agg")   # draw straight to PNG files, no window
import matplotlib.pyplot as plt
import numpy as np

REASONS = ["entered_fire", "caught", "button_burned", "trapped", "timeout"]
REASON_LABELS = {
    "entered_fire": "walked into fire",
    "caught": "fire spread onto bot",
    "button_burned": "button burned first",
    "trapped": "cut off from button",
    "timeout": "timed out",
}


def bot_label(spec):
    """'bot4:penalty=5' -> 'Bot 4 (penalty=5)'."""
    name, _, args = spec.partition(":")
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
                r["steps"] = int(r["steps"])
                r["ms"] = float(r["ms"])
                r["fireproof"] = int(r["fireproof"])
                r["deviations"] = int(r["deviations"])
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
        failures = [r for r in rs if not r["success"]]
        stats[(bot, q)] = {
            "bot": bot, "q": q, "n": n, "wins": wins, "rate": wins / n,
            "ci": wilson(wins, n),
            "reasons": Counter(r["reason"] for r in failures),
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


def certain_wins(rows, bots, qs):
    """Per q: the number of trials, the share that are a certain win from the
    start (a fireproof path exists), and for each bot how many of those
    certain-win trials it actually won."""
    out = {}
    for q in qs:
        rs = [r for r in rows if r["q"] == q]
        trials = {r["trial"] for r in rs}
        certain = {r["trial"] for r in rs if r["fireproof"]}
        won = {b: sum(r["success"] for r in rs if r["bot"] == b and r["fireproof"])
               for b in bots}
        out[q] = (len(trials), len(certain) / len(trials), len(certain), won)
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
                    "mean_ms_per_trial"] + [f"fail_{r}" for r in REASONS])
        for bot in bots:
            for q in qs:
                s = stats.get((bot, q))
                if s is None:
                    continue
                w.writerow([bot, q, s["n"], f"{s['rate']:.4f}", f"{s['ci'][0]:.4f}",
                            f"{s['ci'][1]:.4f}", f"{s['ms']:.2f}"]
                           + [s["reasons"][r] for r in REASONS])


def markdown_tables(rows, bots, qs, stats, base=None):
    lines = []
    D = sorted({r["D"] for r in rows})
    n = sorted({s["n"] for s in stats.values()})
    lines.append(f"Ship size D = {', '.join(map(str, D))}; trials per (bot, q): "
                 f"{n[0]}" + (f" to {n[-1]}" if n[-1] != n[0] else "") + ".\n")

    lines.append("### Success rate (95% CI)\n")
    lines.append("| q | " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * (len(bots) + 1) + "|")
    for q in qs:
        cells = []
        for b in bots:
            s = stats.get((b, q))
            cells.append("" if s is None else
                         f"{s['rate']:.3f} ({s['ci'][0]:.3f}-{s['ci'][1]:.3f})")
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

    lines.append("\n### Why bots fail (all q pooled; share of each bot's failures)\n")
    lines.append("| Bot | failures | " + " | ".join(REASON_LABELS[r] for r in REASONS[:4]) + " |")
    lines.append("|---" * 6 + "|")
    for b in bots:
        reasons = Counter()
        for q in qs:
            if (b, q) in stats:
                reasons += stats[(b, q)]["reasons"]
        total = sum(reasons.values())
        if total == 0:
            continue
        cells = [f"{reasons[r] / total:.0%}" for r in REASONS[:4]]
        lines.append(f"| {bot_label(b)} | {total} | " + " | ".join(cells) + " |")

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
    certain = certain_wins(rows, bots, qs)
    lines.append("\n### Certain wins from the start\n")
    lines.append("A trial is a certain win if some path to the button stays ahead of even "
                 "the fastest possible fire (q = 1), found with two BFSs and no simulation. "
                 "The bot columns count how many of those trials each bot actually won.\n")
    lines.append("| q | trials | certain win | " + " | ".join(bot_label(b) for b in bots) + " |")
    lines.append("|---" * (len(bots) + 3) + "|")
    for q in qs:
        n, share, k, won = certain[q]
        lines.append(f"| {q:g} | {n} | {share:.1%} | "
                     + " | ".join(f"{won[b]}/{k}" for b in bots) + " |")

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
#
# Plain matplotlib charts, just to illustrate the results. Each bot keeps the
# same colour and marker in every chart. The four colours stay distinguishable
# for colour-blind readers, and the markers tell the bots apart without colour.
BOT_COLORS = {"bot1": "#2a78d6", "bot2": "#eb6834", "bot3": "#1baf7a", "bot4": "#4a3aa7"}
BOT_MARKERS = {"bot1": "o", "bot2": "s", "bot3": "^", "bot4": "D"}
# Failure reasons get the same four colours, in order.
REASON_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#4a3aa7"]


def bot_color(bots, b):
    return BOT_COLORS.get(b, f"C{bots.index(b)}")


def bot_marker(b):
    return BOT_MARKERS.get(b, "o")


def significant_span(rows, qs, base="bot4", rivals=("bot2", "bot3")):
    """Smallest and largest q at which `base` beats every rival with 95%
    confidence (paired by trial), or None."""
    diffs = [paired_difference(rows, base, r) for r in rivals]
    sig = [q for q in qs if all(q in d and d[q][0] - d[q][1] > 0 for d in diffs)]
    return (min(sig), max(sig)) if sig else None


def plot_success(path, bots, qs, stats):
    """Success rate against q for every bot."""
    plt.figure(figsize=(8, 5))
    for b in bots:
        x = [q for q in qs if (b, q) in stats]
        plt.plot(x, [stats[(b, q)]["rate"] for q in x], marker=bot_marker(b), markersize=4,
                 color=bot_color(bots, b), label=bot_label(b))
    plt.xlabel("Flammability q")
    plt.ylabel("Success rate")
    plt.title("Success rate vs q")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_differences(path, rows, bots, qs, base):
    """`base` minus every other bot, paired by trial, with 95% error bars."""
    plt.figure(figsize=(8, 5))
    for b in bots:
        if b == base:
            continue
        d = paired_difference(rows, base, b)
        x = [q for q in qs if q in d]
        plt.errorbar(x, [100 * d[q][0] for q in x], yerr=[100 * d[q][1] for q in x],
                     marker=bot_marker(b), markersize=4, capsize=2, color=bot_color(bots, b),
                     label=f"{bot_label(base)} minus {bot_label(b)}")
    plt.axhline(0, color="black", linewidth=1)
    plt.xlabel("Flammability q")
    plt.ylabel("Difference in success rate (points)")
    plt.title(f"{bot_label(base)} vs the other bots, same trials (95% CI)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_centerpiece(path, rows, bots, qs, stats):
    """Top: success rate of every bot against q, and (dashed) the share of
    trials that are a certain win from the start.
    Bottom: Bot 4 minus each other bot on the same trials, with 95% error
    bars. The grey band is where Bot 4 beats both Bot 2 and Bot 3 with 95%
    confidence."""
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 9), sharex=True)
    span = significant_span(rows, qs)
    for b in bots:
        x = [q for q in qs if (b, q) in stats]
        top.plot(x, [stats[(b, q)]["rate"] for q in x], marker=bot_marker(b), markersize=4,
                 color=bot_color(bots, b), label=bot_label(b))
    certain = certain_wins(rows, bots, qs)
    top.plot(qs, [certain[q][1] for q in qs], "k--", label="Certain win from the start")
    if span:
        top.axvspan(span[0], span[1], color="grey", alpha=0.15,
                    label="Bot 4 ahead of Bots 2 and 3 (95%)")
    top.set_ylabel("Success rate")
    top.set_title("Success rate vs flammability q")
    top.legend()
    top.grid(alpha=0.3)

    for b in bots:
        if b == "bot4":
            continue
        d = paired_difference(rows, "bot4", b)
        x = [q for q in qs if q in d]
        bottom.errorbar(x, [100 * d[q][0] for q in x], yerr=[100 * d[q][1] for q in x],
                        marker=bot_marker(b), markersize=4, capsize=2, color=bot_color(bots, b),
                        label=f"Bot 4 minus {bot_label(b)}")
    bottom.axhline(0, color="black", linewidth=1)
    if span:
        bottom.axvspan(span[0], span[1], color="grey", alpha=0.15)
    bottom.set_xlabel("Flammability q")
    bottom.set_ylabel("Difference (points)")
    bottom.set_title("Bot 4's advantage on the same trials (95% CI)")
    bottom.legend()
    bottom.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_divergence(path, bots, qs, div):
    """How often Bots 3 and 4 make a move Bot 2's rule could not."""
    plt.figure(figsize=(8, 5))
    for b in bots:
        if b in ("bot1", "bot2"):
            continue
        x = [q for q in qs if (b, q) in div]
        plt.plot(x, [div[(b, q)][0] for q in x], marker=bot_marker(b), markersize=4,
                 color=bot_color(bots, b), label=bot_label(b))
    plt.xlabel("Flammability q")
    plt.ylabel("Share of trials")
    plt.title("How often a bot leaves Bot 2's rule at least once")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def plot_failures(path, bots, qs, stats):
    """Why bots fail, pooled over the given q values: one stacked bar per bot,
    as a share of all trials."""
    plt.figure(figsize=(8, 5))
    bottoms = [0.0] * len(bots)
    for reason in REASONS[:4]:
        heights = []
        for b in bots:
            failed = sum(stats[(b, q)]["reasons"][reason] for q in qs if (b, q) in stats)
            total = sum(stats[(b, q)]["n"] for q in qs if (b, q) in stats)
            heights.append(failed / total)
        plt.bar([bot_label(b) for b in bots], heights, bottom=bottoms,
                color=REASON_COLORS[REASONS.index(reason)], edgecolor="white",
                linewidth=1.5, label=REASON_LABELS[reason])
        bottoms = [x + h for x, h in zip(bottoms, heights)]
    plt.ylabel("Share of all trials")
    plt.title(f"Why bots fail (q = {min(qs):g} to {max(qs):g})")
    plt.legend(loc="upper left", bbox_to_anchor=(1, 1))
    plt.savefig(path, dpi=120, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--out", default="results")
    parser.add_argument("--no-plots", action="store_true")
    parser.add_argument("--base", help="bot the others are compared with (default: last)")
    parser.add_argument("--D", type=int, help="only use trials on ships of this size")
    parser.add_argument("--bots", nargs="+", help="only these bots, in this order")
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
    if "bot4" in bots:
        plot_centerpiece(os.path.join(args.out, "centerpiece.png"), rows, bots, qs, stats)
        plot_divergence(os.path.join(args.out, "divergence.png"), bots, qs,
                        divergence(rows, bots, qs))
    else:
        plot_success(os.path.join(args.out, "success_rate.png"), bots, qs, stats)
        if len(bots) > 1:
            plot_differences(os.path.join(args.out, "paired_differences.png"), rows, bots, qs,
                             args.base or bots[-1])
    lo, hi = (float(x) for x in args.failure_q.split(":"))
    plot_failures(os.path.join(args.out, "failure_reasons.png"), bots,
                  [q for q in qs if lo <= q <= hi], stats)


if __name__ == "__main__":
    main()
