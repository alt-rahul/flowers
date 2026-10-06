"""Tests for the bots and the planners they use (bots.py, planners.py)."""
import numpy as np
import pytest

from bots import make_bot
from planners import avoid_fire, avoid_fire_and_neighbors, predicted_fire
from planning import bfs_distances, bfs_path
from ship import Ship
from simulation import SUCCESS, TRAPPED, Trial, oracle_steps, run_bot

BOT_SPECS = ["bot1", "bot2", "bot3", "bot4", "bot4_forecast"]


def trials(n, D=20, q=0.3, seed=0):
    for i in range(n):
        yield Trial.generate(D, q, np.random.default_rng([seed, i]))


def corridor(n=12):
    """A ship that is one corridor along the top row: cells 0 .. n-1."""
    grid = np.zeros((n, n), dtype=bool)
    grid[0, :] = True
    return Ship(grid)


def fire_at(ship, *cells):
    burning = np.zeros(ship.D * ship.D, dtype=bool)
    burning[list(cells)] = True
    return burning


# --------------------------------------------------------------- planners --

def test_bot3_falls_back_to_bot2_when_the_buffer_blocks_every_route():
    # A corridor with a side pocket: the fire sits in the pocket, right next
    # to the corridor cell the bot must pass through.
    grid = np.zeros((7, 7), dtype=bool)
    grid[3, :] = True          # the corridor
    grid[2, 3] = True          # the pocket
    ship = Ship(grid)
    burning = fire_at(ship, ship.index(2, 3))
    start, button = ship.index(3, 0), ship.index(3, 6)
    path = avoid_fire_and_neighbors(ship, start, button, burning, 0.3)
    assert path == avoid_fire(ship, start, button, burning, 0.3)
    assert ship.index(3, 3) in path      # it has to walk past the fire


def test_bot3_avoids_the_buffer_when_it_can():
    rng = np.random.default_rng(0)
    for _ in range(20):
        ship = Ship.generate(20, rng)
        start, button, fire = (int(c) for c in rng.choice(ship.open_cells, 3, replace=False))
        burning = fire_at(ship, fire)
        path = avoid_fire_and_neighbors(ship, start, button, burning, 0.3)
        buffered_cells = set(ship.neighbors[fire]) | {fire}
        if path is not None and bfs_path(ship.neighbors, start, button,
                                         [c in buffered_cells for c in range(ship.D ** 2)]):
            assert not buffered_cells & set(path[1:])


def test_predicted_fire_is_not_a_fixed_buffer():
    # Corridor 0..11, fire at 11, q = 0.5, threshold 0.6.
    ship = corridor()
    burning = fire_at(ship, 11)
    # Bot at 9: cell 10 is next to the fire, but the bot gets there in one
    # step and the fire needs a successful advance first (chance 0.5 < 0.6).
    near = predicted_fire(ship, 9, -1, burning, 0.5, threshold=0.6)
    assert not near[10]
    # Bot at 0: it needs 10 steps to reach cell 10, by which time the fire has
    # almost surely got there; it reaches cell 5 in 5 steps, but the fire
    # needs 6 advances in 5 steps, which is impossible.
    far = predicted_fire(ship, 0, -1, burning, 0.5, threshold=0.6)
    assert far[10] and not far[5]


def test_predicted_fire_is_exact_when_q_is_one():
    # At q = 1 the fire advances every step, so a cell is "predicted fire"
    # exactly when the fire is at most as far from it as the bot is.
    rng = np.random.default_rng(3)
    for _ in range(10):
        ship = Ship.generate(20, rng)
        start, fire = (int(c) for c in rng.choice(ship.open_cells, 2, replace=False))
        burning = fire_at(ship, fire)
        danger = predicted_fire(ship, start, -1, burning, 1.0, threshold=0.6)
        from_fire = ship.distances_from(fire)
        from_bot = bfs_distances(ship.neighbors, start, burning.tolist())
        for c in ship.open_cells.tolist():
            if c != fire and from_bot[c] != float("inf"):
                assert danger[c] == (from_fire[c] <= from_bot[c])


# ------------------------------------------------------------------- bots --

def test_bot1_plans_once_and_never_replans():
    for trial in trials(20, q=0.5, seed=1):
        plan = bfs_path(trial.ship.neighbors, trial.bot_start, trial.button,
                        trial.fire.burning_at(0).tolist())
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
def test_no_bot_beats_the_clairvoyant_bound(q):
    for trial in trials(40, q=q, seed=2):
        best = oracle_steps(trial)
        for spec in BOT_SPECS:
            out = run_bot(trial, make_bot(spec), record_path=True)
            assert out.path[0] == trial.bot_start
            assert out.reason != "entered_fire" or spec == "bot1"   # only Bot 1 walks into fire
            if out.success:
                assert best is not None and out.steps >= best
                assert out.path[-1] == trial.button


def test_everyone_wins_without_fire_spread():
    for trial in trials(20, q=0.0, seed=3):
        reachable = bfs_path(trial.ship.neighbors, trial.bot_start, trial.button,
                             trial.fire.burning_at(0).tolist()) is not None
        for spec in BOT_SPECS:
            out = run_bot(trial, make_bot(spec))
            assert out.reason == (SUCCESS if reachable else TRAPPED)


def test_make_bot_parses_options():
    bot = make_bot("bot4:threshold=0.5,penalty=50,lookahead=false,fire_metric=manhattan")
    assert bot.name == "Bot 4"
    assert bot.options == {"threshold": 0.5, "penalty": 50.0, "lookahead": False,
                           "fire_metric": "manhattan"}
    assert make_bot("bot1").replan is False
    assert make_bot("bot2").replan is True


# ------------------------------------------------------------ certain wins --

def test_fireproof_matches_clairvoyant_when_fire_is_fastest():
    # At q = 1 the fire spreads at every chance, so "some path outruns the
    # fastest possible fire" must agree exactly with the clairvoyant bot.
    for trial in trials(60, q=1.0, seed=5):
        assert trial.fireproof() == (oracle_steps(trial) is not None)


@pytest.mark.parametrize("q", [0.1, 0.4, 0.7])
def test_fireproof_trials_are_always_winnable(q):
    for trial in trials(40, q=q, seed=6):
        if trial.fireproof():
            assert oracle_steps(trial) is not None


@pytest.mark.parametrize("q", [0.1, 0.5, 0.9])
def test_forecast_bot_wins_every_fireproof_trial(q):
    for trial in trials(40, q=q, seed=8):
        if trial.fireproof():
            assert run_bot(trial, make_bot("bot4_forecast")).success
