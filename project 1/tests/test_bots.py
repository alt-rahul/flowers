"""Tests for the bots and the planners they use (bots.py, planners.py)."""
import numpy as np
import pytest

from bots import Bot, make_bot
from planners import avoid_fire, avoid_fire_and_neighbors, predicted_fire
from planning import bfs_distances, bfs_path, fire_distances, fireproof_path, with_neighbors
from ship import Ship
from simulation import ENTERED_FIRE, SUCCESS, TRAPPED, Trial, fire_history, run_bot

BOT_SPECS = ["bot1", "bot2", "bot3", "bot4"]


def trials(n, D=20, q=0.3, seed=0):
    for i in range(n):
        yield Trial.generate(D, q, np.random.default_rng([seed, i]))


def corridor(n=12):
    """A ship that is one corridor along the top row: (0, 0) .. (0, n-1)."""
    rows = ["#" * n] * n
    rows[0] = "." * n
    return Ship.from_rows(rows)


def set_fire(ship, *cells):
    ship.clear()
    for pos in cells:
        ship.tile(pos).on_fire = True


# --------------------------------------------------------------- planners --

def test_bot3_falls_back_to_bot2_when_the_buffer_blocks_every_route():
    # A corridor with a side pocket: the fire sits in the pocket, right next
    # to the corridor tile the bot must pass through.
    ship = Ship.from_rows(["#######",
                           "#######",
                           "###.###",
                           ".......",
                           "#######",
                           "#######",
                           "#######"])
    set_fire(ship, (2, 3))
    start, button = (3, 0), (3, 6)
    path = avoid_fire_and_neighbors(ship, start, button, 0.3)
    assert path == avoid_fire(ship, start, button, 0.3)
    assert (3, 3) in path      # it has to walk past the fire


def test_bot3_avoids_the_buffer_when_it_can():
    rng = np.random.default_rng(0)
    for _ in range(20):
        ship = Ship.generate(20, rng)
        cells = ship.open_cells()
        start, button, fire = (cells[i] for i in rng.choice(len(cells), 3, replace=False))
        set_fire(ship, fire)
        buffer = with_neighbors(ship, {fire})
        path = avoid_fire_and_neighbors(ship, start, button, 0.3)
        if path is not None and bfs_path(ship, start, button, buffer):
            assert not buffer & set(path[1:])


def test_predicted_fire_is_not_a_fixed_buffer():
    # Corridor (0, 0) .. (0, 11), fire at (0, 11), q = 0.5, threshold 0.6.
    ship = corridor()
    set_fire(ship, (0, 11))
    # Bot at (0, 9): (0, 10) is next to the fire, but the bot gets there in one
    # step and the fire needs a successful advance first (chance 0.5 < 0.6).
    near = predicted_fire(ship, (0, 9), None, 0.5, threshold=0.6)
    assert (0, 10) not in near
    # Bot at (0, 0): it needs 10 steps to reach (0, 10), by which time the fire
    # has almost surely got there; it reaches (0, 5) in 5 steps, but the fire
    # needs 6 advances in 5 steps, which is impossible.
    far = predicted_fire(ship, (0, 0), None, 0.5, threshold=0.6)
    assert (0, 10) in far and (0, 5) not in far


def test_predicted_fire_is_exact_when_q_is_one():
    # At q = 1 the fire advances every step, so a tile is "predicted fire"
    # exactly when the fire is at most as far from it as the bot is.
    rng = np.random.default_rng(3)
    for _ in range(10):
        ship = Ship.generate(20, rng)
        cells = ship.open_cells()
        start, fire = (cells[i] for i in rng.choice(len(cells), 2, replace=False))
        set_fire(ship, fire)
        danger = predicted_fire(ship, start, None, 1.0, threshold=0.6)
        from_fire = bfs_distances(ship, fire)
        from_bot = bfs_distances(ship, start, restricted={fire})
        for r, c in cells:
            if (r, c) != fire and from_bot[r][c] != float("inf"):
                assert ((r, c) in danger) == (from_fire[r][c] <= from_bot[r][c])


def test_one_step_rule_only_flags_tiles_next_to_the_fire():
    for trial in trials(10, q=0.9, seed=4):
        fire_history(trial, 5)   # leaves the ship's tiles as the fire is after 5 updates
        ship = trial.ship
        danger = predicted_fire(ship, trial.bot_start, trial.button, 0.9, lookahead=False)
        assert danger <= with_neighbors(ship, ship.fire_cells())


