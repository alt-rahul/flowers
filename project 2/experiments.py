from multiprocessing import Pool

import pandas as pd

from simulation import run_search, setup_trial

# this file runs every strategy on teh trails ships and saves the results as csv files in the results folder. the pool 
# runs each trial on each core at the same time to speed up the process same trial uses the same seeds to keep it consistent
# seed increase by i for the searches

D = 50          
TRIALS = 200    
SEED = 67      

# testing values of k and alpha
K_VALUES = [1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25]
ALPHA_VALUES = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]

COLUMNS = ["detector", "setting", "trial", "strategy", "free_moves", "found", "moves", "readings", "cost", "ms"]


# builds the ship for one trial then runs the baseline and our strategy on the k and alpha values and my strategy again 
# but next with no cost for the moves. the baseline doesn't even need a free moves parameter since it never looks at the cost at the first place
# returns one row for each search in the same order as the columns
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


# returns the average of one column over every row with this detector, this includes variables strategy and free moves.
# rows is just a a list of searches, they are all in the same order as the columns
def average(rows, detector, setting, strategy, free_moves, column):
    column_index = COLUMNS.index(column)
    total = 0
    count = 0
    for row in rows:
        if row[0] == detector and row[1] == setting and row[3] == strategy and row[4] == free_moves:
            total += row[column_index]
            count += 1
    return total / count


# returns a table with one row for each value k or alpha, with the average cost of the baseline and my strartegy and how much
# less expensive mine is in a percentage format. when the free_moves variabel is true every cost about half the moves
# and the free moves gets its own column as well
def cost_table(rows, detector, free_moves):
    settings = K_VALUES
    name = "k"
    if detector == "B":
        settings = ALPHA_VALUES
        name = "alpha"
    table = []
    for setting in settings:
        if not free_moves:
            base_cost = average(rows, detector, setting, "baseline", False, "cost")
            my_cost = average(rows, detector, setting, "mine", False, "cost")
            table.append([float(setting), round(base_cost, 1), round(my_cost, 1),
                          round(100 * (base_cost - my_cost) / base_cost, 1)])
        else:
            base_cost = 0.5 * average(rows, detector, setting, "baseline", False, "readings")
            my_normal = 0.5 * average(rows, detector, setting, "mine", False, "readings")
            my_free = average(rows, detector, setting, "mine", True, "cost")
            table.append([float(setting), round(base_cost, 1), round(my_normal, 1), round(my_free, 1),
                          round(100 * (base_cost - my_free) / base_cost, 1)])
    if not free_moves:
        return pd.DataFrame(table, columns=[name, "baseline", "mine", "% cheaper"])
    return pd.DataFrame(table, columns=[name, "baseline", "mine (normal)", "mine (free moves)", "% cheaper"])


# runs every trial with Pool, then saves every search to main.csv and the four cost tables
def main():
    print(f"Running {TRIALS} trials")
    with Pool() as pool:
        trial_rows = pool.map(run_trial, range(TRIALS))
    rows = []
    for one_trial in trial_rows:
        for row in one_trial:
            rows.append(row)
    pd.DataFrame(rows, columns=COLUMNS).to_csv("results/main.csv", index=False)

    cost_table(rows, "A", False).to_csv("results/type_a_cost.csv", index=False)
    cost_table(rows, "B", False).to_csv("results/type_b_cost.csv", index=False)
    cost_table(rows, "A", True).to_csv("results/type_a_free_moves.csv", index=False)
    cost_table(rows, "B", True).to_csv("results/type_b_free_moves.csv", index=False)
    print("Finished!")


if __name__ == "__main__":
    main()
