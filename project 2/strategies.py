import math

import numpy as np

from detector import ping_chance_map
from search import map_distance

# this file has the 4 strategies (2 baselines and 2 of mine) that decide where the LocatorBot goes next.
# every strategy gets the knowledge base and the LocatorBot's position and returns the cell it wants to go to,
# then the simulation walks there with BFS and runs the detector once it gets there.
# map_distance (BFS from project 1) gives the number of moves from pos to every cell, dist[r][c]


# ---------------------------------------------- baselines ----------------------------------------------

# baseline type A: go to the nearest cell the LostBot could still be in, breaking ties at random
def baseline_a(ship, possible, pos):
    dist = map_distance(ship, [pos], set())
    nearest = math.inf
    ties = []
    for r in range(ship.D):
        for c in range(ship.D):
            if possible[r][c] and dist[r][c] < nearest:   # a new closest cell
                nearest = dist[r][c]
                ties = [(r, c)]
            elif possible[r][c] and dist[r][c] == nearest:   # just as close as the closest one
                ties.append((r, c))
    return ties[np.random.randint(len(ties))]


# baseline type B: go to the cell that's most likely to have the LostBot, breaking ties by distance
# and then at random
def baseline_b(ship, prob, pos):
    dist = map_distance(ship, [pos], set())
    # first find the biggest probability
    biggest = 0
    for r in range(ship.D):
        for c in range(ship.D):
            if prob[r][c] > biggest:
                biggest = prob[r][c]
    # then every cell that has it
    ties = []
    for r in range(ship.D):
        for c in range(ship.D):
            if prob[r][c] == biggest:
                ties.append((r, c))
    # if there's more than one, only keep the closest ones
    if len(ties) > 1:
        closest = math.inf
        for r, c in ties:
            if dist[r][c] < closest:
                closest = dist[r][c]
        closest_ties = []
        for r, c in ties:
            if dist[r][c] == closest:
                closest_ties.append((r, c))
        ties = closest_ties
    return ties[np.random.randint(len(ties))]


# ------------------------------------------ my type A: minimax ------------------------------------------

# this is based on minimax from the game trees in class, the LocatorBot is MAX (it picks where to run the
# detector) and the detector is MIN (it picks the answer). MIN always gives the worst answer for us, so this
# counts how many cells a reading at (r, c) is SURE to cross out no matter what the answer is:
# a ping crosses out every possible cell outside the square, a no ping crosses out every one inside it,
# so the worst case is the smaller one. if the LostBot could be in (r, c) itself, it's gone either way
# (it either says found or it gets crossed out) so that's 1 more. total is how many cells are still possible
def sure_crossed_out(possible, r, c, k, total):
    here = 0
    if possible[r][c]:
        here = 1
    inside = 0   # possible cells in the square, not counting (r, c)
    for i in range(r - k, r + k + 1):
        for j in range(c - k, c + k + 1):
            if 0 <= i < len(possible) and 0 <= j < len(possible) and possible[i][j] and (i, j) != (r, c):
                inside += 1
    outside = total - inside - here
    return here + min(inside, outside)


# my type A strategy: go to the spot that's sure to cross out the most cells for what it costs to get there
# and run the detector (moves + 1/2), ties go to the closest spot. before a ping this ends up being a spot just
# past the edge of what we already searched (so the whole square is new), and after a ping it's a spot that
# cuts the possible cells in half (binary search). when moving is free (question 6) we don't divide by the cost
def my_a(ship, possible, pos, k, free_moves):
    dist = map_distance(ship, [pos], set())
    total = 0   # how many cells are still possible
    for r in range(ship.D):
        for c in range(ship.D):
            if possible[r][c]:
                total += 1
    best = None
    best_score = -1
    for r, c in ship.open_cells():
        score = sure_crossed_out(possible, r, c, k, total)
        if not free_moves:
            score = score / (dist[r][c] + 0.5)
        if score > best_score or (score == best_score and dist[r][c] < dist[best[0]][best[1]]):
            best = (r, c)
            best_score = score
    return best


# --------------------------------------- my type B: warmer / colder ---------------------------------------

# how "warm" cell x is: the chance that the detector pings if we run it at x. it's marginalization like
# P(heads) in the two coins example, we add up P(LostBot in b) * P(ping | LostBot in b) over every cell b.
# if the LostBot is in x itself the detector says found, which is even better than a ping, so that counts as 1
def warmth(prob, x, alpha):
    chance = ping_chance_map(len(prob), x, alpha)
    chance[x[0]][x[1]] = 1
    return (prob * chance).sum()   # every cell's probability times its ping chance, all added up


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
