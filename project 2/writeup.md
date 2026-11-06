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
parallelization next time, so this time the knowledge base is a numpy array (an
update to every cell is one line instead of two loops), and the experiments run
one search on each core of the computer at the same time.

For the type A detector, $k = 0$ makes the square just the LocatorBot's own
cell, so the detector only says "found" or "not found", which is no better than
having no detector at all. If $k \ge D - 1$, the square covers the whole ship
from anywhere, so it always pings and also says nothing. On a 50 by 50 ship, a
square with $k = 25$ already covers almost the whole ship from the middle, so I
tested $k$ from 1 to 25. $k$ sets how far the detector reaches and how precise
it is: a small square only pings when the LostBot is close, but then it pins it
down to a few cells, while a big square pings from far away but only says the
LostBot is somewhere in a big area.

For the type B detector, the chance of a ping is $e^{-\alpha(d-1)}$, which is a
50/50 chance at a distance of $d = 1 + \ln 2 / \alpha$. The distances on a 50
by 50 ship go up to about 69. With $\alpha = 0.01$ that 50/50 distance is 70, so
the detector pings almost everywhere (91% of the time even 10 cells away) and a
ping says very little. With $\alpha = 3$ it is 1.23, so the detector only pings
right next to the LostBot (5% of the time just 2 cells away), and a no ping says
very little. The useful values are in between, so I tested 12 values of
$\alpha$ from 0.01 to 3, spaced out on a log scale (0.01, 0.02, 0.05, 0.1, 0.2,
0.3, 0.5, 0.75, 1, 1.5, 2 and 3). $\alpha$ sets how fast the detector "goes
cold" with distance (Figure 1): a small $\alpha$ reaches far but is fuzzy, and a
big $\alpha$ is precise but only works up close.

![Figure 1](plots/ping_chance.png)

*Figure 1: The chance of a type B ping based on how far away the LostBot is, for a small, a medium and a big alpha.*

## 2. Updating the knowledge base (Question 1)

For type A, the knowledge base is the set $S$ of cells the LostBot could still
be in, which starts as every open cell. Let $\text{Sq}_k(a)$ be the
$(2k+1) \times (2k+1)$ square around cell $a$, which is every cell $b$ where
$|b_{row} - a_{row}| \le k$ and $|b_{col} - a_{col}| \le k$. When the
LocatorBot in cell $a$ runs the detector and it doesn't say "found":

