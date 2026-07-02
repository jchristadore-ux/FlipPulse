"""Tests for the Stripe webhook misconfiguration guard: with Stripe live but
STRIPE_WEBHOOK_SECRET unset, the paid→provisioned pipeline must fail LOUDLY
(500 so Stripe retries + flags the endpoint, /healthz ok=false) instead of
silently swallowing real payments.

Run: pytest test_onboarding_webhook.py
"""

import pytest

import onboarding.app as app_mod


@pytest.fixture
def client():
    return app_mod.app.test_client()


def _configure(monkeypatch, stripe_key: str, webhook_secret: str) -> None:
    monkeypatch.setattr(app_mod, "STRIPE_SECRET_KEY", stripe_key)
    monkeypatch.setattr(app_mod, "STRIPE_WEBHOOK_SECRET", webhook_secret)


def test_stripe_live_without_webhook_secret_fails_loudly(client, monkeypatch):
    """Stripe configured, secret missing → 500 (Stripe retries and alerts) and
    /healthz ok=false, so the misconfiguration cannot go unnoticed."""
    _configure(monkeypatch, stripe_key="sk_test_x", webhook_secret="")
    assert client.post("/stripe/webhook", data="{}").status_code == 500
    health = client.get("/healthz").get_json()
    assert health["ok"] is False
    assert health["stripe_webhook"] is False


def test_no_stripe_at_all_stays_a_noop(client, monkeypatch):
    """Stripe-less install (manual billing): webhook stays a harmless 200 no-op
    and /healthz stays green."""
    _configure(monkeypatch, stripe_key="", webhook_secret="")
    assert client.post("/stripe/webhook", data="{}").status_code == 200
    assert client.get("/healthz").get_json()["ok"] is True


def test_secret_set_enforces_signature(client, monkeypatch):
    """With the secret configured, an unsigned/forged payload is rejected 400."""
    _configure(monkeypatch, stripe_key="sk_test_x", webhook_secret="whsec_test")
    assert client.post("/stripe/webhook", data="{}").status_code == 400
    health = client.get("/healthz").get_json()
    assert health["ok"] is True
    assert health["stripe_webhook"] is True
