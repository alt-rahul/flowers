# Project 2: Where is it?

A LocatorBot has to find a LostBot (which never moves) on the same kind of
randomly generated D x D ship as Project 1, using a bot detector. The cost of a
search is (number of moves) + 1/2 (number of detector uses).

## How the code is laid out

| File | What it does |
|---|---|
| `ship.py` | The ship from Project 1 (same generator, so the same seed gives the same ship), without the fire and the button. |
| `search.py` | BFS and the BFS distance map from Project 1, used to walk the LocatorBot around. |
| `detector.py` | The type A and type B detectors, and the knowledge base updates after a reading. |
| `strategies.py` | The two baselines and my two strategies, which pick where the LocatorBot goes next. |
| `simulation.py` | `setup_trial` (one ship with random cells for the two bots) and `run_search` (one search from start to finish). |
| `experiments.py` | Runs every strategy on many searches (on every core at once) and saves the results in `results/`. |
| `analysis.py` | Draws the charts in `plots/` from the results. |

## Running it

Needs Python 3 with `numpy`, `pandas` and `matplotlib`. Run everything from this folder:

```bash
python experiments.py     # every search (slow, see below)
python analysis.py        # the charts, a few seconds
```

The code uses simple for loops so it's easy to read, which makes `experiments.py` very slow (the
fairest coin strategy checks every cell before every other reading, so all the searches would take
days). The results in `results/` were made with a faster copy of the same code that does the same
math on whole numpy arrays at once, and it gives exactly the same numbers: I checked every
function on the same inputs, and reran 168 full searches and got the same moves, readings and cost.

## The results

Every row of `results/main.csv` is one search: the detector (`A` or `B`), the
setting (k or alpha), the trial, the strategy (`baseline` or `mine`), whether
moving was free (question 6), whether the LostBot was found, the moves, the
detector uses (`readings`), the cost and the time it took (`ms`, the only
column that changes if you run it again).

| File | What it has |
|---|---|
| `results/type_a_cost.csv` | Average cost of each type A strategy at every k. |
| `results/type_b_cost.csv` | Average cost of each type B strategy at every alpha. |
| `results/type_a_free_moves.csv` | Question 6 for type A: the cost when only the detector counts. |
| `results/type_b_free_moves.csv` | Question 6 for type B. |

| Chart | What it shows |
|---|---|
| `plots/ping_chance.png` | The chance of a type B ping vs distance for a few alphas. |
| `plots/cost_vs_k.png` | Type A: baseline vs my strategy at every k. |
| `plots/cost_vs_alpha.png` | Type B: baseline vs my strategy at every alpha. |
| `plots/cost_breakdown.png` | Moves vs detector uses for each strategy at the best k and alpha. |
| `plots/free_moves_k.png`, `plots/free_moves_alpha.png` | Question 6, when moving is free. |
