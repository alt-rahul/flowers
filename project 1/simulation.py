import time

import numpy as np

from bots import PENALTY, bot1_path, bot2_path, bot3_path, bot4_path
from fire import spread_fire
from ship import generate_ship

#this is the set up trial, meaning it will set up the "environment" for the us to run the bots
def setup_trial(D, seed):
    ship = generate_ship(D, seed) #generates the ships
    cells = ship.open_cells() #as I mentinoed in the ship.py, this is where we get the list of all open shells
    np.random.shuffle(cells)   # put the open tiles in a random order and take the first three
    #assign the objects to each of the random tile
    bot_start = cells[0] 
    button = cells[1]
    fire_start = cells[2]
    return ship, bot_start, button, fire_start #returns the map the the coordiates of teh cells with the objects


#this is the run bot method, this will run each of the bots in timesteps, if the bot reaches the same cell as the button then it wins
# if the bot reachs the same tile as the fire than it fails - the fire spreads at each timestep
# so the only the fire generation uses the random seeds not the the bots themselves so we can replicate the fire so each bot can experince the 
#same fire generating pattern. The penalty parameter is only for bot4 which tell penalizes cells that are closer to the fire.
# which is explained in a different file. This method returns a dictionary of information like whether the bot was successful, if it wasn't
# what's the reason?, how many moves the bot made, the exact path the bot had taken, and a few other intersting variables, such as close calls, after the bot moves
# if any neighbor of the bot new cell is burning then it counts as a close call, changes of mind meaning if the new plan isn't the same as the previous plan then that's
#recorded as well, there also another one. There is also a ms varible which counts the time the bot took. 


def run_bot(ship, bot_start, button, fire_start, q, bot, fire_seed, penalty=PENALTY):
    #set ups the fire seed and assigns tiles with the respective object corrdinates to true - as if the tile at that location
    #is holding that object
    np.random.seed(fire_seed)
    ship.clear()
    ship.tile(bot_start).has_bot = True
    ship.tile(button).has_button = True
    ship.tile(fire_start).on_fire = True

    #sets the position at the corrdinates 
    pos = bot_start
    #appends the first position into the path (a list of coordinates the bot goes through until it wins/fails)
    path = [pos]
    plan = None #plan the list of corrdinates that the bot wants to go step by step, at the first index is the current position of the bot
    #the second index is the next position the bot will take, the plan gets recomputed at everytime step unless it's bot1
    close_calls = 0 
    change_plan = 0 
    old_plan = None 
    think_time = 0.0 # this just measures the time the bot took
    max_steps = 2 * len(ship.open_cells())   #max number of timesteps, theortically shoudln't take more than 2x the # of cells that exist
    reason = "timeout"

    for t in range(max_steps):
        # 1. The bot decides.
        start = time.perf_counter() #starts the timer
        #checks which bot we are currently running then based off that it creates the plan 
        if bot == 1:
            if t == 0:
                plan = bot1_path(ship, pos, button)   # Bot 1 only plans once
        elif bot == 2:
            plan = bot2_path(ship, pos, button)
        elif bot == 3:
            plan = bot3_path(ship, pos, button)
        else:
            plan = bot4_path(ship, pos, button, q, penalty)
        think_time += time.perf_counter() - start 

        #this checks if bots 2-4 have changed their plan if so then it counts towards change plan 
        if bot != 1 and old_plan is not None and plan is not None and plan != old_plan[1:]:
            change_plan += 1
        old_plan = plan

        if plan is None:
            reason = "trapped"   # it every possible route touches the fire there it's impossible
            break
        if bot == 1:
            next_pos = plan[t + 1]   # bot1 just follows its first plan and takes the next step
        else:
            next_pos = plan[1]


        #actually moves the bot from one tile to another
        ship.tile(pos).has_bot = False
        pos = next_pos
        ship.tile(pos).has_bot = True
        path.append(pos)
        if ship.tile(pos).on_fire: #checks if the bot is currently on a tile that has a fire
            reason = "entered_fire"
            break
        #this checks of the close call, if the neighbor caught on fire then it's technically a close call
        for n in ship.neighbors(pos):
            if ship.tile(n).on_fire:
                close_calls += 1
                break
        if pos == button: #checks if it's reached the goal node or the button
            reason = "success"
            break

        # this actually spreads the fire - the fire should be spreading at every time step
        spread_fire(ship, q)
        if ship.tile(pos).on_fire: #checks again if the current bot location caught on fire - if so then it's a fail
            reason = "caught"
            break
        if ship.tile(button).on_fire:
            reason = "button_burned"   # button can't be reached if the cell is on fire - so it's another fail
            break

    return {
        "success": reason == "success",
        "reason": reason,
        "steps": len(path) - 1,
        "path": path,
        "ms": think_time * 1000,
        "close_calls": close_calls,
        "change_plan": change_plan,
    }
