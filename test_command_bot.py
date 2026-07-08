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
    )


# Snapshot carrying live bounds (1%–15%) as bot.py writes them.
_SNAP = {"normal_trade_pct": 10.0, "risk_min_pct": 1.0, "risk_max_pct": 15.0}


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
