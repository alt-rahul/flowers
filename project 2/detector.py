import math

import numpy as np

# this file has the two detectors and the functions that update the knowledge base after a reading.
# both knowledge bases are D by D numpy arrays, and a cell is still reached with [row][col] like a list


# returns true if the lostbot's row and column are both k away from the locatorbot's,
# which means it is inside the square around the locatorbot
def type_a_ping(bot_position, lost_position, k):
    return abs(bot_position[0] - lost_position[0]) <= k and abs(bot_position[1] - lost_position[1]) <= k


# returns the chance of a type B ping,where distance is the euclidean
# distance between the two bots
def ping_chance(bot_position, lost_position, alpha):
    distance = math.dist(bot_position, lost_position)
    return math.exp(-alpha * (distance - 1))


# returns true with that probabilty, by checking if a random number between 0 and 1 is below that number
def type_b_ping(bot_position, lost_position, alpha):
    return np.random.random() < ping_chance(bot_position, lost_position, alpha)


# returns a D by D array with the type B ping chance for every cell if the locatorbot is at that position
# the two for loops fill in the distance to every cell, then exp turns the distance into probability
def ping_chance_map(D, position, alpha):
    distance = np.zeros((D, D))
    for row in range(D):
        for col in range(D):
            distance[row][col] = math.sqrt((row - position[0]) ** 2 + (col - position[1]) ** 2)
    return np.exp(-alpha * (distance - 1))


# returns a new copy of possible, the true or false array of cells the lostbot could still be i,n the cell at
# position is supposed to be set to false, then every cell where the type of ping would not produce the same answer as
#  ping is set to  be false
def update_type_a(possible, position, ping, k):
    possible = possible.copy()
    possible[position[0]][position[1]] = False   # the detector did not say found here
    for row in range(len(possible)):
        for col in range(len(possible)):
            if type_a_ping(position, (row, col), k) != ping:
                possible[row][col] = False
    return possible


# returns a new copy of prob, the probability of the lostbot being in each cell, the cell at position is set to 0,
# every cell is multiplied by it's respective ping probability for a ping or by 1 minus its ping probability for no ping, 
# and then every cell is divided by the total so they add up to 1 (I am trying to normalize here)
def update_type_b(prob, position, ping, alpha):
    prob = prob.copy()
    prob[position[0]][position[1]] = 0
    chance = ping_chance_map(len(prob), position, alpha)
    if ping:
        prob = prob * chance         # multiplies every cell by its own ping probability
    else:
        prob = prob * (1 - chance)   # multiplies every cell by its own probability of no ping
    return prob / prob.sum()         
