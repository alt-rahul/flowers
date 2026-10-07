"""Run bots on many random ships and fires; write one CSV row per (trial, bot).

Every bot is run on the same trials (same ship, same start tiles and the same
fire), so differences between bots are paired comparisons. Each row records:
  success, reason, steps   how the bot did (see simulation.py for the reasons)
  deviations      moves Bot 2's rule could not have made
  ms              time spent inside the bot's own code (deciding, not simulating)
  fireproof       was the trial a certain win from the start? (some path stays
                  ahead of even the fastest possible fire; the same for every
                  bot on a trial)

Examples:
    python experiments.py --D 50 --q 0:1:0.05 --trials 1000 --out results/coarse.csv
    python experiments.py --D 50 --q 0.3,0.4 --trials 500 \
        --bots bot2 bot3 bot4 bot4:threshold=0.4 bot4:penalty=5 --out results/tune.csv
"""
import argparse
import csv
import os
import time
from multiprocessing import Pool

import numpy as np

from bots import make_bot
from simulation import Trial, run_bot

FIELDS = ["D", "q", "trial", "bot", "success", "reason", "steps", "deviations", "ms",
          "fireproof"]


def parse_qs(text):
    """Either "start:stop:step" (stop included) or a comma-separated list."""
    if ":" in text:
        start, stop, step = (float(x) for x in text.split(":"))
        n = int(round((stop - start) / step))
        return [round(start + i * step, 6) for i in range(n + 1)]
    return [float(x) for x in text.split(",")]


def trial_rng(seed, q, i):
    # Keyed by (seed, q, trial index) so results don't depend on how the work
    # is split between processes, and runs can be extended reproducibly.
    return np.random.default_rng([seed, int(round(q * 1_000_000)), i])


def run_chunk(job):
    D, q, seed, indices, specs = job
    rows = []
    for i in indices:
        trial = Trial.generate(D, q, trial_rng(seed, q, i))
        common = {"D": D, "q": q, "trial": i, "fireproof": int(trial.fireproof())}
        for spec in specs:
            out = run_bot(trial, make_bot(spec), count_deviations=True)
            # "ms" is time spent deciding (inside the bot), not simulating.
            rows.append({**common, "bot": spec, "success": int(out.success),
                         "reason": out.reason, "steps": out.steps,
                         "deviations": out.deviations, "ms": round(out.think_ms, 3)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50, help="ship size (default 50)")
    parser.add_argument("--q", required=True, help='"start:stop:step" or "q1,q2,..."')
    parser.add_argument("--trials", type=int, default=500, help="trials per q")
    parser.add_argument("--first-trial", type=int, default=0,
                        help="index of the first trial (to extend an earlier run)")
    parser.add_argument("--bots", nargs="+", default=["bot1", "bot2", "bot3", "bot4"])
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--chunk", type=int, default=20, help="trials per work unit")
    parser.add_argument("--out", required=True, help="CSV file to append to")
    args = parser.parse_args()

    qs = parse_qs(args.q)
    ids = range(args.first_trial, args.first_trial + args.trials)
    jobs = [(args.D, q, args.seed, ids[i:i + args.chunk], args.bots)
            for q in qs for i in range(0, len(ids), args.chunk)]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    new_file = not os.path.exists(args.out)
    start = time.time()
    with open(args.out, "a", newline="") as f, Pool(args.workers) as pool:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        for done, rows in enumerate(pool.imap_unordered(run_chunk, jobs), start=1):
            writer.writerows(rows)
            f.flush()
            if done % max(1, len(jobs) // 20) == 0 or done == len(jobs):
                print(f"{done}/{len(jobs)} chunks, {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
