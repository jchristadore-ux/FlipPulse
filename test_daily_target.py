"""Tests for the v10.2.0 owner directive: a daily +3% profit target that halts
trading for the day, and flat risk (no laddering).

Two behaviours under test:

  1. DAILY PROFIT TARGET — daily_profit_target_dollars() is a percentage of the
     balance the day OPENED with; daily_profit_target_check() latches the halt
     the moment today's REALIZED P&L reaches it, notifies once, and the UTC
     rollover clears the halt and re-bases the goal.
  2. FLAT RISK — the stake is always the configured fraction of balance. The
     laddering overlay is gone from the engine, the probation ramp is off by
     default, and recovery defaults to "No Stake Change", so nothing steps the
     dollar risk up or down independently of the balance.

Same import shim as test_bot_engine.py (bot.py needs Kalshi credentials at
import; all persistence is disabled so no state files are written).

Run: pytest test_daily_target.py
"""

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()).decode()

os.environ.setdefault("KALSHI_API_KEY_ID", "test-key")
os.environ.setdefault("KALSHI_PRIVATE_KEY_PEM_B64",
                      base64.b64encode(_PEM.encode()).decode())
os.environ.setdefault("DEMO_MODE", "true")
for _persist in ("RECOVERY_PERSIST", "PROBATION_PERSIST", "BUCKET_PERSIST",
                 "BILLING_PERSIST", "REPORT_PERSIST", "LIFETIME_PERSIST"):
    os.environ.setdefault(_persist, "false")

import bot  # noqa: E402  (env must be set first)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """A fresh trading day at $1,000, target on at 3%, Telegram muted."""
    sent = []
    monkeypatch.setattr(bot.tg, "send_telegram_message",
                        lambda msg, **_k: sent.append(msg) or True)
    monkeypatch.setattr(bot.tg, "send_status_message",
                        lambda msg, **_k: sent.append(msg) or True)
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_ENABLED", True)
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_PCT", 0.03)
    monkeypatch.setattr(bot, "session_start_balance", 1000.0)
    monkeypatch.setattr(bot, "_session_halted", False)
    monkeypatch.setattr(bot, "_halt_reason", "")
    monkeypatch.setattr(bot, "paper_daily_pnl", 0.0)
    monkeypatch.setattr(bot, "live_daily_realized", 0.0)
    monkeypatch.setattr(bot, "DEMO_MODE", True)
    yield sent
    bot._session_halted = False
    bot._halt_reason    = ""


# ── the target amount ────────────────────────────────────────────────────────

def test_target_is_pct_of_the_balance_the_day_opened_with():
    assert bot.daily_profit_target_dollars() == 30.0


def test_target_rebases_with_the_session_start_balance(monkeypatch):
    """Yesterday's profit compounds into today's goal."""
    monkeypatch.setattr(bot, "session_start_balance", 1030.0)
    assert bot.daily_profit_target_dollars() == 30.9


