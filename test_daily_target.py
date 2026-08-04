"""Tests for the v10.2.0 owner directive: a daily +3% profit target that halts
trading for the day, and flat risk (no laddering).

Three behaviours under test:

  1. DAILY PROFIT TARGET — daily_profit_target_dollars() is a percentage of the
     balance the day OPENED with; daily_profit_target_check() latches the halt
     the moment today's REALIZED P&L reaches it, notifies once, and the UTC
     rollover clears the halt and re-bases the goal.
  2. FLAT RISK — the stake is always the configured fraction of balance. The
     laddering overlay is gone from the engine, the probation ramp is off by
     default, and recovery defaults to "No Stake Change", so nothing steps the
     dollar risk up or down independently of the balance.
  3. RESTART SURVIVAL (v10.3.1) — the halt, the day's opening balance and
     today's realized P&L are persisted and restored at boot, so a redeploy or
     crash cannot clear a banked target and start a second +3% hunt on the same
     UTC day. A record from another day, or from the other trading mode, is
     ignored.

Same import shim as test_bot_engine.py (bot.py needs Kalshi credentials at
import; all persistence is disabled so no state files are written).

Run: pytest test_daily_target.py
"""

import base64
import json
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
                 "BILLING_PERSIST", "REPORT_PERSIST", "LIFETIME_PERSIST",
                 "DAILY_STATE_PERSIST"):
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


# ── the day's state survives a restart (v10.3.1) ─────────────────────────────

@pytest.fixture
def _daily_state(monkeypatch, tmp_path):
    """Persistence pointed at a tmp file, with today's date as the session day."""
    path = tmp_path / "daily_state.json"
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", str(path))
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "_session_day", bot.datetime.now(bot.timezone.utc)
                        .strftime("%Y-%m-%d"))
    return path


def _boot_fresh(monkeypatch, balance):
    """Simulate what main() sets up before restore_daily_state() runs."""
    monkeypatch.setattr(bot, "_session_halted", False)
    monkeypatch.setattr(bot, "_halt_reason", "")
    monkeypatch.setattr(bot, "session_start_balance", balance)
    monkeypatch.setattr(bot, "session_stop_threshold",
                        balance * bot.SESSION_STOP_FRACTION)
    monkeypatch.setattr(bot, "paper_daily_pnl", 0.0)
    monkeypatch.setattr(bot, "live_daily_realized", 0.0)


