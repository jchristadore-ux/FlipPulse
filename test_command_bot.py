"""Tests for the Telegram /risk command and its engine-side counterpart.

Two halves:
  * command_bot.CommandHandler — authorization, parsing/clamping of the customer's
    "/risk <percent>" message, and the atomic override file it writes.
  * bot.effective_normal_trade_pct — the engine reading that file back at the
    sizing chokepoint, clamped into the safe band, and falling back cleanly.

bot.py needs Kalshi credentials + persistence disabled at import (same shim as
test_bot_engine.py).

Run: pytest test_command_bot.py
"""

import base64
import json
import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import command_bot

_PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()).decode()
os.environ.setdefault("KALSHI_API_KEY_ID", "test-key")
os.environ.setdefault("KALSHI_PRIVATE_KEY_PEM_B64",
                      base64.b64encode(_PEM.encode()).decode())
os.environ.setdefault("DEMO_MODE", "true")
for _persist in ("RECOVERY_PERSIST", "PROBATION_PERSIST",
                 "BUCKET_PERSIST", "BILLING_PERSIST"):
    os.environ.setdefault(_persist, "false")

import bot  # noqa: E402  (env must be set first)


# ── helpers ───────────────────────────────────────────────────────────────────
def _handler(tmp_path, snap=None):
    """A CommandHandler wired to temp files, with an optional status snapshot."""
    snap_path = tmp_path / "snapshot.json"
    if snap is not None:
        snap_path.write_text(json.dumps(snap))
    return command_bot.CommandHandler(
        authorized_chats={"123"},
        snapshot_path=str(snap_path),
        health_log_path=str(tmp_path / "health.log"),
        risk_override_path=str(tmp_path / "risk_override.json"),
        mode_override_path=str(tmp_path / "mode_override.json"),
        nsc_override_path=str(tmp_path / "nsc_override.json"),
    )


# Snapshot carrying live bounds (1%–15%) as bot.py writes them.
_SNAP = {"normal_trade_pct": 10.0, "risk_min_pct": 1.0, "risk_max_pct": 15.0,
         "demo_mode": True}


# ── authorization ─────────────────────────────────────────────────────────────
def test_stranger_is_ignored(tmp_path):
    h = _handler(tmp_path, _SNAP)
    assert h.handle("999", "/risk 8") is None
    # ...and no override file was written on their behalf.
    assert not os.path.exists(h.risk_override_path)


