"""Tests for the customer self-service dashboard.

Three layers:
  * dashboard.Settings — reading live state and writing validated/clamped override
    files (risk, reserve, format, telegram prefs).
  * dashboard session tokens + a live HTTP round-trip (login → save → state) against
    a real ThreadingHTTPServer on a throwaway port.
  * The engine + telegram sides that consume those files: bot.effective_reserve /
    tradeable_balance / active_trade_size, and telegram_utils.notifications_enabled.

bot.py needs Kalshi creds + persistence disabled at import (same shim as
test_bot_engine.py).

Run: pytest test_dashboard.py
"""

import base64
import json
import os
import threading
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

import dashboard
import telegram_utils as tg

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

import bot  # noqa: E402


_SNAP = {"demo_mode": True, "balance": 1000.0, "tradeable_balance": 1000.0,
         "session_pnl": 12.5, "normal_trade_pct": 10.0, "risk_min_pct": 1.0,
         "risk_max_pct": 15.0, "reserve_dollars": 0.0, "trading_format": "balanced",
         "updated_at": "2026-07-08T00:00:00Z"}


def _settings(tmp_path, snap=_SNAP):
    snap_path = tmp_path / "snapshot.json"
    if snap is not None:
        snap_path.write_text(json.dumps(snap))
    return dashboard.Settings(
        snapshot_path=str(snap_path),
        risk_path=str(tmp_path / "risk.json"),
        reserve_path=str(tmp_path / "reserve.json"),
        format_path=str(tmp_path / "format.json"),
        telegram_path=str(tmp_path / "tg.json"),
    )


# ── Settings: state view ───────────────────────────────────────────────────────
def test_state_reflects_snapshot(tmp_path):
    st = _settings(tmp_path).state()
    assert st["connected"] and st["mode"] == "paper"
    assert st["risk_pct"] == 10.0 and st["balance"] == 1000.0
    assert {f["key"] for f in st["formats"]} == {"conservative", "balanced", "aggressive"}
    assert st["telegram"] == {"trade_entry": True, "wins": True, "losses": True}


def test_state_without_snapshot_is_graceful(tmp_path):
    s = dashboard.Settings(snapshot_path=str(tmp_path / "none.json"),
                           risk_path=str(tmp_path / "r.json"),
                           reserve_path=str(tmp_path / "rs.json"),
                           format_path=str(tmp_path / "f.json"),
                           telegram_path=str(tmp_path / "t.json"))
    st = s.state()
    assert st["connected"] is False
    assert st["risk_min_pct"] == 1.0 and st["risk_max_pct"] == 15.0  # fallbacks


# ── Settings: writes + validation ──────────────────────────────────────────────
def test_set_risk_writes_fraction(tmp_path):
    s = _settings(tmp_path)
    ok, msg = s.set_risk(8.0)
    assert ok and "8.0%" in msg
    assert json.loads(open(s.risk_path).read())["normal_trade_pct"] == 0.08


def test_set_risk_clamps_to_ceiling(tmp_path):
    s = _settings(tmp_path)
    ok, msg = s.set_risk(90.0)
    assert ok and "clamped" in msg
    assert json.loads(open(s.risk_path).read())["normal_trade_pct"] == 0.15


def test_set_reserve_caps_at_balance(tmp_path):
    s = _settings(tmp_path)
    ok, msg = s.set_reserve(5000.0)          # balance is 1000
    assert ok and "capped" in msg
    assert json.loads(open(s.reserve_path).read())["reserve_dollars"] == 1000.0


def test_set_reserve_negative_is_zero(tmp_path):
    s = _settings(tmp_path)
    s.set_reserve(-50.0)
    assert json.loads(open(s.reserve_path).read())["reserve_dollars"] == 0.0


def test_set_format_valid_and_invalid(tmp_path):
    s = _settings(tmp_path)
    ok, msg = s.set_format("Aggressive")
    assert ok and "restart" in msg.lower()
    assert json.loads(open(s.format_path).read())["trading_format"] == "aggressive"
    ok2, msg2 = s.set_format("banana")
    assert not ok2 and "unknown" in msg2.lower()


def test_set_telegram_merges(tmp_path):
    s = _settings(tmp_path)
    s.set_telegram({"wins": False})
    saved = json.loads(open(s.telegram_path).read())
    assert saved["wins"] is False and saved["trade_entry"] is True


def test_apply_multiple_and_empty(tmp_path):
    s = _settings(tmp_path)
    ok, msgs = s.apply({"risk_pct": 5, "reserve_dollars": 100})
    assert ok and len(msgs) == 2
    ok2, msgs2 = s.apply({"nonsense": 1})
    assert not ok2 and "No recognized" in msgs2[0]


# ── session tokens ─────────────────────────────────────────────────────────────
def test_session_token_roundtrip():
    secret = b"s3cr3t"
    tok = dashboard.make_session(secret, ttl=100)
    assert dashboard.valid_session(secret, tok)
    assert not dashboard.valid_session(b"other", tok)
    assert not dashboard.valid_session(secret, "garbage")


def test_session_token_expired():
    secret = b"s3cr3t"
    assert not dashboard.valid_session(secret, dashboard.make_session(secret, ttl=-1))


# ── live HTTP round-trip ───────────────────────────────────────────────────────
def _serve(tmp_path):
    settings = _settings(tmp_path)
    handler = type("H", (dashboard._Handler,),
                   {"settings": settings, "password": "pw", "secret": b"k"})
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, settings