def test_halt_is_written_the_moment_it_latches(_daily_state, monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    assert bot.daily_profit_target_check(1030.0) is False
    saved = json.loads(_daily_state.read_text())
    assert saved["halted"] is True
    assert saved["halt_reason"] == "profit_target"
    assert saved["session_start_balance"] == 1000.0
    assert saved["paper_daily_pnl"] == 30.0


def test_restart_resumes_a_banked_day(_daily_state, monkeypatch):
    """The whole point: the bot banks +3%, is restarted at a HIGHER balance, and
    must come back halted with the day's ORIGINAL opening balance — not a fresh
    3% budget measured off the profit it just made."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)

    _boot_fresh(monkeypatch, 1030.0)               # boot re-reads the live balance
    assert bot.restore_daily_state(1030.0) is True
    assert bot._session_halted is True
    assert bot._halt_reason == "profit_target"
    assert bot.session_start_balance == 1000.0     # NOT re-based to 1030
    assert bot.daily_profit_target_dollars() == 30.0
    assert bot.paper_daily_pnl == 30.0
    assert bot.daily_profit_target_check(1030.0) is False


def test_restart_restores_the_session_stop_floor(_daily_state, monkeypatch):
    """The floor is 40% of the day's OPENING balance; a restart must not re-arm
    it against a balance the day's trading already moved."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)
    _boot_fresh(monkeypatch, 1030.0)
    bot.restore_daily_state(1030.0)
    assert bot.session_stop_threshold == 1000.0 * bot.SESSION_STOP_FRACTION


def test_restart_mid_day_below_target_keeps_trading(_daily_state, monkeypatch):
    """Restoring is not halting: a day that had NOT hit the goal resumes trading
    with its progress intact."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 12.0)
    bot.save_daily_state()
    _boot_fresh(monkeypatch, 1012.0)
    assert bot.restore_daily_state(1012.0) is True
    assert bot._session_halted is False
    assert bot.paper_daily_pnl == 12.0             # progress carried, not zeroed
    assert bot.daily_profit_target_check(1012.0) is True


def test_yesterdays_record_is_ignored(_daily_state, monkeypatch):
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)
    monkeypatch.setattr(bot, "_session_day", "2099-12-31")   # a different day
    _boot_fresh(monkeypatch, 1030.0)
    assert bot.restore_daily_state(1030.0) is False
    assert bot._session_halted is False
    assert bot.session_start_balance == 1030.0
    assert bot.paper_daily_pnl == 0.0


def test_the_other_modes_record_is_ignored(_daily_state, monkeypatch):
    """A paper day's P&L must never halt the live account (or vice-versa) —
    they are different books."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)          # written in PAPER mode
    monkeypatch.setattr(bot, "DEMO_MODE", False)   # ...restarted into LIVE
    _boot_fresh(monkeypatch, 1030.0)
    assert bot.restore_daily_state(1030.0) is False
    assert bot._session_halted is False
    assert bot.session_start_balance == 1030.0


def test_rollover_overwrites_the_record(_daily_state, monkeypatch):
    """A finished day can never be resurrected: the rollover rewrites the file
    with the new day's baseline before the next cycle can restart."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)
    monkeypatch.setattr(bot, "_session_day", "1999-01-01")   # force a rollover
    monkeypatch.setattr(bot.probation, "start", lambda *a, **k: None)
    assert bot.maybe_roll_session_day(1030.0) is True
    saved = json.loads(_daily_state.read_text())
    assert saved["halted"] is False
    assert saved["halt_reason"] == ""
    assert saved["session_start_balance"] == 1030.0
    assert saved["day"] == bot.datetime.now(bot.timezone.utc).strftime("%Y-%m-%d")


def test_a_corrupt_record_never_blocks_boot(_daily_state, monkeypatch):
    _daily_state.write_text("{not json")
    _boot_fresh(monkeypatch, 1030.0)
    assert bot.restore_daily_state(1030.0) is False
    assert bot._session_halted is False


def test_a_missing_record_never_blocks_boot(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", str(tmp_path / "absent.json"))
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    _boot_fresh(monkeypatch, 1030.0)
    assert bot.restore_daily_state(1030.0) is False
    assert bot._session_halted is False


def test_an_unwritable_path_never_stops_trading(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", "/nonexistent-dir/daily.json")
    bot.save_daily_state()                          # must not raise
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    assert bot.daily_profit_target_check(1030.0) is False
    assert bot._session_halted is True


def test_persistence_off_is_a_clean_no_op(monkeypatch, tmp_path):
    path = tmp_path / "daily_state.json"
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", str(path))
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", False)
    bot.save_daily_state()
    assert not path.exists()
    assert bot.restore_daily_state(1000.0) is False


def test_live_mode_round_trips_the_live_accumulator(_daily_state, monkeypatch):
    monkeypatch.setattr(bot, "DEMO_MODE", False)
    monkeypatch.setattr(bot, "live_daily_realized", 30.0)
    assert bot.daily_profit_target_check(1030.0) is False
    _boot_fresh(monkeypatch, 1030.0)
    assert bot.restore_daily_state(1030.0) is True
    assert bot.live_daily_realized == 30.0
    assert bot.today_realized_pnl() == 30.0
    assert bot._session_halted is True


# ── second layer: rebuild the day from the exchange (v10.3.2) ────────────────

def _settlement(pnl_dollars, when=None):
    """A settlement record in the real KXBTC15M schema: revenue is in CENTS,
    costs and fees in dollars (see _extract_realized_dollars)."""
    when = when or bot.datetime.now(bot.timezone.utc)
    return {
        "ticker": "KXBTC15M-TEST",
        "settled_time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "revenue": (pnl_dollars + 1.0) * 100,     # cost is $1.00, so pnl = revenue/100 - 1
        "yes_total_cost_dollars": 1.0,
        "no_total_cost_dollars": 0.0,
        "fee_cost": 0.0,
    }


@pytest.fixture
def _live_boot(monkeypatch, tmp_path):
    """LIVE mode, no local daily record — the state the fallback exists for."""
    monkeypatch.setattr(bot, "DEMO_MODE", False)
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", str(tmp_path / "daily_state.json"))
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "_session_day", bot.datetime.now(bot.timezone.utc)
                        .strftime("%Y-%m-%d"))
    monkeypatch.setattr(bot, "_session_halted", False)
    monkeypatch.setattr(bot, "_halt_reason", "")
    monkeypatch.setattr(bot, "live_daily_realized", 0.0)


def test_no_local_record_rebuilds_the_day_from_the_exchange(_live_boot, monkeypatch):
    """The case that bit us live: the redeploy that first shipped persistence had
    no file to read. Today's settlements still prove the goal was banked."""
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(1.23), _settlement(0.74)])
    monkeypatch.setattr(bot, "session_start_balance", 61.24)   # fresh-boot value
    assert bot.reconcile_today_from_exchange(61.24) is True
    assert bot.live_daily_realized == 1.97
    assert bot.session_start_balance == 59.27      # inferred day-open, not 61.24
    assert bot.daily_profit_target_dollars() == 1.78
    assert bot._session_halted is True
    assert bot._halt_reason == "profit_target"


