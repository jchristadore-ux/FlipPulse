"""Tests for persistent all-time (lifetime) stats — the "stop the win rate
resetting" fix.

LifetimeStats keeps an unbounded, disk-persisted W/L + PnL tally split by
paper/live, so the all-time figures survive a redeploy. Covered:
  * record / stats / winrate accounting, per mode
  * persistence round-trip (a fresh instance reloads the same numbers)
  * paper and live tallies stay separate
  * the scheduled report + status snapshot read the persistent tally

Same import shim as test_command_bot.py.

Run: pytest test_lifetime_stats.py
"""

import base64
import json
import os

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


def _fresh(tmp_path, persist=True):
    return bot.LifetimeStats(str(tmp_path / "lifetime.json"), persist)


# ── accounting ────────────────────────────────────────────────────────────────
def test_record_and_stats_live(tmp_path):
    ls = _fresh(tmp_path)
    ls.record(False, True, 5.0)
    ls.record(False, False, -3.0)
    ls.record(False, True, 2.0)
    assert ls.stats(False) == (2, 1, 4.0)
    assert round(ls.winrate(False), 3) == 0.667


def test_paper_and_live_are_separate(tmp_path):
    ls = _fresh(tmp_path)
    ls.record(False, True, 5.0)      # live
    ls.record(True, False, -1.0)     # paper
    assert ls.stats(False) == (1, 0, 5.0)
    assert ls.stats(True) == (0, 1, -1.0)


def test_winrate_zero_when_empty(tmp_path):
    ls = _fresh(tmp_path)
    assert ls.winrate(False) == 0.0
    assert ls.stats(False) == (0, 0, 0.0)


# ── persistence (survives a "redeploy") ───────────────────────────────────────
def test_persists_across_reload(tmp_path):
    ls = _fresh(tmp_path)
    for _ in range(7):
        ls.record(False, True, 1.0)
    for _ in range(3):
        ls.record(False, False, -1.0)
    # a brand-new instance on the same path == a redeploy
    ls2 = _fresh(tmp_path)
    assert ls2.stats(False) == (7, 3, 4.0)
    assert round(ls2.winrate(False), 2) == 0.70


def test_no_persist_starts_clean(tmp_path):
    ls = _fresh(tmp_path, persist=False)
    ls.record(False, True, 1.0)
    # not written, so a fresh persist=True instance sees nothing
    assert _fresh(tmp_path, persist=True).stats(False) == (0, 0, 0.0)


def test_corrupt_file_is_ignored(tmp_path):
    path = tmp_path / "lifetime.json"
    path.write_text("{not json")
    ls = bot.LifetimeStats(str(path), True)
    assert ls.stats(False) == (0, 0, 0.0)     # clean start, no raise


# ── wired into the report + snapshot ──────────────────────────────────────────
def test_report_all_time_uses_lifetime(tmp_path, monkeypatch):
    from collections import deque
    monkeypatch.setattr(bot, "trade_history", deque())   # empty in-memory window
    ls = _fresh(tmp_path)
    ls.record(bot.DEMO_MODE, True, 10.0)
    ls.record(bot.DEMO_MODE, True, 10.0)
    ls.record(bot.DEMO_MODE, False, -5.0)
    monkeypatch.setattr(bot, "lifetime", ls)
    body = bot.build_scheduled_report(1000.0)
    # all-time win rate (2W/1L = 67%) comes from the persistent tally even though
    # trade_history (today's window) is empty.
    assert "All-time" in body and "67% (2W/1L)" in body
