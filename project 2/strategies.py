import numpy as np

from detector import ping_chance_map
from search import map_distance

# this file has the 4 strategies (2 baselines and 2 of mine) that decide where the LocatorBot goes next.
# every strategy gets the knowledge base and the LocatorBot's position and returns the cell it wants to go to,
# then the simulation walks there with BFS and runs the detector once it gets there


# BFS distances (number of moves) from pos to every cell as a numpy array, it's just map_distance from
# project 1 turned into an array so we can do math on every cell at once
def walk_distances(ship, pos):
    return np.array(map_distance(ship, [pos], set()))


# ---------------------------------------------- baselines ----------------------------------------------

# baseline type A: go to the nearest cell the LostBot could still be in, breaking ties at random
def baseline_a(ship, possible, pos):
    dist = walk_distances(ship, pos)
    dist[~possible] = np.inf   # only look at cells that are still possible
    ties = np.argwhere(dist == dist.min())
    r, c = ties[np.random.randint(len(ties))]
    return (int(r), int(c))


# baseline type B: go to the cell that's most likely to have the LostBot, breaking ties by distance
# and then at random
def baseline_b(ship, prob, pos):
    dist = walk_distances(ship, pos)
    ties = np.argwhere(prob == prob.max())
    if len(ties) > 1:
        tie_dist = dist[ties[:, 0], ties[:, 1]]
        ties = ties[tie_dist == tie_dist.min()]
    r, c = ties[np.random.randint(len(ties))]
    return (int(r), int(c))


# ------------------------------------------ my type A: minimax ------------------------------------------

# this is based on minimax from the game trees in class, the LocatorBot is MAX (it picks where to run the
# detector) and the detector is MIN (it picks the answer). MIN always gives the worst answer for us, so this
# counts how many cells a reading at x is SURE to cross out no matter what the answer is:
# a ping crosses out every possible cell outside the square, a no ping crosses out every one inside it,
# so the worst case is the smaller one. if the LostBot could be in x itself, x is gone either way
# (it either says found or x gets crossed out) so that's 1 more
def sure_crossed_out(possible, x, k):
    r, c = x
    here = 1 if possible[r, c] else 0
    inside = possible[max(r - k, 0):r + k + 1, max(c - k, 0):c + k + 1].sum() - here
    outside = possible.sum() - inside - here
    return here + min(inside, outside)


# my type A strategy: go to the spot that's sure to cross out the most cells for what it costs to get there
# and run the detector (moves + 1/2), ties go to the closest spot. before a ping this ends up being a spot just
# past the edge of what we already searched (so the whole square is new), and after a ping it's a spot that
# cuts the possible cells in half (binary search). when moving is free (question 6) we don't divide by the cost
def my_a(ship, possible, pos, k, free_moves):
    dist = walk_distances(ship, pos)
    best = None
    best_score = -1
    for x in ship.open_cells():
        score = sure_crossed_out(possible, x, k)
        if not free_moves:
            score = score / (dist[x] + 0.5)
        if score > best_score or (score == best_score and dist[x] < dist[best]):
            best = x
            best_score = score
    return best


# --------------------------------------- my type B: warmer / colder ---------------------------------------

# how "warm" cell x is: the chance that the detector pings if we run it at x. it's marginalization like
# P(heads) in the two coins example, we add up P(LostBot in b) * P(ping | LostBot in b) over every cell b.
# if the LostBot is in x itself the detector says found, which is even better than a ping, so that counts as 1
def warmth(prob, x, alpha):
    chance = ping_chance_map(prob.shape[0], x, alpha)
    chance[x] = 1
    return (prob * chance).sum()


# my type B strategy is hill climbing (local search) on the warmth, like playing "warmer / colder". it steps to
# the warmest cell next to it if that cell is warmer than where it is now. if none of them are warmer it's at
# the top of a hill, so it goes to the most likely cell like the baseline does to get off of it
def my_b(ship, prob, pos, alpha):
    best = None
    best_warmth = warmth(prob, pos, alpha)
    for cell in ship.neighbors(pos):
        w = warmth(prob, cell, alpha)
        if w > best_warmth:
            best = cell
            best_warmth = w
    if best is None:
        return baseline_b(ship, prob, pos)
    return best


# my type B strategy when moving is free (question 6). a reading you can already guess teaches you nothing
# (like flipping a coin you know is double headed), so it goes where the chance of a ping is closest to 50/50,
# the "fairest coin". but every other reading it checks the most likely cell instead, since that's the only
# way to actually find the LostBot. readings is how many times we've run the detector so far
def fairest_coin(ship, prob, pos, alpha, readings):
    if readings % 2 == 0:
        return baseline_b(ship, prob, pos)
    best = None
    best_gap = 1
    for cell in ship.open_cells():
        gap = abs(warmth(prob, cell, alpha) - 0.5)   # how far from a 50/50 coin
        if gap < best_gap:
            best = cell
            best_gap = gap
    return best