def _req(url, data=None, headers=None, method=None):
    r = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    return urllib.request.urlopen(r, timeout=5)


def test_http_login_required_then_flow(tmp_path):
    srv, settings = _serve(tmp_path)
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        # Unauthenticated API is 401.
        try:
            _req(base + "/api/state")
            assert False, "expected 401"
        except urllib.error.HTTPError as e:
            assert e.code == 401
        # Wrong password → 401, no cookie.
        try:
            _req(base + "/login", data=b"password=nope",
                 headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
            assert False
        except urllib.error.HTTPError as e:
            assert e.code == 401
        # Correct password → 303 to / (urllib follows it; the followed GET has no
        # cookie so it renders the login page, but the request itself succeeds).
        resp = _req(base + "/login", data=b"password=pw",
                    headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
        assert resp.status == 200
        cookie = dashboard.make_session(b"k")
        hdr = {"Cookie": f"fp_session={cookie}"}
        # Authenticated state read works.
        resp = _req(base + "/api/state", headers=hdr)
        assert json.loads(resp.read())["risk_pct"] == 10.0
        # Save a setting through the API.
        resp = _req(base + "/api/settings",
                    data=json.dumps({"risk_pct": 7}).encode(),
                    headers={**hdr, "Content-Type": "application/json"}, method="POST")
        d = json.loads(resp.read())
        assert d["ok"] and json.loads(open(settings.risk_path).read())["normal_trade_pct"] == 0.07
    finally:
        srv.shutdown()


# ── engine side: reserve ───────────────────────────────────────────────────────
def test_engine_reserve_reduces_sizing(tmp_path, monkeypatch):
    path = str(tmp_path / "reserve.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_reserve_cache", None)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", str(tmp_path / "none.json"))
    # No reserve → full balance sized at NORMAL_TRADE_PCT.
    assert bot.effective_reserve() == 0.0
    base = bot.active_trade_size(1000.0)
    # Reserve $400 → only $600 is tradeable, so the stake shrinks proportionally.
    with open(path, "w") as f:
        json.dump({"reserve_dollars": 400.0}, f)
    monkeypatch.setattr(bot, "_reserve_cache", None)
    assert bot.effective_reserve() == 400.0
    assert bot.tradeable_balance(1000.0) == 600.0
    assert bot.active_trade_size(1000.0) < base
    assert bot.active_trade_size(1000.0) == round(base * 0.6, 2)


def test_engine_reserve_above_balance_zeroes_stake(tmp_path, monkeypatch):
    path = str(tmp_path / "reserve.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_reserve_cache", None)
    with open(path, "w") as f:
        json.dump({"reserve_dollars": 5000.0}, f)
    assert bot.tradeable_balance(1000.0) == 0.0
    assert bot.active_trade_size(1000.0) == 0.0


def test_engine_reserve_ignores_corrupt(tmp_path, monkeypatch):
    path = str(tmp_path / "reserve.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", path)
    monkeypatch.setattr(bot, "_reserve_cache", None)
    with open(path, "w") as f:
        f.write("{bad")
    assert bot.effective_reserve() == 0.0


# ── engine side: boot trading-format override ──────────────────────────────────
def test_boot_format_override_read(tmp_path, monkeypatch):
    path = str(tmp_path / "format.json")
    monkeypatch.setenv("FORMAT_OVERRIDE_PATH", path)
    monkeypatch.setenv("TRADING_FORMAT", "balanced")
    with open(path, "w") as f:
        json.dump({"trading_format": "aggressive"}, f)
    assert bot._boot_trading_format() == "aggressive"   # override beats env


def test_boot_format_falls_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FORMAT_OVERRIDE_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("TRADING_FORMAT", "conservative")
    assert bot._boot_trading_format() == "conservative"


# ── telegram side: notification prefs ──────────────────────────────────────────
def test_telegram_prefs_gate(tmp_path, monkeypatch):
    path = str(tmp_path / "tg.json")
    monkeypatch.setattr(tg, "TELEGRAM_PREFS_PATH", path)
    monkeypatch.setattr(tg, "_prefs_cache", None)
    # No file → all enabled.
    assert tg.notifications_enabled("wins") is True
    with open(path, "w") as f:
        json.dump({"wins": False, "losses": True, "trade_entry": True}, f)
    monkeypatch.setattr(tg, "_prefs_cache", None)
    assert tg.notifications_enabled("wins") is False
    assert tg.notifications_enabled("losses") is True
    # Unknown category defaults on (safety alerts are never gated by this).
    assert tg.notifications_enabled("halt") is True


def test_win_notification_suppressed_when_muted(tmp_path, monkeypatch):
    path = str(tmp_path / "tg.json")
    monkeypatch.setattr(tg, "TELEGRAM_PREFS_PATH", path)
    monkeypatch.setattr(tg, "_prefs_cache", None)
    monkeypatch.setattr(tg, "_telegram_enabled", True)
    sent = []
    monkeypatch.setattr(tg, "send_telegram_message", lambda text: sent.append(text) or True)
    with open(path, "w") as f:
        json.dump({"wins": False}, f)
    tg.send_win_notification(5.0, 1000.0, 5.0, "KXBTC", "YES", 1, 0)
    assert sent == []                        # muted → nothing sent
