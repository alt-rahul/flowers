"""Running one bot on one trial."""
import copy
import time

from bots import bot1_path, bot2_path, bot3_path, bot4_path
from fire import spread_fire
from search import distance_map, fireproof_path
from ship import generate_ship


class Trial:
    """One setup: a ship, where the bot, the button and the first fire start,
    and the random numbers the fire will use."""

    def __init__(self, D, q, rng):
        self.q = q
        self.ship = generate_ship(D, rng)
        cells = self.ship.open_cells()
        picks = rng.choice(len(cells), size=3, replace=False)   # three different open tiles
        self.bot_start = cells[picks[0]]
        self.button = cells[picks[1]]
        self.fire_start = cells[picks[2]]
        # Save the random generator as it is now. Every run of this trial
        # starts the fire from a copy of it, so every bot faces the same fire.
        self.fire_rng = copy.deepcopy(rng)


def reset_trial(trial):
    """Put the bot, the button and the first fire back where they start, with
    nothing else burning. Returns a fresh copy of the fire's random generator."""
    ship = trial.ship
    ship.clear()
    ship.tile(trial.bot_start).has_bot = True
    ship.tile(trial.button).has_button = True
    ship.tile(trial.fire_start).on_fire = True
    return copy.deepcopy(trial.fire_rng)


def run_bot(trial, bot):
    """Run Bot 1, 2, 3 or 4 on a trial. Each time step, in order:
    the bot decides and moves; if it is on the button it wins; otherwise the
    fire spreads, and the bot fails if the fire reaches it or the button.

    Returns a dictionary with:
        success     True if the button was pressed
        reason      success, entered_fire, caught, button_burned, trapped or timeout
        steps       how many moves the bot made
        path        every position the bot was on
        deviations  moves Bot 2's rule could not have made
        ms          time spent deciding, in milliseconds
    """
    ship = trial.ship
    button = trial.button
    fire_rng = reset_trial(trial)
    pos = trial.bot_start
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
            plan = bot4_path(ship, pos, button, trial.q)
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
        spread_fire(ship, trial.q, fire_rng)
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


def is_certain_win(trial):
    """True if the bot has a path that even the fastest possible fire (q = 1)
    can't catch, so it is going to win whatever happens. Two BFSs, no simulation."""
    fire_dist = distance_map(trial.ship, [trial.fire_start], set())
    return fireproof_path(trial.ship, trial.bot_start, trial.button, fire_dist) is not None
