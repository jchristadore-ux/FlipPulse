"""Tests for the customer-chosen bot handle: the form now accepts an optional
`handle` that names the bot/project (flippulse-<handle>). It is slugified for
safety and falls back to the customer's name when blank.

Run: pytest test_onboarding_handle.py
"""

import json

import pytest
from cryptography.fernet import Fernet

import onboarding.app as app_mod


@pytest.fixture
def client():
    return app_mod.app.test_client()


@pytest.fixture(autouse=True)
def fresh_rate_window():
    app_mod._submit_hits.clear()
    yield
    app_mod._submit_hits.clear()


BASE_FORM = {
    "full_name": "John Christadore", "email": "john@example.com",
    "starting_balance": "1000", "trading_format": "aggressive",
    "kalshi_api_key_id": "key-id", "kalshi_private_key_pem": "PEM",
    "telegram_bot_token": "123:abc", "telegram_chat_id": "555",
    "ack_risk": "on", "ack_software": "on", "ack_eligibility": "on", "agree": "on",
}


@pytest.fixture
def submit(tmp_path, monkeypatch):
    """Post a form (Stripe disabled, secrets validation stubbed) and return the
    single saved submission dict."""
    monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)
    monkeypatch.setattr(app_mod, "FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(app_mod, "_pem_looks_valid", lambda pem: True)
    monkeypatch.setattr(app_mod, "_validate_telegram_setup", lambda t, c: None)
    monkeypatch.setattr(app_mod, "_notify_operator", lambda sub: None)
    monkeypatch.setattr(app_mod, "_start_stripe_checkout", lambda sub: None)

    def _do(**overrides):
        data = dict(BASE_FORM, **overrides)
        client = app_mod.app.test_client()
        r = client.post("/submit", data=data)
        assert r.status_code == 302
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        sub = json.loads(files[0].read_text())
        files[0].unlink()                        # reset for the next call
        return sub

    return _do


def test_blank_handle_falls_back_to_name(submit):
    sub = submit(handle="")
    assert sub["handle"] == "john-christadore"


def test_missing_handle_field_falls_back_to_name(submit):
    sub = submit()                               # form without a handle key at all
    assert sub["handle"] == "john-christadore"


def test_custom_handle_is_used(submit):
    sub = submit(handle="john-btc")
    assert sub["handle"] == "john-btc"


def test_custom_handle_is_slugified(submit):
    sub = submit(handle="John's BTC Bot!")
    assert sub["handle"] == "john-s-btc-bot"
    # slug is safe as a Railway project name fragment
    assert app_mod.re.fullmatch(r"[a-z0-9\-]+", sub["handle"])


def test_handle_length_capped(submit):
    sub = submit(handle="x" * 100)
    assert len(sub["handle"]) <= 40
