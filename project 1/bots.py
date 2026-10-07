"""The bots: one Bot class, and a table saying how each bot is built.

A bot is just:
    a name           e.g. "Bot 2"
    a planner        a function from planners.py that returns a path
    replan           True: ask the planner again every step
                     False: plan once at the start, then follow that plan
    options          extra settings passed to the planner (e.g. Bot 4's threshold)

The simulator (simulation.run_bot) talks to every bot the same way:
    bot.reset(ship, button, q)    once, when a trial starts
    bot.act(pos)                  every step; returns the next position, or
                                  None if no route to the button avoids the fire
The bot sees the fire by looking at the ship's tiles (tile.on_fire). Because the
fire never shrinks, None means the bot can never win, so the simulator ends the
trial as "trapped".
"""
from planners import avoid_fire, avoid_fire_and_neighbors, avoid_predicted_fire


class Bot:
    def __init__(self, name, planner, replan=True, **options):
        # **options collects any extra keyword arguments into a dictionary,
        # e.g. Bot("Bot 4", avoid_predicted_fire, threshold=0.5) gives
        # options = {"threshold": 0.5}.
        self.name = name
        self.planner = planner
        self.replan = replan
        self.options = options

    def reset(self, ship, button, q):
        """Forget everything from the previous trial."""
        self.ship = ship
        self.button = button
        self.q = q
        self.path = None   # the plan being followed
        self.k = 0         # index of the bot's current position in self.path

    def act(self, pos):
        """Return the next position to move to, or None if there is no route."""
        if self.replan or self.path is None:
            # **self.options passes the dictionary back as keyword arguments.
            self.path = self.planner(self.ship, pos, self.button, self.q, **self.options)
            self.k = 0
            if self.path is None:
                return None
        self.k += 1
        return self.path[self.k]   # path[0] is where the bot stands now


# How each bot is built: (display name, planner, replan every step?)
BOTS = {
    # Bot 1: plan the shortest path once, avoiding the initial fire tile (the
    # only tile burning at the start), then follow it whatever the fire does.
    "bot1": ("Bot 1", avoid_fire, False),
    # Bot 2: every step, the shortest path that avoids the tiles burning now.
    "bot2": ("Bot 2", avoid_fire, True),
    # Bot 3: every step, also avoid tiles next to the fire if possible,
    # otherwise fall back to Bot 2's planner.
    "bot3": ("Bot 3", avoid_fire_and_neighbors, True),
    # Bot 4: every step, A* that avoids the fire and penalises tiles the fire
    # will probably reach before the bot does.
    "bot4": ("Bot 4", avoid_predicted_fire, True),
}


def parse_value(text):
    """'true'/'false' -> bool, numbers -> float, anything else stays text."""
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    try:
        return float(text)
    except ValueError:
        return text


def make_bot(spec):
    """Build a bot from a spec like "bot3" or "bot4:threshold=0.5,penalty=50".
    Options after the colon are passed to the bot's planner."""
    name, _, args = spec.partition(":")
    options = {}
    for item in args.split(","):
        if item:
            key, _, value = item.partition("=")
            options[key] = parse_value(value)
    label, planner, replan = BOTS[name]
    return Bot(label, planner, replan, **options)
