import time

import numpy as np

import strategies
from detector import type_a_ping, type_b_ping, update_type_a, update_type_b
from search import bfs
from ship import generate_ship

MAX_ACTIONS = 100000   # a safety limit on moves plus readings so a search can never loop forever ( can't have this issue again :( like last time)


# goes through the process of building  the ship with the trials seed, shuffling the open cells then returns the ship, 
# the first cell is for the locatorbot while the next one is for the lost bot, seeds keep it consistent with same ship and starting locations
def setup_trial(D, seed):
    ship = generate_ship(D, seed)
    cells = ship.open_cells()
    np.random.shuffle(cells)
    bot_start = cells[0]
    lost = cells[1]
    return ship, bot_start, lost


# returns a D by D true or false array that is true for every open cell, this is the starting knowledge base
def open_mask(ship):
    mask = np.zeros((ship.D, ship.D), dtype=bool)
    for row, col in ship.open_cells():
        mask[row, col] = True
    return mask


# runs one search and returns a few variables like found, moves, readings, cost and the time in ms. detector is A or B, setting (or the 
# parameter) is k or alpha, strategy is baseline or mine, and seed sets the random numbers. basically all the parameterization happens here to determine
# how the search will work, every loop does the following three things:
# 1. runs the detector where the locatbor is currenlty sitting at, and stops if it is in the lostbot cell
# 2. updates the knowledge base with the detection
# 3. gets the next cell from the pick target var and moves there with BFS
def run_search(ship, bot_start, lost, detector, setting, strategy, seed, free_moves=False):
    np.random.seed(seed)
    start_time = time.perf_counter()
    ship.clear()
    ship.tile(bot_start).has_bot = True
    ship.tile(lost).has_lost_bot = True

    # true or false for every cell for type A and a probability for every cell for type B
    knowledge = open_mask(ship)
    if detector == "B":
        knowledge = knowledge / knowledge.sum()

    position = bot_start
    moves = 0
    readings = 0
    found = False

    while moves + readings < MAX_ACTIONS:
        # run the detector and update the knowledge base
        readings += 1
        if position == lost:
            found = True   # the detector says weve found it
            break
        if detector == "A":
            ping = type_a_ping(position, lost, setting)
            knowledge = update_type_a(knowledge, position, ping, setting)
        else:
            ping = type_b_ping(position, lost, setting)
            knowledge = update_type_b(knowledge, position, ping, setting)

        # pick where to go next and move there, every cell on the path is one move
        # if it picks the cell it's already in, it just runs the detector there again
        target = pick_target(ship, knowledge, position, detector, setting, strategy, readings, free_moves)
        path = bfs(ship, position, target, set())
        moves += len(path) - 1
        ship.tile(position).has_bot = False
        position = target
        ship.tile(position).has_bot = True

    cost = moves + 0.5 * readings
    if free_moves:
        cost = 0.5 * readings   # moving is free so only the detector counts
    return {
        "found": found,
        "moves": moves,
        "readings": readings,
        "cost": cost,
        "ms": (time.perf_counter() - start_time) * 1000,
    }


def pick_target(ship, knowledge, position, detector, setting, strategy, readings, free_moves):
    if detector == "A" and strategy == "baseline":
        return strategies.baseline_a(ship, knowledge, position)
    if detector == "A":
        return strategies.my_a(ship, knowledge, position, setting, free_moves)
    if strategy == "baseline":
        return strategies.baseline_b(ship, knowledge, position)
    if free_moves:
        return strategies.fairest_coin(ship, knowledge, position, setting, readings)
    return strategies.my_b(ship, knowledge, position, setting)
