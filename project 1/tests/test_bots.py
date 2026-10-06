import numpy as np
import pytest

from bots import Bot2, Bot3, make_bot
from planning import bfs_path, with_neighbors
from simulation import SUCCESS, TRAPPED, Trial, oracle_steps, run_bot

BOT_SPECS = ["bot1", "bot2", "bot3", "bot4"]


def trials(n, D=20, q=0.3, seed=0):
    for i in range(n):
        yield Trial.generate(D, q, np.random.default_rng([seed, i]))


class CheckedBot2(Bot2):
    """Bot 2 that checks every lazily reused plan against a fresh BFS."""

    def act(self, pos, burning):
        move = super().act(pos, burning)
        fresh = bfs_path(self.ship.neighbors, pos, self.button, burning.tolist())
        assert (fresh is None) == (move is None)
        if fresh is not None:
            assert len(self.path) - self.k + 1 == len(fresh)
        return move


class CheckedBot3(Bot3):
    def act(self, pos, burning):
        move = super().act(pos, burning)
        danger = with_neighbors(burning, self.ship.D).tolist()
        buffered = bfs_path(self.ship.neighbors, pos, self.button, danger)
        assert self.buffered == (buffered is not None)
        fresh = buffered or bfs_path(self.ship.neighbors, pos, self.button, burning.tolist())
        if fresh is not None:
            assert len(self.path) - self.k + 1 == len(fresh)
        return move


@pytest.mark.parametrize("q", [0.1, 0.4, 0.8])
def test_lazy_replanning_matches_full_replanning(q):
    for trial in trials(40, q=q, seed=1):
        run_bot(trial, CheckedBot2())
        run_bot(trial, CheckedBot3())


@pytest.mark.parametrize("q", [0.0, 0.2, 0.5, 1.0])
def test_no_bot_beats_the_clairvoyant_bound(q):
    for trial in trials(40, q=q, seed=2):
        best = oracle_steps(trial)
        for spec in BOT_SPECS:
            out = run_bot(trial, make_bot(spec), record_path=True)
            assert out.path[0] == trial.bot_start
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


def test_bot4_without_risk_matches_bot2_path_lengths():
    for trial in trials(30, q=0.3, seed=4):
        a = run_bot(trial, make_bot("bot2"))
        b = run_bot(trial, make_bot("bot4:risk_weight=0"))
        if a.success and b.success:
            assert a.steps == b.steps


def test_make_bot_parses_options():
    bot = make_bot("bot4:risk_weight=2.5")
    assert bot.risk_weight == 2.5
    assert make_bot("bot2:lazy=false").lazy is False
