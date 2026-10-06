# Project 1: This Ship is on Fiiiiire! (C++)

A bot on a randomly generated D x D ship has to reach the fire-suppression
button before the fire spreading through the ship gets to it (or to the
button). This folder is a complete C++ implementation: the ship generator,
the fire, Bots 1-4, a clairvoyant upper bound for judging the bots, an
experiment runner, an analysis tool, and tests.

The code is written to be read by someone learning C++. Every file starts
with a comment explaining what it does, and the comments explain each C++
idea the first time it appears. "C++ ideas, and where to find them" below
is an index.

## Building and running

You need a C++17 compiler (g++ or clang++) and `make`. There are no
libraries to install.

```bash
cd "project 1"
make                 # builds bin/experiments, bin/analyze and bin/tests
make test            # 33 tests, about a second

# Run every bot on 1,000 random trials at each q = 0, 0.05, ..., 1 (one CSV row per trial and bot)
./bin/experiments --D 50 --q 0:1:0.05 --trials 1000 --out results/main.csv

# Summary tables (Markdown), plus the success rates as a CSV for plotting
./bin/analyze results/main.csv --out results/summary.md --table results/summary.csv

# Bot variants are spec strings: compare thresholds, penalties, or the literal one-step rule
./bin/experiments --q 0.3,0.4 --trials 500 --bots bot2 bot3 bot4 bot4:threshold=0.4 \
    bot4:penalty=5 bot4:lookahead=false --out results/tune.csv
```

`bin/experiments` uses one core. To use more, start several runs on
different q values, each writing its own CSV, and pass all the CSVs to
`bin/analyze`, which combines them.

## Files, in reading order

| File | What it does |
|---|---|
| `src/common.hpp` | Shared type names (`Mask`, `Path`, `Adjacency`, `Rng`) and random-number helpers. |
| `src/ship.hpp`, `.cpp` | Ship generation (both phases from the assignment) and the `Ship` struct. |
| `src/fire.hpp`, `.cpp` | The spread rule and `FireTrajectory`, one fire per trial. |
| `src/planning.hpp`, `.cpp` | The search algorithms: BFS, A*, the Manhattan heuristic, distance maps, the certain-win check. |
| `src/planners.hpp`, `.cpp` | One function per way of choosing a path. Bot 4's race model lives here. |
| `src/bots.hpp`, `.cpp` | The single `Bot` class and how Bots 1-4 are built from planners. |
| `src/simulation.hpp`, `.cpp` | Runs a bot on a trial in the assignment's order; the clairvoyant bound. |
| `src/experiments.cpp` | The experiment runner (a program with `main`). Writes a CSV. |
| `src/analyze.cpp` | Turns CSVs into the summary tables (another program). |
| `src/tests.cpp` | The tests (a third program). |
| `Makefile` | How to build the three programs. |
| `results/` | Output of the run described under Results. |

## The problem in brief

**The ship.** Phase 1 opens a random interior cell, then keeps opening a
random blocked cell that has exactly one open neighbour, until none is
left. That grows a maze with exactly one route between any two cells.
Phase 2 opens a random wall next to a random dead end until at most half of
the original dead ends remain, which adds loops.

**The fire.** Every step, each open cell that isn't burning catches fire
with probability $1 - (1 - q)^K$, where $K$ is how many of its four
neighbours are burning. The update is **synchronous**: all cells are
judged against the fire as it was at the start of the step, so a cell that
catches fire can't spread it until the next step. The fire never reacts to
the bot, so each trial's fire is simulated once and every bot faces the
same one. That makes bot comparisons fair and much less noisy.

**One time step.** The bot moves; if it walked into fire it fails; if it is
on the button it wins; otherwise the fire spreads, and the bot fails if the
fire reached it or the button. A bot with no fire-free route left is
"trapped": the fire never goes out, so it can't win any more.

## The bots: one class, four planners

There is a single `Bot` class. A bot is a name, a **planner** (a function
from `planners.cpp` that returns a path to the button, or an empty path if
none avoids the fire) and a flag saying whether to call the planner again
every step:

