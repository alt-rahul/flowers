import math

import numpy as np

from detector import ping_chance_map
from search import map_distance

# this file has the 4 strategies (2 baselines and 2 of mine) that decide where the LocatorBot goes next.
# every strategy gets the knowledge base and the LocatorBot's position and returns the cell it wants to go to,
# then the simulation walks there with BFS and runs the detector once it gets there.
# map_distance is the BFS from project 1, it gives the number of moves from position to every cell, dist[row][col]


# baseline type A goes to the nearest cell the LostBot could still be in, breaking ties at random
def baseline_a(ship, possible, position):
    dist = map_distance(ship, [position], set())
    nearest = math.inf
    ties = []
    for row in range(ship.D):
        for col in range(ship.D):
            if possible[row][col] and dist[row][col] < nearest:   # a new closest cell
                nearest = dist[row][col]
                ties = [(row, col)]
            elif possible[row][col] and dist[row][col] == nearest:   # just as close as the closest one
                ties.append((row, col))
    return ties[np.random.randint(len(ties))]


# baseline type B goes to the cell that's most likely to have the LostBot, breaking ties by distance
# and then at random
def baseline_b(ship, prob, position):
    dist = map_distance(ship, [position], set())
    # first find the biggest probability
    biggest = 0
    for row in range(ship.D):
        for col in range(ship.D):
            if prob[row][col] > biggest:
                biggest = prob[row][col]
    # then every cell that has it
    ties = []
    for row in range(ship.D):
        for col in range(ship.D):
            if prob[row][col] == biggest:
                ties.append((row, col))
    # if there's more than one, only keep the closest ones
    if len(ties) > 1:
        closest = math.inf
        for row, col in ties:
            if dist[row][col] < closest:
                closest = dist[row][col]
        closest_ties = []
        for row, col in ties:
            if dist[row][col] == closest:
                closest_ties.append((row, col))
        ties = closest_ties
    return ties[np.random.randint(len(ties))]


# this is based on minimax from the game trees in class. the LocatorBot is the max player since it picks where
# to run the detector, and the detector is the min player since it picks the answer. the min player always gives
# the worst answer for us, so this counts how many cells a reading at row, col is sure to cross out no matter
# what the answer is. a ping crosses out every possible cell outside the square and a no ping crosses out every
# one inside it, so the worst case is the smaller one. if the LostBot could be in row, col itself it's gone
# either way, since it either says found or gets crossed out, so that's 1 more. total is how many cells are
# still possible
def sure_crossed_out(possible, row, col, k, total):
    here = 0
    if possible[row][col]:
        here = 1
    inside = 0   # possible cells in the square, not counting row, col itself
    for square_row in range(row - k, row + k + 1):
        for square_col in range(col - k, col + k + 1):
            if 0 <= square_row < len(possible) and 0 <= square_col < len(possible) and possible[square_row][square_col] and (square_row, square_col) != (row, col):
                inside += 1
    outside = total - inside - here
    return here + min(inside, outside)


# my type A strategy goes to the spot that's sure to cross out the most cells for what it costs to get there
# and run the detector, which is the moves plus 1/2, and ties go to the closest spot. before a ping this ends up
# being a spot just past the edge of what we already searched so the whole square is new, and after a ping it's
# a spot that cuts the possible cells in half, like binary search. when moving is free for question 6 we don't
# divide by the cost
def my_a(ship, possible, position, k, free_moves):
    dist = map_distance(ship, [position], set())
    total = 0   # how many cells are still possible
    for row in range(ship.D):
        for col in range(ship.D):
            if possible[row][col]:
                total += 1
    best = None
    best_score = -1
    for row, col in ship.open_cells():
        score = sure_crossed_out(possible, row, col, k, total)
        if not free_moves:
            score = score / (dist[row][col] + 0.5)
        if score > best_score or (score == best_score and dist[row][col] < dist[best[0]][best[1]]):
            best = (row, col)
            best_score = score
    return best


# how warm a cell is, which is the chance that the detector pings if we run it there. it's marginalization like
# P(heads) in the two coins example, for every other cell we take the chance the LostBot is there times the
# chance of a ping if it was there, and add them all up. if the LostBot is in the cell itself the detector says
# found, which is even better than a ping, so that counts as 1
def warmth(prob, cell, alpha):
    chance = ping_chance_map(len(prob), cell, alpha)
    chance[cell[0]][cell[1]] = 1
    return (prob * chance).sum()   # every cell's probability times its ping chance, all added up


# my type B strategy is hill climbing from local search on the warmth, like playing warmer or colder. it steps to
# the warmest cell next to it if that cell is warmer than where it is now. if none of them are warmer it's at
# the top of a hill, so it goes to the most likely cell like the baseline does to get off of it
def my_b(ship, prob, position, alpha):
    best = None
    best_warmth = warmth(prob, position, alpha)
    for cell in ship.neighbors(position):
        cell_warmth = warmth(prob, cell, alpha)
        if cell_warmth > best_warmth:
            best = cell
            best_warmth = cell_warmth
    if best is None:
        return baseline_b(ship, prob, position)
    return best


# my type B strategy when moving is free for question 6. a reading you can already guess teaches you nothing,
# like flipping a coin you know is double headed, so it goes where the chance of a ping is closest to 0.5,
# which is the fairest coin. but every other reading it checks the most likely cell instead, since that's the
# only way to actually find the LostBot. readings is how many times we've run the detector so far
def fairest_coin(ship, prob, position, alpha, readings):
    if readings % 2 == 0:
        return baseline_b(ship, prob, position)
    best = None
    best_gap = 1
    for cell in ship.open_cells():
        difference = abs(warmth(prob, cell, alpha) - 0.5)   # how far it is from a fair coin
        if difference < best_gap:
            best = cell
            best_gap = difference
    return best
