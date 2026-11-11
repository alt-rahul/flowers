import math

import numpy as np

# this file has everything about the two bot detectors: when they ping, and how the LocatorBot updates
# what it knows (its knowledge base) after it runs a detector. the knowledge bases are D by D numpy arrays
# this time instead of lists (in project 1 I said I would try this), you still get a cell with [r][c]


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


# a D by D array with the chance that the type B detector pings for a LostBot in each cell, if the LocatorBot
# is at pos. the two for loops find the distance to every cell, then np.exp does e^(-alpha * (d - 1)) on every
# cell at once
def ping_chance_map(D, pos, alpha):
    d = np.zeros((D, D))
    for r in range(D):
        for c in range(D):
            d[r][c] = math.sqrt((r - pos[0]) ** 2 + (c - pos[1]) ** 2)
    return np.exp(-alpha * (d - 1))


# the type A knowledge base is a True/False array of every cell the LostBot could still be in (it starts as
# every open cell). after a reading we go through every cell and ask: if the LostBot was here, would the
# detector have said what it just said? if not, it can't be there, so it gets crossed out
def update_type_a(possible, pos, ping, k):
    possible = possible.copy()
    possible[pos[0]][pos[1]] = False   # it didn't say found, so the LostBot isn't where we're standing
    for r in range(len(possible)):
        for c in range(len(possible)):
            if type_a_ping(pos, (r, c), k) != ping:
                possible[r][c] = False
    return possible


# the type B knowledge base is the probability that the LostBot is in each cell (it starts the same for every
# open cell). after a reading we use bayes' rule like the two coins example from class:
#   P(LostBot in c | reading) = P(LostBot in c) * P(reading | LostBot in c) / P(reading)
# P(reading | LostBot in c) is the ping chance for a ping, and 1 - the ping chance for no ping, and
# P(reading) is just the sum of the top over every cell, so dividing by the sum makes everything add up to 1 again.
# the cell we're standing on goes to 0 first since the detector would have said found if it was there
def update_type_b(prob, pos, ping, alpha):
    prob = prob.copy()
    prob[pos[0]][pos[1]] = 0
    chance = ping_chance_map(len(prob), pos, alpha)
    if ping:
        prob = prob * chance         # multiplies every cell by its own ping chance
    else:
        prob = prob * (1 - chance)   # multiplies every cell by its own chance of no ping
    return prob / prob.sum()         # divide every cell by the total so it all adds up to 1 again
