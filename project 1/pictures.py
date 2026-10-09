"""Draws the pictures in the writeup: a ship being generated, Bot 4's heat map,
single trials, and single Bot 4 decisions.

    python pictures.py
"""
import matplotlib
matplotlib.use("Agg")   # save pictures to files without opening a window
import matplotlib.pyplot as plt
import numpy as np

from bots import PENALTY, bot2_path, bot4_path, heat_map
from experiments import FIRE_SEED
from fire import spread_fire
from simulation import run_bot, setup_trial
from ship import Ship

# Colours for the ship pictures, as [red, green, blue] between 0 and 1
BLACK = [0, 0, 0]          # wall
WHITE = [1, 1, 1]          # open tile
ORANGE = [1, 0.6, 0]       # burned, or a dead end
RED = [1, 0, 0]            # burning now
BLUE = [0.2, 0.5, 0.9]     # opened in phase 2

D = 50   # the trials drawn are all from the main run


def path_rows_and_columns(path):
    """Split a path into its rows and its columns, for plt.plot."""
    rows = []
    cols = []
    for r, c in path:
        rows.append(r)
        cols.append(c)
    return rows, cols


def draw_ship_phases():
    """The same 30 x 30 ship after phase 1 and after phase 2."""
    np.random.seed(3)
    ship = Ship(30)

    ship.generate_blocks()
    open_after_phase_1 = ship.open_cells()
    ends = ship.dead_ends()
    picture_1 = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if (r, c) in ends:
                row.append(ORANGE)
            elif ship.grid[r][c].is_open:
                row.append(WHITE)
            else:
                row.append(BLACK)
        picture_1.append(row)

    ship.reduce_dead_ends()
    ends_2 = ship.dead_ends()
    picture_2 = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if (r, c) in ends_2:
                row.append(ORANGE)
            elif ship.grid[r][c].is_open and (r, c) not in open_after_phase_1:
                row.append(BLUE)
            elif ship.grid[r][c].is_open:
                row.append(WHITE)
            else:
                row.append(BLACK)
        picture_2.append(row)

    plt.figure(figsize=(10, 5))
    plt.subplot(1, 2, 1)
    plt.imshow(picture_1)
    plt.title(f"After phase 1: {len(ends)} dead ends")
    plt.axis("off")
    plt.subplot(1, 2, 2)
    plt.imshow(picture_2)
    plt.title(f"After phase 2: {len(ends_2)} dead ends")
    plt.axis("off")
    plt.savefig("plots/ship_phases.png", dpi=120, bbox_inches="tight")
    plt.close()


def heat_colour(heat):
    """White for heat 0, getting more orange as the heat goes up to 1."""
    return [1, 1 - 0.6 * heat, 1 - heat]


def draw_heat_maps(trial_number, fire_steps):
    """The same fire, and the heat map Bot 4 would make from it, for a slow
    fire (q = 0.2) and a fast fire (q = 0.8)."""
    ship, bot_start, button, fire_start = setup_trial(D, trial_number)
    burned_by_step(ship, fire_start, 0.5, FIRE_SEED + trial_number, fire_steps)

    plt.figure(figsize=(10, 5))
    qs = [0.2, 0.8]
    for i in range(len(qs)):
        q = qs[i]
        heat = heat_map(ship, q)
        picture = []
        for r in range(ship.D):
            row = []
            for c in range(ship.D):
                if not ship.grid[r][c].is_open:
                    row.append(BLACK)
                elif ship.grid[r][c].on_fire:
                    row.append(RED)
                else:
                    row.append(heat_colour(heat[r][c]))
            picture.append(row)
        plt.subplot(1, 2, i + 1)
        plt.imshow(picture)
        plt.title(f"Heat map for q = {q}")
        plt.axis("off")
    plt.savefig("plots/heat_maps.png", dpi=120, bbox_inches="tight")
    plt.close()


def burned_by_step(ship, fire_start, q, fire_seed, steps):
    """The tiles that are burning after the fire has spread `steps` times
    (the same fire the bots saw, because it starts from the same seed)."""
    np.random.seed(fire_seed)
    ship.clear()
    ship.tile(fire_start).on_fire = True
    for t in range(steps):
        spread_fire(ship, q)
    return ship.fire_cells()


