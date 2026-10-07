"""Draws the pictures in the writeup: a ship being generated, Bot 4's danger
radius, single trials, and single Bot 4 decisions.

    python pictures.py
"""
import matplotlib
matplotlib.use("Agg")   # save pictures to files without opening a window
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from bots import THRESHOLD, bot2_path, bot4_path, danger_radius, predicted_fire
from experiments import trial_rng
from fire import spread_fire
from simulation import Trial, reset_trial, run_bot
from ship import Ship

# The trials to draw (all from the main run: D = 50, seed 440)
D = 50
SEED = 440
TRIAL_PICTURES = [(0.3, 463), (0.2, 2252), (0.85, 96)]   # (q, trial number)
DECISION_PICTURES = [(0.3, 463), (0.85, 96)]


def draw_ship_phases():
    """The same 30 x 30 ship after phase 1 and after phase 2."""
    D = 30
    rng = np.random.default_rng(3)
    ship = Ship(D)
    ship.grow_maze(rng)
    open_after_phase_1 = [[ship.grid[r][c].is_open for c in range(D)] for r in range(D)]
    ends_after_phase_1 = ship.dead_ends()
    ship.reduce_dead_ends(rng)
    ends_after_phase_2 = ship.dead_ends()

    # 0 = wall, 1 = open, 2 = dead end, 3 = opened in phase 2
    picture_1 = []
    picture_2 = []
    for r in range(D):
        row_1 = []
        row_2 = []
        for c in range(D):
            if not open_after_phase_1[r][c]:
                row_1.append(0)
            elif (r, c) in ends_after_phase_1:
                row_1.append(2)
            else:
                row_1.append(1)

            if not ship.grid[r][c].is_open:
                row_2.append(0)
            elif (r, c) in ends_after_phase_2:
                row_2.append(2)
            elif not open_after_phase_1[r][c]:
                row_2.append(3)
            else:
                row_2.append(1)
        picture_1.append(row_1)
        picture_2.append(row_2)

    colors = ListedColormap(["black", "white", "#eb6834", "#2a78d6"])
    fig, axes = plt.subplots(1, 2, figsize=(10, 5.4))
    axes[0].imshow(picture_1, cmap=colors, vmin=0, vmax=3)
    axes[0].set_title(f"After phase 1: {len(ends_after_phase_1)} dead ends")
    axes[1].imshow(picture_2, cmap=colors, vmin=0, vmax=3)
    axes[1].set_title(f"After phase 2: {len(ends_after_phase_2)} dead ends")
    axes[0].axis("off")
    axes[1].axis("off")
    fig.legend(handles=[Patch(color="#eb6834", label="dead end"),
                        Patch(color="#2a78d6", label="opened in phase 2")],
               loc="lower center", ncol=2, frameon=False)
    plt.savefig("results/ship_phases.png", dpi=120, bbox_inches="tight")
    plt.close()


def draw_danger_radius():
    """For a tile the bot needs k moves to reach: the largest fire distance d
    at which Bot 4 treats it as predicted fire, for several values of q."""
    qs = [0.1, 0.2, 0.3, 0.5, 0.8]
    shades = ["#b9b2e3", "#9a91d0", "#7b6fc0", "#5e4fb0", "#3d2c96"]
    ks = list(range(41))
    plt.figure(figsize=(8, 5))
    for i in range(len(qs)):
        radius = danger_radius(qs[i], THRESHOLD, 40)
        plt.plot(ks, radius, drawstyle="steps-post", color=shades[i], linewidth=2,
                 label=f"Bot 4, q = {qs[i]:g}")
    plt.axhline(1, color="#1baf7a", linestyle="--", linewidth=2,
                label="Bot 3's buffer (d = 1 at every k)")
    plt.xlabel("Moves the bot needs to reach the cell (k)")
    plt.ylabel("Largest fire distance d treated as fire")
    plt.title("Which cells Bot 4 treats as predicted fire (threshold 0.6)")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.savefig("results/danger_radius.png", dpi=120, bbox_inches="tight")
    plt.close()


def burned_by_step(trial, steps):
    """The tiles that are burning after the fire has spread `steps` times."""
    fire_rng = reset_trial(trial)
    for t in range(steps):
        spread_fire(trial.ship, trial.q, fire_rng)
    return trial.ship.fire_cells()


