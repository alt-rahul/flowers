"""Bad decision or bad luck? Replay starting configurations under many fires.

A single lost trial can't tell you whether the bot decided badly: the same
choice may win most of the time and have just been unlucky. This script
takes trials from a results CSV where one bot lost and another won, keeps
each trial's ship and starting cells, and reruns every bot on many fresh
fire realisations. If the loser still does better on average from that
start, the loss was bad luck; if it does worse, its decisions there were
genuinely worse.

    python replay_check.py results/main.csv.gz --lost bot4 --won bot3 --fires 40
"""
import argparse
import os
from collections import defaultdict
from multiprocessing import Pool

import numpy as np

from analyze import bot_label, load
from bots import make_bot
from experiments import trial_rng
from simulation import Trial, run_bot


def replay(job):
    D, q, seed, trial, bots, fires = job
    base = Trial.generate(D, q, trial_rng(seed, q, trial))
    wins = dict.fromkeys(bots, 0)
    for j in range(fires):
        rng = np.random.default_rng([seed, 999, trial, j])
        t = base.with_new_fire(rng)
        for b in bots:
            wins[b] += run_bot(t, make_bot(b)).success
    return q, trial, {b: w / fires for b, w in wins.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv", nargs="+")
    parser.add_argument("--lost", required=True, help="bot that lost the original trial")
    parser.add_argument("--won", required=True, help="bot that won it")
    parser.add_argument("--bots", nargs="+", help="bots to replay (default: --lost and --won)")
    parser.add_argument("--fires", type=int, default=40, help="fresh fires per configuration")
    parser.add_argument("--seed", type=int, default=440, help="seed the CSV was made with")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    args = parser.parse_args()

    rows = load(args.csv)
    by = defaultdict(dict)
    for r in rows:
        by[(r["D"], r["q"], r["trial"])][r["bot"]] = r["success"]
    cases = sorted(k for k, v in by.items()
                   if v.get(args.lost) == 0 and v.get(args.won) == 1)
    bots = args.bots or [args.lost, args.won]
    jobs = [(D, q, args.seed, t, bots, args.fires) for D, q, t in cases]
    print(f"{len(cases)} trials where {bot_label(args.lost)} lost and "
          f"{bot_label(args.won)} won; replaying each with {args.fires} fresh fires")
    with Pool(args.workers) as pool:
        results = pool.map(replay, jobs)
    print("q, trial: " + ", ".join(bot_label(b) for b in bots))
    for q, t, rates in results:
        print(f"{q:g}, {t}: " + ", ".join(f"{rates[b]:.2f}" for b in bots))
    print("Mean win rate over these starts: " + ", ".join(
        f"{bot_label(b)} {np.mean([r[b] for _, _, r in results]):.3f}" for b in bots))
    better = sum(r[args.lost] > r[args.won] for _, _, r in results)
    worse = sum(r[args.lost] < r[args.won] for _, _, r in results)
    print(f"{bot_label(args.lost)} does better from {better} of these starts, "
          f"worse from {worse}, the same from {len(results) - better - worse}.")


if __name__ == "__main__":
    main()