| Bot | Planner | Replans? | Search |
|---|---|---|---|
| Bot 1 | `avoid_fire` | no, plans once at the start | BFS avoiding the initial fire cell |
| Bot 2 | `avoid_fire` | every step | BFS avoiding every burning cell |
| Bot 3 | `avoid_fire_and_neighbors`, falling back to `avoid_fire` | every step | BFS avoiding burning cells and their neighbours |
| Bot 4 | `avoid_predicted_fire` | every step | A* with a race model of the fire |

The `Bot` class stores its planner as a **function pointer** and just calls
it, so it never needs to know which search is inside. Bot 3's fallback is
literally a call to Bot 2's planner.

### Bot 4: avoid the fire that will probably get there first

**The race.** Each step, for every open cell $c$:

- $k(c)$ = the number of moves the bot needs to reach $c$ (BFS from the
  bot, avoiding burning cells);
- $d(c)$ = the number of cells the fire must travel to reach $c$ (BFS
  through the maze from every burning cell).

Along a single route the fire's front advances one cell per step with
probability $q$, so in $k$ steps it advances $\text{Binomial}(k, q)$ cells:

$$
P(\text{fire reaches } c \text{ first}) = P\big(\text{Binomial}(k(c), q) \ge d(c)\big) = \sum_{j=d(c)}^{k(c)} \binom{k(c)}{j} q^j (1-q)^{k(c)-j}
$$

(For the button $k$ is one less: it is pressed before the fire moves.) If
this is above a threshold $\theta = 0.6$, the cell is **predicted fire**.
`danger_radius` turns the sum into a lookup table once per $q$, so checking
a cell is a single comparison.

**The search.** A* from the bot to the button, where entering a cell costs

$$
w(c) = \begin{cases}
\infty & \text{if } c \text{ is burning now} \\
1 + \lambda & \text{if } c \text{ is predicted fire} \\
1 & \text{otherwise}
\end{cases}
$$

with penalty $\lambda = 20$. The heuristic is the Manhattan distance to the
button, which never overestimates (walls only make routes longer), so A*
returns the cheapest path. Bot 4 takes its first step and replans next step.

```
each step, given pos, burning, q:
    d ← BFS distance from the burning cells to every cell
    k ← BFS distance from pos to every cell, avoiding burning cells
    predicted ← cells with P(Binomial(k, q) ≥ d) > θ        (k - 1 for the button)
    cost ← ∞ for burning cells, 1 + λ for predicted cells, 1 otherwise
    plan ← A*(pos → button, cost, heuristic = Manhattan distance to the button)
    if no plan: trapped
    take the plan's first step
```

**Short-but-risky vs long-but-safe.** A path costs its length plus
$\lambda$ per predicted-fire cell, so Bot 4 detours up to $\lambda$ extra
steps around a predicted-fire cell, and goes through predicted fire only
when every way around is longer.

**Not "Bot 3 with a wider buffer"** (the one thing the assignment rules
out). The avoided region depends on where the bot is: a cell next to the
fire that the bot reaches first is not avoided, and a cell far from the
fire that the bot reaches late can be. It depends on $q$. And it is a cost,
not a wall. The literal rule "avoid cells with a > 60% chance of catching
fire next step" would only ever flag cells touching the fire, which *would*
be a thinner Bot 3 buffer. It is kept as `bot4:lookahead=false` for
comparison.

**How good is the race model?** Along one route it is exact: each cell on
the route waits for its own q-coin from the cell before it. The real fire
can also arrive by other routes (loops, other burning cells), which only
makes it faster. So the true probability is never lower than the model's:
the model is a slightly optimistic lower bound. Two tests check this
against simulated fires: `race model matches the real fire on a corridor`
and `race model never overestimates the fire`.

**Known limitations.** (1) $k(c)$ is the bot's *shortest* distance to $c$,
not when the plan actually gets there, so long detours look safer than they
are. (2) The threshold looks at one cell at a time: several moderate risks
in a row (say 20%, 49% and 18%) never add up to a reason to detour. Both
show up in the results.

**Assumption:** Bot 4 knows q, the ship's flammability.

### Measuring the bots

- **Clairvoyant bound** (`oracle_steps`): a BFS that knows the fire's whole
  future and enters a cell only when it won't be burning then. No bot can
  beat it, and it splits every failure into avoidable and unavoidable.
