import math
from collections import deque


#this method builds the path from the original start location to all the way to goal coordinates
#since the "prev" parameter will contain a dictionary of states, where the keys are the next states and the
#items are the previous states, it iterates through it and builds the path, once it's done it's reversed to
# return the path from start to finish
def build_from_prev(prev, goal):
    path = []
    state = goal
    while state is not None:
        path.append(state)
        state = prev[state]
    path.reverse()
    return path

# this file is copied from project 1, the LocatorBot still moves one cell at a time up, down, left or right, so
# BFS still gives the shortest path between two cells. there's no fire this time so restricted is always empty,
# but I kept it so the code stays the same as the pseudo code from class

# This is the just the basic BFS algorithim that the LocatorBot uses to walk from one cell to another
# the code is almost similar to the pseduo code that is mentioned in class, however we also check for restricted states
# this method is mostly self explanatory - I used the deque for efficiency as it a data structure
# that I learned in a previous class (data structures)
def bfs(ship, start, goal, restricted):
    fringe = deque([start])
    closed_set = set()
    prev = {start: None}
    while len(fringe) > 0:
        current_state = fringe.popleft()
        if current_state == goal:
            return build_from_prev(prev, goal)
        for child in ship.neighbors(current_state):
            if child not in restricted and child not in closed_set and child not in prev:
                fringe.append(child)
                prev[child] = current_state
        closed_set.add(current_state)
    return None

# this function calculates the distance or the number of moves need to reach a cell based on the starting cells
# initially all cells are assigned a infinity then it puts all the starting cells into a queue
# then it unpacks each cell's children, if the children is unseen before (by check if it's a restricted cell or if it still has the 
# infinity value that was first assigned to all cells) then a distance of 1 is added and the child is 
#added to the queue as well, each new child takes the distance of the parent and adds another unit of distance (1). 
def map_distance(ship, starts, restricted):
    dist = []
    for row in range(ship.D): # goes through all the rows 
        dist.append([math.inf] * ship.D) # assigns infinity states to all columns in each row
    fringe = deque() # starts the queue
    for row, col in starts:
        dist[row][col] = 0 #the start cells obviously have a distance of 0 since it takes 0 distance to reach there
        fringe.append((row, col)) # added to the queue
    while len(fringe) > 0:
        current_state = fringe.popleft()
        row, col = current_state 
        for child in ship.neighbors(current_state): #iterates through each child
            child_row, child_col = child
            if dist[child_row][child_col] == math.inf and child not in restricted: # check if the child has been seen before 
                dist[child_row][child_col] = dist[row][col] + 1 #doesn't just add 1 to all unseen cells, but takes the distance of the parent...
                # ...and adds another unit of distance
                fringe.append(child)
    return dist
