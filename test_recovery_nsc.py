"""Tests for Recovery Mode "No Stake Change" (task 2).

The toggle makes recovery still TRIGGER and TRACK, but keep the stake at the full
normal fraction and leave laddering active — no de-risk, no post-recovery ramp.

Covers:
  * recovery_no_stake_change_enabled() — env default + runtime override file.
  * active_trade_fraction() / in_clawback() honoring the toggle while recovery is
    active (the two sizing chokepoints the ladder reads).
  * enter()/maybe_exit() taking the no-stake-change path (messaging + no ladder
    pause on exit).

Same import shim as test_command_bot.py.

Run: pytest test_recovery_nsc.py
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
                 "BILLING_PERSIST", "REPORT_PERSIST"):
    os.environ.setdefault(_persist, "false")

import bot  # noqa: E402  (env must be set first)


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Reset recovery + the NSC toggle around every test, and mute Telegram."""
    monkeypatch.setattr(bot.tg, "send_telegram_message", lambda *_a, **_k: True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", False)
    # a private, non-existent override path by default (→ env default)
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", "/nonexistent/nsc.json")
    bot.recovery.active = False
    bot.recovery.target_balance = 0.0
    yield
    bot.recovery.active = False
    bot.recovery.target_balance = 0.0


def _activate_recovery():
    bot.recovery.active = True
    bot.recovery.target_balance = 1000.0


# ── the toggle read ───────────────────────────────────────────────────────────
def test_enabled_defaults_to_env(monkeypatch):
    assert bot.recovery_no_stake_change_enabled() is False
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is True


def test_override_file_wins_over_env(tmp_path, monkeypatch):
    path = str(tmp_path / "nsc.json")
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", path)
    # env default False, but override turns it on
    with open(path, "w") as f:
        json.dump({"enabled": True}, f)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is True
    # ...and an override can also turn it OFF against an env default of True
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    with open(path, "w") as f:
        json.dump({"enabled": False}, f)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is False


def test_corrupt_override_falls_back_to_env(tmp_path, monkeypatch):
    path = str(tmp_path / "nsc.json")
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    with open(path, "w") as f:
        f.write("{not json")
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is True


# ── sizing chokepoints while recovery is active ───────────────────────────────
def test_standard_recovery_drops_stake_and_clawback(monkeypatch):
    _activate_recovery()                       # NSC off (default)
    assert bot.active_trade_fraction() == bot.RECOVERY_TRADE_PCT
    assert bot.in_clawback() is True


def test_nsc_recovery_keeps_full_stake_and_ladders(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    _activate_recovery()
    assert bot.active_trade_fraction() == bot.effective_normal_trade_pct()
    assert bot.in_clawback() is False          # ladder keeps sizing up


def test_toggle_flips_live_without_reentry(monkeypatch):
    """Flipping the toggle changes how an already-active recovery sizes."""
    _activate_recovery()
    assert bot.active_trade_fraction() == bot.RECOVERY_TRADE_PCT
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.active_trade_fraction() == bot.effective_normal_trade_pct()


# ── enter() / maybe_exit() paths ──────────────────────────────────────────────
def test_enter_nsc_sends_no_stake_change_message(monkeypatch):
    # Recovery notices are lifecycle "status" messages (gated by minimal-alerts
    # mode), so capture send_status_message directly to assert the copy.
    sent = []
    monkeypatch.setattr(bot.tg, "send_status_message",
                        lambda msg: sent.append(msg) or True)
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery.enter(1000.0, 900.0) is True
    assert bot.recovery.active is True
    assert any("No Stake Change" in m for m in sent)


def test_exit_nsc_does_not_pause_ladder_or_ramp(monkeypatch):
    """On exit in NSC mode the ladder pause is never called (nothing to ramp)."""
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)

    calls = {"pause": 0}

    class _FakeLadder:
        def pause_size_up(self, n):
            calls["pause"] += 1

    monkeypatch.setattr(bot, "stake_ladder", _FakeLadder())
    _activate_recovery()
    assert bot.recovery.maybe_exit(1000.0) is True   # target met → exits
    assert bot.recovery.active is False
    assert calls["pause"] == 0                        # NSC: no ladder pause


def test_exit_standard_pauses_ladder(monkeypatch):
    """Control: standard recovery exit DOES pause the ladder size-up."""
    calls = {"pause": 0}

    class _FakeLadder:
        def pause_size_up(self, n):
            calls["pause"] += 1

    monkeypatch.setattr(bot, "stake_ladder", _FakeLadder())
    monkeypatch.setattr(bot, "RECOVERY_LADDER_PAUSE_TRADES", 5)
    _activate_recovery()
    assert bot.recovery.maybe_exit(1000.0) is True
    assert calls["pause"] == 1


# ── win-rate restore (owner directive) ────────────────────────────────────────
def _prime_recovery(wins, losses):
    bot.recovery.active = True
    bot.recovery.target_balance = 1000.0
    bot.recovery.wins = wins
    bot.recovery.losses = losses


def test_winrate_record_only_counts_recovery_mode_trades():
    _prime_recovery(0, 0)
    bot.recovery_winrate_record(True, {"mode_at_entry": "normal"})    # the arming loss's win — n/a
    bot.recovery_winrate_record(True, {"mode_at_entry": "probation"})  # wrong mode
    assert (bot.recovery.wins, bot.recovery.losses) == (0, 0)
    bot.recovery_winrate_record(True, {"mode_at_entry": "recovery"})
    bot.recovery_winrate_record(False, {"mode_at_entry": "recovery"})
    assert (bot.recovery.wins, bot.recovery.losses) == (1, 1)


def test_stake_below_base_true_in_standard_recovery():
    _prime_recovery(0, 0)                      # NSC off → active frac = RECOVERY_TRADE_PCT
    assert bot.stake_below_base(1000.0) is True


def test_stake_not_below_base_in_nsc_without_ladder(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    monkeypatch.setattr(bot, "stake_ladder", None)
    _prime_recovery(0, 0)
    assert bot.stake_below_base(1000.0) is False


def test_restore_fires_at_threshold_with_min_sample(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_RESTORE_PCT", 0.70)
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_MIN_TRADES", 5)
    _prime_recovery(4, 0)                       # only 4 trades — under min sample
    assert bot.maybe_winrate_restore(900.0) is False
    assert bot.recovery.active is True
    bot.recovery.record_result(True)            # 5W/0L = 100% ≥ 70%, sample met
    assert bot.maybe_winrate_restore(900.0) is True
    assert bot.recovery.active is False         # exited, no probation ramp
    assert bot.probation.active is False


def test_restore_does_not_fire_below_threshold(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_RESTORE_PCT", 0.70)
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_MIN_TRADES", 5)
    _prime_recovery(3, 2)                        # 60% < 70%
    assert bot.maybe_winrate_restore(900.0) is False
    assert bot.recovery.active is True


def test_restore_skips_probation_ramp(monkeypatch):
    """The whole point: a win-rate restore must NOT engage the probation ramp."""
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_RESTORE_PCT", 0.70)
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_MIN_TRADES", 3)
    started = {"n": 0}
    monkeypatch.setattr(bot.probation, "start",
                        lambda *a, **k: started.__setitem__("n", started["n"] + 1))
    _prime_recovery(3, 0)
    assert bot.maybe_winrate_restore(900.0) is True
    assert started["n"] == 0


def test_restore_resumes_ladder(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_RESTORE_PCT", 0.70)
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_MIN_TRADES", 3)
    calls = {"resume": 0}

    class _FakeLadder:
        def resume_size_up(self):
            calls["resume"] += 1

        def peek_multiplier(self, balance=None):
            return 1.0

    monkeypatch.setattr(bot, "stake_ladder", _FakeLadder())
    _prime_recovery(3, 0)
    assert bot.maybe_winrate_restore(900.0) is True   # standard recovery → below base
    assert calls["resume"] == 1


def test_restore_disabled_never_fires(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_WINRATE_RESTORE_ENABLED", False)
    _prime_recovery(10, 0)
    assert bot.maybe_winrate_restore(900.0) is False
    assert bot.recovery.active is True