$$S \leftarrow \begin{cases} (S \setminus \{a\}) \cap \text{Sq}_k(a) & \text{if it pings} \\ (S \setminus \{a\}) \setminus \text{Sq}_k(a) & \text{if it doesn't ping} \end{cases}$$

This is correct because the type A detector has no randomness: it pings exactly
when the LostBot is in $\text{Sq}_k(a)$, and it would have said "found" if the
LostBot was in $a$. So a cell gets crossed out exactly when "the LostBot is in
this cell" contradicts one of the readings, like a proof by contradiction from
class, and the real cell can never be crossed out since it agrees with every
reading. It is also the same as a CSP with one variable (where the LostBot is)
whose domain is every open cell: every reading is a constraint, and the update is
just crossing out the values that break it. To check my code, I compared it with
a brute force version that tests every cell against every reading one by one,
and they always matched.

For type B, the knowledge base is $P(b)$, the probability that the LostBot is in
cell $b$, which starts as $1/N$ for each of the $N$ open cells. When the
LocatorBot in cell $a$ runs the detector, doesn't find the LostBot and gets the
reading $r$ (ping or no ping), it first sets $P(a) = 0$ and then updates every
cell with

$$P(b \mid r) = \frac{P(b) \, P(r \mid b)}{\sum_{b'} P(b') \, P(r \mid b')}, \qquad P(\text{ping} \mid b) = e^{-\alpha (d(a, b) - 1)}, \qquad P(\text{no ping} \mid b) = 1 - e^{-\alpha (d(a, b) - 1)}$$

where $d(a, b)$ is the euclidean distance. This is Bayes' theorem, exactly like
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

## 3. My strategies (Question 2)

Before writing any code, I wrote down every idea I could think of and then threw
out the most common ones. For type A, I threw out running the detector at every
step (the readings from two cells next to each other mostly say the same thing),
sweeping the ship in rows like a lawnmower (the walls make that messy, and the
baseline already sweeps), and always splitting the possible cells in half like
binary search (that ignores how far you have to walk to do it). For type B, I
threw out information gain (the textbook answer), and walking to the "center" of
the probabilities (the center can be inside a wall, or between two separate
groups of likely cells). I also tried one idea from the local search lecture:
choosing a set of detector stops that covers the whole ship, then ordering them
with hill climbing like the traveling salesman example. In a quick test it
wasn't consistently better than the baseline's nearest-first sweep, so I dropped
it. The two ideas I kept are below.

My type A strategy picks the spot where running the detector crosses out the
most cells for what it costs to get there. If there are $N$ possible cells left
and $n_{in}$ of them are inside the square around a spot $x$ (and
$n_{out} = N - n_{in}$ outside), then with chance $n_{in}/N$ it pings and the
$n_{out}$ outside cells get crossed out, and with chance $n_{out}/N$ it doesn't
and the $n_{in}$ inside cells get crossed out. So the expected number of cells
crossed out is

$$E(x) = \frac{n_{in}}{N} n_{out} + \frac{n_{out}}{N} n_{in}$$

(if the LostBot could be in $x$ itself, there is also a $1/N$ chance of finding
it right there, which I count as solving the whole search). The bot goes to the
spot with the best $E(x) / (w(x) + \tfrac{1}{2})$, where $w(x)$ is the number
of moves to get there with BFS and the $\tfrac{1}{2}$ is the detector use. So it
uses everything in its knowledge base: which cells are still possible, where
they are compared to every spot's square, and how far every spot is. The best
spot is usually a cell where the LostBot can't even be. Before the first ping,
it's a spot just past the edge of what has already been searched, so the whole
square is new. The baseline instead walks to the nearest possible cell, which is
right on that edge, so half of every square it checks was already searched.
After a ping, the best spot is one whose square cuts the possible cells roughly
in half, which is basically binary search, but only when the walk is worth it.
The baseline instead shuffles over one cell at a time. One more rule: before the
first ping, the bot only looks at spots at most $k$ moves further than the
nearest possible cell. Without it, the bot jumped to the biggest unsearched area
and left small holes behind, and walking back to those later cost more than it
saved.

My type B strategy heads towards the cell with the best chance of having the
LostBot for how far away it is, $P(b) / (w(b) + 1)$, instead of just the most
likely cell. After a "no ping", the most likely cell is the cell furthest away
(that's where a no ping makes the most sense), so the baseline walks all the way
across the ship without running the detector once on the way. Mine walks one
cell at a time and decides again after every step, so it uses the new readings
as it goes and would rather check a slightly less likely cell that's much
closer. The second part decides how many times to run the detector in each cell.
A reading costs half a move, so it's only worth it if the answer could change
what the bot does next. In every cell the bot works out what its knowledge base
would be after a ping and after a no ping. If both would send it to the same
next cell, it skips the reading. If they'd send it to different cells, it runs
the detector, then checks again, so sometimes it runs it 2 or 3 times in the
same cell, like flipping the mystery coin again in the two coins example. It
always runs it in the cell it was heading for, since that's how it finds the
LostBot. So it uses the whole probability map, the BFS distances, and $\alpha$
(to work out the two possible knowledge bases).

## 4. Type A: baseline vs my strategy (Question 3)

I used 50 by 50 ships, the same size as Project 1. Every search needs a BFS
after every reading, and when I timed a few searches, a 100 by 100 ship took
about 10 times longer (1.4 seconds per search instead of 0.13), so the whole
experiment would take about 2.5 hours instead of 15 minutes on 4 cores. I ran
200 searches for each strategy at each $k$, and both strategies search the exact
same 200 ships with the same starting cells, so the difference between them
comes from their decisions and not from easier ships.

![Figure 2](plots/cost_vs_k.png)

*Figure 2: The average cost of finding the LostBot with the type A detector, for every k, with 200 searches at each k (from results/type_a_cost.csv).*

*Table 1: The average cost of each type A strategy, and how much cheaper mine is.*

| $k$ | baseline | mine | % cheaper |
|---|---|---|---|
| 1 | 884.7 | 791.2 | 10.6 |
| 2 | 526.6 | 471.8 | 10.4 |
| 3 | 366.7 | 312.9 | 14.7 |
| 4 | 268.8 | 261.0 | 2.9 |
| 5 | 243.6 | 214.5 | 11.9 |
| 6 | 223.8 | 166.3 | 25.7 |
| 8 | 175.2 | 147.7 | 15.7 |
| 10 | 174.4 | 132.8 | 23.8 |
| 12 | 160.5 | 117.3 | 26.9 |
| 15 | 173.3 | 116.7 | 32.7 |
| 20 | 221.3 | 133.8 | 39.5 |
| 25 | 284.6 | 160.4 | 43.7 |

My strategy is cheaper at every $k$, from 3% at $k = 4$ up to 44% at $k = 25$.
It isn't cheaper on every single search (at $k = 12$ it's cheaper on 66% of
them), but it avoids most of the really long searches. For small $k$ both
strategies are expensive, since a tiny square means sweeping most of the ship,
and almost all the cost is walking (at $k = 1$ the baseline makes 761 moves).
For big $k$ the baseline gets more expensive again (285 at $k = 25$), because
the first reading usually pings and then it checks cells one at a time. It runs
the detector 122 times at $k = 25$, while mine only needs about 16, since every
reading cuts the possible cells roughly in half.

The most interesting $k$ regime is from about $k = 6$ to $k = 15$ (about $D/8$
to $D/3$). That's where both strategies are cheapest: mine is lowest at
$k = 15$ (116.7) and $k = 12$ (117.3), and the baseline is lowest at $k = 12$
(160.5). It's also where picking the right spot to run the detector starts to
really matter, since my strategy is 16% to 33% cheaper there. Below $k = 5$ both
strategies are mostly just sweeping the ship, so they're close.

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
| 0.01 | 905.3 | 267.3 | 70.5 |
| 0.02 | 713.4 | 208.2 | 70.8 |
| 0.05 | 670.3 | 178.4 | 73.4 |
| 0.1 | 885.7 | 153.4 | 82.7 |
| 0.2 | 1248.1 | 181.6 | 85.4 |
| 0.3 | 1738.4 | 204.2 | 88.3 |
| 0.5 | 3023.0 | 317.8 | 89.5 |
| 0.75 | 4459.1 | 434.2 | 90.3 |
| 1 | 5257.0 | 572.8 | 89.1 |
| 1.5 | 7513.2 | 773.6 | 89.7 |
| 2 | 8992.2 | 834.9 | 90.7 |
| 3 | 9917.3 | 1006.8 | 89.8 |

Here the difference is huge: my strategy is 70% to 91% cheaper at every
$\alpha$, and cheaper on 90% to 99% of the searches. Almost all of the
baseline's cost is walking. After a "no ping", the most likely cell is the one
furthest away, so it walks all the way across the ship without running the
detector once on the way, and the bigger $\alpha$ is, the more often it doesn't
ping. At $\alpha = 0.1$ the baseline makes 867 moves, while mine makes 122. Mine
actually runs the detector more (62 times vs 38), but that's the point: a
reading only costs half a move, and it uses them to avoid long walks. It also
skips a lot of readings: at $\alpha = 0.2$ it runs the detector 0.46 times per
move, so on most steps the answer couldn't have changed where it was going.

My strategy is cheapest at $\alpha = 0.1$ (153.4), and the baseline at
$\alpha = 0.05$ (670.3). At $\alpha = 0.1$ the 50/50 distance is about 8
cells, so a ping means "it's fairly close" and a no ping means "it's probably
not close", which is useful at the distances on a 50 by 50 ship. For small
$\alpha$ almost every reading is a ping, so each one says very little. For big
$\alpha$ the detector only pings right next to the LostBot, so the search
becomes checking cells almost one at a time, and the cost goes up to 1006.8 at
$\alpha = 3$.

## 6. Which detector is more efficient? (Question 5)

At its most efficient setting, the type A detector is cheaper. With my
strategies, type A costs 116.7 at $k = 15$ and type B costs 153.4 at
$\alpha = 0.1$, so type A is about 24% cheaper. With the baselines the gap is
much bigger (160.5 at $k = 12$ vs 670.3 at $\alpha = 0.05$).

![Figure 4](plots/cost_breakdown.png)

*Figure 4: Where the cost goes for each strategy at k = 15 and alpha = 0.1: the average number of moves, and half the average number of detector uses.*

The reason is that a type A reading is certain: a ping or a no ping crosses
cells out for good and is never wrong, so once it pings, every reading cuts the
possible cells roughly in half, and my strategy only needs about 16 readings in
a whole search. A type B reading is a coin flip. A single ping doesn't prove the
LostBot is close, and a no ping doesn't prove it's far, so the bot has to run
the detector many more times (62 at $\alpha = 0.1$) and walk carefully towards
where the probability builds up, re-deciding at every step. Figure 4 shows this:
both of my strategies walk about the same amount (108 and 122 moves), and the
difference is mostly the extra readings type B needs.

## 7. When moving is free (Question 6)

If only the detector costs anything, both of my strategies change, because the
walking part of their scores goes away.

For type A, my strategy just picks the spot anywhere on the ship whose reading
is expected to cross out the most cells, $E(x)$, without dividing by the walk
and without the "stay near what's been searched" rule. So it's basically binary
search: every reading splits the possible cells about in half. For type B, my
score $P(b) / (w(b) + 1)$ becomes just $P(b)$, so my strategy goes and runs the
detector at the most likely cell, which is exactly what the baseline does. I
also tried two smarter rules for type B in quick tests while building this:
running the detector wherever it is expected to teach the most (information
gain), and a two-reading look ahead (where to read now so that the next reading,
at the most likely cell, has the best chance of finding the LostBot). Neither
did better overall. They were slightly cheaper for medium $\alpha$ and more
expensive for big $\alpha$, since they don't value actually checking the most
likely cell. So I kept the simple rule. Running the detector more than once in a
cell also doesn't make sense anymore, since the bot can just go wherever the
best reading is.

![Figure 5](plots/free_moves_k.png)

*Figure 5: Type A when moving is free: the cost (half the detector uses) of the baseline, of my normal strategy, and of my strategy changed for free moves (from results/type_a_free_moves.csv).*

![Figure 6](plots/free_moves_alpha.png)

*Figure 6: The same for type B (from results/type_b_free_moves.csv). My free moves strategy is the same as the baseline here, so its dashed line is right on top of the baseline's line.*

*Table 3: The cost when moving is free (half the detector uses) at a few values of k and alpha.*

| | baseline | mine (normal) | mine (free moves) |
|---|---|---|---|
| type A, $k = 8$ | 15.2 | 10.3 | 6.5 |
| type A, $k = 20$ | 41.8 | 7.9 | 5.5 |
| type B, $\alpha = 0.1$ | 19.2 | 31.1 | 19.2 |
| type B, $\alpha = 0.2$ | 18.3 | 34.0 | 18.3 |

For type A the change makes a big difference. My free moves strategy is 46% to
91% cheaper than the baseline, and from $k = 12$ up it needs about 11 readings
(a cost of 5.5 to 5.7), which is close to $\log_2$ of the roughly 1,600 open
cells, about 10.7 readings, which is what perfect binary search would need. The
best $k$ also moves up: when walking is free, a bigger square is better since it
can split the ship anywhere, so the cost keeps going down until about $k = 20$.
The baseline is best at $k = 8$ (15.2) and gets worse after that, since it still
checks cells one at a time after the first ping. My normal strategy is in
between, since it already runs the detector rarely.

For type B, my normal strategy actually costs more than the baseline when only
readings count (34.0 vs 18.3 at $\alpha = 0.2$), because it runs the detector
along the way to save walking, which is now free. That's why the change to "go
straight to the most likely cell" matters. The best $\alpha$ also moves from 0.1
to 0.2.

The type A detector is still the more efficient one, and by more than before:
5.5 at $k = 20$ against 18.3 at $\alpha = 0.2$, about 3.3 times cheaper. With
free moves, the only thing that matters is how much each reading tells you, and
a certain reading that can split the ship in half is worth a lot more than a
coin flip.

## 8. What I learned

The biggest surprise was how bad the type B baseline is (up to almost 10,000 on
average), only because "go to the most likely cell" ignores how far away it is.
Just adding the distance to the score and re-deciding after every step makes it
70% to 91% cheaper. Type A was harder to improve, since its baseline is already
a decent sweep. Most of my improvement there came from where it runs the
detector (spots where the LostBot can't even be), not from where it walks. I was
also surprised that the best rule for type B with free moves was the simplest
one. For running the experiments, building every ship once per trial and running
one trial on each core of the computer means all 14,400 searches take about 15
minutes on 4 cores.