def draw_trial(q, trial_number):
    """All four bots on one trial: walls black, open tiles white, the tiles
    that burned before the bot's run ended orange, and the bot's path in blue."""
    ship, bot_start, button, fire_start = setup_trial(D, trial_number)
    fire_seed = FIRE_SEED + trial_number
    plt.figure(figsize=(10, 10))
    for bot in [1, 2, 3, 4]:
        result = run_bot(ship, bot_start, button, fire_start, q, bot, fire_seed)
        burned = burned_by_step(ship, fire_start, q, fire_seed, result["steps"])
        picture = []
        for r in range(ship.D):
            row = []
            for c in range(ship.D):
                if not ship.grid[r][c].is_open:
                    row.append(BLACK)
                elif (r, c) in burned:
                    row.append(ORANGE)
                else:
                    row.append(WHITE)
            picture.append(row)

        plt.subplot(2, 2, bot)
        plt.imshow(picture)
        rows, cols = path_rows_and_columns(result["path"])
        plt.plot(cols, rows, color="blue")
        plt.plot(bot_start[1], bot_start[0], "bo")          # where the bot starts
        plt.plot(button[1], button[0], "g*", markersize=12)  # the button
        reason = result["reason"].replace("_", " ")
        plt.title(f"Bot {bot}: {reason} after {result['steps']} steps")
        plt.axis("off")
    plt.savefig(f"plots/q{q}_trial{trial_number}.png", dpi=120, bbox_inches="tight")
    plt.close()


def draw_decision(q, trial_number):
    """Replays Bot 4 until the first move where its plan is longer than the
    shortest path that avoids the fire (Bot 2's choice), then draws that moment:
    the heat map, the shortest path (dashed) and Bot 4's plan (solid)."""
    ship, bot_start, button, fire_start = setup_trial(D, trial_number)
    np.random.seed(FIRE_SEED + trial_number)   # the same fire Bot 4 saw
    ship.clear()
    ship.tile(fire_start).on_fire = True
    pos = bot_start
    move = 1
    while True:
        plan = bot4_path(ship, pos, button, q)
        short = bot2_path(ship, pos, button)
        if plan is None or short is None:
            print(f"Trial {trial_number}, q = {q}: Bot 4 was cut off before it took a longer path")
            return
        if len(plan) > len(short):
            break
        pos = plan[1]
        if pos == button:
            print(f"Trial {trial_number}, q = {q}: Bot 4 never took a longer path than Bot 2")
            return
        spread_fire(ship, q)
        if ship.tile(pos).on_fire:
            print(f"Trial {trial_number}, q = {q}: Bot 4 was caught before it took a longer path")
            return
        move += 1

    burning = ship.fire_cells()
    heat = heat_map(ship, q)
    short_cost = 0
    for r, c in short[1:]:
        short_cost += 1 + PENALTY * heat[r][c]
    plan_cost = 0
    for r, c in plan[1:]:
        plan_cost += 1 + PENALTY * heat[r][c]
    print(f"Trial {trial_number}, q = {q}, move {move}:")
    print(f"  shortest path: {len(short) - 1} steps, cost {short_cost:.1f}")
    print(f"  Bot 4's plan:  {len(plan) - 1} steps, cost {plan_cost:.1f}")

    picture = []
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if not ship.grid[r][c].is_open:
                row.append(BLACK)
            elif (r, c) in burning:
                row.append(RED)
            else:
                row.append(heat_colour(heat[r][c]))
        picture.append(row)

    plt.figure(figsize=(7, 7))
    plt.imshow(picture)
    rows, cols = path_rows_and_columns(short)
    plt.plot(cols, rows, "b--")   # Bot 2's shortest path
    rows, cols = path_rows_and_columns(plan)
    plt.plot(cols, rows, "b-")    # Bot 4's plan
    plt.plot(pos[1], pos[0], "bo")
    plt.plot(button[1], button[0], "g*", markersize=15)

    # Zoom in on the two paths and the fire.
    rows, cols = path_rows_and_columns(plan + short + list(burning))
    plt.xlim(min(cols) - 3, max(cols) + 3)
    plt.ylim(max(rows) + 3, min(rows) - 3)   # row 0 at the top, like the grid
    plt.axis("off")
    plt.title(f"Trial {trial_number}, q = {q}, move {move}\n"
              f"dashed: shortest path, {len(short) - 1} steps, cost {short_cost:.1f}\n"
              f"solid: Bot 4's plan, {len(plan) - 1} steps, cost {plan_cost:.1f}")
    plt.savefig(f"plots/decision_q{q}_trial{trial_number}.png", dpi=120, bbox_inches="tight")
    plt.close()


def main():
    draw_ship_phases()
    draw_heat_maps(463, 15)
    draw_trial(0.3, 463)
    draw_trial(0.2, 2252)
    draw_decision(0.3, 463)
    draw_decision(0.85, 96)
    print("Pictures saved in plots/")


if __name__ == "__main__":
    main()