def draw_trial(q, trial_number):
    """All four bots on one trial: walls black, floor white, the tiles that
    burned by the end of the bot's run orange, and the bot's path in blue."""
    trial = Trial(D, q, trial_rng(SEED, q, trial_number))
    ship = trial.ship
    colors = ListedColormap(["black", "white", "orange"])   # 0 wall, 1 floor, 2 burned
    fig, axes = plt.subplots(2, 2, figsize=(10, 11))
    for bot in [1, 2, 3, 4]:
        ax = axes[(bot - 1) // 2][(bot - 1) % 2]
        result = run_bot(trial, bot)
        burned = burned_by_step(trial, result["steps"])
        picture = []
        for r in range(ship.D):
            row = []
            for c in range(ship.D):
                if not ship.grid[r][c].is_open:
                    row.append(0)
                elif (r, c) in burned:
                    row.append(2)
                else:
                    row.append(1)
            picture.append(row)
        ax.imshow(picture, cmap=colors, vmin=0, vmax=2)
        path = result["path"]
        ax.plot([c for r, c in path], [r for r, c in path], color="blue", linewidth=2)
        ax.plot(trial.bot_start[1], trial.bot_start[0], "bo", markersize=8, label="bot start")
        ax.plot(trial.button[1], trial.button[0], "g*", markersize=14, label="button")
        ax.plot(trial.fire_start[1], trial.fire_start[0], "rx", markersize=10, mew=3, label="fire start")
        verdict = result["reason"].replace("_", " ")
        ax.set_title(f"Bot {bot}: {verdict} after {result['steps']} steps")
        ax.axis("off")
    axes[0][0].legend(loc="upper left", fontsize=8)
    fig.suptitle(f"Trial {trial_number}, D = {D}, q = {q:g}")
    fig.tight_layout()
    fig.savefig(f"results/examples/q{q:g}_trial{trial_number}.png", dpi=120)
    plt.close(fig)


def draw_decision(q, trial_number):
    """Replays Bot 4 until the first move where its plan is longer than the
    shortest path that avoids the fire (Bot 2's choice), then draws that moment:
    burning tiles red, predicted-fire tiles yellow, Bot 2's path dashed and Bot
    4's plan solid."""
    trial = Trial(D, q, trial_rng(SEED, q, trial_number))
    ship = trial.ship
    fire_rng = reset_trial(trial)
    pos = trial.bot_start
    move = 1
    while True:
        plan = bot4_path(ship, pos, trial.button, q)
        short = bot2_path(ship, pos, trial.button)
        if len(plan) > len(short):
            break
        pos = plan[1]
        spread_fire(ship, q, fire_rng)
        move += 1

    burning = ship.fire_cells()
    danger = predicted_fire(ship, pos, trial.button, q, THRESHOLD)
    short_flagged = len([p for p in short[1:] if p in danger])
    plan_flagged = len([p for p in plan[1:] if p in danger])
    print(f"Trial {trial_number}, q = {q:g}, move {move}:")
    print(f"  shortest path: {len(short) - 1} steps, {short_flagged} predicted-fire tiles")
    print(f"  Bot 4's plan:  {len(plan) - 1} steps, {plan_flagged} predicted-fire tiles")

    picture = []   # 0 wall, 1 floor, 2 predicted fire, 3 burning
    for r in range(ship.D):
        row = []
        for c in range(ship.D):
            if not ship.grid[r][c].is_open:
                row.append(0)
            elif (r, c) in burning:
                row.append(3)
            elif (r, c) in danger:
                row.append(2)
            else:
                row.append(1)
        picture.append(row)

    plt.figure(figsize=(7, 7))
    plt.imshow(picture, cmap=ListedColormap(["black", "white", "gold", "red"]), vmin=0, vmax=3)
    plt.plot([c for r, c in short], [r for r, c in short], "b--", linewidth=2,
             label=f"shortest path (Bot 2): {len(short) - 1} steps, {short_flagged} predicted-fire tiles")
    plt.plot([c for r, c in plan], [r for r, c in plan], "b-", linewidth=2,
             label=f"Bot 4's plan: {len(plan) - 1} steps, {plan_flagged} predicted-fire tiles")
    plt.plot(pos[1], pos[0], "bo", markersize=9, label="bot")
    plt.plot(trial.button[1], trial.button[0], "g*", markersize=15, label="button")

    # Zoom in on the two paths and the fire (row 0 at the top, like the grid).
    cells = plan + short + list(burning)
    rows = [r for r, c in cells]
    cols = [c for r, c in cells]
    plt.xlim(min(cols) - 3, max(cols) + 3)
    plt.ylim(max(rows) + 3, min(rows) - 3)
    plt.axis("off")
    plt.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
    plt.title(f"Bot 4's decision at move {move}: trial {trial_number}, q = {q:g}, D = {D}")
    plt.savefig(f"results/examples/decision_q{q:g}_trial{trial_number}.png", dpi=120, bbox_inches="tight")
    plt.close()


def main():
    draw_ship_phases()
    draw_danger_radius()
    for q, trial_number in TRIAL_PICTURES:
        draw_trial(q, trial_number)
    for q, trial_number in DECISION_PICTURES:
        draw_decision(q, trial_number)
    print("Pictures saved in results/ and results/examples/")


if __name__ == "__main__":
    main()
