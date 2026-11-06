import numpy as np

from detector import update_type_b
from search import bfs, map_distance

# this file has the 4 strategies (2 baselines and 2 of mine) that decide where the LocatorBot goes next.
# every strategy gets the knowledge base and the LocatorBot's position and returns the cell it wants to go to,
# the simulation then walks there with BFS. my type B strategy also decides how many times to run the
# detector before moving, the other three always run it once when they get somewhere

MAX_READINGS = 3   # the most times my type B strategy runs the detector in one cell before moving on


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


# ---------------------------------------------- my type A ----------------------------------------------

# how many cells we expect to cross out if we run the type A detector at spot x. there are N possible cells
# left and they're all equally likely, so if "inside" of them are in x's square:
#   - with chance inside/N it pings and the "outside" cells get crossed out
#   - with chance outside/N it doesn't ping and the "inside" cells get crossed out
# if the LostBot could be in x itself, there's also a 1/N chance we find it right there (which solves
# everything, so it counts as 1 whole search), and x gets crossed out when it pings but we didn't find it
def expected_crossed_out(possible, x, k):
    N = possible.sum()
    r, c = x
    inside = possible[max(r - k, 0):r + k + 1, max(c - k, 0):c + k + 1].sum()
    outside = N - inside
    if possible[r, c]:
        return 1 + (inside - 1) / N * (outside + 1) + outside / N * inside
    return inside / N * outside + outside / N * inside


# my type A strategy: instead of walking to the nearest cell that the LostBot could be in, pick the spot
# where running the detector crosses out the most cells for what it costs to get there and run it
# (moves + 1/2). the best spot is usually a cell where the LostBot can't even be: before a ping it's a spot just
# past the edge of what we've already searched so the whole square is new, and after a ping it's a spot whose
# square cuts the possible cells roughly in half, kind of like binary search.
# before the first ping I only let it look at spots a little past the nearest possible cell (at most k more
# moves), so it pushes out from where it already searched and doesn't leave holes it has to walk back to later.
# when moving is free (question 6), the walking cost doesn't matter so it just picks the spot that crosses
# out the most cells
def my_a(ship, possible, pos, k, pinged, free_moves):
    dist = walk_distances(ship, pos)
    nearest = dist[possible].min()
    best = None
    best_score = -1
    for x in ship.open_cells():
        if not pinged and not free_moves and dist[x] > nearest + k:
            continue
        score = expected_crossed_out(possible, x, k)
        if not free_moves:
            score = score / (dist[x] + 0.5)
        if score > best_score:
            best = x
            best_score = score
    return best


# ---------------------------------------------- my type B ----------------------------------------------

# the cell my type B strategy wants to head towards: the cell with the best chance of having the LostBot
# for how far away it is, P(cell) / (moves to get there + 1). the baseline only looks at P(cell), so after a
# "no ping" it walks all the way across the ship to the cell that's furthest away. this one would rather check a
# slightly less likely cell that's way closer
def b_goal(prob, dist):
    score = prob / (dist + 1)
    r, c = np.unravel_index(np.argmax(score), score.shape)
    return (int(r), int(c))


# the next cell on the way to the goal (or the goal itself if we're already there)
def next_cell(ship, pos, goal):
    if goal == pos:
        return pos
    return bfs(ship, pos, goal, set())[1]


# my type B strategy walks one cell at a time towards b_goal, and every step it decides again where to go.
def my_b(ship, prob, pos):
    dist = walk_distances(ship, pos)
    return next_cell(ship, pos, b_goal(prob, dist))


# this decides if my type B strategy should run the detector (again) in the cell it's in. a reading costs
# half a move, so it's only worth it if the answer could actually change what we do next: I work out the
# knowledge base for both answers (ping and no ping) and if both would send the bot to the same next cell,
# the reading wouldn't change anything so we skip it. if they'd send it to different cells we run it, and then
# check again, so sometimes it runs the detector 2 or 3 times in one spot when the readings disagree. that's
# like flipping the mystery coin again from the two coins example in class, every extra flip makes us more sure.
# it always runs the detector when the cell it's standing on is the goal, since that's how it finds the LostBot
def my_b_wants_reading(ship, prob, pos, alpha, readings_here):
    dist = walk_distances(ship, pos)
    goal = b_goal(prob, dist)
    if goal == pos:
        return True
    if readings_here >= MAX_READINGS:
        return False
    goal_if_ping = b_goal(update_type_b(prob, pos, True, alpha), dist)
    goal_if_no_ping = b_goal(update_type_b(prob, pos, False, alpha), dist)
    if goal_if_ping == goal_if_no_ping:
        return False
    return next_cell(ship, pos, goal_if_ping) != next_cell(ship, pos, goal_if_no_ping)
