import numpy as np

from detector import ping_chance_map
from search import map_distance

# this file has the 4 strategies (2 baselines and 2 of mine) that decide where the LocatorBot goes next.
# every strategy gets the knowledge base and the LocatorBot's position and returns the cell it wants to go to,
# the simulation then walks there with BFS and runs the detector once when it gets there.
# both of my strategies come from ideas from class: type A treats the detector like the MIN player in a
# minimax game tree, and type B plays "warmer / colder" with hill climbing from the local search lecture


# BFS distances (number of moves) from pos to every cell as a numpy array, it's just map_distance from
# project 1 turned into an array so we can do math on every cell at once
def walk_distances(ship, pos):
    return np.array(map_distance(ship, [pos], set()))


# ---------------------------------------------- baselines ----------------------------------------------

# baseline type A: go to the nearest cell the LostBot could still be in, breaking ties at random
def baseline_a(ship, possible, pos):
    dist = walk_distances(ship, pos)
    dist[~possible] = np.inf   # only look at cells that are still possible
    ties = np.argwhere(dist == dist.min())
    r, c = ties[np.random.randint(len(ties))]
    return (int(r), int(c))


# baseline type B: go to the cell that's most likely to have the LostBot, breaking ties by distance
# and then at random
def baseline_b(ship, prob, pos):
    dist = walk_distances(ship, pos)
    ties = np.argwhere(prob == prob.max())
    if len(ties) > 1:
        tie_dist = dist[ties[:, 0], ties[:, 1]]
        ties = ties[tie_dist == tie_dist.min()]
    r, c = ties[np.random.randint(len(ties))]
    return (int(r), int(c))


# ------------------------------------------ my type A: minimax ------------------------------------------

# in a game tree from class, MAX picks the move whose WORST case is the best, because it assumes MIN will
# always answer with the move that's worst for MAX. here the LocatorBot is MAX (it picks where to run the
# detector) and the detector is MIN (it picks the answer, ping or no ping). so for a spot x, this counts the
# cells the reading is sure to cross out, whichever answer we get:
#   - ping: every possible cell outside x's square gets crossed out
#   - no ping: every possible cell inside x's square gets crossed out
# so the worst case is the smaller of the two. if the LostBot could be in x itself, x is gone either way
# (either the detector says found or x gets crossed out), so it counts as 1 more
def sure_crossed_out(possible, x, k):
    r, c = x
    here = 1 if possible[r, c] else 0
    inside = possible[max(r - k, 0):r + k + 1, max(c - k, 0):c + k + 1].sum() - here
    outside = possible.sum() - inside - here
    return here + min(inside, outside)


# my type A strategy: go to the spot where running the detector is sure to cross out the most cells for what
# it costs to get there and run it (moves + 1/2), breaking ties by the closest spot. before the first ping
# a square full of cells we haven't searched yet has a small inside and a huge outside, so this picks a spot
# just past the edge of what we've already searched (the baseline reads right on that edge, so half its square
# was already searched). after a ping, the possible cells are all inside one square, so the best spot is one
# whose square cuts them in half, which is just binary search (each reading halves the possible cells).
# when moving is free (question 6) the walking cost doesn't matter, so it just picks the spot that's sure
# to cross out the most cells anywhere on the ship, so every reading is a perfect "20 questions" split
def my_a(ship, possible, pos, k, free_moves):
    dist = walk_distances(ship, pos)
    best = None
    best_score = -1
    for x in ship.open_cells():
        score = sure_crossed_out(possible, x, k)
        if not free_moves:
            score = score / (dist[x] + 0.5)
        if score > best_score or (score == best_score and dist[x] < dist[best]):
            best = x
            best_score = score
    return best


# --------------------------------------- my type B: warmer / colder ---------------------------------------

# how "warm" a cell is: the chance that running the detector there pings (or finds the LostBot). this is
# marginalization like P(heads) in the two coins example from class, we don't know where the LostBot is so
# we add up every place it could be times the chance of a ping if it was there:
#   warmth(x) = sum over cells b of P(LostBot in b) * P(ping | we're in x, LostBot in b)
# if the LostBot is in x itself the detector says found, which is even better than a ping so it counts as 1
def warmth(prob, x, alpha):
    chance = ping_chance_map(prob.shape[0], x, alpha)
    chance[x] = 1
    return (prob * chance).sum()


# my type B strategy is hill climbing (from the local search lecture) on how warm a cell is, like the game
# "warmer / colder". it only ever looks at the cells next to it: if one of them is warmer than where it is,
# it steps there (and runs the detector there, since every new cell gets a reading). every reading updates
# the probabilities, so the hill moves as the bot learns: a ping makes the cells around us warmer, a no ping
# makes them colder and pushes the bot away. if no neighbor is warmer, it's at the top of a hill, and like
# the baseline it goes to the most likely cell (this is how it gets out of a local maximum)
def my_b(ship, prob, pos, alpha):
    best = None
    best_warmth = warmth(prob, pos, alpha)
    for y in ship.neighbors(pos):
        w = warmth(prob, y, alpha)
        if w > best_warmth:
            best = y
            best_warmth = w
    if best is None:
        return baseline_b(ship, prob, pos)
    return best


# ---------------------------------- my type B when moving is free: fairest coin ----------------------------------

# the warmth of every open cell at once. it uses a table of the ping chance between every pair of open
# cells (an open cells by open cells array), so the warmth of every cell is one matrix times vector. the table
# only depends on the ship and alpha, so it gets saved on the ship and only rebuilt when alpha changes
def warmth_everywhere(ship, prob, alpha):
    if getattr(ship, "table_alpha", None) != alpha:
        cells = np.array(ship.open_cells())
        d = np.sqrt(((cells[:, None, :] - cells[None, :, :]) ** 2).sum(axis=2))
        ship.table = np.exp(-alpha * (d - 1))
        np.fill_diagonal(ship.table, 1)   # the LostBot's own cell says found, which counts as 1 (same as warmth)
        ship.table_cells = cells
        ship.table_alpha = alpha
    cells = ship.table_cells
    return cells, ship.table @ prob[cells[:, 0], cells[:, 1]]


# my type B strategy when moving is free (question 6). a reading you can already predict teaches you
# nothing, like flipping a coin you know is double headed. so it runs the detector where the chance of a
# ping is closest to 50/50, which is the "fairest coin" we could flip. but a fair coin far away can't tell
# apart cells that are right next to each other, so every other reading it checks its best guess (the most
# likely cell, like the baseline), which is also the only way to actually find the LostBot.
# readings is how many times we've run the detector so far, so this switches between the two each time
def fairest_coin(ship, prob, pos, alpha, readings):
    if readings % 2 == 0:
        return baseline_b(ship, prob, pos)
    cells, w = warmth_everywhere(ship, prob, alpha)
    i = np.argmin(np.abs(w - 0.5))
    return (int(cells[i, 0]), int(cells[i, 1]))