# ── /risk read ────────────────────────────────────────────────────────────────
def test_risk_no_args_reports_current_and_range(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk")
    assert "10.0%" in reply and "1–15%" in reply


def test_risk_no_snapshot_yet_is_graceful(tmp_path):
    h = _handler(tmp_path, snap=None)
    reply = h.handle("123", "/risk")
    assert "booting" in reply.lower()


# ── /risk set ─────────────────────────────────────────────────────────────────
def test_risk_set_whole_percent_writes_fraction(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk 8")
    assert "8.0%" in reply
    saved = json.loads(open(h.risk_override_path).read())
    assert saved["normal_trade_pct"] == 0.08
    assert saved["set_by"] == "123"


def test_risk_set_percent_sign_is_stripped(tmp_path):
    h = _handler(tmp_path, _SNAP)
    h.handle("123", "/risk 12%")
    saved = json.loads(open(h.risk_override_path).read())
    assert saved["normal_trade_pct"] == 0.12


def test_risk_set_fraction_form(tmp_path):
    h = _handler(tmp_path, _SNAP)
    h.handle("123", "/risk 0.05")
    saved = json.loads(open(h.risk_override_path).read())
    assert saved["normal_trade_pct"] == 0.05


def test_risk_above_ceiling_is_clamped(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk 90")
    assert "clamped" in reply.lower()
    saved = json.loads(open(h.risk_override_path).read())
    assert saved["normal_trade_pct"] == 0.15   # MAX_TRADE_PCT ceiling


def test_risk_below_floor_is_clamped(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk 0.5%")      # explicit 0.5% → below 1% floor
    assert "clamped" in reply.lower()
    saved = json.loads(open(h.risk_override_path).read())
    assert saved["normal_trade_pct"] == 0.01


def test_risk_non_numeric_rejected_no_write(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk lots")
    assert "number" in reply.lower()
    assert not os.path.exists(h.risk_override_path)


def test_risk_zero_rejected(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk 0")
    assert "positive" in reply.lower()
    assert not os.path.exists(h.risk_override_path)


# ── /risk reset ───────────────────────────────────────────────────────────────
def test_risk_reset_removes_override(tmp_path):
    h = _handler(tmp_path, _SNAP)
    h.handle("123", "/risk 8")
    assert os.path.exists(h.risk_override_path)
    reply = h.handle("123", "/risk reset")
    assert "default" in reply.lower()
    assert not os.path.exists(h.risk_override_path)


def test_risk_reset_when_none_set(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/risk reset")
    assert "already" in reply.lower()


# ── /mode · /live · /paper ─────────────────────────────────────────────────────
def _mode_file(h):
    return json.loads(open(h.mode_override_path).read())


def test_live_requires_confirm(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/live")
    assert "confirm" in reply.lower() and "REAL money" in reply
    assert not os.path.exists(h.mode_override_path)      # nothing written yet


def test_live_confirm_writes_live(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/live confirm")
    assert "LIVE" in reply
    assert _mode_file(h)["demo_mode"] is False and _mode_file(h)["set_by"] == "123"


def test_paper_switches_back_without_confirm(tmp_path):
    live_snap = dict(_SNAP, demo_mode=False)
    h = _handler(tmp_path, live_snap)
    reply = h.handle("123", "/paper")
    assert "PAPER" in reply
    assert _mode_file(h)["demo_mode"] is True


def test_paper_when_already_paper_is_noop(tmp_path):
    h = _handler(tmp_path, _SNAP)                          # snapshot says paper
    reply = h.handle("123", "/paper")
    assert "Already in PAPER" in reply
    assert not os.path.exists(h.mode_override_path)


def test_live_when_already_live_is_noop(tmp_path):
    h = _handler(tmp_path, dict(_SNAP, demo_mode=False))
    reply = h.handle("123", "/live confirm")
    assert "Already in LIVE" in reply


def test_mode_shows_current_and_pending(tmp_path):
    h = _handler(tmp_path, dict(_SNAP, demo_mode=True, pending_demo_mode=False))
    reply = h.handle("123", "/mode")
    assert "PAPER" in reply and "once the bot is flat" in reply


def test_mode_flip_ignored_for_stranger(tmp_path):
    h = _handler(tmp_path, _SNAP)
    assert h.handle("999", "/live confirm") is None
    assert not os.path.exists(h.mode_override_path)


# ── engine side: bot.effective_normal_trade_pct ───────────────────────────────
def test_engine_reads_override(tmp_path, monkeypatch):
    path = str(tmp_path / "risk_override.json")
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    with open(path, "w") as f:
        json.dump({"normal_trade_pct": 0.07}, f)
    assert bot.effective_normal_trade_pct() == 0.07


def test_engine_falls_back_without_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    assert bot.effective_normal_trade_pct() == bot.NORMAL_TRADE_PCT


def test_engine_clamps_override_to_ceiling(tmp_path, monkeypatch):
    path = str(tmp_path / "risk_override.json")
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    with open(path, "w") as f:
        json.dump({"normal_trade_pct": 0.99}, f)   # absurd — engine re-clamps
    assert bot.effective_normal_trade_pct() == bot.MAX_TRADE_PCT


def test_engine_ignores_corrupt_override(tmp_path, monkeypatch):
    path = str(tmp_path / "risk_override.json")
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    with open(path, "w") as f:
        f.write("{not json")
    assert bot.effective_normal_trade_pct() == bot.NORMAL_TRADE_PCT


def test_round_trip_command_to_engine(tmp_path, monkeypatch):
    """The fraction the /risk command writes is exactly what the engine sizes on."""
    path = str(tmp_path / "risk_override.json")
    h = command_bot.CommandHandler(
        authorized_chats={"123"},
        snapshot_path=str(tmp_path / "snap.json"),
        health_log_path=str(tmp_path / "h.log"),
        risk_override_path=path,
    )
    # snapshot with default bounds is absent → falls back to env bounds (1–15%)
    h.handle("123", "/risk 6")
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    assert bot.effective_normal_trade_pct() == 0.06


# ── /winrate + /pnl ───────────────────────────────────────────────────────────
_PERF_SNAP = dict(
    _SNAP,
    balance=1200.0, session_pnl=51.0, win_rate=75.0, wins=6, losses=2,
    wins_today=2, losses_today=1, win_rate_today=66.7, pnl_today=1.0,
    wins_week=6, losses_week=2, win_rate_week=75.0, pnl_week=51.0,
)


def test_winrate_all_windows(tmp_path):
    h = _handler(tmp_path, _PERF_SNAP)
    reply = h.handle("123", "/winrate")
    assert "Today: 67% (2W/1L)" in reply
    assert "This week: 75% (6W/2L)" in reply
    assert "All-time" in reply


def test_winrate_week_only(tmp_path):
    h = _handler(tmp_path, _PERF_SNAP)
    reply = h.handle("123", "/winrate week")
    assert "This week: 75% (6W/2L)" in reply
    assert "Today" not in reply


def test_winrate_percent_suffix_and_day(tmp_path):
    """The guide writes '/winrate% day' — the '%' must not break routing."""
    h = _handler(tmp_path, _PERF_SNAP)
    reply = h.handle("123", "/WinRate% day")
    assert "Today: 67% (2W/1L)" in reply


def test_winrate_no_snapshot_is_graceful(tmp_path):
    h = _handler(tmp_path, snap=None)
    assert "minute" in h.handle("123", "/winrate").lower()


def test_pnl_all_and_week(tmp_path):
    h = _handler(tmp_path, _PERF_SNAP)
    allr = h.handle("123", "/pnl")
    assert "$+1.00" in allr and "$+51.00" in allr
    wk = h.handle("123", "/pnl week")
    assert "This week: $+51.00 (6W/2L)" in wk


# ── /recoverynostakechange ────────────────────────────────────────────────────
def _nsc_file(h):
    return json.loads(open(h.nsc_override_path).read())


def test_nsc_status_no_arg(tmp_path):
    h = _handler(tmp_path, dict(_SNAP, recovery_no_stake_change=False))
    reply = h.handle("123", "/recoverynostakechange")
    assert "OFF" in reply


def test_nsc_on_writes_override(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/RecoveryModeNoStakeChange on")
    assert "ON" in reply
    assert _nsc_file(h)["enabled"] is True and _nsc_file(h)["set_by"] == "123"


def test_nsc_off_writes_override(tmp_path):
    h = _handler(tmp_path, _SNAP)
    h.handle("123", "/rnsc off")
    assert _nsc_file(h)["enabled"] is False


def test_nsc_bad_arg_rejected_no_write(tmp_path):
    h = _handler(tmp_path, _SNAP)
    reply = h.handle("123", "/rnsc maybe")
    assert "on" in reply.lower() and "off" in reply.lower()
    assert not os.path.exists(h.nsc_override_path)


def test_nsc_ignored_for_stranger(tmp_path):
    h = _handler(tmp_path, _SNAP)
    assert h.handle("999", "/rnsc on") is None
    assert not os.path.exists(h.nsc_override_path)


def test_nsc_round_trip_to_engine(tmp_path, monkeypatch):
    """The toggle the command writes is exactly what the engine reads back."""
    h = _handler(tmp_path, _SNAP)
    h.handle("123", "/rnsc on")
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", h.nsc_override_path)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is True
    h.handle("123", "/rnsc off")
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    assert bot.recovery_no_stake_change_enabled() is False


def test_status_shows_nsc_and_recovery_wr(tmp_path):
    snap = dict(
        _SNAP, balance=1000.0, session_pnl=0.0, active_mode="recovery",
        recovery_no_stake_change=True, recovery_wins=4, recovery_losses=1,
        recovery_win_rate=80.0, recovery_winrate_restore_pct=70.0,
        active_trade_pct=10.0, active_trade_size=100.0,
        session_state="ACTIVE", updated_at="2026-07-12T00:00:00Z",
    )
    reply = _handler(tmp_path, snap).handle("123", "/status")
    assert "No-Stake-Change ON" in reply
    assert "Recovery WR: 80% (4W/1L)" in reply
