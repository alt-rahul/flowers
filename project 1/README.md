# Project 1: This Ship is on Fiiiiire!

A bot on a randomly generated D x D ship has to reach the button before the
fire spreading through the ship gets to it (or to the button). This folder has
the ship, the fire, Bots 1-4, the experiments, and the writeup.

## How the code is laid out

Each file is one step, in the order things happen:

| File | What it does |
|---|---|
| `ship.py` | The ship: a 2D grid of `Tile` objects (open or blocked, on fire, bot, button). `generate_ship` builds one with the two phases from the assignment. |
| `fire.py` | `spread_fire`: one fire update. Every tile is checked against the fire as it was at the start of the step, then the new fires start (synchronous). |
| `search.py` | BFS and A* from the lecture pseudocode (`fringe`, `closed_set`, `prev`), plus `distance_map` (BFS distances to every tile) and `fireproof_path` (the certain-win check). |
| `bots.py` | One function per bot that returns the path it wants to take. Bot 4's race model and its two settings (`THRESHOLD`, `PENALTY`) are here too. |
| `simulation.py` | `Trial` (one ship with its start tiles and fire), `run_bot` (one bot on one trial, one time step at a time), and `is_certain_win`. |
| `experiments.py` | Runs every bot on thousands of trials and saves one row per (trial, bot) in `results/`. |
| `analysis.py` | Reads the saved results and makes the tables (`results/summary.md`) and the charts in `plots/`. |
| `pictures.py` | Draws the ship generation, Bot 4's danger radius, single trials and single Bot 4 decisions, into `plots/`. |
| `tests/` | Checks for each step (`python -m pytest`). |
| `writeup.md` | The writeup, with its figures in `plots/`. |

## Running it

Needs Python 3 with `numpy` and `matplotlib` (and `pytest` for the tests).
Run everything from this folder:

```bash
cd "project 1"
python -m pytest          # 30 tests
python experiments.py     # the main run (settings at the top of the file)
python analysis.py        # tables (results/summary.md) and charts (plots/)
python pictures.py        # the other pictures in plots/
```

`experiments.py` overwrites `results/main.csv.gz`, and the main run takes
under two hours on 4 cores, so you only need it to make the data again. The
settings are written at the top of each script: for example `D`, `SEED` and
`TRIALS_PER_Q` in `experiments.py`, and the trials to draw in `pictures.py`.

## The results

Every row of a results file is one bot on one trial:

| Column | Meaning |
|---|---|
| `D`, `q`, `trial` | which trial (ship size, flammability, trial number); together they make the trial again exactly |
| `bot` | `bot1` to `bot4` |
| `success` | 1 if the button was pressed |
| `reason` | `success`, `entered_fire`, `caught`, `button_burned` or `trapped` (cut off from the button) |
| `steps` | how many moves the bot made |
| `deviations` | moves Bot 2's rule couldn't have made (0 = it acted like Bot 2) |
| `ms` | time spent deciding, in milliseconds |
| `fireproof` | 1 if the trial was a certain win from the start |

- `results/main.csv.gz`: the main run, 83,000 trials at D = 50 (seed 440).
- `results/size.csv.gz`: the same bots at D = 25 and D = 100 (seed 440).
- `results/tuning.csv.gz`: the Bot 4 settings tried before the main run, on
  4,000 separate trials (seed 7). These were run with an earlier version of
  the code that could switch Bot 4's settings and two variants (the literal
  one-step 60% rule, and Manhattan distance for the fire); that version is in
  the git history.
- `results/summary.md` and the pictures in `plots/` are made from those by
  `analysis.py` and `pictures.py`.

The code was simplified several times after the main run. Each time, sampled
trials were run again and compared with the saved rows, and they matched
exactly (most recently 1,336 of 1,336 rows across D = 25, 50 and 100), so the
saved results are the results of this code.

## Differences from the original plan

- Bot 4's heuristic is the Manhattan distance to the button instead of the
  Euclidean distance: the bot only moves up, down, left and right, so it is
  the exact cost on an open grid and is still admissible.
- Bot 4 uses a race between the bot and the fire (how likely the fire gets to
  a tile first) instead of the one-step "more than 60% chance of catching
  fire" rule, which can only flag tiles next to the fire. The writeup explains
  why.
- BFS has one line more than the lecture pseudocode: a child that is already
  in `prev` is already on the fringe, so it isn't added again.
- From the instructor's guidance: every bot faces the same fire on a trial,
  the certain-win check, and counting the moves Bot 2's rule couldn't make.
- The folder is called `project 1` (with a space), so quote it in the shell.
