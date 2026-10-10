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
| `search.py` | BFS and A* from the lecture pseudocode (`fringe`, `closed_set`, `prev`), plus `map_distance` (BFS distances to every tile). |
| `bots.py` | One function per bot that returns the path it wants to take. Bot 4's heat map and its setting (`PENALTY`) are here too. |
| `simulation.py` | `setup_trial` (one ship with three random tiles for the bot, the button and the first fire) and `run_bot` (one bot on one trial, one time step at a time). |
| `experiments.py` | Runs every bot on thousands of trials and saves one row per (trial, bot) in `results/`, plus two tables: each bot's success rate at every q, and Bot 4's advantage over the other bots. |
| `analysis.py` | Reads the saved results, saves the tables used in the writeup as CSV files in `results/`, and draws the charts in `plots/` from them. |
| `tests/` | Checks for each step (`python -m pytest`). `tests/helpers.py` draws small ships by hand for them. |
| `writeup.md` | The writeup, with its figures in `plots/`. |

## Running it

Needs Python 3 with `numpy`, `pandas` and `matplotlib` (and `pytest` for the
tests). Run everything from this folder:

```bash
cd "project 1"
python -m pytest          # the tests
python experiments.py     # all the experiments (about an hour and a half)
python analysis.py        # tables (results/*.csv) and charts (plots/), a few seconds
```

`experiments.py` runs one trial after another and writes the results
files, so you only need it to make the data again. The settings are written in
each function (for example the q values and how many trials at each).

## Random numbers

Everything random uses `np.random`. `np.random.seed(i)` before building trial
number `i` means the same trial number always gives the same ship and the same
starting tiles. The fire uses `np.random.seed(FIRE_SEED + i)` (`FIRE_SEED` is
67), set again at the start of every bot's run, so every bot on a trial faces
exactly the same fire.

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
| `close_calls` | moves that ended right next to a burning cell |
| `mind_changes` | times the bot dropped its plan for a different route (always 0 for Bot 1) |
| `victory_margin` | if the bot won, how many moves the fire still needed to reach the button (empty if it lost) |

- `results/main.csv`: the main run at D = 50: every q from 0 to 1 in steps of
  0.05, with 200 trials at each q (the same 200 ships at every q).
- `results/success_by_q.csv`: each bot's success rate (%) at every q.
- `results/bot4_advantage.csv`: Bot 4's success rate minus each other bot's,
  on the same trials, for low, middle and high q (in percentage points).
- `results/tuning.csv`: Bot 2, Bot 3 and different Bot 4 penalties on 800
  separate trials (q = 0.2, 0.4, 0.6 and 0.8, trial numbers 5000 to 5199,
  which the main run never uses).
- `results/size.csv`: Bot 4 alone on smaller and bigger ships (D = 25 and
  D = 100), 100 trials at each q from 0.1 to 0.8.

`analysis.py` makes these tables from them (each one is a plain CSV, so every
number in the writeup can be read straight off it):

| File | What it has |
|---|---|
| `results/deviations_by_q.csv` | the % of trials at each q where Bot 3 or Bot 4 left Bot 2's rule at least once |
| `results/bot4_detour_outcomes.csv` | at each q, the trials where Bot 4 left Bot 2's rule and won while Bot 2 lost, and the other way round |
| `results/close_calls_by_q.csv` | close calls per 100 runs, for every bot at every q |
| `results/mind_changes_by_q.csv` | changes of mind per run, for Bots 2, 3 and 4 at every q |
| `results/victory_margin_by_q.csv` | the average victory margin over the wins, for every bot at every q |
| `results/breaking_point_by_ship.csv` | for every ship, the lowest q at which each bot first loses it (empty if it never does) |
| `results/breaking_point_summary.csv` | ships each bot never loses, and its average breaking point on the ships every bot loses |
| `results/think_time.csv` | how long each bot takes to decide one move (ms) |
| `results/tuning_by_q.csv` | the success rate (%) of every tuning setting at every q and overall |
| `results/size_by_q.csv` | Bot 4's success rate (%) on 25, 50 and 100 ships |

## The charts

`analysis.py` saves these in `plots/`:

| Chart | What it shows |
|---|---|
| `heat_cost.png` | What a cell costs Bot 4 based on how far the fire has to travel to reach it, for q = 0.2, 0.5 and 0.8 (Figure 1 in the writeup). |
| `success_rate.png` | Each bot's success rate at every q (Figure 2). |
| `breaking_point.png` | The % of ships a bot hasn't lost yet at any q up to each q (Figure 3). |
| `divergence.png` | How often Bots 3 and 4 make a move Bot 2's rule couldn't have made (Figure 4). |
| `close_calls.png` | Close calls per 100 runs (Figure 5). |
| `mind_changes.png` | Changes of mind per run (Figure 6). |
| `victory_margin.png` | The average victory margin over the wins (Figure 7). |
| `tuning.png` | The success rate of every setting in the tuning run (Figure 8). |

## What the results show

- Bot 4 is the best bot from q = 0.2 to 0.7. On the same trials it is
  1.5 points ahead of Bot 2 and 0.8 points ahead of Bot 3 for q from 0.25 to
  0.65, and 3 to 6 points ahead of Bot 1 for q from 0.15 to 0.4.
- For q from 0.8 to 1 it is about 2.5 points behind Bot 2. When the fire is
  that fast, the heat spreads far, so Bot 4 takes detours that give the fire
  time to cut it off.
- From q = 0.6 up, thinking stops mattering: Bot 1, which never replans, has
  exactly the same success rate as Bot 2, and at q = 1 all four bots win 53%
  of the trials.
- Bots 3 and 4 have far fewer close calls than Bots 1 and 2, every replanning
  bot changes its mind more as q grows, and the victory margin shrinks from
  about 41 moves at q = 0 to about 18 at q = 1 for every bot.
- Bot 4 holds out to the highest q on the 94 ships every bot eventually loses,
  but it is the only bot that loses 5 ships the others never lose.
- In tuning, penalties 5, 10, 20 and 30 all did about the same, so `PENALTY`
  stays at 10.
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
  and counting the moves Bot 2's rule couldn't make.
- The folder is called `project 1` (with a space), so quote it in the shell.
