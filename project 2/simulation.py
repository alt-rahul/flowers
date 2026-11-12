import time

import numpy as np

import strategies
from detector import type_a_ping, type_b_ping, update_type_a, update_type_b
from search import bfs
from ship import generate_ship

MAX_ACTIONS = 100000   # a safety limit on moves plus readings so a search can never loop forever


# builds the ship with the trial's seed, shuffles the open cells, and returns the ship, the first cell for the
# LocatorBot and the second cell for the LostBot, so the same seed always gives the same ship and starting cells
def setup_trial(D, seed):
    ship = generate_ship(D, seed)
    cells = ship.open_cells()
    np.random.shuffle(cells)
    bot_start = cells[0]
    lost = cells[1]
    return ship, bot_start, lost


# returns a D by D True or False array that is True for every open cell, this is the starting knowledge base
def open_mask(ship):
    mask = np.zeros((ship.D, ship.D), dtype=bool)
    for row, col in ship.open_cells():
        mask[row, col] = True
    return mask


# runs one search and returns found, moves, readings, cost and the time in ms. detector is A or B, setting is k or
# alpha, strategy is baseline or mine, and seed sets the random numbers. the cost is moves + 1/2 * readings, or
# only 1/2 * readings when free_moves is True. every loop does 3 things
# 1. runs the detector where the LocatorBot is, and stops if it is in the LostBot's cell
# 2. updates the knowledge base with the reading
# 3. gets the next cell from pick_target and walks there with BFS
def run_search(ship, bot_start, lost, detector, setting, strategy, seed, free_moves=False):
    np.random.seed(seed)
    start_time = time.perf_counter()
    ship.clear()
    ship.tile(bot_start).has_bot = True
    ship.tile(lost).has_lost_bot = True

    # True or False for every cell for type A, a probability for every cell for type B
    knowledge = open_mask(ship)
    if detector == "B":
        knowledge = knowledge / knowledge.sum()

    position = bot_start
    moves = 0
    readings = 0
    found = False

    while moves + readings < MAX_ACTIONS:
        # 1 and 2. run the detector and update the knowledge base
        readings += 1
        if position == lost:
            found = True   # the detector says we've found it
            break
        if detector == "A":
            ping = type_a_ping(position, lost, setting)
            knowledge = update_type_a(knowledge, position, ping, setting)
        else:
            ping = type_b_ping(position, lost, setting)
            knowledge = update_type_b(knowledge, position, ping, setting)

        # 3. pick where to go next and walk there, every cell on the path is one move
        # if it picks the cell it's already in, it just runs the detector there again
        target = pick_target(ship, knowledge, position, detector, setting, strategy, readings, free_moves)
        path = bfs(ship, position, target, set())
        moves += len(path) - 1
        ship.tile(position).has_bot = False
        position = target
        ship.tile(position).has_bot = True

    cost = moves + 0.5 * readings
    if free_moves:
        cost = 0.5 * readings   # moving is free, so only the detector counts
    return {
        "found": found,
        "moves": moves,
        "readings": readings,
        "cost": cost,
        "ms": (time.perf_counter() - start_time) * 1000,
    }


# calls the strategy that matches detector, strategy and free_moves, and returns the cell it picks
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
