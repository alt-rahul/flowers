import numpy as np

from bots import bot1_path
from experiments import trial_rng
from fire import spread_fire
from search import bfs, distance_map, fireproof_path
from simulation import Trial, is_certain_win, reset_trial, run_bot


def some_trials(count, q, seed):
    trials = []
    for i in range(count):
        trials.append(Trial(20, q, np.random.default_rng([seed, i])))
    return trials


def test_bot1_follows_its_first_plan():
    for trial in some_trials(20, 0.5, 1):
        reset_trial(trial)
        plan = bot1_path(trial.ship, trial.bot_start, trial.button)
        result = run_bot(trial, 1)
        if plan is not None:
            assert result["path"] == plan[:len(result["path"])]


def test_bot2_never_leaves_its_own_rule():
    for q in [0.2, 0.5]:
        for trial in some_trials(30, q, 7):
            assert run_bot(trial, 2)["deviations"] == 0


def test_every_run_follows_the_rules():
    for q in [0.0, 0.2, 0.5, 1.0]:
        for trial in some_trials(25, q, 2):
            for bot in [1, 2, 3, 4]:
                result = run_bot(trial, bot)
                path = result["path"]
                assert path[0] == trial.bot_start
                assert len(path) == result["steps"] + 1   # one move per time step
                for i in range(len(path) - 1):
                    assert path[i + 1] in trial.ship.neighbors(path[i])
                if result["reason"] == "entered_fire":
                    assert bot == 1   # only Bot 1 ever walks into fire
                if result["success"]:
                    assert path[-1] == trial.button


def test_every_bot_wins_when_the_fire_does_not_spread():
    for trial in some_trials(20, 0.0, 3):
        reset_trial(trial)
        reachable = bfs(trial.ship, trial.bot_start, trial.button, trial.ship.fire_cells()) is not None
        for bot in [1, 2, 3, 4]:
            result = run_bot(trial, bot)
            if reachable:
                assert result["reason"] == "success"
            else:
                assert result["reason"] == "trapped"


def test_every_run_of_a_trial_sees_the_same_fire():
    trial = some_trials(1, 0.4, 9)[0]
    first = run_bot(trial, 2)
    run_bot(trial, 4)
    again = run_bot(trial, 2)
    assert first["reason"] == again["reason"]
    assert first["path"] == again["path"]


def test_following_the_fireproof_path_always_wins():
    # On a certain-win trial, walking the fireproof path wins against the real
    # fire, whatever q is.
    for q in [0.1, 0.4, 0.7, 1.0]:
        certain = 0
        for trial in some_trials(40, q, 6):
            if not is_certain_win(trial):
                continue
            certain += 1
            ship = trial.ship
            fire_rng = reset_trial(trial)
            fire_dist = distance_map(ship, [trial.fire_start], set())
            path = fireproof_path(ship, trial.bot_start, trial.button, fire_dist)
            for pos in path[1:]:
                assert not ship.tile(pos).on_fire
                if pos == trial.button:
                    break
                spread_fire(ship, q, fire_rng)
                assert not ship.tile(pos).on_fire
        assert certain > 0


def test_a_trial_from_the_main_run():
    # q = 0.3, trial 463 of the main run (D = 50, seed 440), as recorded in
    # results/main.csv.gz.
    trial = Trial(50, 0.3, trial_rng(440, 0.3, 463))
    bot2 = run_bot(trial, 2)
    bot4 = run_bot(trial, 4)
    assert (bot2["reason"], bot2["steps"]) == ("trapped", 24)
    assert (bot4["reason"], bot4["steps"]) == ("success", 27)
