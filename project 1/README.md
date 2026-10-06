# Project 1: This Ship is on Fiiiiire!

A bot on a randomly generated D x D ship has to reach the fire-suppression
button before the fire spreading through the ship gets to it (or to the
button). This directory has the ship generator, the fire model, Bots 1-4, a
clairvoyant upper bound used for the failure analysis, and the experiment,
analysis and visualisation scripts.

## Running it

Needs Python 3.10+ with `numpy` and `matplotlib` (and `pytest` for the tests).

```bash
cd "project 1"
pip install numpy matplotlib pytest

python -m pytest                                   # 81 tests, a few seconds

# Experiments: one CSV row per (trial, bot); uses every core.
python experiments.py --D 50 --q 0:1:0.05 --trials 1000 --out results/main.csv
python analyze.py results/main.csv --out results   # tables + charts

# Replay a single trial (trial numbers match the CSV) or find an interesting one
python visualize.py --D 50 --q 0.3 --trial 17 --out trial17.png
python visualize.py --D 50 --q 0.3 --where bot3=0 bot4=1 --bots bot3 bot4 --out case.png

# How well Bot 4's fire forecast matches the real fire
python forecast_check.py --out results/forecast_calibration.png
```

Bots are named by spec strings, so variants can be compared in one run:
`bot2:lazy=false`, `bot4:risk_weight=30`, `bot4:forecast=meanfield`.

## Files

| File | What it does |
|---|---|
| `ship.py` | Ship generation (both phases from the spec) and the `Ship` class. No fire/bot code, so it can be reused in later projects. |
| `fire.py` | The spread rule and `FireTrajectory`, one fire realisation per trial. |
| `planning.py` | BFS shortest path and the time-dependent, risk-aware A* used by Bot 4. |
| `forecast.py` | Bot 4's probabilistic fire forecasts (message passing, plus the naive mean-field version for comparison). |
| `bots.py` | Bots 1-4 behind one `reset()` / `act()` interface. |
| `simulation.py` | Runs a bot on a trial in the order the spec gives; clairvoyant upper bound. |
| `experiments.py` | Parallel, reproducible parameter sweeps that write CSVs. |
| `analyze.py` | Success rates with 95% CIs, paired bot comparisons, failure breakdowns, charts. |
| `visualize.py` | Draws what each bot did on one trial. |
| `forecast_check.py` | Calibration of the fire forecasts against Monte Carlo runs of the real fire. |
| `tests/` | Unit tests (see "Correctness checks"). |
| `results/` | Data and charts from the runs described below. |

## Design

