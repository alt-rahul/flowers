import pandas as pd

from simulation import run_bot, setup_trial

# this file runs the bots on thousands of random trials and saves the results as csv files in the results folder,
# but it takes a few hours since it runs one trial after another (though I learn more about parallelization in python soon 
# to make future projects faster - especially for a project related to inference)
# trial number i always uses seed i for the ship and the starting cells, and seed FIRE_SEED + i for the fire,
# so any trial can be made again exactly the same way, and every bot on a trial faces the exact same fire

FIRE_SEED = 67   # added to the trial number to get the fire's seed, so the fire's seed is never the same as the ship's 
#the seed also happens to be a specical number these days...something to ponder about

# the columns of every results file, each row is one bot on one trial
COLUMNS = ["D", "q", "trial", "bot", "success", "reason", "steps", "ms", "close_calls", "change_plan"]


# turns the result of one run into one row of the results file (in the same order as COLUMNS)
def make_row(D, q, trial, name, result):
    return [D, q, trial, name, int(result["success"]), result["reason"], result["steps"],
            round(result["ms"], 3), result["close_calls"], result["change_plan"]]


# this function runs all 4 bots on one trial (the same ship, the same starting cells and the same fire)
# and returns one row of results for each bot
def run_trial(D, q, trial):
    ship, bot_start, button, fire_start = setup_trial(D, trial)
    rows = []
    for bot in [1, 2, 3, 4]:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial)
        rows.append(make_row(D, q, trial, f"bot{bot}", result))
    return rows


# this is the main part of the experiment, it uses a 50 by 50 ship and tries every q from 0 to 1 in steps of 0.05.
# this runs 200 trials at every q, and since trial i is always the same ship, every q uses the exact same 200 ships
# and starting cells, so the only thing that changes from one q to the next is how fast the fire spreads (keeping this fair 
# to compare performance between bots) once it's done it saves every row in a csv file and also makes the two tables
# one is the tables is the success rate of each bot at every q, and the other table how much better bot4 does than 
# every other bot (to measure the performance gains)
def main_run():
    rows = []
    for i in range(21):
        q = round(0.05 * i, 2) 
        trials = 200
        print(f"Main run: q = {q}, {trials} trials")
        for trial in range(trials):
            for row in run_trial(50, q, trial):
                rows.append(row)

    # saves every row to results/main.csv, then makes the two tables and saves them in the results folder too
    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/main.csv", index=False)

    success = success_table(results)
    success.to_csv("results/success_by_q.csv", index=False)

    advantage = advantage_table(results)
    advantage.to_csv("results/bot4_advantage.csv", index=False)


# makes a table with one row for each q and every bot's success rate at that q,
# a success is saved as 1 and a failure as 0 so the mean of the success column 
# is technically the success rate
def success_table(results):
    table = results.pivot_table(index="q", columns="bot", values="success")   # the mean success of every bot at every q
    table = (100 * table).round(1)
    table.columns = ["Bot 1", "Bot 2", "Bot 3", "Bot 4"]
    return table.reset_index()


# calculates how much better bot4 does than another bot for every q between low_q and high_q.
# since both bots literally face the exact same fire on every single trial, it's safe to compare them directly:
# bot4's success rate minus the other bot's success rate over the same trials is how much better bot4 is
def bot4_advantage(results, low_q, high_q, other):
    rows = results[(results["q"] >= low_q) & (results["q"] <= high_q)]
    bot4_rate = rows[rows["bot"] == "bot4"]["success"].mean()
    other_rate = rows[rows["bot"] == other]["success"].mean()
    return 100 * (bot4_rate - other_rate)   # times 100 to turn it into percentage points


# the q ranges that are used in the advantage table: (name, lowest q, highest q)
ranges = [
    ("0.1 to 0.2", 0.1, 0.2),
    ("0.25 to 0.65", 0.25, 0.65),
    ("0.7 to 1", 0.7, 1.0),
    ("all q", 0.0, 1.0),
]


# makes the advantage table, one row for each q range, with how much better bot4 does than bot1, bot2 and bot3
def advantage_table(results):
    rows = []
    for name, low_q, high_q in ranges:
        row = [name]
        for other in ["bot1", "bot2", "bot3"]:
            mean = bot4_advantage(results, low_q, high_q, other)
            row.append(f"{mean:+.1f}")
        rows.append(row)
    return pd.DataFrame(rows, columns=["q range", "vs Bot 1", "vs Bot 2", "vs Bot 3"])


# the bots that are tried in the tuning run: (name, bot number, penalty), the penalty only matters for bot4,
# bot2 and bot3 are there so we can see how the different bot4 penalties compare to them
bot_params_changed = [
    ("bot2", 2, 10),
    ("bot3", 3, 10),
    ("bot4 penalty=5", 4, 5),
    ("bot4 penalty=10", 4, 10),
    ("bot4 penalty=20", 4, 20),
    ("bot4 penalty=30", 4, 30),
]


# same as run_trial but for the tuning run, it runs every bot in bot_params_changed on one trial and returns a row for each
def run_tuning_trial(q, trial):
    ship, bot_start, button, fire_start = setup_trial(50, trial)
    rows = []
    for name, bot, penalty in bot_params_changed:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, FIRE_SEED + trial, penalty)
        rows.append(make_row(50, q, trial, name, result))
    return rows


# this is how I picked bot4's penalty, it tries different penalties on trials 5000 to 5199, which the main run
# never uses, so picking the penalty didn't use the main results at all (otherwise the main results would be
# a bit biased towards bot4). the q values go up to 0.8 because a big penalty can hurt when the fire is fast
def tuning_run():
    rows = []
    for q in [0.2, 0.4, 0.6, 0.8]:
        print(f"Tuning run: q = {q}, 200 trials")
        for trial in range(5000, 5200):
            for row in run_tuning_trial(q, trial):
                rows.append(row)

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/tuning.csv", index=False)


# runs only bot4 on one trial with a ship of size D and returns its row
def run_size_trial(D, q, trial):
    ship, bot_start, button, fire_start = setup_trial(D, trial)
    result = run_bot(ship, bot_start, button, fire_start, q, 4, FIRE_SEED + trial)
    return make_row(D, q, trial, "bot4", result)


# this runs bot4 on a smaller ship (25 by 25) and a bigger ship (100 by 100) with 100 trials at each q
# from 0.1 to 0.8, to check that the results from the 50 by 50 ship aren't special to that one size
def size_run():
    rows = []
    for D in [25, 100]:
        for q in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
            print(f"Ship size run: D = {D}, q = {q}, 100 trials")
            for trial in range(100):
                rows.append(run_size_trial(D, q, trial))

    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/size.csv", index=False)


# runs all three experiments one after another
def main():
    main_run()
    tuning_run()
    size_run()
    print("Finished succssfuly!")


if __name__ == "__main__":
    main()
