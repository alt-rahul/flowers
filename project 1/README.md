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
| `bots.py` | One function per bot that returns the path it wants to take. Bot 4's heat map and its setting (`PENALTY`) are here too. |
| `simulation.py` | `Trial` (one ship with its start tiles and fire), `run_bot` (one bot on one trial, one time step at a time), and `is_certain_win`. |
| `experiments.py` | Runs every bot on thousands of trials and saves one row per (trial, bot) in `results/`, plus two tables: each bot's success rate at every q, and Bot 4's advantage over the other bots. |
| `analysis.py` | Reads the saved results and makes the tables (`results/summary.md`) and the charts in `plots/`. |
| `tests/` | Checks for each step (`python -m pytest`). |
| `writeup.md` | The writeup, with its figures in `plots/`. |

## Running it

Needs Python 3 with `numpy`, `pandas` and `matplotlib` (and `pytest` for the
tests). Run everything from this folder:

```bash
cd "project 1"
python -m pytest          # the tests
python experiments.py     # all the experiments (a few hours)
python analysis.py        # tables (results/summary.md) and charts (plots/)
```

`experiments.py` runs one trial after another and writes the two results
files, so you only need it to make the data again. The settings are written in
each function (for example the q values and how many trials at each).

## Random numbers

Everything random uses `np.random`. `np.random.seed(i)` before building trial
number `i` means the same trial number always gives the same ship and the same
starting tiles. The fire uses `np.random.seed(1000000 + i)`, set again at the
start of every bot's run, so every bot on a trial faces exactly the same fire.

## The results

Every row of a results file is one bot on one trial:

| Column | Meaning |
|---|---|
| `D`, `q`, `trial` | which trial (ship size, flammability, trial number); together they make the trial again exactly |
| `bot` | `bot1` to `bot4` (in the tuning file, also the Bot 4 settings tried) |
| `success` | 1 if the button was pressed |
| `reason` | `success`, `entered_fire`, `caught`, `button_burned` or `trapped` (cut off from the button) |
| `steps` | how many moves the bot made |
| `deviations` | moves Bot 2's rule couldn't have made (0 = it acted like Bot 2) |
| `ms` | time spent deciding, in milliseconds (the only column that changes if you run it again) |
| `fireproof` | 1 if the trial was a certain win from the start |

- `results/main.csv`: the main run at D = 50: every q from 0 to 1 in steps of
  0.05, with 1,000 trials at each q from 0.1 to 0.7 and 200 elsewhere.
- `results/success_by_q.csv`: each bot's success rate (%) at every q.
- `results/bot4_advantage.csv`: Bot 4's success rate minus each other bot's,
  on the same trials, for low, middle and high q (points, 95% confidence).
- `results/tuning.csv`: Bot 2, Bot 3 and different Bot 4 penalties on 800
  separate trials (q = 0.2, 0.4, 0.6 and 0.8, trial numbers 5000 to 5199,
  which the main run never uses).
- `results/size.csv`: Bot 4 alone on smaller and bigger ships (D = 25 and
  D = 100), 200 trials at each q from 0.1 to 0.8.
- `results/summary.md` and the charts in `plots/` are made from those by
  `analysis.py`.

## The charts

`analysis.py` saves these in `plots/`:

| Chart | What it shows |
|---|---|
| `success_rate.png` | Each bot's success rate at every q, and the share of trials that are a certain win from the start (Figure 1 in the writeup). |
| `bot4_advantage.png` | Bot 4's success rate minus each other bot's, on the same trials (Figure 2). |
| `ship_size.png` | Bot 4's success rate on ships of size 25, 50 and 100 (Figure 3). |
| `divergence.png` | How often Bots 3 and 4 make a move Bot 2's rule couldn't have made (Figure 4). |
| `failure_reasons.png` | Why each bot fails (Figure 5). |
| `tuning.png` | Each Bot 4 penalty (and Bots 2 and 3) minus the chosen penalty of 10, with 95% confidence intervals (Figure 6). |
| `head_to_head.png` | At each q, out of every 1,000 trials: how often Bot 4 won where Bot 3 lost, and the other way round (not in the writeup). |

## What the results show

- Bot 4 is the best bot from q = 0.1 to 0.7. On the same trials it is about
  1 point ahead of Bots 2 and 3 for q from 0.25 to 0.65, and 4 to 5 points
  ahead of Bot 1 for q from 0.1 to 0.3.
- For q from 0.8 to 1 it is about 2 points behind Bot 2. When the fire is
  that fast, the heat spreads far, so Bot 4 takes detours that give the fire
  time to cut it off.
- About half the trials are a certain win from the start (a fireproof path
  exists). Bots 1, 2 and 3 won all 7,348 of them, and Bot 4 lost 9, all at
  q = 0.8 or more.
- In tuning, penalties 5, 10 and 20 did about the same and 30 did worse, so
  `PENALTY` is 10.
- Bot 4 does about the same on 25 by 25, 50 by 50 and 100 by 100 ships: a
  bigger ship makes both the bot's path and the fire's path longer.

## Differences from the original plan

- Bot 4's heuristic is the Manhattan distance to the button instead of the
  Euclidean distance: the bot only moves up, down, left and right, so it is
  the exact cost on an open grid and is still admissible.
- Bot 4 puts the fire's risk into A*'s path cost, as planned, with a heat
  map: a tile's heat is q^(d - 1), where d is the fire's distance to it, and
  stepping onto it costs 1 + PENALTY * heat. A burning tile costs a huge
  number (BURNING_COST), so the bot never steps on fire.
- BFS has one line more than the lecture pseudocode: a child that is already
  in `prev` is already on the fringe, so it isn't added again.
- From the instructor's guidance: every bot faces the same fire on a trial,
  the certain-win check, and counting the moves Bot 2's rule couldn't make.
- The folder is called `project 1` (with a space), so quote it in the shell.
