from multiprocessing import Pool

import pandas as pd

from simulation import run_search, setup_trial

# this file runs every strategy on thousands of searches and saves the results as csv files in the results folder.
# in project 1 I said I wanted to learn parallelization to make the experiments faster, so this time I used
# Pool from multiprocessing: it runs one trial on each core of the computer at the same time, so with 4 cores
# it's about 4 times faster. every trial is completely separate from the others so they can run in any order.
# trial number i always uses seed i for the ship and the two starting cells (the same as project 1), and seed
# SEED + i for the random numbers during the search, so any search can be made again exactly the same way

D = 50          # the ship is 50 by 50, the same size as project 1
TRIALS = 200    # how many searches for each strategy at each k or alpha
SEED = 67       # added to the trial number to get the seed for the random numbers during a search

# the values of k and alpha that get tested (the writeup explains how I picked these ranges)
K_VALUES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
ALPHA_VALUES = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

# the columns of the results file, each row is one search
COLUMNS = ["detector", "setting", "trial", "strategy", "free_moves", "found", "moves", "readings", "cost", "ms"]


# every search on one trial: the ship only gets built once (building it takes longer than most searches) and
# then every strategy runs on it at every k and alpha. both strategies run with the normal costs, and my strategies
# also run again with free moves for question 6. the baselines don't need a free moves run, they don't look at
# the cost at all so they do the exact same thing either way, their free moves cost is just half their readings.
# it returns one row for each search (in the same order as COLUMNS)
def run_trial(trial):
    ship, bot_start, lost = setup_trial(D, trial)
    rows = []
    for detector, settings in [("A", K_VALUES), ("B", ALPHA_VALUES)]:
        for setting in settings:
            for strategy, free_moves in [("baseline", False), ("mine", False), ("mine", True)]:
                result = run_search(ship, bot_start, lost, detector, setting, strategy, SEED + trial, free_moves)
                rows.append([detector, setting, trial, strategy, free_moves, int(result["found"]),
                             result["moves"], result["readings"], result["cost"], round(result["ms"], 1)])
    return rows


# makes a table with one row for each k (or alpha) and the average cost of each strategy, plus how much
# cheaper (in %) my strategy is than the baseline. free moves is for the question 6 table, where the cost is
# only the detector (1/2 per reading) for everything, including the baseline and my normal strategy
def cost_table(results, detector, free_moves):
    rows = []
    settings = sorted(results[results["detector"] == detector]["setting"].unique())
    for setting in settings:
        runs = results[(results["detector"] == detector) & (results["setting"] == setting)]
        baseline = runs[(runs["strategy"] == "baseline") & (runs["free_moves"] == False)]
        mine = runs[(runs["strategy"] == "mine") & (runs["free_moves"] == False)]
        if not free_moves:
            base_cost = baseline["cost"].mean()
            my_cost = mine["cost"].mean()
            rows.append([setting, round(base_cost, 1), round(my_cost, 1),
                         round(100 * (base_cost - my_cost) / base_cost, 1)])
        else:
            my_free = runs[(runs["strategy"] == "mine") & (runs["free_moves"] == True)]
            base_cost = 0.5 * baseline["readings"].mean()
            rows.append([setting, round(base_cost, 1), round(0.5 * mine["readings"].mean(), 1),
                         round(my_free["cost"].mean(), 1),
                         round(100 * (base_cost - my_free["cost"].mean()) / base_cost, 1)])
    name = "k" if detector == "A" else "alpha"
    if not free_moves:
        return pd.DataFrame(rows, columns=[name, "baseline", "mine", "% cheaper"])
    return pd.DataFrame(rows, columns=[name, "baseline", "mine (normal)", "mine (free moves)", "% cheaper"])


# runs every trial (one trial on each core at a time), then saves every row and the four tables
def main():
    print(f"Running {TRIALS} trials")
    with Pool() as pool:
        trial_rows = pool.map(run_trial, range(TRIALS))
    rows = []
    for one_trial in trial_rows:
        for row in one_trial:
            rows.append(row)
    results = pd.DataFrame(rows, columns=COLUMNS)
    results.to_csv("results/main.csv", index=False)

    cost_table(results, "A", False).to_csv("results/type_a_cost.csv", index=False)
    cost_table(results, "B", False).to_csv("results/type_b_cost.csv", index=False)
    cost_table(results, "A", True).to_csv("results/type_a_free_moves.csv", index=False)
    cost_table(results, "B", True).to_csv("results/type_b_free_moves.csv", index=False)
    print("Finished!")


# the "if __name__" part is needed for Pool, otherwise every core would start running main() again
if __name__ == "__main__":
    main()
