"""Running a bot on a trial.

A TRIAL is one complete setup: a ship, the flammability q, the bot's start,
the button, the fire's first tile, and the random generator the fire will use.

ONE TIME STEP (the order the assignment specifies)
    1. The bot decides where to go and moves there.
    2. If it moved onto a burning tile, it fails ("entered_fire").
    3. If it is on the button, it presses it and wins ("success").
    4. Otherwise the fire spreads once.
    5. If the fire reached the bot's tile, it fails ("caught").
    6. If the fire reached the button, nobody can press it any more, so the
       trial ends as a certain loss ("button_burned").
    A bot that has no route left ends the trial too ("trapped"): every route
    to the button runs through fire, and the fire never goes out.

EVERY BOT FACES THE SAME FIRE
    The fire never reacts to the bot, so if two runs start the fire's random
    generator from the same point, they get exactly the same fire. Each run
    takes a fresh copy of the trial's generator (Trial.start), so all the bots
    on a trial face the same fire. Differences between bots then come from
    their decisions, not from luck. (The instructor's guidance suggests
    exactly this: run the bots against the same fire progression.)
"""
import copy
import time

from fire import spread_chances, spread_fire
from planning import bfs_distances, fire_distances, fireproof_path
from ship import Ship

SUCCESS = "success"
ENTERED_FIRE = "entered_fire"    # the bot stepped onto a burning tile
CAUGHT = "caught"                # the fire spread onto the bot's tile
BUTTON_BURNED = "button_burned"  # the button caught fire before the bot got there
TRAPPED = "trapped"              # the bot is alive, but every route to the button is on fire
TIMEOUT = "timeout"              # safety cap, should not happen


class Trial:
    """One configuration. Every bot is run on the same Trial."""

    def __init__(self, ship, q, bot_start, button, fire_start, fire_rng):
        self.ship = ship
        self.q = q
        self.bot_start = bot_start
        self.button = button
        self.fire_start = fire_start
        # Our own copy of the generator, so nothing outside can move it on.
        self.fire_rng = copy.deepcopy(fire_rng)

    @classmethod
    def generate(cls, D, q, rng):
        """A random trial: a new ship, then three different random open tiles
        for the bot, the button and the fire. The fire then keeps drawing from
        the same generator."""
        ship = Ship.generate(D, rng)
        cells = ship.open_cells()
        picks = rng.choice(len(cells), size=3, replace=False)
        bot, button, fire = (cells[i] for i in picks)
        return cls(ship, q, bot, button, fire, rng)

    @property
    def max_steps(self):
        return 10 * len(self.ship.open_cells())

    def start(self):
        """Put the ship in its starting state: bot, button and the first fire
        tile in place, nothing else burning. Returns a fresh copy of the fire's
        random generator, so this run's fire is the same as every other run's."""
        self.ship.clear()
        self.ship.tile(self.bot_start).has_bot = True
        self.ship.tile(self.button).has_button = True
        self.ship.tile(self.fire_start).on_fire = True
        return copy.deepcopy(self.fire_rng)

    def fireproof(self):
        """True if the bot can win for certain from the start: some path to
        the button stays ahead of even the fastest possible fire (q = 1).
        Decided with two BFSs and no simulation."""
        fire_dist = fire_distances(self.ship, [self.fire_start])
        return fireproof_path(self.ship, self.bot_start, self.button, fire_dist) is not None


class Outcome:
    """How one bot did on one trial."""

    def __init__(self, success, reason, steps, path=None, deviations=0, think_ms=0.0):
        self.success = success          # True if the button was pressed
        self.reason = reason            # one of the constants above
        self.steps = steps              # moves made
        self.path = path if path is not None else []   # positions visited (if recorded)
        # Moves Bot 2's rule would never make: ones that don't shorten the
        # distance to the button through tiles that aren't burning.
        self.deviations = deviations
        self.think_ms = think_ms        # time spent inside the bot's reset() and act()


def run_bot(trial, bot, record_path=False, count_deviations=False):
    """Run one bot on one trial, in the order described at the top of this file.

    With count_deviations, also count the moves that Bot 2's rule could not
    have made (see Outcome.deviations). That is how we check whether Bots 3
    and 4 ever actually decide differently from Bot 2."""
    ship = trial.ship
    button = trial.button
    fire_rng = trial.start()
    chance = spread_chances(trial.q)
    pos = trial.bot_start
    path = [pos]
    deviations = 0
    t0 = time.perf_counter()
    bot.reset(ship, button, trial.q)
    think = time.perf_counter() - t0
    t = 0   # number of fire updates so far

    def done(success, reason, steps):
        return Outcome(success, reason, steps, path, deviations, think * 1000)

    while t < trial.max_steps:
        # 1. The bot decides.
        t0 = time.perf_counter()
        nxt = bot.act(pos)
        think += time.perf_counter() - t0
        if nxt is None:
            return done(False, TRAPPED, t)
        if nxt != pos and nxt not in ship.neighbors(pos):
            raise RuntimeError(f"{bot.name} made an illegal move {pos} -> {nxt}")
        if count_deviations:
            dist = bfs_distances(ship, button, restricted=ship.fire_cells())
            if dist[nxt[0]][nxt[1]] != dist[pos[0]][pos[1]] - 1:
                deviations += 1

        # 2-3. The bot moves.
        ship.tile(pos).has_bot = False
        pos = nxt
        ship.tile(pos).has_bot = True
        if record_path:
            path.append(pos)
        if ship.tile(pos).on_fire:
            return done(False, ENTERED_FIRE, t + 1)
        if pos == button:
            return done(True, SUCCESS, t + 1)

        # 4-6. The fire spreads, then check the bot and the button.
        spread_fire(ship, chance, fire_rng)
        t += 1
        if ship.tile(pos).on_fire:
            return done(False, CAUGHT, t)
        if ship.tile(button).on_fire:
            return done(False, BUTTON_BURNED, t)
    return done(False, TIMEOUT, t)


def fire_history(trial, steps):
    """ignite[r][c] = the update at which tile (r, c) caught fire (0 for the
    first fire tile), or None if it hasn't burned within `steps` updates.
    Used to draw pictures of a trial."""
    ship = trial.ship
    fire_rng = trial.start()
    chance = spread_chances(trial.q)
    ignite = [[None] * ship.D for r in range(ship.D)]
    r, c = trial.fire_start
    ignite[r][c] = 0
    for t in range(1, steps + 1):
        for r, c in spread_fire(ship, chance, fire_rng):
            ignite[r][c] = t
    return ignite
