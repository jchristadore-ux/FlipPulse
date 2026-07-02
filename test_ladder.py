"""Tests for the ladder's drawdown guard: the trigger is a FRACTION of the
current balance (v10 percentage sizing), not a fixed dollar figure — a $15
default tripped on the first loss for any real balance and permanently held
the ladder at 1x.

Run: pytest test_ladder.py
"""

from ladder import LadderConfig, StakeLadder


def _hot_ladder(**cfg_overrides) -> StakeLadder:
    """A ladder past warm-up with a hot win rate, so the tier wants to size up
    and the drawdown guard is the only thing that can hold it at baseline."""
    cfg = LadderConfig(window=20, min_trades=10, cooldown_secs=0,
                       cooldown_cycles=0, persist=False, **cfg_overrides)
    ladder = StakeLadder(cfg=cfg, clock=lambda: 1_700_000_000.0)
    for _ in range(12):
        ladder.tracker.record(True)        # 100% WR → T5 wants 2.0x
    return ladder


def test_percentage_drawdown_scales_with_balance():
    ladder = _hot_ladder()                  # default: 20% of balance
    ladder.daily_pnl = -1000.0
    # $10k balance → cap $2000 → a $1000 day is fine, tier sizes up.
    assert ladder.get_stake(100.0, balance=10_000.0).multiplier == 2.0
    # $4k balance → cap $800 → the same $1000 day trips the revert.
    d = ladder.get_stake(100.0, balance=4_000.0)
    assert d.multiplier == 1.0
    assert "DRAWDOWN" in d.reason


def test_dollar_override_wins_over_percentage():
    ladder = _hot_ladder(max_daily_loss=50.0)
    ladder.daily_pnl = -60.0
    # 20% of $10k would allow -$2000, but the explicit $50 override trips first.
    d = ladder.get_stake(100.0, balance=10_000.0)
    assert d.multiplier == 1.0
    assert "DRAWDOWN" in d.reason


def test_no_balance_and_no_override_disables_drawdown_guard():
    """Callers that can't supply a balance (and set no dollar override) get no
    drawdown clamp — the other guardrails (streak, ceiling) still apply."""
    ladder = _hot_ladder()
    ladder.daily_pnl = -10_000.0
    assert ladder.get_stake(100.0).multiplier == 2.0


def test_pause_action_zeroes_stake():
    ladder = _hot_ladder(drawdown_action="pause")
    ladder.daily_pnl = -300.0
    d = ladder.get_stake(100.0, balance=1_000.0)   # cap $200 → paused
    assert d.stake == 0.0
    assert d.tier == "PAUSED"