def test_target_zero_when_disabled(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_ENABLED", False)
    assert bot.daily_profit_target_dollars() == 0.0


def test_target_zero_when_pct_is_zero(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_PCT", 0.0)
    assert bot.daily_profit_target_dollars() == 0.0


def test_target_zero_before_a_session_baseline_exists(monkeypatch):
    monkeypatch.setattr(bot, "session_start_balance", 0.0)
    assert bot.daily_profit_target_dollars() == 0.0


# ── the halt ─────────────────────────────────────────────────────────────────

def test_below_target_keeps_trading(monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 29.99)
    assert bot.daily_profit_target_check(1029.99) is True
    assert bot._session_halted is False


def test_reaching_target_halts_the_day(monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    assert bot.daily_profit_target_check(1030.0) is False
    assert bot._session_halted is True
    assert bot._halt_reason == "profit_target"


def test_overshooting_target_halts_the_day(monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 55.0)
    assert bot.daily_profit_target_check(1055.0) is False
    assert bot._session_halted is True


def test_halt_notifies_once(monkeypatch, _clean_state):
    sent = _clean_state
    monkeypatch.setattr(bot, "paper_daily_pnl", 42.0)
    bot.daily_profit_target_check(1042.0)
    bot.daily_profit_target_check(1042.0)      # second cycle: already halted
    hits = [m for m in sent if "DAILY TARGET HIT" in m]
    assert len(hits) == 1
    assert "$30.00" in hits[0]                 # the goal it reports


def test_disabled_target_never_halts(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_ENABLED", False)
    monkeypatch.setattr(bot, "paper_daily_pnl", 500.0)
    assert bot.daily_profit_target_check(1500.0) is True
    assert bot._session_halted is False


def test_losses_never_trip_the_target(monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", -80.0)
    assert bot.daily_profit_target_check(920.0) is True
    assert bot._session_halted is False


def test_progress_is_realized_pnl_not_the_balance_delta(monkeypatch):
    """An open position's cash outlay moves the balance but not realized P&L —
    the v9.3.1 phantom-P&L trap, in the other direction. A $200 balance jump with
    nothing settled must NOT bank the day."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 0.0)
    assert bot.daily_profit_target_check(1200.0) is True
    assert bot._session_halted is False


def test_live_mode_reads_the_live_realized_accumulator(monkeypatch):
    monkeypatch.setattr(bot, "DEMO_MODE", False)
    monkeypatch.setattr(bot, "paper_daily_pnl", 999.0)   # paper figure ignored
    monkeypatch.setattr(bot, "live_daily_realized", 12.0)
    assert bot.today_realized_pnl() == 12.0
    assert bot.daily_profit_target_check(1012.0) is True
    monkeypatch.setattr(bot, "live_daily_realized", 31.5)
    assert bot.daily_profit_target_check(1031.5) is False


def test_an_existing_halt_short_circuits(monkeypatch):
    """A session stop already halted the day — the target check must not
    overwrite the reason with the good-news one."""
    monkeypatch.setattr(bot, "_session_halted", True)
    monkeypatch.setattr(bot, "_halt_reason", "session_stop")
    monkeypatch.setattr(bot, "paper_daily_pnl", 500.0)
    assert bot.daily_profit_target_check(1500.0) is False
    assert bot._halt_reason == "session_stop"


# ── the rollover re-arms the day ─────────────────────────────────────────────

def test_rollover_clears_a_target_halt_and_rebases_the_goal(monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    assert bot.daily_profit_target_check(1030.0) is False
    monkeypatch.setattr(bot, "_session_day", "1999-01-01")   # force a rollover
    monkeypatch.setattr(bot.probation, "start", lambda *a, **k: None)
    assert bot.maybe_roll_session_day(1030.0) is True
    assert bot._session_halted is False
    assert bot._halt_reason == ""
    assert bot.paper_daily_pnl == 0.0
    assert bot.session_start_balance == 1030.0
    assert bot.daily_profit_target_dollars() == 30.9         # 3% of the new open
    assert bot.daily_profit_target_check(1030.0) is True


# ── flat risk: nothing ladders the stake ─────────────────────────────────────

def test_engine_has_no_ladder_wired_in():
    assert not hasattr(bot, "stake_ladder")
    assert not hasattr(bot, "ladder_record")


def test_probation_ramp_off_by_default():
    assert bot.PROBATION_RAMP_ENABLED is False


def test_recovery_defaults_to_no_stake_change():
    assert bot.RECOVERY_NO_STAKE_CHANGE is True


def test_stake_is_the_flat_fraction_of_balance(monkeypatch):
    """The whole directive in one assertion: the stake is the configured
    percentage of the balance, and it moves only when the balance does."""
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.15)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", "/nonexistent/risk.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", "/nonexistent/reserve.json")
    for balance in (100.0, 1000.0, 2500.0):
        assert bot.kelly_bet(0.70, 50, balance) == round(0.10 * balance, 2)


def test_stake_does_not_grow_with_a_hot_streak(monkeypatch):
    """The retired ladder's headline behaviour: a run of wins used to scale the
    stake up to 2x. It must now be identical to the cold-start stake."""
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", "/nonexistent/risk.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", "/nonexistent/reserve.json")
    cold = bot.kelly_bet(0.70, 50, 1000.0)
    for _ in range(25):
        bot.perf_guard_record(True)
    assert bot.kelly_bet(0.70, 50, 1000.0) == cold
