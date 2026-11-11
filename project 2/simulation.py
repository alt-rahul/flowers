import time

import numpy as np

import strategies
from detector import type_a_ping, type_b_ping, update_type_a, update_type_b
from search import bfs
from ship import generate_ship

MAX_ACTIONS = 100000   # a safety limit so a run can never loop forever (no run ever gets close to this)


# this sets up a trial the same way as in project 1, the ship is built with the trial's seed, then the open
# cells are shuffled and the first one gets the LocatorBot and the second one gets the LostBot.
# so trial i is always the same ship with the same two starting cells
def setup_trial(D, seed):
    ship = generate_ship(D, seed)
    cells = ship.open_cells()
    np.random.shuffle(cells)
    bot_start = cells[0]
    lost = cells[1]
    return ship, bot_start, lost


# a D by D True or False array with True for every open cell, this is the starting knowledge base, at the
# start the LostBot could be in any open cell
def open_mask(ship):
    mask = np.zeros((ship.D, ship.D), dtype=bool)
    for row, col in ship.open_cells():
        mask[row, col] = True
    return mask


# this runs one search from start to finish. detector is A or B, setting is k for type A or alpha for
# type B, and strategy is baseline or mine. free_moves is for question 6 where only the detector costs
# anything. the seed is for the random numbers for type B pings and breaking ties, so the same run can be done
# again exactly the same way. every loop the LocatorBot does 3 things
# 1. runs the detector where it is, once, every strategy does this
# 2. updates its knowledge base with the reading
# 3. picks where to go next and walks there with BFS
# it stops as soon as it runs the detector in the LostBot's cell. it returns how many moves and detector
# uses it took, the total cost which is moves + 1/2 * detector uses, and how long it took to run
def run_search(ship, bot_start, lost, detector, setting, strategy, seed, free_moves=False):
    np.random.seed(seed)
    start_time = time.perf_counter()
    ship.clear()
    ship.tile(bot_start).has_bot = True
    ship.tile(lost).has_lost_bot = True

    # the knowledge base is True or False for every cell for type A, and a probability for every cell for type B
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


# which strategy picks the next cell to go to
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
