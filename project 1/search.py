import heapq
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

# This is the just the basic BFS algorithim that the bots 1,2, and 3(if it's restricted bfs fails) will use 
# # the code is almost similar to the pseduo code that is mentioned in class, however we also check for restricted states 
# # that represent the fire cells - this method is mostly self explanatory - I used the deque for efficiency as it a data structure 
# #that I learned in a previous class (data structures)
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
    for r, c in starts:
        dist[r][c] = 0 #the start cells obviously have a distance of 0 since it takes 0 distance to reach there
        fringe.append((r, c)) # added to the queue
    while len(fringe) > 0:
        current_state = fringe.popleft()
        r, c = current_state 
        for child in ship.neighbors(current_state): #iterates through each child
            cr, cc = child
            if dist[cr][cc] == math.inf and child not in restricted: # check if the child has been seen before 
                dist[cr][cc] = dist[r][c] + 1 #doesn't just add 1 to all unseen cells, but takes the distance of the parent...
                # ...and adds another unit of distance
                fringe.append(child)
    return dist

#function just calculates the manhattan distance 
def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# this version of A* considers a "cost" element of moving to a particular node - this is be elaborated on in a different file but essientally
# the closer a cell is to a exisiting fire cell, the more the costly it is to use that cell to reach the button, obvisouly A*
# tries to find the goal node or the button with least cost since it is using a priority queue
def a_star(ship, start, goal, cost):
    fringe = [(manhattan_distance(start, goal), 0.0, start)]   # (priority, g, state)
    prev = {start: None} # starts off as none
    dist = {start: 0.0} # no distance for start node
    while len(fringe) > 0:
        priority, g, curr = heapq.heappop(fringe) # unpacks the initial node
        if curr == goal: #checks if it's a goal node if so then return the path
            return build_from_prev(prev, goal)
        for child in ship.neighbors(curr): #unpacks the children
            cr, cc = child
            dist_to_child = dist[curr] + cost[cr][cc] # takes the distance of the current node and adds the cost of going to the child node
            if child not in dist or dist_to_child < dist[child]: # check if it's been seen before 
                dist[child] = dist_to_child #updates the distance
                prev[child] = curr #updates the path to get to child
                priority = dist[child] + manhattan_distance(child, goal) # adds the heuristic p = g(current cost) + h(heuristic cost)
                heapq.heappush(fringe, (priority, dist[child], child)) 
    return None
