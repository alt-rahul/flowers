"""Show one of Bot 4's real decisions: what it predicted and which path it chose.

Replays Bot 4 on a trial until the first move where its plan is longer than
the shortest fire-free path (the shortest path is what Bot 2 would take), so
the bot is genuinely trading length for safety. Then it draws the ship at
that moment, with the burning tiles, the tiles Bot 4 predicted would be on
fire, and both paths on top, and prints the numbers Bot 4 compared.

    python decision.py --D 50 --q 0.3 --trial 5 --out results/examples/decision.png
"""
import argparse

import matplotlib
matplotlib.use("Agg")   # draw straight to PNG files, no window
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

from bots import make_bot
from experiments import trial_rng
from planners import avoid_fire, avoid_predicted_fire, predicted_fire
from fire import spread_chances, spread_fire
from simulation import Trial


def path_numbers(path, danger, penalty):
    """Steps, predicted-fire tiles on the path, and the A* cost Bot 4 gives it."""
    steps = len(path) - 1
    flagged = sum(1 for pos in path[1:] if pos in danger)
    return {"steps": steps, "flagged": flagged, "cost": steps + penalty * flagged}


def find_decision(trial, options):
    """Replay Bot 4 until it first prefers a longer path. Returns (t, pos,
    plan, short) and leaves the ship's tiles as they were at that moment, or
    returns None if that never happens."""
    ship, button, q = trial.ship, trial.button, trial.q
    fire_rng = trial.start()
    chance = spread_chances(q)
    pos, t = trial.bot_start, 0
    while True:
        plan = avoid_predicted_fire(ship, pos, button, q, **options)
        short = avoid_fire(ship, pos, button, q)
        if plan is None or short is None:
            return None
        if len(plan) > len(short):
            return t, pos, plan, short
        ship.tile(pos).has_bot = False
        pos = plan[1]
        ship.tile(pos).has_bot = True
        if pos == button:
            return None
        spread_fire(ship, chance, fire_rng)
        t += 1
        if ship.tile(pos).on_fire:
            return None


def draw(trial, pos, burning, danger, plan, short, nums, out, title):
    """The ship at the moment of the decision: walls black, floor white,
    burning tiles red, predicted-fire tiles yellow; Bot 2's shortest path
    dashed and Bot 4's plan solid. Zoomed to the part that matters, with the
    legend to the right."""
    ship = trial.ship
    colors = ListedColormap(["black", "white", "gold", "red"])   # wall, floor, predicted, burning
    picture = []
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
    plt.imshow(picture, cmap=colors, vmin=0, vmax=3)
    plt.plot([c for r, c in short], [r for r, c in short], "b--", linewidth=2,
             label=f"shortest path (Bot 2): {nums['short']['steps']} steps, "
                   f"{nums['short']['flagged']} predicted-fire tiles")
    plt.plot([c for r, c in plan], [r for r, c in plan], "b-", linewidth=2,
             label=f"Bot 4's plan: {nums['plan']['steps']} steps, "
                   f"{nums['plan']['flagged']} predicted-fire tiles")
    plt.plot(pos[1], pos[0], "bo", markersize=9, label="bot")
    plt.plot(trial.button[1], trial.button[0], "g*", markersize=15, label="button")

    # Zoom to both paths and the fire.
    cells = plan + short + list(burning)
    rows = [r for r, c in cells]
    cols = [c for r, c in cells]
    plt.xlim(min(cols) - 3, max(cols) + 3)
    plt.ylim(max(rows) + 3, min(rows) - 3)   # row 0 at the top, like the grid
    plt.axis("off")
    plt.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9)
    plt.title(title)
    plt.savefig(out, dpi=120, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--D", type=int, default=50)
    parser.add_argument("--q", type=float, required=True)
    parser.add_argument("--seed", type=int, default=440)
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--bot", default="bot4", help="a Bot 4 spec, e.g. bot4:threshold=0.5")
    parser.add_argument("--out", default="decision.png")
    args = parser.parse_args()

    options = make_bot(args.bot).options
    threshold = options.get("threshold", 0.6)
    penalty = options.get("penalty", 20.0)
    trial = Trial.generate(args.D, args.q, trial_rng(args.seed, args.q, args.trial))
    found = find_decision(trial, options)
    if found is None:
        raise SystemExit("Bot 4 never preferred a longer path on this trial")
    t, pos, plan, short = found
    lookahead = options.get("lookahead", True)
    fire_metric = options.get("fire_metric", "maze")
    burning = trial.ship.fire_cells()
    danger = predicted_fire(trial.ship, pos, trial.button, trial.q, threshold,
                            lookahead, fire_metric)
    nums = {"short": path_numbers(short, danger, penalty),
            "plan": path_numbers(plan, danger, penalty)}
    for name in ("short", "plan"):
        n = nums[name]
        print(f"{name:5s}: {n['steps']} steps, {n['flagged']} predicted-fire tiles, "
              f"cost {n['cost']:g}")
    title = (f"Bot 4's decision at move {t + 1}: trial {args.trial}, q = {args.q:g}, "
             f"D = {args.D}")
    draw(trial, pos, burning, danger, plan, short, nums, args.out, title)
    print(f"move {t + 1} -> {args.out}")


if __name__ == "__main__":
    main()
