"""Runs the bots on lots of random trials and saves the results as CSV files.

    python experiments.py

Trial number i uses seed i for the ship and the starting tiles, and seed
FIRE_SEED + i for the fire. So any trial can be made again exactly, and every
bot on a trial faces the same fire.

It runs one trial after another and takes about an hour on a laptop.
"""
import pandas as pd

from simulation import is_certain_win, run_bot, setup_trial

FIRE_SEED = 1000000   # added to the trial number to get the fire's seed
COLUMNS = ["D", "q", "trial", "bot", "success", "reason", "steps", "deviations", "ms", "fireproof"]


def run_trial(D, q, trial):
    """Bots 1 to 4 on one trial. Returns one row for each bot."""
    ship, bot_start, button, fire_start = setup_trial(D, trial)
    certain_win = is_certain_win(ship, bot_start, button, fire_start)
    rows = []
    for bot in [1, 2, 3, 4]:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial)
        rows.append([D, q, trial, f"bot{bot}", int(result["success"]), result["reason"], result["steps"],
                     result["deviations"], round(result["ms"], 3), int(certain_win)])
    return rows


def main_run():
    """D = 50, at every q from 0 to 1 in steps of 0.05: 1,000 trials where the
    bots differ (q from 0.1 to 0.7) and 200 trials everywhere else."""
    rows = []
    for i in range(21):
        q = round(0.05 * i, 2)
        if q >= 0.1 and q <= 0.7:
            trials = 1000
        else:
            trials = 200
        print(f"Main run: q = {q}, {trials} trials")
        for trial in range(trials):
            for row in run_trial(50, q, trial):
                rows.append(row)

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/main.csv", index=False)


# The bots tried in tuning: (name, bot number, threshold, penalty, one_step)
TUNING_BOTS = [
    ("bot2", 2, 0.6, 20, False),
    ("bot3", 3, 0.6, 20, False),
    ("bot4 threshold=0.4 penalty=20", 4, 0.4, 20, False),
    ("bot4 threshold=0.6 penalty=20", 4, 0.6, 20, False),
    ("bot4 threshold=0.8 penalty=20", 4, 0.8, 20, False),
    ("bot4 threshold=0.6 penalty=5", 4, 0.6, 5, False),
    ("bot4 threshold=0.6 penalty=100", 4, 0.6, 100, False),
    ("bot4 one-step rule", 4, 0.6, 20, True),
]


def run_tuning_trial(q, trial):
    """Every bot in TUNING_BOTS on one trial. Returns one row for each."""
    ship, bot_start, button, fire_start = setup_trial(50, trial)
    certain_win = is_certain_win(ship, bot_start, button, fire_start)
    rows = []
    for name, bot, threshold, penalty, one_step in TUNING_BOTS:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial,
                         threshold, penalty, one_step)
        rows.append([50, q, trial, name, int(result["success"]), result["reason"], result["steps"],
                     result["deviations"], round(result["ms"], 3), int(certain_win)])
    return rows


def tuning_run():
    """Different Bot 4 settings, on trials 5000 to 5199 (the main run never
    uses them), so choosing the settings didn't use the main results."""
    rows = []
    for q in [0.2, 0.3, 0.4, 0.5]:
        print(f"Tuning run: q = {q}, 200 trials")
        for trial in range(5000, 5200):
            for row in run_tuning_trial(q, trial):
                rows.append(row)

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/tuning.csv", index=False)


def main():
    main_run()
    tuning_run()
    print("Finished succssfuly!")


if __name__ == "__main__":
    main()