# ------------------------------------------------------------------- bots --

def test_bot1_plans_once_and_never_replans():
    for trial in trials(20, q=0.5, seed=1):
        trial.start()
        plan = bfs_path(trial.ship, trial.bot_start, trial.button, trial.ship.fire_cells())
        out = run_bot(trial, make_bot("bot1"), record_path=True)
        if plan is not None:
            assert out.path == plan[:len(out.path)]


@pytest.mark.parametrize("q", [0.2, 0.5])
def test_bot2_never_deviates_from_its_own_rule(q):
    for trial in trials(30, q=q, seed=7):
        assert run_bot(trial, make_bot("bot2"), count_deviations=True).deviations == 0


def test_bot4_without_penalty_behaves_like_bot2():
    # With no penalty every step costs 1, so A* only ever takes steps along
    # a shortest fire-free path: never a move Bot 2's rule couldn't make.
    for trial in trials(30, q=0.3, seed=4):
        out = run_bot(trial, make_bot("bot4:penalty=0"), count_deviations=True)
        assert out.deviations == 0


@pytest.mark.parametrize("q", [0.0, 0.2, 0.5, 1.0])
def test_runs_follow_the_rules(q):
    for trial in trials(25, q=q, seed=2):
        for spec in BOT_SPECS:
            out = run_bot(trial, make_bot(spec), record_path=True)
            assert out.path[0] == trial.bot_start
            assert len(out.path) == out.steps + 1        # one move per time step
            assert out.reason != ENTERED_FIRE or spec == "bot1"   # only Bot 1 walks into fire
            if out.success:
                assert out.path[-1] == trial.button


def test_everyone_wins_without_fire_spread():
    for trial in trials(20, q=0.0, seed=3):
        trial.start()
        reachable = bfs_path(trial.ship, trial.bot_start, trial.button,
                             trial.ship.fire_cells()) is not None
        for spec in BOT_SPECS:
            out = run_bot(trial, make_bot(spec))
            assert out.reason == (SUCCESS if reachable else TRAPPED)


def test_every_run_of_a_trial_sees_the_same_fire():
    trial = next(trials(1, q=0.4, seed=9))
    assert fire_history(trial, 40) == fire_history(trial, 40)
    first = run_bot(trial, make_bot("bot2"), record_path=True)
    run_bot(trial, make_bot("bot4"))
    again = run_bot(trial, make_bot("bot2"), record_path=True)
    assert (first.reason, first.steps, first.path) == (again.reason, again.steps, again.path)


def test_make_bot_parses_options():
    bot = make_bot("bot4:threshold=0.5,penalty=50,lookahead=false,fire_metric=manhattan")
    assert bot.name == "Bot 4"
    assert bot.options == {"threshold": 0.5, "penalty": 50.0, "lookahead": False,
                           "fire_metric": "manhattan"}
    assert make_bot("bot1").replan is False
    assert make_bot("bot2").replan is True


# ------------------------------------------------------------ certain wins --

def follow_fireproof_path(ship, pos, button, q):
    """A planner for the test below: the path the fastest possible fire can't catch."""
    return fireproof_path(ship, pos, button, fire_distances(ship, ship.fire_cells()))


@pytest.mark.parametrize("q", [0.1, 0.4, 0.7, 1.0])
def test_following_the_fireproof_path_always_wins(q):
    # If a trial is a certain win, a bot that plans the fireproof path once and
    # follows it must win against the real fire, whatever q is.
    bot = Bot("fireproof", follow_fireproof_path, replan=False)
    certain = 0
    for trial in trials(40, q=q, seed=6):
        if trial.fireproof():
            certain += 1
            assert run_bot(trial, bot).success
    assert certain > 0


# ------------------------------------------------------ known results --

def test_known_trial_outcomes():
    # Two trials from the main experiment (D = 50, seed 440), with the
    # outcomes recorded in results/main.csv.gz.
    from experiments import trial_rng
    trial = Trial.generate(50, 0.3, trial_rng(440, 0.3, 463))
    out2 = run_bot(trial, make_bot("bot2"))
    out4 = run_bot(trial, make_bot("bot4"))
    assert (out2.reason, out2.steps) == ("trapped", 24)
    assert (out4.reason, out4.steps) == ("success", 27)
