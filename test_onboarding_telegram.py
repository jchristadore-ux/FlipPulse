"""Tests for the onboarding-time Telegram validation, which stops a broken bot
token / unreachable chat id from ever being saved and deployed.

Run: pytest test_onboarding_telegram.py
"""

import pytest

import onboarding.app as app


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _patch(monkeypatch, getme, send):
    monkeypatch.setattr(app.requests, "get", lambda *a, **k: FakeResp(getme))
    monkeypatch.setattr(app.requests, "post", lambda *a, **k: FakeResp(send))


def test_valid_setup_passes(monkeypatch):
    _patch(monkeypatch,
           getme={"ok": True, "result": {"username": "CustBot"}},
           send={"ok": True})
    assert app._validate_telegram_setup("123:abc", "555") is None


def test_bad_token_rejected(monkeypatch):
    _patch(monkeypatch,
           getme={"ok": False, "description": "Unauthorized"},
           send={"ok": True})
    err = app._validate_telegram_setup("bad", "555")
    assert err and "token" in err.lower()


def test_chat_not_found_rejected_with_guidance(monkeypatch):
    _patch(monkeypatch,
           getme={"ok": True, "result": {"username": "CustBot"}},
           send={"ok": False, "error_code": 400, "description": "Bad Request: chat not found"})
    err = app._validate_telegram_setup("123:abc", "8617823570")
    assert err is not None
    assert "CustBot" in err            # names the exact bot to press Start on
    assert "Start" in err


def test_transient_network_does_not_block_signup(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("dns down")
    monkeypatch.setattr(app.requests, "get", boom)
    # getMe unreachable → allow signup (None), don't punish customer for our blip
    assert app._validate_telegram_setup("123:abc", "555") is None