def test_rebuilt_day_below_target_keeps_trading(_live_boot, monkeypatch):
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(0.50)])
    monkeypatch.setattr(bot, "session_start_balance", 59.77)
    assert bot.reconcile_today_from_exchange(59.77) is True
    assert bot.live_daily_realized == 0.50
    assert bot.session_start_balance == 59.27
    assert bot._session_halted is False


def test_rebuild_restores_the_session_stop_floor(_live_boot, monkeypatch):
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(1.97)])
    bot.reconcile_today_from_exchange(61.24)
    assert bot.session_stop_threshold == 59.27 * bot.SESSION_STOP_FRACTION


def test_rebuild_writes_the_record_it_reconstructed(_live_boot, monkeypatch):
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(1.97)])
    bot.reconcile_today_from_exchange(61.24)
    saved = json.loads(open(bot.DAILY_STATE_PATH).read())
    assert saved["halted"] is True
    assert saved["live_daily_realized"] == 1.97
    assert saved["session_start_balance"] == 59.27


def test_yesterdays_settlements_are_not_counted(_live_boot, monkeypatch):
    old = bot.datetime.now(bot.timezone.utc) - bot.timedelta(days=1)
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(5.00, when=old)])
    monkeypatch.setattr(bot, "session_start_balance", 61.24)
    assert bot.reconcile_today_from_exchange(61.24) is False
    assert bot.live_daily_realized == 0.0
    assert bot.session_start_balance == 61.24      # fresh-boot baseline stands


def test_a_settlements_outage_never_blocks_boot(_live_boot, monkeypatch):
    def _boom(_since):
        raise RuntimeError("Kalshi 503")
    monkeypatch.setattr(bot, "_fetch_settled_records", _boom)
    assert bot.reconcile_today_from_exchange(61.24) is False
    assert bot._session_halted is False


def test_paper_mode_has_nothing_to_reconcile(monkeypatch):
    monkeypatch.setattr(bot, "DEMO_MODE", True)
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: [_settlement(99.0)])
    assert bot.reconcile_today_from_exchange(1030.0) is False


def test_the_local_record_wins_over_the_exchange(_daily_state, monkeypatch):
    """restore_daily_state carries the day's TRUE opening balance, so when it
    succeeds the (approximating) exchange rebuild must not run."""
    monkeypatch.setattr(bot, "paper_daily_pnl", 30.0)
    bot.daily_profit_target_check(1030.0)
    called = []
    monkeypatch.setattr(bot, "_fetch_settled_records",
                        lambda since: called.append(since) or [])
    monkeypatch.setattr(bot, "_session_halted", False)
    monkeypatch.setattr(bot, "session_start_balance", 1030.0)
    assert bot.restore_daily_state(1030.0) is True
    assert bot.session_start_balance == 1000.0
    assert called == []


# ── the state path is proven writable at boot ────────────────────────────────

def test_boot_confirms_a_writable_state_path(monkeypatch, tmp_path):
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", str(tmp_path / "daily_state.json"))
    assert bot.verify_daily_state_path() is True


def test_boot_falls_back_to_the_mounted_volume(monkeypatch, tmp_path):
    """An unwritable configured path must not silently mean 'no halt tomorrow'."""
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", "/proc/nope/daily_state.json")
    monkeypatch.setenv("RAILWAY_VOLUME_MOUNT_PATH", str(tmp_path))
    assert bot.verify_daily_state_path() is True
    assert bot.DAILY_STATE_PATH == str(tmp_path / "daily_state.json")
    bot.save_daily_state()
    assert (tmp_path / "daily_state.json").exists()


def test_boot_reports_no_writable_path(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_STATE_PERSIST", True)
    monkeypatch.setattr(bot, "DAILY_STATE_PATH", "/proc/nope/daily_state.json")
    monkeypatch.delenv("RAILWAY_VOLUME_MOUNT_PATH", raising=False)
    assert bot.verify_daily_state_path() is False
