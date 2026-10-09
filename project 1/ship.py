
import numpy as np


# This is the class tile, basically each cell is actually a "tile" where it it has the ability to 
# have either a button, a bot, or a fire. The ship is made of 2d array of tiles where the bot and
# the fire can traverse through. 

class Tile:
    def __init__(self):
        #attributes of each tile object, has the ability to store fire, bot, and button, inially all cells start cells start 
        #as being blocked
        self.is_open = False
        self.on_fire = False
        self.has_bot = False
        self.has_button = False
        self.neighbors = []   # positions of the open tiles next to this one


def check_neighbors(D, r, c):
    # a list of "neighbors" that the bot has access at the time of it's current position at all sides 
    # up, down, right, left
    neighbors = []
    if r > 0:
        neighbors.append((r - 1, c))
    if r < D - 1:
        neighbors.append((r + 1, c))
    if c > 0:
        neighbors.append((r, c - 1))
    if c < D - 1:
        neighbors.append((r, c + 1))
    return neighbors


class Ship:
    # this object generates the ship itself consiting of a 2d array of tile objects based on the dimension of D
    def __init__(self, D):
        self.D = D
        self.grid = []   # once again, every tile starts blocked
        for r in range(D):
            row = []
            for c in range(D):
                row.append(Tile())
            self.grid.append(row)
    
    #returns the curernt tile based on the position
    def tile(self, pos):
        r, c = pos
        return self.grid[r][c]
    
    #return the neighbors attribute of the tile based on the current position
    def neighbors(self, pos):
        return self.tile(pos).neighbors
   
    #goes through each cell, if it's open or not, if it it's added to the list with the position
    # this is used later in the program to get a random open codel cell and assign a button, bot and fire cell to it
    # this is not a set because this list of cells will later be shuffled to random pick which cells will get those 3 objects
    def open_cells(self):
        cells = []
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].is_open:
                    cells.append((r, c))
        return cells

    #same as the open cell method, finds a set of cells that are fire cells
    def fire_cells(self):
        fire = set()
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].on_fire:
                    fire.add((r, c))
        return fire
    #iterates through and checks the # of open neighbors 
    def count_open_neighbors(self, r, c):
        count = 0
        for nr, nc in check_neighbors(self.D, r, c):
            if self.grid[nr][nc].is_open:
                count += 1
        return count
    #goes through all tiles in the ship, checks if the cell has only 1 open neighbor, 
    #if it does then it's a dead end is added to the list
    def dead_ends(self):
        ends = []
        for r in range(self.D):
            for c in range(self.D):
                if self.grid[r][c].is_open and self.count_open_neighbors(r, c) == 1:
                    ends.append((r, c))
        return ends

    def generate_blocks(self):
        candidates = []   # blocked tiles with exactly one open neighbour
        #finds the a random cell (the coordinates) within the inner boundries of the ship to open
        r = np.random.randint(1, self.D - 1)   
        c = np.random.randint(1, self.D - 1)   
        # this loops continues until the # of candiates is zero 
        while True:
            self.grid[r][c].is_open = True #opens up the cell, in the initial iteration, this is the random cell
            if (r, c) in candidates:
                candidates.remove((r, c)) #continues to remove the # of eleigable candiates in the ship

            for nr, nc in check_neighbors(self.D, r, c):
                if not self.grid[nr][nc].is_open:
                    count = self.count_open_neighbors(nr, nc)
                    # if there is only 1 open cell then add it could potentially be opened up
                    if count == 1:
                        candidates.append((nr, nc))
                    #if there are already 2 adjacent open cells then it shouldn't be opened up
                    elif count == 2:
                        candidates.remove((nr, nc))

            if len(candidates) == 0: #breaks the loop
                break
            r, c = candidates[np.random.randint(len(candidates))] #randomly picks the next eligable code to open 
    
    #the method that goes through all the dead end cells and a randomly chooses some of those dead end cells
    # to open up until the # of dead cells is reduced in half
    def reduce_dead_ends(self):
        ends = self.dead_ends()
        target = len(ends) / 2
        while len(ends) > target:
            r, c = ends[np.random.randint(len(ends))]
            blocked = []
            for nr, nc in check_neighbors(self.D, r, c):
                if not self.grid[nr][nc].is_open:
                    blocked.append((nr, nc))
            nr, nc = blocked[np.random.randint(len(blocked))]
            self.grid[nr][nc].is_open = True
            ends = self.dead_ends()

    #once we've gone through all the steps, we want to fill the neighbors attribute for each cell to 
    # so we know exactly how many and what open cells are avaiable to us when we are on a cell
    def find_neighbors(self):
        for r in range(self.D):
            for c in range(self.D):
                tile = self.grid[r][c]
                tile.neighbors = []
                if tile.is_open:
                    for nr, nc in check_neighbors(self.D, r, c):
                        if self.grid[nr][nc].is_open:
                            tile.neighbors.append((nr, nc))
    
    #pretty obvious, clears the entire ship of all the objects(bot, button, fire)
    def clear(self):
        """Take away the bot, the button and the fire, keeping the walls."""
        for row in self.grid:
            for tile in row:
                tile.on_fire = False
                tile.has_bot = False
                tile.has_button = False

# actually creates the ship, runs through all the methods in order based off the dimensions and seed
def generate_ship(D, seed):
    np.random.seed(seed)
    ship = Ship(D)
    ship.generate_blocks()
    ship.reduce_dead_ends()
    ship.find_neighbors()
    return ship