### Ship
`generate_layout` follows the spec exactly. Phase 1 (`grow_maze`) opens a
random interior cell, then repeatedly opens a random blocked cell with exactly
one open neighbour. Phase 2 (`reduce_dead_ends`) opens a random closed
neighbour of a random dead end until at most half of the original dead ends
remain. Phase 1 keeps the set of candidate cells up to date incrementally
(opening a cell only changes its 4 neighbours' counts), so it is O(D^2)
instead of rescanning the grid every iteration (O(D^4)). Only the first open
cell has to be in the interior; later cells may be on the edge of the grid.

### Fire
Each step every non-burning open cell ignites with probability
1 - (1 - q)^K, where K is its number of burning neighbours. As the TA
feedback asked, the update is **synchronous**: K is counted from the fire as
it was at the start of the step, and newly ignited cells are only added
afterwards, so they cannot spread fire in the same step
(`fire.fire_step`; `test_update_is_synchronous` checks this). The whole update
is a handful of numpy operations on the grid.

The fire does not react to the bot, so `FireTrajectory` simulates it once per
trial (lazily, only as far as anyone needs) and records each cell's ignition
time. All four bots and the clairvoyant bound then face the **same** fire on
each trial, which makes bot comparisons paired and much less noisy. Bots only
ever see the cells burning at the current time step.

### Time step and outcomes
`simulation.run_bot` follows the spec's order: the bot picks a move, moves,
presses the button if it is on it, and otherwise the fire advances. Every
failure is labelled with its cause:

| Outcome | Meaning |
|---|---|
| `entered_fire` | the bot moved into a burning cell (only Bot 1 does this) |
| `caught` | the fire spread onto the bot's cell |
| `button_burned` | the button caught fire first; nobody can press it any more |
| `trapped` | the bot is alive but every route to the button runs through fire |

The last two end the trial early. That doesn't change any result, because
the fire never goes out, so once either happens the bot is certain to fail.

### Bots
- **Bot 1**: BFS once at t = 0, avoiding the initial fire cell, then follows
  that path whatever the fire does.
- **Bot 2**: shortest path avoiding all burning cells, replanned every step.
- **Bot 3**: shortest path avoiding burning cells *and* their neighbours if
  one exists, otherwise Bot 2's path. The bot's own cell is never avoided;
  the button is avoided like any other cell, so a button next to the fire
  means Bot 3 falls back to Bot 2's rule.
- **Bot 4**: risk-aware A*, described next.

### Bot 4: risk-aware, time-dependent A*

Every step Bot 4:

1. **Forecasts the fire.** From the cells burning now and q, it computes
   p_t(c), the probability that cell c is burning t steps from now, for as
   many future steps as the search needs. It uses *dynamic message passing*
   (`forecast.MessagePassingForecast`). The fire is an SI epidemic (each
   burning cell independently ignites each neighbour with probability q per
   step), and message passing tracks, for every directed edge k -> i, the
   chance that k has *not yet* ignited i, computed with i held unburnt. That
   last detail is the key: it stops probability from echoing back and forth
   between neighbours. Each step is a few vectorised gathers over the
   ship's edges.
2. **Searches over (cell, time).** Entering cell c on move t costs
   `1 + risk_weight * -log(1 - p_t(c))`. Summed along a path, the risk term
   is -log of the chance of surviving every cell on it (treating cells as
   independent), so the bot minimises
   `path length + risk_weight * -log P(survive the path)`.
   Because the risk depends on *when* each cell is reached, a longer, safer
   detour is not free: every later cell, and above all the button, is
   reached later, when the fire has had longer to get there. That is
   exactly the shorter-but-riskier vs longer-but-safer trade-off the TA
   feedback points at, priced in one currency.
3. **Takes the first step** of the cheapest plan, then replans next step
   with the new fire.

Details that make it exact and fast:
- *Heuristic.* The BFS distance from each cell to the button through open
  cells, ignoring fire, computed once per trial. Every move costs at least 1,
  so it is admissible and consistent. In a maze it is far tighter than
  Euclidean or Manhattan distance, so A* expands far fewer states.
- *Pruning.* The fire only grows, so forecast risk never decreases over
  time. Reaching a cell earlier and no more expensively is therefore never
  worse, so a state (c, t) is skipped once (c, t') with t' <= t has been
  expanded. `test_risk_astar_matches_brute_force` checks the result against
  an unpruned Dijkstra over every (cell, time) state. The same monotonicity
  means waiting in place never helps, so it is not searched.
- *Laziness and reuse.* Forecast layers are only computed up to the time
  steps the search actually reaches. A forecast is reused while the fire has
  not changed (common at low q), and the edge index used by message passing
  is built once per ship.
- With `risk_weight = 0` Bot 4 is exactly Bot 2 (tested).
- **Assumption:** Bot 4 knows q, the ship's flammability.

**Why message passing and not a simpler forecast.** The first version used
a naive mean-field forecast: treat each neighbour as burning independently
with its current probability. `forecast_check.py` showed it was badly
miscalibrated (chart below). On these mostly tree-shaped ships, probability
leaks along every back-and-forth walk, so cells forecast at 85% actually
burn about 10% of the time when q = 0.3. Message passing fixes this. It is
exact on trees (and exactly matches the closed-form answer on a corridor in
`test_message_passing_is_exact_on_a_corridor`), and only slightly
pessimistic on these ships, which have a few loops.

![Forecast calibration](results/forecast_calibration.png)

### Clairvoyant upper bound
`simulation.oracle_steps` asks whether *any* sequence of moves could have
won, given the entire future of that trial's fire. It is a BFS in which a
cell can be entered on move k only if it is not burning after k fire updates.
Because the fire only grows, arriving anywhere as early as possible is
always best, so each cell is visited once. This bounds every possible bot,
and it splits each failure into **avoidable** (some sequence of moves would
have won) and **unavoidable**.

## Deviations from the original plan

1. **No `Tile` objects.** The plan stored the ship as a 2D array of `Tile`
   objects. The code holds the same information in numpy arrays and integers
   instead: `ship.grid` (open/blocked), the fire's burning mask and ignition
   times, and the bot and button as flat cell indices. The fire update and
   the "next to the fire" test then become a few whole-grid numpy
   operations, and the planners work on plain ints, which is what made tens
   of thousands of trials per bot affordable. If you want a `Tile` view for
   the writeup or later projects it is easy to add on top, but it would be
   slow in the inner loops.
2. **Bots 2 and 3 don't literally rerun BFS every step.** They reuse their
   current plan until fire lands on it (for Bot 3, while it is on a buffered
   plan). This gives the same behaviour: the set of usable cells only
   shrinks, so an untouched shortest path is still a shortest path. The only
   possible difference is which of several equally short paths gets picked.
   `test_lazy_replanning_matches_full_replanning` compares against a fresh
   BFS at every step, and `bot2:lazy=false` / `bot3:lazy=false` replan every
   step if you want the literal version.
3. **Bot 4 still uses A*, with three changes.** (a) The heuristic is the
   true BFS distance to the button instead of Euclidean distance. Both are
   admissible, but the BFS distance is much tighter in a maze. (b) The search
   runs over (cell, time) instead of cells, because a cell's risk depends on
   when the bot arrives. (c) The risk cost comes from a calibrated
   probabilistic forecast, as described above.
4. **Additions that were not in the plan:** a fire realisation shared by all
   bots on each trial (paired comparisons), the clairvoyant bound, early
   stopping once failure is certain, and the forecast calibration check.
5. The directory is named `project 1` (with a space) as requested, so quote
   it in shells: `cd "project 1"`.

## Correctness checks (`tests/`)
- Ship: phase 1 yields a tree with no cell left to open; phase 2 at least
  halves the dead ends and only opens cells; every open cell is reachable;
  generation is reproducible.
- Fire: synchronous update, ignition frequency matches 1 - (1 - q)^K, no
  spread at q = 0, fire stays on open cells.
- Planning: BFS paths are valid and shortest; risk-aware A* matches an
  unpruned brute force; both forecasts are exact when q = 1; message passing
  is exact on a corridor; forecast probabilities are valid and only grow.
- Bots: lazy replanning matches full replanning; no bot ever beats the
  clairvoyant bound; with q = 0 every bot wins whenever winning is possible;
  Bot 4 without risk takes paths as short as Bot 2's.

<!-- RESULTS -->
