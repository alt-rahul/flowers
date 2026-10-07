"""Runs all four bots on lots of random trials and saves one row per (trial, bot).

    python experiments.py

Change the settings below for a different run. The main run took several
hours on 4 cores.
"""
import csv
import gzip
import time
from multiprocessing import Pool

import numpy as np

from simulation import Trial, is_certain_win, run_bot

# Settings for the main run
D = 50
SEED = 440
OUTPUT_FILE = "results/main.csv.gz"

# 1,000 trials at every q from 0 to 1 in steps of 0.05, and 3,000 trials at
# every q from 0.1 to 0.7 in steps of 0.025 (where the bots differ).
TRIALS_PER_Q = {}
for i in range(21):
    TRIALS_PER_Q[round(0.05 * i, 6)] = 1000
for i in range(25):
    TRIALS_PER_Q[round(0.1 + 0.025 * i, 6)] = 3000

# The ship-size run used the same seed with:
#   D = 25:  2,000 trials at q = 0.1, 0.2, 0.3, 0.4, 0.5, 0.6 and 0.8
#   D = 100:   400 trials at the same q values
# and saved to results/size.csv.gz.


def trial_rng(seed, q, trial_number):
    """The random generator for one trial. It only depends on the seed, q and
    the trial number, so any trial can be made again later."""
    return np.random.default_rng([seed, int(round(q * 1000000)), trial_number])


def run_one_trial(D, seed, q, trial_number):
    """Run every bot on one trial and return their rows for the CSV file."""
    trial = Trial(D, q, trial_rng(seed, q, trial_number))
    certain_win = is_certain_win(trial)
    rows = []
    for bot in [1, 2, 3, 4]:
        result = run_bot(trial, bot)
        rows.append([D, q, trial_number, f"bot{bot}", int(result["success"]), result["reason"],
                     result["steps"], result["deviations"], round(result["ms"], 3), int(certain_win)])
    return rows


def main():
    jobs = []
    for q in TRIALS_PER_Q:
        for trial_number in range(TRIALS_PER_Q[q]):
            jobs.append((D, SEED, q, trial_number))
    print(f"Running {len(jobs)} trials...")
    start = time.time()

    # Run the trials on every core at once.
    with Pool() as pool:
        results = pool.starmap(run_one_trial, jobs)

    with gzip.open(OUTPUT_FILE, "wt", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["D", "q", "trial", "bot", "success", "reason", "steps",
                         "deviations", "ms", "fireproof"])
        for rows in results:
            for row in rows:
                writer.writerow(row)
    print(f"Done in {time.time() - start:.0f} seconds, saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
