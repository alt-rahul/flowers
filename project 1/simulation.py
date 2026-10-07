"""Setting up a trial and running one bot on it."""
import time

import numpy as np

from bots import PENALTY, THRESHOLD, bot1_path, bot2_path, bot3_path, bot4_path
from fire import spread_fire
from search import distance_map, fireproof_path
from ship import generate_ship


def setup_trial(D, seed):
    """A random ship, and three different random open tiles for the bot, the
    button and the first fire. The same seed always gives the same trial."""
    ship = generate_ship(D, seed)
    cells = ship.open_cells()
    np.random.shuffle(cells)   # put the open tiles in a random order and take the first three
    bot_start = cells[0]
    button = cells[1]
    fire_start = cells[2]
    return ship, bot_start, button, fire_start


def run_bot(ship, bot_start, button, fire_start, q, bot, fire_seed,
            threshold=THRESHOLD, penalty=PENALTY, one_step=False):
    """Run Bot 1, 2, 3 or 4. Each time step, in order: the bot decides and
    moves; if it is on the button it wins; otherwise the fire spreads, and the
    bot fails if the fire reaches it or the button.

    The fire only uses random numbers, and the bots never do. So starting the
    random numbers from the same fire_seed gives exactly the same fire, which
    is how every bot on a trial faces the same fire.

    threshold, penalty and one_step only matter for Bot 4 (see bots.py).

    Returns a dictionary with:
        success     True if the button was pressed
        reason      success, entered_fire, caught, button_burned, trapped or timeout
        steps       how many moves the bot made
        path        every position the bot was on
        deviations  moves Bot 2's rule could not have made
        ms          time spent deciding, in milliseconds
    """
    np.random.seed(fire_seed)
    ship.clear()
    ship.tile(bot_start).has_bot = True
    ship.tile(button).has_button = True
    ship.tile(fire_start).on_fire = True

    pos = bot_start
    path = [pos]
    plan = None
    deviations = 0
    think_time = 0.0
    max_steps = 10 * len(ship.open_cells())   # safety limit, never reached
    reason = "timeout"

    for t in range(max_steps):
        # 1. The bot decides.
        start = time.perf_counter()
        if bot == 1:
            if t == 0:
                plan = bot1_path(ship, pos, button)   # Bot 1 only plans once
        elif bot == 2:
            plan = bot2_path(ship, pos, button)
        elif bot == 3:
            plan = bot3_path(ship, pos, button)
        else:
            plan = bot4_path(ship, pos, button, q, threshold, penalty, one_step)
        think_time += time.perf_counter() - start

        if plan is None:
            reason = "trapped"   # every route to the button runs through fire
            break
        if bot == 1:
            next_pos = plan[t + 1]   # Bot 1 just follows its first plan
        else:
            next_pos = plan[1]

        # Was this a move Bot 2's rule could have made? Bot 2 always moves one
        # step closer to the button along tiles that aren't burning.
        to_button = distance_map(ship, [button], ship.fire_cells())
        r, c = pos
        nr, nc = next_pos
        if to_button[nr][nc] != to_button[r][c] - 1:
            deviations += 1

        # 2. The bot moves.
        ship.tile(pos).has_bot = False
        pos = next_pos
        ship.tile(pos).has_bot = True
        path.append(pos)
        if ship.tile(pos).on_fire:
            reason = "entered_fire"
            break
        if pos == button:
            reason = "success"
            break

        # 3. The fire spreads.
        spread_fire(ship, q)
        if ship.tile(pos).on_fire:
            reason = "caught"
            break
        if ship.tile(button).on_fire:
            reason = "button_burned"   # nobody can press it any more
            break

    return {
        "success": reason == "success",
        "reason": reason,
        "steps": len(path) - 1,
        "path": path,
        "deviations": deviations,
        "ms": think_time * 1000,
    }


def is_certain_win(ship, bot_start, button, fire_start):
    """True if the bot has a path that even the fastest possible fire (q = 1)
    can't catch, so it is going to win whatever happens. Two BFSs, no simulation."""
    fire_dist = distance_map(ship, [fire_start], set())
    return fireproof_path(ship, bot_start, button, fire_dist) is not None
