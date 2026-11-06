import math

import numpy as np

# this file has everything about the two bot detectors: when they ping, and how the LocatorBot updates
# what it knows (its knowledge base) after it runs a detector. I used numpy 2d arrays for the knowledge base
# this time instead of lists (in project 1 I said I would try this), so updating every cell at once is
# one line of code instead of two for loops


# the type A detector pings if the LostBot is inside the (2k+1) by (2k+1) square centered on the LocatorBot,
# which is the same thing as saying the LostBot's row and column are both at most k away from ours
def type_a_ping(bot, lost, k):
    return abs(bot[0] - lost[0]) <= k and abs(bot[1] - lost[1]) <= k


# the chance that the type B detector pings, e^(-alpha * (d - 1)) where d is the euclidean distance between
# the two bots. a LostBot right next to us (d = 1) always pings, and the further away it is the less likely
def ping_chance(bot, lost, alpha):
    d = math.dist(bot, lost)
    return math.exp(-alpha * (d - 1))


# the type B detector actually "flips a coin" with that chance to decide if it pings or not
def type_b_ping(bot, lost, alpha):
    return np.random.random() < ping_chance(bot, lost, alpha)


# a D by D array of True/False, True for every cell inside the (2k+1) by (2k+1) square around pos
def square_mask(D, pos, k):
    mask = np.zeros((D, D), dtype=bool)
    r, c = pos
    mask[max(r - k, 0):r + k + 1, max(c - k, 0):c + k + 1] = True
    return mask


# a D by D array with the chance that the type B detector pings for a LostBot in each cell, if the LocatorBot
# is at pos. np.indices gives the row and the column of every cell so we can get every distance at once
def ping_chance_map(D, pos, alpha):
    rows, cols = np.indices((D, D))
    d = np.sqrt((rows - pos[0]) ** 2 + (cols - pos[1]) ** 2)
    return np.exp(-alpha * (d - 1))


# the type A knowledge base is a True/False array of every cell the LostBot could still be in (it starts as
# every open cell). this is basically the domain of a CSP variable (where is the LostBot?) and every reading
# is a constraint that crosses out the cells that disagree with it:
#   - we ran the detector here and it didn't say found, so the LostBot isn't in this cell
#   - ping: it has to be inside the square, so every cell outside the square is crossed out
#   - no ping: it can't be inside the square, so every cell inside the square is crossed out
def update_type_a(possible, pos, ping, k):
    possible = possible.copy()
    possible[pos] = False
    square = square_mask(possible.shape[0], pos, k)
    if ping:
        possible = possible & square
    else:
        possible = possible & ~square
    return possible


# the type B knowledge base is the probability that the LostBot is in each cell (it starts the same for every
# open cell). after a reading we use bayes' rule like the two coins example from class:
#   P(LostBot in c | reading) = P(LostBot in c) * P(reading | LostBot in c) / P(reading)
# P(reading | LostBot in c) is the ping chance for a ping, and 1 - the ping chance for no ping, and
# P(reading) is just the sum of the top over every cell, so dividing by the sum makes everything add up to 1 again.
# the cell we're standing on goes to 0 first since the detector would have said found if it was there
def update_type_b(prob, pos, ping, alpha):
    prob = prob.copy()
    prob[pos] = 0
    chance = ping_chance_map(prob.shape[0], pos, alpha)
    if ping:
        prob = prob * chance
    else:
        prob = prob * (1 - chance)
    return prob / prob.sum()
