from bots import bot1_path
from search import bfs
from simulation import run_bot, setup_trial


def test_bot1_follows_its_first_plan():
    for trial in range(20):
        ship, bot_start, button, fire_start = setup_trial(20, trial)
        ship.clear()
        ship.tile(fire_start).on_fire = True
        plan = bot1_path(ship, bot_start, button)
        result = run_bot(ship, bot_start, button, fire_start, 0.5, 1, trial)
        if plan is not None:
            assert result["path"] == plan[:len(result["path"])]


def test_every_run_follows_the_rules():
    for q in [0.0, 0.2, 0.5, 1.0]:
        for trial in range(25):
            ship, bot_start, button, fire_start = setup_trial(20, trial)
            for bot in [1, 2, 3, 4]:
                result = run_bot(ship, bot_start, button, fire_start, q, bot, trial)
                path = result["path"]
                assert path[0] == bot_start
                assert len(path) == result["steps"] + 1   # one move per time step
                for i in range(len(path) - 1):
                    assert path[i + 1] in ship.neighbors(path[i])
                if result["reason"] == "entered_fire":
                    assert bot == 1   # only Bot 1 ever walks into fire
                if result["success"]:
                    assert path[-1] == button


def test_every_bot_wins_when_the_fire_does_not_spread():
    for trial in range(20):
        ship, bot_start, button, fire_start = setup_trial(20, trial)
        reachable = bfs(ship, bot_start, button, {fire_start}) is not None
        for bot in [1, 2, 3, 4]:
            result = run_bot(ship, bot_start, button, fire_start, 0.0, bot, trial)
            if reachable:
                assert result["reason"] == "success"
            else:
                assert result["reason"] == "trapped"


def test_the_same_fire_seed_gives_the_same_run():
    ship, bot_start, button, fire_start = setup_trial(20, 9)
    first = run_bot(ship, bot_start, button, fire_start, 0.4, 2, 9)
    run_bot(ship, bot_start, button, fire_start, 0.4, 4, 9)
    again = run_bot(ship, bot_start, button, fire_start, 0.4, 2, 9)
    assert first["reason"] == again["reason"]
    assert first["path"] == again["path"]
