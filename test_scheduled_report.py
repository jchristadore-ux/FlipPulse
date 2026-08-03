"""Tests for the twice-daily scheduled Telegram report (task 1).

Covers the three moving parts:
  * trade_window_stats — day/all-time W/L + PnL tallies over trade_history.
  * build_scheduled_report — the briefing body (today vs all-time).
  * ReportScheduler — slot selection, fire-once, stale-skip, and persistence.

Same import shim as test_command_bot.py (Kalshi creds + persistence off).

Run: pytest test_scheduled_report.py
"""

import base64
import json
import os
from datetime import datetime, timedelta, timezone

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


def _seed_history(monkeypatch):
    """Fresh trade_history: 2 wins + 1 loss today, and an old win 10 days back."""
    from collections import deque
    now = datetime.now(timezone.utc)
    h = deque(maxlen=500)
    h.append({"time": now.isoformat(), "result": "win",  "pnl": 5.0})
    h.append({"time": now.isoformat(), "result": "win",  "pnl": 4.0})
    h.append({"time": now.isoformat(), "result": "loss", "pnl": -8.0})
    h.append({"time": (now - timedelta(days=10)).isoformat(),
              "result": "win", "pnl": 50.0})
    # a still-open trade must never count toward either window
    h.append({"time": now.isoformat(), "result": "pending", "pnl": None})
    monkeypatch.setattr(bot, "trade_history", h)


# ── trade_window_stats ────────────────────────────────────────────────────────
def test_window_stats_today_excludes_old_and_pending(monkeypatch):
    _seed_history(monkeypatch)
    w, l, pnl = bot.trade_window_stats(bot._tz_day_start_epoch(0))
    assert (w, l, pnl) == (2, 1, 1.0)


def test_window_stats_all_time_includes_old(monkeypatch):
    _seed_history(monkeypatch)
    w, l, pnl = bot.trade_window_stats(None)
    assert (w, l, pnl) == (3, 1, 51.0)


def test_window_stats_empty_is_zeroes(monkeypatch):
    from collections import deque
    monkeypatch.setattr(bot, "trade_history", deque())
    assert bot.trade_window_stats(None) == (0, 0, 0.0)


# ── build_scheduled_report ────────────────────────────────────────────────────
def _seed_lifetime(monkeypatch, wins, losses, pnl):
    """A fresh (non-persistent) lifetime tally seeded for the current mode."""
    ls = bot.LifetimeStats("/dev/null", persist=False)
    for _ in range(wins):
        ls.record(bot.DEMO_MODE, True, pnl / max(wins, 1))
    for _ in range(losses):
        ls.record(bot.DEMO_MODE, False, 0.0)
    monkeypatch.setattr(bot, "lifetime", ls)
    return ls


def test_report_shows_today_and_all_time(monkeypatch):
    _seed_history(monkeypatch)                 # today window: 2W/1L
    _seed_lifetime(monkeypatch, 3, 1, 51.0)    # all-time (persistent): 3W/1L
    body = bot.build_scheduled_report(1234.56)
    assert "$1,234.56" in body
    assert "Today" in body and "All-time" in body
    assert "67% (2W/1L)" in body     # today (from trade_history)
    assert "75% (3W/1L)" in body     # all-time (from persistent lifetime tally)


def test_report_handles_no_trades(monkeypatch):
    from collections import deque
    monkeypatch.setattr(bot, "trade_history", deque())
    _seed_lifetime(monkeypatch, 0, 0, 0.0)
    body = bot.build_scheduled_report(1000.0)
    assert "no settled trades yet" in body


# ── ReportScheduler slot logic ────────────────────────────────────────────────
def _sched(tmp_path, persist=False):
    return bot.ReportScheduler(str(tmp_path / "report_state.json"), persist)


def _at(hour, minute=0):
    return datetime.now(bot._report_tz()).replace(
        hour=hour, minute=minute, second=0, microsecond=0)


def test_latest_slot_picks_this_mornings_nine(tmp_path):
    s = _sched(tmp_path)
    assert s._latest_past_slot(_at(9, 5)).hour == 9


def test_latest_slot_before_nine_is_prev_evening(tmp_path):
    s = _sched(tmp_path)
    slot = s._latest_past_slot(_at(8, 0))
    assert slot.hour == 21
    assert slot.date() == (_at(8, 0).date() - timedelta(days=1))


def test_maybe_send_fires_once_then_dedupes(tmp_path, monkeypatch):
    _seed_history(monkeypatch)
    sent = []
    monkeypatch.setattr(bot.tg, "send_telegram_message",
                        lambda msg: sent.append(msg) or True)
    # freeze "now" at 9:05am so the morning slot is fresh and in-window
    monkeypatch.setattr(bot, "datetime", _FrozenDatetime(_at(9, 5)))
    s = _sched(tmp_path)
    assert s.maybe_send(1000.0) is True
    assert len(sent) == 1
    # same slot → no second send
    assert s.maybe_send(1000.0) is False
    assert len(sent) == 1


def test_maybe_send_skips_stale_slot(tmp_path, monkeypatch):
    _seed_history(monkeypatch)
    sent = []
    monkeypatch.setattr(bot.tg, "send_telegram_message",
                        lambda msg: sent.append(msg) or True)
    # 9am slot, but "now" is 5 hours later — beyond REPORT_MAX_LATE_SECS (2h)
    monkeypatch.setattr(bot, "datetime", _FrozenDatetime(_at(14, 0)))
    s = _sched(tmp_path)
    assert s.maybe_send(1000.0) is False       # not sent
    assert sent == []
    # ...but the slot was consumed, so it won't re-fire
    assert s.last_slot.endswith(" 09")


def test_maybe_send_persists_last_slot(tmp_path, monkeypatch):
    _seed_history(monkeypatch)
    monkeypatch.setattr(bot.tg, "send_telegram_message", lambda msg: True)
    monkeypatch.setattr(bot, "datetime", _FrozenDatetime(_at(9, 5)))
    s = _sched(tmp_path, persist=True)
    s.maybe_send(1000.0)
    saved = json.loads(open(s._path).read())
    assert saved["last_slot"].endswith(" 09")
    # a fresh scheduler (redeploy) reloads it and won't double-send
    s2 = _sched(tmp_path, persist=True)
    assert s2.last_slot == s.last_slot
    assert s2.maybe_send(1000.0) is False


def test_disabled_never_sends(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "REPORT_SCHEDULE_ENABLED", False)
    monkeypatch.setattr(bot, "datetime", _FrozenDatetime(_at(9, 5)))
    sent = []
    monkeypatch.setattr(bot.tg, "send_telegram_message",
                        lambda msg: sent.append(msg) or True)
    s = _sched(tmp_path)
    assert s.maybe_send(1000.0) is False
    assert sent == []


def _FrozenDatetime(frozen):
    """A drop-in for bot.datetime whose .now() returns a fixed instant, so the
    scheduler's wall-clock read is deterministic. Subclasses datetime so the
    constructor and the other classmethods bot.py uses keep working."""

    class _Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz is not None else frozen

    return _Frozen
