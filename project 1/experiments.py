"""Runs the bots on lots of random trials and saves the results as CSV files.

    python experiments.py

Trial number i uses seed i for the ship and the starting tiles, and seed
FIRE_SEED + i for the fire. So any trial can be made again exactly, and every
bot on a trial faces the same fire.

It runs one trial after another and takes a few hours on a laptop.

After the main run it also prints and saves two tables:
    results/success_by_q.csv     each bot's success rate (%) at every q
    results/bot4_advantage.csv   Bot 4's success rate minus each other bot's,
                                 on the same trials, for low, middle and high q
"""
import math

import pandas as pd

from simulation import run_bot, setup_trial

FIRE_SEED = 1000000   # added to the trial number to get the fire's seed
COLUMNS = ["D", "q", "trial", "bot", "success", "reason", "steps", "deviations", "ms"]


def run_trial(D, q, trial):
    """Bots 1 to 4 on one trial. Returns one row for each bot."""
    ship, bot_start, button, fire_start = setup_trial(D, trial)
    rows = []
    for bot in [1, 2, 3, 4]:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial)
        rows.append([D, q, trial, f"bot{bot}", int(result["success"]), result["reason"], result["steps"],
                     result["deviations"], round(result["ms"], 3)])
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

    success = success_table(results)
    success.to_csv("results/success_by_q.csv", index=False)
    print("\nSuccess rate (%) at each q:")
    print(success.to_string(index=False))

    advantage = advantage_table(results)
    advantage.to_csv("results/bot4_advantage.csv", index=False)
    print("\nBot 4 minus each other bot, same trials (points, 95% confidence):")
    print(advantage.to_string(index=False))


def success_table(results):
    """One row for each q: every bot's success rate, in %."""
    rows = []
    for q in sorted(results["q"].unique()):
        row = [q]
        for bot in ["bot1", "bot2", "bot3", "bot4"]:
            successes = results[(results["q"] == q) & (results["bot"] == bot)]["success"]
            row.append(round(100 * successes.mean(), 1))
        rows.append(row)
    return pd.DataFrame(rows, columns=["q", "Bot 1", "Bot 2", "Bot 3", "Bot 4"])


def bot4_advantage(results, low_q, high_q, other):
    """Bot 4's success rate minus the other bot's, for every q from low_q to
    high_q, in points, and the size of its 95% confidence interval.

    Both bots faced the same fire on every trial, so we compare them trial by
    trial: each trial gives 1 (only Bot 4 won), -1 (only the other bot won)
    or 0 (both won or both lost)."""
    diffs = []
    for q in sorted(results["q"].unique()):
        if q < low_q or q > high_q:
            continue
        bot4 = results[(results["q"] == q) & (results["bot"] == "bot4")].sort_values("trial")
        rival = results[(results["q"] == q) & (results["bot"] == other)].sort_values("trial")
        bot4_success = list(bot4["success"])
        rival_success = list(rival["success"])
        for i in range(len(bot4_success)):
            diffs.append(bot4_success[i] - rival_success[i])

    mean = sum(diffs) / len(diffs)
    total = 0
    for d in diffs:
        total += (d - mean) ** 2
    standard_deviation = math.sqrt(total / (len(diffs) - 1))
    error = 1.96 * standard_deviation / math.sqrt(len(diffs))
    return 100 * mean, 100 * error


# The q ranges in the advantage table: (name, lowest q, highest q)
Q_RANGES = [
    ("0.1 to 0.2", 0.1, 0.2),
    ("0.25 to 0.65", 0.25, 0.65),
    ("0.7 to 1", 0.7, 1.0),
    ("all q", 0.0, 1.0),
]


def advantage_table(results):
    """One row for each q range: Bot 4 minus Bot 1, Bot 2 and Bot 3."""
    rows = []
    for name, low_q, high_q in Q_RANGES:
        row = [name]
        for other in ["bot1", "bot2", "bot3"]:
            mean, error = bot4_advantage(results, low_q, high_q, other)
            row.append(f"{mean:+.1f} ± {error:.1f}")
        rows.append(row)
    return pd.DataFrame(rows, columns=["q range", "vs Bot 1", "vs Bot 2", "vs Bot 3"])


# The bots tried in tuning: (name, bot number, penalty)
TUNING_BOTS = [
    ("bot2", 2, 10),
    ("bot3", 3, 10),
    ("bot4 penalty=5", 4, 5),
    ("bot4 penalty=10", 4, 10),
    ("bot4 penalty=20", 4, 20),
    ("bot4 penalty=30", 4, 30),
]


def run_tuning_trial(q, trial):
    """Every bot in TUNING_BOTS on one trial. Returns one row for each."""
    ship, bot_start, button, fire_start = setup_trial(50, trial)
    rows = []
    for name, bot, penalty in TUNING_BOTS:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial, penalty)
        rows.append([50, q, trial, name, int(result["success"]), result["reason"], result["steps"],
                     result["deviations"], round(result["ms"], 3)])
    return rows


def tuning_run():
    """Different Bot 4 penalties, on trials 5000 to 5199 (the main run never
    uses them), so choosing the penalty didn't use the main results. The q
    values go up to 0.8 because a big penalty can hurt when the fire is fast."""
    rows = []
    for q in [0.2, 0.4, 0.6, 0.8]:
        print(f"Tuning run: q = {q}, 200 trials")
        for trial in range(5000, 5200):
            for row in run_tuning_trial(q, trial):
                rows.append(row)

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/tuning.csv", index=False)


def run_size_trial(D, q, trial):
    """Only Bot 4, on one trial on a ship of size D. Returns one row."""
    ship, bot_start, button, fire_start = setup_trial(D, trial)
    result = run_bot(ship, bot_start, button, fire_start, q, 4, FIRE_SEED + trial)
    return [D, q, trial, "bot4", int(result["success"]), result["reason"], result["steps"],
            result["deviations"], round(result["ms"], 3)]


def size_run():
    """Bot 4 on smaller and bigger ships (D = 25 and D = 100), 200 trials at
    each q from 0.1 to 0.8, to check that D = 50 isn't special."""
    rows = []
    for D in [25, 100]:
        for q in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            print(f"Ship size run: D = {D}, q = {q}, 200 trials")
            for trial in range(200):
                rows.append(run_size_trial(D, q, trial))

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/size.csv", index=False)


def main():
    main_run()
    tuning_run()
    size_run()
    print("Finished succssfuly!")


if __name__ == "__main__":
    main()
