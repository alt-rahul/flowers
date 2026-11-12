import math

import numpy as np

from detector import ping_chance_map
from search import map_distance

# this file has the 2 baselines and my 2 strategies. each one takes the knowledge base and the LocatorBot's
# position and returns the cell to go to next. map_distance from project 1 gives dist[row][col], the number of
# moves from position to every cell


# baseline type A, returns the closest cell that is still possible, ties are broken at random
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


# baseline type B, returns the cell with the highest probability, ties are broken by the closest one and
# then at random
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


# returns how many possible cells a reading at row, col is sure to remove whatever the answer is. a ping removes
# the possible cells outside the square and a no ping removes the ones inside it, so it takes the smaller of the
# two, plus 1 if row, col itself is still possible. total is the number of possible cells
def sure_crossed_out(possible, row, col, k, total):
    here = 0
    if possible[row][col]:
        here = 1
    inside = 0   # possible cells in the square, not counting row, col itself
    for i in range(row - k, row + k + 1):
        for j in range(col - k, col + k + 1):
            if 0 <= i < len(possible) and 0 <= j < len(possible) and possible[i][j] and (i, j) != (row, col):
                inside += 1
    outside = total - inside - here
    return here + min(inside, outside)


# my type A strategy, returns the open cell with the best score, which is sure_crossed_out divided by the moves to
# get there plus 1/2, ties go to the closest cell. when free_moves is True the score is not divided by the cost
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


# returns the warmth of cell, the chance that a reading there pings. every cell's probability is multiplied by its
# ping chance from cell and added up, and cell itself counts as 1 since a reading there would find the LostBot
def warmth(prob, cell, alpha):
    chance = ping_chance_map(len(prob), cell, alpha)
    chance[cell[0]][cell[1]] = 1
    return (prob * chance).sum()   # every cell's probability times its ping chance, all added up


# my type B strategy, returns the warmest cell next to position if it is warmer than position, otherwise it
# returns the most likely cell from baseline_b
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


# my type B strategy when moving is free. when readings, the number of detector uses so far, is even it returns
# the most likely cell from baseline_b, otherwise it returns the open cell whose warmth is closest to 0.5
def fairest_coin(ship, prob, position, alpha, readings):
    if readings % 2 == 0:
        return baseline_b(ship, prob, position)
    best = None
    best_gap = 1
    for cell in ship.open_cells():
        difference = abs(warmth(prob, cell, alpha) - 0.5)   # how far its warmth is from 0.5
        if difference < best_gap:
            best = cell
            best_gap = difference
    return best
