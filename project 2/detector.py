import math

import numpy as np

# this file has the two detectors and the functions that update the knowledge base after a reading.
# both knowledge bases are D by D numpy arrays, and a cell is still reached with [row][col] like a list


# returns True if the LostBot's row and column are both at most k away from the LocatorBot's,
# which means it is inside the 2k + 1 by 2k + 1 square around the LocatorBot
def type_a_ping(bot_position, lost_position, k):
    return abs(bot_position[0] - lost_position[0]) <= k and abs(bot_position[1] - lost_position[1]) <= k


# returns the chance of a type B ping, e ** (-alpha * (distance - 1)), where distance is the euclidean
# distance between the two bots
def ping_chance(bot_position, lost_position, alpha):
    distance = math.dist(bot_position, lost_position)
    return math.exp(-alpha * (distance - 1))


# returns True with that chance, by checking if a random number between 0 and 1 is below it
def type_b_ping(bot_position, lost_position, alpha):
    return np.random.random() < ping_chance(bot_position, lost_position, alpha)


# returns a D by D array with the type B ping chance for every cell if the LocatorBot is at position.
# the two for loops fill in the distance to every cell, then np.exp turns every distance into a chance at once
def ping_chance_map(D, position, alpha):
    distance = np.zeros((D, D))
    for row in range(D):
        for col in range(D):
            distance[row][col] = math.sqrt((row - position[0]) ** 2 + (col - position[1]) ** 2)
    return np.exp(-alpha * (distance - 1))


# returns a new copy of possible, the True or False array of cells the LostBot could still be in. the cell at
# position is set to False, then every cell where type_a_ping would not give the same answer as ping is set to False
def update_type_a(possible, position, ping, k):
    possible = possible.copy()
    possible[position[0]][position[1]] = False   # the detector did not say found here
    for row in range(len(possible)):
        for col in range(len(possible)):
            if type_a_ping(position, (row, col), k) != ping:
                possible[row][col] = False
    return possible


# returns a new copy of prob, the probability of the LostBot being in each cell. the cell at position is set to 0,
# every cell is multiplied by its ping chance for a ping or by 1 minus its ping chance for no ping, and then
# every cell is divided by the total so they add up to 1
def update_type_b(prob, position, ping, alpha):
    prob = prob.copy()
    prob[position[0]][position[1]] = 0
    chance = ping_chance_map(len(prob), position, alpha)
    if ping:
        prob = prob * chance         # multiplies every cell by its own ping chance
    else:
        prob = prob * (1 - chance)   # multiplies every cell by its own chance of no ping
    return prob / prob.sum()         # divide every cell by the total so it all adds up to 1 again
