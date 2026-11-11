# Project 2: Where is it?

Rahul Rajkumar (NetID: rr1437)

## 1. The setup, and the range of k and alpha

I built Project 2 on top of my Project 1 code. The ship is generated exactly the
same way (it's the same `ship.py`, so trial $i$ gives the same ship as trial $i$
in Project 1), the LocatorBot walks from cell to cell with the same BFS, and the
BFS distance map from Project 1 gives the number of moves from the LocatorBot to
every cell. Each trial puts the LocatorBot and the LostBot in two random open
cells, and the LostBot never moves. The LocatorBot only finds the LostBot by
running the detector in its cell, so every search ends with one detector use,
and the cost of a search is the number of moves plus half the number of detector
uses. In my Project 1 writeup I said I wanted to use numpy 2D arrays and
parallelization next time, so this time the knowledge base is a numpy array, and
the experiments run one search on each core of the computer at the same time.

**The range of k and alpha (the question for analysis on page 1).** With
$k = 0$ the square is just the LocatorBot's own cell, so the detector says
nothing new, and with $k \ge D - 1$ the square covers the whole ship from
anywhere and always pings, so it also says nothing. On a 50 by 50 ship, $k = 25$
already covers almost the whole ship from the middle, so I tested $k$ from 1 to
25. $k$ sets the sensitivity like this: a small square only pings when the
LostBot is close but then pins it down to a few cells, and a big square pings
from far away but only says it's somewhere in a big area.

For type B, the chance of a ping is $e^{-\alpha(d-1)}$, which is 0.5 at a
distance of $d = 1 + \ln 2 / \alpha$, and distances on a 50 by 50 ship go up to
about 69. At $\alpha = 0.01$ that distance is 70, so the detector pings almost
everywhere and a ping says very little. At $\alpha = 3$ it's 1.23, so it only
pings right next to the LostBot and a no ping says very little. So I tested 12
values of $\alpha$ from 0.01 to 3, spaced out on a log scale. $\alpha$ sets how
fast the detector goes cold with distance (Figure 1): a small $\alpha$ reaches
far but is fuzzy, and a big $\alpha$ is precise but only works up close.

![Figure 1](plots/ping_chance.png)

*Figure 1: The chance of a type B ping based on how far away the LostBot is, for a small, a medium and a big alpha.*

## 2. Updating the knowledge base (Question 1)

For type A, the knowledge base is $S$, the set of cells the LostBot could still
be in, which starts as every open cell. The "square around $a$" is the
$(2k+1)$ by $(2k+1)$ square centered on cell $a$, which is every cell whose row
and column are both at most $k$ away from $a$'s. When the LocatorBot in cell $a$
runs the detector and it doesn't say "found":

- **ping:** new $S$ = the cells in $S$, without $a$, that are **inside** the square around $a$
- **no ping:** new $S$ = the cells in $S$, without $a$, that are **outside** the square around $a$

This is correct because the type A detector has no randomness: it pings exactly
when the LostBot is in the square, and it would have said "found" if the
LostBot was in $a$. So a cell gets crossed out exactly when "the LostBot is in
this cell" contradicts one of the readings, like a proof by contradiction from
class, and the real cell can never be crossed out since it agrees with every
reading. It is also the same as a CSP with one variable (where the LostBot is)
whose domain is every open cell: every reading is a constraint, and the update is
just crossing out the values that break it. My code does exactly this: it goes
through every cell and asks "if the LostBot was here, would the detector have
said what it just said?", and if not, it crosses that cell out.

**Example (type A).** Take a tiny 5 by 5 ship with every cell open, so $S$
starts as all 25 cells, and $k = 1$ (a 3 by 3 square). Cells are (row, column).