- **Certain wins** (`Trial::fireproof`): the fire moves at most one cell per
  step whatever q is, so two BFSs can tell, before anything moves, whether
  some path stays ahead of even the fastest possible fire. That is the
  instructor's "how could you tell immediately that the bot wins?" hint.
  It splits trials into certain, contested and impossible; only contested
  trials can separate good decisions from bad ones.
- **Deviations** (`run_bot(..., count_deviations = true)`): moves that are
  not a step along some shortest fire-free path, i.e. moves Bot 2's rule
  could never make. They show when Bots 3 and 4 really decide differently.

## Results (from this code)

### What was run

Ship size D = 50. Every q from 0 to 1 in steps of 0.05 with 1,000 trials
each, plus every q from 0.1 to 0.7 in steps of 0.025 with 3,000 trials each:
83,000 trials, each on a freshly generated ship, with every bot facing the
same ship, start cells and fire. Five runs in parallel took about 25
minutes on 4 cores:

```bash
./bin/experiments --q 0,0.05,0.75,0.8,0.85,0.9,0.95,1 --trials 1000 --out results/part0.csv
./bin/experiments --q 0.1,0.2,0.3,0.4,0.5,0.6,0.7 --trials 3000 --out results/part1.csv
./bin/experiments --q 0.125,0.225,0.325,0.425,0.525,0.625 --trials 3000 --out results/part2.csv
./bin/experiments --q 0.15,0.25,0.35,0.45,0.55,0.65 --trials 3000 --out results/part3.csv
./bin/experiments --q 0.175,0.275,0.375,0.475,0.575,0.675 --trials 3000 --out results/part4.csv
./bin/analyze results/part*.csv --out results/summary.md --table results/summary.csv
```

Every table is in `results/summary.md`, and the success rates (with 95%
confidence intervals and the clairvoyant bound) are in
`results/summary.csv`, ready to plot. The raw CSVs (about 20 MB) are not
committed. Each trial's seed depends only on (seed, q, trial index), so
these commands recreate them exactly.

### Success rate against q

| q | Bot 1 | Bot 2 | Bot 3 | Bot 4 | Clairvoyant bound |
|---|---|---|---|---|---|
| 0 | 99.7% | 99.7% | 99.7% | 99.7% | 99.7% |
| 0.1 | 93.7% | 97.0% | 97.5% | 97.3% | 97.6% |
| 0.2 | 89.2% | 93.5% | 93.6% | 93.8% | 94.8% |
| 0.3 | 83.0% | 86.5% | 87.2% | 87.9% | 89.1% |
| 0.4 | 76.1% | 78.3% | 78.5% | 79.4% | 80.9% |
| 0.5 | 71.6% | 72.5% | 72.6% | 73.9% | 74.8% |
| 0.6 | 65.3% | 65.9% | 65.9% | 66.5% | 67.5% |
| 0.7 | 61.6% | 61.8% | 61.9% | 62.1% | 62.9% |
| 0.8 | 57.4% | 57.6% | 57.7% | 58.1% | 58.5% |
| 0.9 | 52.0% | 52.0% | 52.0% | 51.9% | 52.3% |
| 1 | 51.2% | 51.2% | 51.2% | 51.3% | 51.3% |

(At q = 0 the 0.3% of losses are ships where the fire's starting cell
blocks the only route to the button.)

- **Equally good (q ≤ 0.05).** Bots 2-4 win every trial a clairvoyant bot
  could win. Bot 1 already falls behind at q = 0.05 (97.0% vs 99.4%): it
  never replans, so even a slow fire that creeps onto its path kills it.
- **Bot 4 ahead (q = 0.3 to 0.65).** Bot 4 beats both Bot 2 and Bot 3 with
  95% confidence at every one of the 15 tested q values in this range.
  Its lead peaks at +1.6 ± 0.5 points over Bot 2 (q = 0.425) and
  +1.5 ± 0.5 over Bot 3 (q = 0.375), and is +3.3 to +4.9 points over Bot 1
  for q = 0.1-0.425. On contested trials (next section) the gap is larger:
  for q = 0.3-0.7 Bot 4 wins 93-97% of them, Bots 2 and 3 90-95%, and
  Bot 1 84-91%.
