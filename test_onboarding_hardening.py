"""Tests for the public-form hardening: submit rate limiting, the request body
size cap, and the Stripe-checkout-failure path (a customer must never see the
"payment received" page when no payment was collected).

Run: pytest test_onboarding_hardening.py
"""

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


VALID_FORM = {
    "full_name": "Jane Doe", "email": "jane@example.com",
    "starting_balance": "1000", "trading_format": "balanced",
    "kalshi_api_key_id": "key-id", "kalshi_private_key_pem": "PEM",
    "telegram_bot_token": "123:abc", "telegram_chat_id": "555",
    "agree": "on",
}


def test_submit_rate_limited_per_ip(client):
    for _ in range(app_mod._SUBMIT_MAX_PER_IP):
        r = client.post("/submit", data={})            # invalid form → validation error
        assert "Too+many" not in r.headers["Location"]
    r = client.post("/submit", data={})                # one past the window cap
    assert r.status_code == 302
    assert "Too+many" in r.headers["Location"] or "Too%20many" in r.headers["Location"]


def test_oversized_body_rejected_413(client):
    r = client.post("/submit", data={"kalshi_private_key_pem": "x" * (128 * 1024)})
    assert r.status_code == 413


def test_checkout_failure_shows_pending_not_paid(client, tmp_path, monkeypatch):
    """Stripe Checkout blowing up must route to the payment-pending success
    variant and alert the operator — not the 'we received your payment' page."""
    alerts = []
    monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)
    monkeypatch.setattr(app_mod, "FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(app_mod, "_pem_looks_valid", lambda pem: True)
    monkeypatch.setattr(app_mod, "_validate_telegram_setup", lambda t, c: None)
    monkeypatch.setattr(app_mod, "_notify_operator", lambda sub: None)
    monkeypatch.setattr(app_mod, "_send_operator_message", alerts.append)

    def boom(sub):
        raise RuntimeError("stripe down")
    monkeypatch.setattr(app_mod, "_start_stripe_checkout", boom)

    r = client.post("/submit", data=VALID_FORM)
    assert r.status_code == 302
    assert "/success" in r.headers["Location"] and "pay=pending" in r.headers["Location"]
    assert len(alerts) == 1 and "FAILED" in alerts[0]
    assert len(list(tmp_path.glob("*.json"))) == 1      # submission still saved

    page = client.get("/success?pay=pending").get_data(as_text=True)
    assert "No card was charged" in page
    page_ok = client.get("/success").get_data(as_text=True)
    assert "No card was charged" not in page_ok
