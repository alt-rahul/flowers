import math

import numpy as np

# this file has everything about the two bot detectors, when they ping and how the LocatorBot updates
# what it knows, its knowledge base, after it runs a detector. the knowledge bases are D by D numpy arrays
# this time instead of lists since in project 1 I said I would try this, you still get a cell with [row][col]


# the type A detector pings if the LostBot is inside the (2k+1) by (2k+1) square centered on the LocatorBot,
# which is the same thing as saying the LostBot's row and column are both at most k away from ours
def type_a_ping(bot_position, lost_position, k):
    return abs(bot_position[0] - lost_position[0]) <= k and abs(bot_position[1] - lost_position[1]) <= k


# the chance that the type B detector pings, e^(-alpha * (d - 1)) where d is the euclidean distance between
# the two bots. a LostBot right next to us (d = 1) always pings, and the further away it is the less likely
def ping_chance(bot_position, lost_position, alpha):
    distance = math.dist(bot_position, lost_position)
    return math.exp(-alpha * (distance - 1))


# the type B detector actually flips a coin with that chance to decide if it pings or not
def type_b_ping(bot_position, lost_position, alpha):
    return np.random.random() < ping_chance(bot_position, lost_position, alpha)


# a D by D array with the chance that the type B detector pings for a LostBot in each cell, if the LocatorBot
# is at position. the two for loops find the distance to every cell, then np.exp does e^(-alpha * (d - 1)) on every
# cell at once
def ping_chance_map(D, position, alpha):
    distance = np.zeros((D, D))
    for row in range(D):
        for col in range(D):
            distance[row][col] = math.sqrt((row - position[0]) ** 2 + (col - position[1]) ** 2)
    return np.exp(-alpha * (distance - 1))


# the type A knowledge base is a True or False array of every cell the LostBot could still be in, it starts as
# every open cell. after a reading we go through every cell and ask, if the LostBot was here would the
# detector have said what it just said? if not, it can't be there, so it gets crossed out
def update_type_a(possible, position, ping, k):
    possible = possible.copy()
    possible[position[0]][position[1]] = False   # it didn't say found, so the LostBot isn't where we're standing
    for row in range(len(possible)):
        for col in range(len(possible)):
            if type_a_ping(position, (row, col), k) != ping:
                possible[row][col] = False
    return possible


# the type B knowledge base is the probability that the LostBot is in each cell, it starts the same for every
# open cell. after a reading we use bayes' rule like the two coins example from class, the new chance of a cell
# is its old chance times the chance of getting that reading if the LostBot was there, divided by the total of
# that over every cell so it all adds up to 1 again. the chance of the reading is the ping chance for a ping,
# and 1 minus the ping chance for no ping. the cell we're standing on goes to 0 first since the detector would
# have said found if it was there
def update_type_b(prob, position, ping, alpha):
    prob = prob.copy()
    prob[position[0]][position[1]] = 0
    chance = ping_chance_map(len(prob), position, alpha)
    if ping:
        prob = prob * chance         # multiplies every cell by its own ping chance
    else:
        prob = prob * (1 - chance)   # multiplies every cell by its own chance of no ping
    return prob / prob.sum()         # divide every cell by the total so it all adds up to 1 again
