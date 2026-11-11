
import numpy as np


# this file is mostly the same as the ship.py from project 1, the ship is still built the exact same way
# so with the same seed you get the exact same ship as in project 1. the only difference is that there is no
# fire or button anymore, instead a tile can hold the LocatorBot (our bot) or the LostBot (the bot we're looking for)

# This is the class tile, basically each cell is actually a "tile" where it it has the ability to
# have either the LocatorBot or the LostBot. The ship is made of 2d array of tiles where the LocatorBot
# can move through.

class Tile:
    def __init__(self):
        #attributes of each tile object, has the ability to store the LocatorBot and the LostBot, initially all cells start
        #as being blocked
        self.is_open = False
        self.has_bot = False        # the LocatorBot
        self.has_lost_bot = False   # the LostBot, it never moves
        self.neighbors = []   # positions of the open tiles next to this one


def check_neighbors(D, row, col):
    # a list of "neighbors" that the bot has access at the time of it's current position at all sides 
    # up, down, right, left
    neighbors = []
    if row > 0:
        neighbors.append((row - 1, col))
    if row < D - 1:
        neighbors.append((row + 1, col))
    if col > 0:
        neighbors.append((row, col - 1))
    if col < D - 1:
        neighbors.append((row, col + 1))
    return neighbors


class Ship:
    # this object generates the ship itself consiting of a 2d array of tile objects based on the dimension of D
    def __init__(self, D):
        self.D = D
        self.grid = []   # once again, every tile starts blocked
        for row in range(D):
            tiles = []
            for col in range(D):
                tiles.append(Tile())
            self.grid.append(tiles)
    
    #returns the curernt tile based on the position
    def tile(self, position):
        row, col = position
        return self.grid[row][col]
    
    #return the neighbors attribute of the tile based on the current position
    def neighbors(self, position):
        return self.tile(position).neighbors
   
    #goes through each cell, if it's open or not, if it it's added to the list with the position
    # this is used later in the program to get a random open cell for the LocatorBot and the LostBot
    # this is not a set because this list of cells will later be shuffled to random pick which cells will get those 2 bots
    def open_cells(self):
        cells = []
        for row in range(self.D):
            for col in range(self.D):
                if self.grid[row][col].is_open:
                    cells.append((row, col))
        return cells

    #iterates through and checks the # of open neighbors 
    def count_open_neighbors(self, row, col):
        count = 0
        for neighbor_row, neighbor_col in check_neighbors(self.D, row, col):
            if self.grid[neighbor_row][neighbor_col].is_open:
                count += 1
        return count
    #goes through all tiles in the ship, checks if the cell has only 1 open neighbor, 
    #if it does then it's a dead end is added to the list
    def dead_ends(self):
        ends = []
        for row in range(self.D):
            for col in range(self.D):
                if self.grid[row][col].is_open and self.count_open_neighbors(row, col) == 1:
                    ends.append((row, col))
        return ends

    def generate_blocks(self):
        candidates = []   # blocked tiles with exactly one open neighbour
        #finds the a random cell (the coordinates) within the inner boundries of the ship to open
        row = np.random.randint(1, self.D - 1)   
        col = np.random.randint(1, self.D - 1)   
        # this loops continues until the # of candiates is zero 
        while True:
            self.grid[row][col].is_open = True #opens up the cell, in the initial iteration, this is the random cell
            if (row, col) in candidates:
                candidates.remove((row, col)) #continues to remove the # of eleigable candiates in the ship

            for neighbor_row, neighbor_col in check_neighbors(self.D, row, col):
                if not self.grid[neighbor_row][neighbor_col].is_open:
                    count = self.count_open_neighbors(neighbor_row, neighbor_col)
                    # if there is only 1 open cell then add it could potentially be opened up
                    if count == 1:
                        candidates.append((neighbor_row, neighbor_col))
                    #if there are already 2 adjacent open cells then it shouldn't be opened up
                    elif count == 2:
                        candidates.remove((neighbor_row, neighbor_col))

            if len(candidates) == 0: #breaks the loop
                break
            row, col = candidates[np.random.randint(len(candidates))] #randomly picks the next eligable code to open 
    
    #the method that goes through all the dead end cells and a randomly chooses some of those dead end cells
    # to open up until the # of dead cells is reduced in half
    def reduce_dead_ends(self):
        ends = self.dead_ends()
        target = len(ends) / 2
        while len(ends) > target:
            row, col = ends[np.random.randint(len(ends))]
            blocked = []
            for neighbor_row, neighbor_col in check_neighbors(self.D, row, col):
                if not self.grid[neighbor_row][neighbor_col].is_open:
                    blocked.append((neighbor_row, neighbor_col))
            neighbor_row, neighbor_col = blocked[np.random.randint(len(blocked))]
            self.grid[neighbor_row][neighbor_col].is_open = True
            ends = self.dead_ends()

    #once we've gone through all the steps, we want to fill the neighbors attribute for each cell to 
    # so we know exactly how many and what open cells are avaiable to us when we are on a cell
    def find_neighbors(self):
        for row in range(self.D):
            for col in range(self.D):
                tile = self.grid[row][col]
                tile.neighbors = []
                if tile.is_open:
                    for neighbor_row, neighbor_col in check_neighbors(self.D, row, col):
                        if self.grid[neighbor_row][neighbor_col].is_open:
                            tile.neighbors.append((neighbor_row, neighbor_col))
    
    #pretty obvious, clears the entire ship of both bots but keeps the walls
    def clear(self):
        for row in self.grid:
            for tile in row:
                tile.has_bot = False
                tile.has_lost_bot = False

# actually creates the ship, runs through all the methods in order based off the dimensions and seed
def generate_ship(D, seed):
    np.random.seed(seed)
    ship = Ship(D)
    ship.generate_blocks()
    ship.reduce_dead_ends()
    ship.find_neighbors()
    return ship