- **Where Bot 4 does not outperform (q ≤ 0.2).** Bot 4 ties Bots 2 and 3,
  and Bot 3 is slightly ahead at q = 0.1-0.15 (significantly only at
  q = 0.125: 0.5 ± 0.3 points). A slow fire gives the cells next to it
  moderate risks, each under Bot 4's 60% threshold, so Bot 4 walks right
  past it while Bot 3's buffer keeps its distance. Of the 66 trials at
  q ≤ 0.2 that Bot 4 lost and Bot 3 won, 58 were "fire spread onto bot".
- **Equally bad (q ≥ 0.75).** All four bots are within about a point of
  each other and of the clairvoyant bound. At q = 1 the fire is as fast as
  the bot, and the start decides everything.
- Bot 4 is within 1.6 points of the clairvoyant bound at every q (Bot 3:
  2.7, Bot 2: 3.0, Bot 1: 6.4). Pooled over all 83,000 trials: Bot 1
  76.3%, Bot 2 78.3%, Bot 3 78.5%, Bot 4 79.1%.

### Which trials can a bot's decisions change?

About half of all trials (46-52% at every q; 40,829 in all) are **certain
wins**, decided by two BFSs before the fire moves. Bot 4 won all 40,829.
Bots 1-3 won all but one. In that one (q = 1, trial 868) there are several
equally short paths to the button and only some of them stay ahead of the
fire. Bots 1-3 took one that doesn't, because of how BFS breaks ties. At
q = 1 Bot 4's race model is exact, so it flagged the cells on the losing
paths and took a fireproof one. So "certain win" means "a bot that takes
the fireproof path is certain to win", not "every bot wins". It is still
the right answer to the instructor's hint: the check itself is exact, and
a data-collection run could score these trials without simulating them.

As q grows, **contested** trials (winnable, but only by deciding well)
turn into **impossible** ones: from about 48% contested at q = 0.1 to 8% at
q = 0.8. That is why the bots converge at both ends of the range.

### Does Bot 4 decide differently from Bot 2?

| Bot | Leaves Bot 2's rule? | Trials | Won where Bot 2 lost | Lost where Bot 2 won |
|---|---|---|---|---|
| Bot 3 | yes | 8,793 (10.6%) | 459 | 305 |
| Bot 3 | no | 74,207 | 58 | 1 |
| Bot 4 | yes | 9,235 (11.1%) | 712 | 182 |
| Bot 4 | no | 73,765 | 220 | 63 |

Both bots make exactly Bot 2's kind of move in about 89% of trials. When
Bot 4 chooses differently, it wins 3.9 times as often as it loses against
Bot 2. Bot 3's departures help only 1.5 times as often as they hurt: its
buffer is a fixed rule that ignores whether the detour is worth it. The
wins and losses without ever leaving Bot 2's rule come from choosing
between equally short paths, where Bot 2 picks arbitrarily.

### Why bots fail

| Bot | Walked into fire | Fire spread onto bot | Button burned first | Cut off from button | Avoidable |
|---|---|---|---|---|---|
| Bot 1 | 40% | 24% | 35% | 0% | 16% |
| Bot 2 | 0% | 14% | 40% | 46% | 8% |
| Bot 3 | 0% | 5% | 44% | 51% | 7% |
| Bot 4 | 0% | 7% | 46% | 47% | 5% |

"Avoidable" is the share of a bot's failures where the clairvoyant bot
would have won. Bot 1 dies most often by walking into fire, since it never
looks again. Bot 2 is often caught hugging the fire's edge. Bot 3's buffer
cuts that to 5%, but its detours cost time, so more of its failures are a
burned button. Only 5% of Bot 4's failures could have been avoided even
with perfect knowledge of the future.

### Thinking time

| | Bot 1 | Bot 2 | Bot 3 | Bot 4 |
|---|---|---|---|---|
| per move | 0.6 µs | 10.6 µs | 12.7 µs | 104 µs |
| per trial | 0.02 ms | 0.39 ms | 0.48 ms | 3.9 ms |

Bot 4 does about 10 times the work of Bot 2 per move: two BFSs, a pass
over every cell, and one A*, against one BFS.

### Checked against the Python version