- The LocatorBot is in the corner (0, 0) and gets **no ping**. Its square is
  only 4 cells, since it's in the corner: (0, 0), (0, 1), (1, 0) and (1, 1). So
  those 4 cells get crossed out (including (0, 0), where it's standing), and
  $S$ has 21 cells left.
- It moves to (3, 3) and gets a **ping**. Its square is the 9 cells with rows
  and columns 2 to 4. Every cell outside that square gets crossed out, and so
  does (3, 3) itself, since the detector didn't say found. So $S$ has 8 cells
  left: (2, 2), (2, 3), (2, 4), (3, 2), (3, 4), (4, 2), (4, 3) and (4, 4).

For type B, the knowledge base is $P(b)$, the probability that the LostBot is in
cell $b$, which starts as $1/N$ for each of the $N$ open cells. When the
LocatorBot in cell $a$ runs the detector, doesn't find the LostBot and gets the
reading $r$ (ping or no ping), it first sets $P(a) = 0$ and then updates every
cell with

$$P(b \mid r) = \frac{P(b) \, P(r \mid b)}{\sum_{b'} P(b') \, P(r \mid b')}, \qquad P(\text{ping} \mid b) = e^{-\alpha (d(a, b) - 1)}, \qquad P(\text{no ping} \mid b) = 1 - e^{-\alpha (d(a, b) - 1)}$$

where $d(a, b)$ is the euclidean distance. In words: the new chance of cell $b$
is the old chance of $b$, times the chance of getting this reading if the
LostBot was in $b$, divided by the total of that over every cell (so everything
adds up to 1 again). This is Bayes' theorem, exactly like
the two coins example from class: the prior is the old knowledge base, the
reading is the data, and the bottom is $P(r)$, found by adding up the top over
every cell (marginalization). Not finding the LostBot in $a$ is also a reading,
whose chance is 0 if the LostBot is in $a$ and 1 anywhere else, which is why
$P(a)$ goes to 0. As a Bayesian network, the LostBot's location is the parent of
every reading, and the readings don't affect each other once you know the
location, since the detector's randomness is new each time (just like flipping
the same mystery coin twice). So the probability after many readings is
$P(b) \prod_i P(r_i \mid b)$ divided by its sum, and doing one reading at a time
gives the exact same answer. I checked this in code too: updating one reading at
a time, all at once, and in reverse order all gave the same knowledge base. One
thing worth noticing: when $d = 1$ the chance of a ping is 1, so a "no ping"
completely rules out the 4 cells next to the LocatorBot.

**Example (type B).** Take a tiny ship that is just 4 open cells in a row,
cells 1 to 4, with $\alpha = 1$. At the start each cell has a chance of 1/4.
The LocatorBot is in cell 1 and runs the detector, and it doesn't say found, so
cell 1 goes to 0. Cells 2, 3 and 4 are 1, 2 and 3 cells away, so their chances
of a ping are $e^{0} = 1$, $e^{-1} = 0.368$ and $e^{-2} = 0.135$.

| | cell 2 | cell 3 | cell 4 | total |
|---|---|---|---|---|
| **ping**: 1/4 times the ping chance | 0.25 | 0.092 | 0.034 | 0.376 |
| new chance (divide by the total) | 0.665 | 0.245 | 0.090 | 1 |
| **no ping**: 1/4 times (1 minus the ping chance) | 0 | 0.158 | 0.216 | 0.374 |
| new chance (divide by the total) | 0 | 0.422 | 0.578 | 1 |

So a ping makes the closest cell the most likely one (0.665), and a no ping
rules out cell 2 completely (it's right next to us, so it would have pinged for
sure) and pushes the chance to the far end of the row.

## 3. My strategies (Question 2)

The baselines are reasonable, so instead of just tuning them, I looked at the
problem through ideas from other parts of the class, and kept each strategy to
one simple rule so it's clear what it's doing and why. Before picking these two,
I tried a few other ideas from class in quick tests on a small number of ships:
hill climbing the reading spot (local search) for type A, and for type B,
sampling a target cell from the probabilities (sampling from the approximate
inference lecture) and a "treasure map" built with the $U^*_T$ recursion from
the MDP lecture. They all beat the baselines too, but the two below were the
simplest to explain and the most different from what the baselines do.

**Type A: the detector as the MIN player (minimax).** In the game trees from
class, MAX picks the move whose worst case is the best, because it assumes MIN
will always answer in the way that's worst for MAX. I treat the search the same
way: the LocatorBot is MAX and picks where to run the detector, and the detector
is MIN and "picks" the answer. For a spot $x$, let $n_{in}$ be the possible
cells inside its square (not counting $x$ itself) and $n_{out}$ the possible
cells outside it. A ping crosses out the $n_{out}$ cells and a no ping crosses
out the $n_{in}$ cells, so whatever the answer is, the reading is sure to cross
out

$$\text{sure}(x) = [x \in S] + \min(n_{in}, n_{out})$$

cells, where $[x \in S]$ is 1 if the LostBot could be in $x$ (then $x$ is gone
either way: the detector either says found or crosses it out) and 0 if not. The
bot goes to the spot with the best $\text{sure}(x) / (w(x) + \tfrac{1}{2})$,
where $w(x)$ is the number of moves to get there with BFS and the
$\tfrac{1}{2}$ is the detector use, breaking ties by the closest spot. So it uses
everything in its knowledge base: which cells are still possible, where they are
compared to every spot's square, and how far away every spot is.

This one rule acts differently before and after the first ping without me having
to tell it to. Before a ping, a square full of unsearched cells has a small
inside and a huge outside, so the worst case is "no ping", and the best spot is
the one whose square holds the most unsearched cells for its cost. That's
usually a spot just past the edge of what's already been searched. The baseline
walks to the nearest possible cell instead, which is right on that edge, so about
half of every square it checks was already searched. After a ping, every
possible cell is inside one square, so the best spot is the one whose square
cuts them in half, since then neither answer can be bad. That's binary search:
each reading halves the possible cells, while the baseline goes back to checking
the nearest cell one at a time. The best spot is often a cell where the LostBot
can't even be, which the baseline never considers. I used the worst case instead
of the average because a reading that splits the cells evenly is good whatever
the answer is, while a lopsided reading is only good if we get lucky.

**Example (type A).** Here's a simple example of how the score works. Take a
5 by 5 ship with every cell open and $k = 1$, so every square is 3 by 3.

1. The LocatorBot starts in the corner (0, 0) and gets no ping. Its square there
   is just the 4 cells (0, 0), (0, 1), (1, 0) and (1, 1), so those 4 are removed
   and 21 cells are still possible.
2. Wherever it runs the detector next, a ping removes every possible cell
   outside the square, and a no ping removes every possible cell inside it. So
   the number of cells it's sure to remove is the smaller of those two groups,
   and the score is that number divided by the cost (the moves plus 1/2).
3. The baseline walks 2 moves to the nearest possible cell, (0, 2) or (2, 0).
   Its square there only has 4 possible cells, since the rest was already
   searched, so it's sure to remove 4 cells. Its score is $4 / 2.5 = 1.6$.
4. My strategy also walks 2 moves, but to (1, 1). That seems strange, since the
   LostBot can't be there, but its square has 5 possible cells, (0, 2), (1, 2),
   (2, 0), (2, 1) and (2, 2), and 16 outside. So whatever the answer is, it's
   sure to remove at least 5 cells. Its score is $5 / 2.5 = 2.0$, the best on
   the ship. A few cells further away also get 2.0, but ties go to the closest.

So for the same 2 moves, my strategy learns more, because its square isn't
wasted on cells that were already searched.

**Type B: warmer / colder (hill climbing).** For the type B detector I used the
game "warmer / colder" with hill climbing from the local search lecture. The
"warmth" of a cell $x$ is the chance that running the detector there pings (or
finds the LostBot), which I get with marginalization, like $P(H)$ in the two
coins example:

$$\text{warmth}(x) = \sum_{b} P(b) \, P(\text{ping} \mid \text{LocatorBot in } x, \text{LostBot in } b)$$

where the LostBot's own cell counts as 1, since there the detector says found,
which is even better than a ping. In every cell, the bot runs the detector and
updates its knowledge base, then it only looks at the cells next to it. If one
of them is warmer than where it is, it steps to the warmest one (hill climbing:
move to the best neighbor if it's better than where you are). If none of them
are warmer, the bot is at the top of a hill (a local maximum), so it walks to
the most likely cell like the baseline does, which works like a restart. Every
reading changes the hill: a ping makes the cells around the bot warmer so it
keeps climbing towards them, and a no ping makes them colder and pushes it away.
So it uses the whole probability map (through the warmth) and $\alpha$ to decide
between the cells next to it.

This should beat the baseline because the baseline makes one decision and then
walks the whole way without running the detector. After a "no ping", the most
likely cell is the one furthest away, so the baseline walks all the way across
the ship and learns nothing on the way. Mine runs the detector in every cell it
steps on (half a move each) and lets every reading change where it goes next.
Warmth is also smoother than the probabilities themselves: a cell is warm if a
lot of probability is near it, not just in it, so the bot heads for the area
where the LostBot probably is, instead of one cell that's only slightly more
likely than the cells around it.

**Example (type B).** Take a tiny ship that's just 4 cells in a row, cells 1
to 4, with $\alpha = 1$.

1. The LocatorBot starts in cell 1 and gets no ping. From the question 1
   example, the chances of cells 1 to 4 are now 0, 0, 0.422 and 0.578.
2. The baseline walks straight to cell 4, the most likely cell. That's 3 moves
   without running the detector on the way.
3. My strategy only compares where it is with the cell next to it. The warmth
   of a cell is the chance the detector pings there. For cell 1 that's
   $0.422 \times e^{-1} + 0.578 \times e^{-2} = 0.234$, and for cell 2 it's
   $0.422 \times 1 + 0.578 \times e^{-1} = 0.635$.
4. Cell 2 is warmer, so it steps there and runs the detector again. If the
   LostBot is in cell 3, the detector pings for sure, since it's right next to
   it, so this one reading tells it a lot.

Averaged over 4,000 searches for each cell the LostBot could be in, a whole
search costs 3.5 with mine and 3.61 with the baseline. The baseline does win
when the LostBot really is in cell 4, since walking straight there is right,
but on a real ship the walks are much longer, so checking along the way saves a
lot more (Section 5).

**Scoring rules, and my TA's advice.** When I sent my plan to my TA, they
said that when choosing where to run the detector, I should think about what the
rest of the search will cost, not just how much the knowledge base shrinks, and
that I should write the scoring rule down and compare it with the baselines. So
every strategy here, the baselines included, comes down to one score:

| strategy | where it can run the detector next | the score it picks the best of |
|---|---|---|
| baseline type A | the nearest possible cell | fewest moves |
| my type A | any open cell | $\text{sure}(x) / (w(x) + \tfrac{1}{2})$ |
| baseline type B | the most likely cell, ties by distance | $P(b)$ |
| my type B | a cell next to it, or the most likely cell at the top of a hill | warmth |
| my type A, free moves | any open cell | $\text{sure}(x)$ |
| my type B, free moves | any open cell | warmth closest to 0.5, every other reading $P(b)$ |

Each baseline only looks at one side of the TA's advice. Baseline A only looks
at cost (the closest possible cell) and never at how much a reading there would
cross out, which is why half its square is usually already searched. Baseline B
only looks at the knowledge base (the most likely cell) and never at the cost of
getting there, which is why it walks across the ship after every no ping. My
type A score puts both sides in one number: the top is how much the knowledge
base is sure to shrink, and the bottom is what it costs to get that, so a spot
that crosses out a lot of cells isn't picked if it's too far away. I used the
worst case instead of the expected amount, since it's simpler and never counts
on getting lucky. For type B, I kept the cost side simple instead of computing
it: every step costs the same (one move and one reading), so the score only
has to compare the warmth of the cells next to it, and the bot never pays for a
long walk without learning anything on the way. When moving is free, the cost
side is 0, so both scores are only about how much a reading tells us. Sections 4
to 7 compare every strategy with its baseline.

## 4. Type A: baseline vs my strategy (Question 3)

I used 50 by 50 ships, the same size as Project 1. I wrote my code with simple
for loops so it's easy to follow, but that makes it slow, so I ran the
experiments with a faster copy that does the same math on whole numpy arrays at
once (I checked that it gives exactly the same numbers, search by search). Even
then, the whole experiment takes about 30 minutes on 4 cores, and a bigger ship
has more cells to check after every reading and longer searches, so it would
take hours. I ran 200
searches for each strategy at each $k$, and both strategies search the exact
same 200 ships with the same starting cells, so the difference between them
comes from their decisions and not from easier ships.

![Figure 2](plots/cost_vs_k.png)

*Figure 2: The average cost of finding the LostBot with the type A detector, for every k, with 200 searches at each k (from results/type_a_cost.csv).*

*Table 1: The average cost of each type A strategy, and how much cheaper mine is.*

| $k$ | baseline | mine | % cheaper |
|---|---|---|---|
| 1 | 884.7 | 767.6 | 13.2 |
| 2 | 526.6 | 465.7 | 11.6 |
| 3 | 366.7 | 303.2 | 17.3 |
| 4 | 268.8 | 245.5 | 8.7 |
| 5 | 243.6 | 207.2 | 14.9 |
| 6 | 223.8 | 184.3 | 17.6 |
| 8 | 175.2 | 157.5 | 10.1 |
| 10 | 174.4 | 148.0 | 15.1 |
| 12 | 160.5 | 128.2 | 20.1 |
| 15 | 173.3 | 124.6 | 28.1 |
| 20 | 221.3 | 141.7 | 36.0 |
| 25 | 284.6 | 171.0 | 39.9 |

My strategy is cheaper at every $k$, from 9% at $k = 4$ up to 40% at
$k = 25$. It isn't cheaper on every single search (it's cheaper on 56% to 64%
of them, depending on $k$), but on average it always wins. For small $k$ both
strategies are expensive, since a tiny square means sweeping most of the ship,
and almost all the cost is walking (at $k = 1$ the baseline makes 761 moves and
mine makes 676). Mine still saves 9% to 18% there, because it reads past the
edge of what's been searched instead of right on it. For big $k$ the baseline
gets more expensive again (285 at $k = 25$), because the first reading usually
pings and then it checks cells one at a time. It runs the detector 122 times at
$k = 25$, while mine only needs about 13, since after the ping every reading
cuts the possible cells in half.

The most interesting $k$ regime is from about $k = 8$ to $k = 15$ (about
$D/6$ to $D/3$). That's where both strategies are cheapest: mine is lowest at
$k = 15$ (124.6) and the baseline is lowest at $k = 12$ (160.5). It's also
where splitting the possible cells in half starts to really pay off, so the gap
between the two strategies starts to grow (20% at $k = 12$ and 28% at
$k = 15$).

## 5. Type B: baseline vs my strategy (Question 4)

I picked the values of $\alpha$ from where the detector stops being useful on
both ends (Section 1): at $\alpha = 0.01$ it pings almost everywhere, and at
$\alpha = 3$ it only pings right next to the LostBot. Since what matters is how
fast the ping chance falls off, and that changes the most for small $\alpha$, I
spaced the values out on a log scale instead of evenly, and I checked that the
cost goes back up at both ends of the range, so the best $\alpha$ is inside it.

![Figure 3](plots/cost_vs_alpha.png)

*Figure 3: The average cost of finding the LostBot with the type B detector, for every alpha, with 200 searches at each alpha (from results/type_b_cost.csv). Both axes are on a log scale since the baseline costs are so much bigger.*

*Table 2: The average cost of each type B strategy, and how much cheaper mine is.*

| $\alpha$ | baseline | mine | % cheaper |
|---|---|---|---|
| 0.01 | 905.3 | 609.4 | 32.7 |
| 0.02 | 713.4 | 431.2 | 39.6 |
| 0.05 | 670.3 | 341.1 | 49.1 |
| 0.1 | 885.7 | 309.3 | 65.1 |
| 0.2 | 1248.1 | 392.6 | 68.5 |
| 0.3 | 1738.4 | 530.1 | 69.5 |
| 0.5 | 3023.0 | 723.3 | 76.1 |
| 0.75 | 4459.1 | 1062.4 | 76.2 |
| 1 | 5257.0 | 1222.6 | 76.7 |
| 1.5 | 7513.2 | 1481.3 | 80.3 |
| 2 | 8992.2 | 1567.8 | 82.6 |
| 3 | 9917.3 | 1795.8 | 81.9 |

My strategy is 33% to 83% cheaper at every $\alpha$, and cheaper on 70% to 90%
of the searches. Almost all of the baseline's cost is walking. After a "no
ping", the most likely cell is the one furthest away, so it walks all the way
across the ship without running the detector once on the way, and the bigger
$\alpha$ is, the more often it doesn't ping. At $\alpha = 0.1$ the baseline
makes 867 moves, while mine makes 277. Mine actually runs the detector more (65
times vs 38), but that's the point: a reading only costs half a move, and every
reading tells it which way is warmer.

My strategy is cheapest at $\alpha = 0.1$ (309.3), and the baseline at
$\alpha = 0.05$ (670.3). At $\alpha = 0.1$ the 50/50 distance is about 8
cells, so moving one cell changes the warmth enough to tell which way to go.
Mine helps the least at small $\alpha$ (33% cheaper at $\alpha = 0.01$): the
detector pings from almost anywhere, so the warmth is almost the same in every
cell, the hill is very flat, and the bot keeps reaching a "top" and
walking to the most likely cell like the baseline. When I counted this on 15
searches, 23% of its decisions at $\alpha = 0.01$ were a "top", compared to
7% at $\alpha = 1$. For big $\alpha$ the
detector only pings right next to the LostBot, so the search becomes checking
cells almost one at a time, and the cost goes up to 1795.8 at $\alpha = 3$, but
mine still avoids the baseline's long blind walks.

## 6. Which detector is more efficient? (Question 5)

At its most efficient setting, the type A detector is cheaper. With my
strategies, type A costs 124.6 at $k = 15$ and type B costs 309.3 at
$\alpha = 0.1$, so type A is about 60% cheaper (2.5 times). With the baselines
the gap is even bigger (160.5 at $k = 12$ vs 670.3 at $\alpha = 0.05$).

![Figure 4](plots/cost_breakdown.png)

*Figure 4: Where the cost goes for each strategy at k = 15 and alpha = 0.1: the average number of moves, and half the average number of detector uses.*

The reason is that a type A reading is certain: a ping or a no ping crosses
cells out for good and is never wrong, so once it pings, every reading cuts the
possible cells in half, and my strategy only needs about 13 readings in a whole
search. A type B reading is a coin flip. A single ping doesn't prove the
LostBot is close, and a no ping doesn't prove it's far, so the bot has to keep
reading as it walks (65 readings at $\alpha = 0.1$) and it walks more too (277
moves vs 118), since it figures out which way to go a step at a time. Figure 4
shows this: most of the difference is the extra walking.

## 7. When moving is free (Question 6)

If only the detector costs anything, both of my strategies change, because the
walking part of their decisions doesn't matter anymore.

For type A, my minimax strategy just drops the cost: it picks the spot anywhere
on the ship that's sure to cross out the most cells, without dividing by the
walk. That's basically "20 questions": every reading splits the possible cells
as close to half as it can.

For type B, warmer / colder doesn't make sense anymore, since its whole point is
to take small steps instead of long walks. So I changed it to a "fairest coin"
rule. A reading you can already guess teaches you nothing, like flipping a coin
you know is double headed. So the bot runs the detector where the chance of a
ping (the warmth) is closest to 50/50. But a fair coin far away can't tell apart
cells that are right next to each other, and you can only find the LostBot by
reading in its cell, so every other reading it checks the most likely cell
instead, like the baseline. When moving is free, it can also run the detector in
the same cell twice in a row if that's still the best spot.

![Figure 5](plots/free_moves_k.png)

*Figure 5: Type A when moving is free: the cost (half the detector uses) of the baseline, of my normal strategy, and of my strategy changed for free moves (from results/type_a_free_moves.csv).*

![Figure 6](plots/free_moves_alpha.png)

*Figure 6: The same for type B (from results/type_b_free_moves.csv).*

*Table 3: The cost when moving is free (half the detector uses) at a few values of k and alpha.*

| | baseline | mine (normal) | mine (free moves) |
|---|---|---|---|
| type A, $k = 8$ | 15.2 | 8.8 | 6.8 |
| type A, $k = 20$ | 41.8 | 6.5 | 5.9 |
| type B, $\alpha = 0.02$ | 35.2 | 53.2 | 58.7 |
| type B, $\alpha = 0.2$ | 18.3 | 35.3 | 20.5 |
| type B, $\alpha = 2$ | 103.5 | 217.5 | 89.0 |

For type A the change makes a big difference. My free moves strategy is 45% to
90% cheaper than the baseline, and from $k = 15$ up it needs about 11.7
readings (a cost of 5.9), which is close to $\log_2$ of the roughly 1,600 open
cells, about 10.7 readings, which is what perfect binary search would need. The
best $k$ also moves up: when walking is free, a bigger square is better since it
can split the ship anywhere, so the cost keeps going down until $k = 15$ and
then stays flat. The baseline is best at $k = 8$ (15.2) and gets worse after
that, since it still checks cells one at a time after the first ping. My normal
strategy is already close (6.5 at $k = 20$), since it was already doing binary
search after the first ping.

For type B, to be honest, the fairest coin only partly worked. It's worse than
the baseline for small $\alpha$ (45% to 67% more expensive for $\alpha \le
0.05$, and 12% to 17% more for $\alpha$ from 0.1 to 0.3), about the same from
$\alpha = 0.5$ to 1, and better for big $\alpha$ (10% to 15% cheaper for
$\alpha \ge 1.5$). The reason is where the 50/50 spot is. It's about
$1 + \ln 2 / \alpha$ cells away from where the LostBot probably is, which is 70
cells at $\alpha = 0.01$, so the bot reads from the far side of the ship, and
from that far away every likely cell is about the same distance, so the reading
can't tell them apart and those readings are mostly wasted. For big $\alpha$
the 50/50 spot is only 1 or 2 cells away from the likely area, so one fair coin
tests a small group of cells at once, which beats checking one cell at a time
like the baseline. My normal strategy (warmer / colder) costs 1.5 to 2.2 times as
much as the baseline here, because it runs the detector on every step to save walking, which
is now free.

The type A detector is still the more efficient one, and by more than before:
5.9 at $k = 15$ (or more) against 18.3 for the baseline at $\alpha = 0.2$ (the
best type B result here, my fairest coin gets 20.5 there), about 3 times
cheaper. With free moves, the only thing that matters is how much each reading
tells you, and a certain reading that can split the ship in half is worth a lot
more than a coin flip.

## 8. What I learned

The biggest surprise was how much one simple rule could do. My type A strategy
is just "assume the detector gives the worst answer", but that one rule makes it
read past the edge of what it searched before a ping, and do binary search after
one, without me telling it about either. For type B, the baseline was really bad
(up to almost 10,000 on average) only because it makes one decision and then
walks blind. Playing warmer / colder and deciding again after every step made
it 33% to 83% cheaper. The fairest coin taught me that "the reading you're
least sure about" isn't always the best reading: it also has to be able to tell
apart the cells you actually care about. All 14,400 searches take about 30
minutes on 4 cores with the faster numpy copy of my code, and most of that is the
fairest coin checking the warmth of every cell before every other reading.
