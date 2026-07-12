"""Tests for telegram_utils resilience: the boot-time validation must be
diagnosable (surface *why* a send failed) and recoverable (self-heal after a
transient deploy-network outage) so alerts don't silently die at scale.

Run: pytest test_telegram_utils.py
"""

import time

import pytest
import requests

import telegram_utils as tg


class FakeResp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Reset module globals and speed up sleeps so each test is isolated."""
    monkeypatch.setattr(tg, "_telegram_enabled", False)
    monkeypatch.setattr(tg, "_bot_token", "")
    monkeypatch.setattr(tg, "_chat_id", "")
    monkeypatch.setattr(tg, "_recipients", [])
    monkeypatch.setattr(tg, "_last_error", "")
    monkeypatch.setattr(tg, "_last_error_transient", True)
    monkeypatch.setattr(tg, "_self_heal_thread", None)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "555")
    monkeypatch.delenv("TELEGRAM_OPERATOR_CHAT_ID", raising=False)
    # no real waiting in retry/backoff paths
    monkeypatch.setattr(tg.time, "sleep", lambda *_: None)


def test_validate_success_enables(monkeypatch):
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: FakeResp(200))
    assert tg.validate_telegram_connection() is True
    assert tg._telegram_enabled is True


def test_bad_token_is_permanent_no_selfheal(monkeypatch):
    called = {"heal": False}
    monkeypatch.setattr(tg, "_start_self_heal", lambda: called.__setitem__("heal", True))
    monkeypatch.setattr(tg.requests, "post",
                        lambda *a, **k: FakeResp(401, '{"description":"Unauthorized"}'))
    assert tg.validate_telegram_connection() is False
    assert tg._telegram_enabled is False
    assert tg._last_error_transient is False          # classified as a config error
    assert "401" in tg._last_error
    assert called["heal"] is False                    # no point retrying a bad token


def test_network_failure_is_transient_and_starts_selfheal(monkeypatch):
    started = {"heal": False}
    monkeypatch.setattr(tg, "_start_self_heal", lambda: started.__setitem__("heal", True))

    def boom(*a, **k):
        raise requests.exceptions.ConnectionError("name resolution failed")

    monkeypatch.setattr(tg.requests, "post", boom)
    assert tg.validate_telegram_connection() is False
    assert tg._last_error_transient is True           # network → retryable
    assert started["heal"] is True                    # self-heal was launched


def test_selfheal_recovers_once_network_returns(monkeypatch):
    """Simulate a deploy where the network is down at boot then comes up."""
    monkeypatch.setenv("TELEGRAM_SELFHEAL_INTERVAL", "0")
    monkeypatch.setenv("TELEGRAM_SELFHEAL_MAX_MINUTES", "1")
    tg._bot_token = "token123"
    tg._recipients = ["555"]

    attempts = {"n": 0}

    def flaky(*a, **k):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise requests.exceptions.ConnectionError("network not ready")
        return FakeResp(200)

    monkeypatch.setattr(tg.requests, "post", flaky)
    tg._start_self_heal()

    # Wait for the daemon thread to succeed (interval=0, sleeps stubbed out).
    deadline = time.time() + 5
    while time.time() < deadline and not tg._telegram_enabled:
        time.sleep(0.01)
    assert tg._telegram_enabled is True


def test_send_raw_reports_reason_on_total_failure(monkeypatch):
    tg._bot_token = "token123"
    tg._recipients = ["555"]
    monkeypatch.setattr(tg.requests, "post", lambda *a, **k: FakeResp(400, "chat not found"))
    assert tg._send_raw("hi") is False
    assert "400" in tg._last_error
    assert tg._last_error_transient is False


def test_send_raw_fanout_partial_success(monkeypatch):
    """One recipient bad, one good → still counts as delivered."""
    tg._bot_token = "token123"
    tg._recipients = ["good", "bad"]

    def post(url, json=None, **k):
        return FakeResp(200) if json["chat_id"] == "good" else FakeResp(400, "nope")

    monkeypatch.setattr(tg.requests, "post", post)
    assert tg._send_raw("hi") is True


def test_disabled_gate_blocks_sends(monkeypatch):
    tg._telegram_enabled = False
    monkeypatch.setattr(tg, "_send_raw", lambda *_: pytest.fail("should not send when disabled"))
    assert tg.send_telegram_message("nope") is False


# ── minimal-alerts mode (Task 4) ──────────────────────────────────────────────
def test_minimal_alerts_defaults_on(monkeypatch):
    monkeypatch.delenv("TELEGRAM_MINIMAL_ALERTS", raising=False)
    assert tg.minimal_alerts() is True


def test_minimal_alerts_can_be_disabled(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MINIMAL_ALERTS", "false")
    assert tg.minimal_alerts() is False


def test_status_message_suppressed_in_minimal_mode(monkeypatch):
    monkeypatch.delenv("TELEGRAM_MINIMAL_ALERTS", raising=False)   # default → quiet
    tg._telegram_enabled = True
    monkeypatch.setattr(tg, "_send_raw", lambda *_: pytest.fail("status msg must be suppressed"))
    assert tg.send_status_message("🤖 boot summary") is False


def test_status_message_delivered_when_not_minimal(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MINIMAL_ALERTS", "false")
    tg._telegram_enabled = True
    sent = []
    monkeypatch.setattr(tg, "_send_raw", lambda text: sent.append(text) or True)
    assert tg.send_status_message("recovery notice") is True
    assert sent == ["recovery notice"]


def test_safety_message_always_delivered_even_in_minimal_mode(monkeypatch):
    """send_telegram_message (used by HALT / circuit breaker) is never gated by
    minimal-alerts mode."""
    monkeypatch.delenv("TELEGRAM_MINIMAL_ALERTS", raising=False)   # minimal ON
    tg._telegram_enabled = True
    sent = []
    monkeypatch.setattr(tg, "_send_raw", lambda text: sent.append(text) or True)
    assert tg.send_telegram_message("⛔ HALTED") is True
    assert sent == ["⛔ HALTED"]


class JsonResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_config_diagnostic_lists_reachable_chats(monkeypatch, caplog):
    """On a 'chat not found' failure the bot should name its @username and the
    chat ids that HAVE messaged it — handing the operator the correct value."""
    def fake_get(url, **k):
        if url.endswith("/getMe"):
            return JsonResp({"ok": True, "result": {"username": "CustBot", "first_name": "Cust"}})
        return JsonResp({"ok": True, "result": [
            {"message": {"chat": {"id": 42, "username": "realuser"}}}]})

    monkeypatch.setattr(tg.requests, "get", fake_get)
    with caplog.at_level("ERROR"):
        tg._log_config_diagnostic("token123")
    text = caplog.text
    assert "CustBot" in text
    assert "42" in text and "realuser" in text