The same design also exists in Python (branch `python-bot`). The two use
different random generators, so their experiments run on different random
trials, and the numbers above are an independent replication of the
Python results. They agree within sampling noise: of 165 per-q
comparisons of success rates and clairvoyant bounds, 9 fall outside a 95%
interval, about the 8 that chance alone would give. The ships match too:
over 40,000 fresh trials each, 1,627 open cells and about 260 loops per
ship in both, and 49.95% vs 50.03% certain wins.

To check the decisions themselves, 420 trials (60 at each of seven values
of q) were exported from Python with their exact ships and fires and
replayed here through `FireTrajectory`'s replay constructor. All seven bot
variants (Bots 1-4, plus three Bot 4 settings) had the same outcome, the
same number of steps and the same number of departures from Bot 2's rule
in every one of them, and the clairvoyant bound and certain-win check
agreed too.

## C++ ideas, and where to find them

| Idea | Where it is explained |
|---|---|
| Headers vs source files, `#include`, `#pragma once` | `common.hpp`, top of `ship.hpp` |
| Type aliases (`using Mask = ...`) | `common.hpp` |
| References and `const` references (no copies) | `common.hpp` (`Rng&`), `ship.cpp` (`count_neighbors`) |
| Pass by value to get your own copy | `ship.hpp` (`reduce_dead_ends`) |
| `std::vector`, `std::deque` as a BFS queue | `planning.cpp` (`bfs_path`) |
| `struct` vs `class`, `public` / `private`, `const` member functions | `ship.hpp`, `fire.hpp` |
| Constructors, member initializer lists, overloading | `ship.cpp`, `fire.hpp`, `bots.cpp` |
| `static` member functions (`Ship::generate`) | `ship.hpp` |
| Default member values and default arguments | `planners.hpp` (`BotOptions`), `simulation.hpp` |
| `std::priority_queue` with your own ordering (`operator>`) | `planning.cpp` (A*) |
| Pointers, `nullptr`, `->` and `*` | `bots.hpp`, `bots.cpp` |
| Function pointers | `bots.hpp` (the `Planner` type), `tests.cpp` (the test list) |
| `static` local variables as a cache; `std::map` with `std::tuple` keys | `planners.cpp` (`danger_radius`) |
| Unnamed parameters (silencing "unused" warnings) | `planners.cpp` (`avoid_fire`) |
| Exceptions: `throw`, `try` / `catch` | `ship.cpp`, `bots.cpp`, `experiments.cpp`, `tests.cpp` |
| Random generators and `std::seed_seq` | `common.hpp`, `experiments.cpp` |
| Reading and writing files, `std::getline`, `snprintf` | `analyze.cpp`, `experiments.cpp` |
| Timing code with `std::chrono` | `simulation.cpp` |
| Building with a Makefile | `Makefile` |

## Correctness checks (`src/tests.cpp`)

- **Ship:** phase 1 yields a tree with nothing left to open; phase 2 at
  least halves the dead ends and only opens cells; every open cell is
  reachable; generation is reproducible; neighbour lists are right.
- **Fire:** the spread probabilities; the update is synchronous; no spread
  at q = 0; walls never burn; ignition frequency matches $1 - (1 - q)^K$;
  a recorded fire replays exactly.
- **Search:** BFS paths are valid, shortest, and avoid blocked cells; A*
  with unit costs finds shortest paths; A* with mixed costs matches a plain
  Dijkstra search; the Manhattan heuristic never overestimates.
- **Race model:** the lookup table agrees with the binomial formula; it
  matches simulated fires on a corridor; it never predicts more fire than
  simulated fires produce on a real ship; predicted fire is not a fixed
  buffer; at q = 1 a cell is predicted fire exactly when the fire is no
  farther from it than the bot; the one-step rule only flags cells next to
  the fire.
- **Bots:** Bot 3 falls back to Bot 2's planner, and avoids the buffer when
  it can; Bot 1 plans once; Bot 2 never deviates from its own rule; Bot 4
  with no penalty never does either; no bot beats the clairvoyant bound,
  and only Bot 1 walks into fire; with q = 0 every bot wins whenever
  winning is possible; bot specs are parsed and bad ones rejected.
- **Certain wins:** at q = 1 "certain win" agrees exactly with the
  clairvoyant bot; certain-win trials are always winnable.
