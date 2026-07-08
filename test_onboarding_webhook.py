"""Tests for the Stripe webhook: the misconfiguration guard (Stripe live but
STRIPE_WEBHOOK_SECRET unset must fail LOUDLY — 500 so Stripe retries + flags
the endpoint, /healthz ok=false) and the paid-marking path itself, driven with
a genuinely SIGNED event so the payload goes through stripe.Webhook.construct_event
and comes back as real StripeObjects. The old tests never got past signature
verification, which hid that StripeObject has no .get() on stripe ≥ 8 — every
real completed checkout 500'd and paid customers were never marked paid.

Run: pytest test_onboarding_webhook.py
"""

import hashlib
import hmac
import json
import time

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


def _signed(payload: str, secret: str) -> dict:
    """Build a valid Stripe-Signature header for the payload, exactly as Stripe
    computes it (t=<ts>,v1=HMAC-SHA256(secret, "<ts>.<payload>"))."""
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.{payload}".encode(),
                   hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={ts},v1={sig}"}


def test_signed_checkout_completed_marks_submission_paid(client, monkeypatch, tmp_path):
    """A real signed checkout.session.completed event must mark the submission
    paid and record the Stripe customer/subscription ids — via construct_event,
    so the handler is exercised against genuine StripeObject semantics."""
    secret = "whsec_test"
    _configure(monkeypatch, stripe_key="sk_test_x", webhook_secret=secret)
    monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)
    monkeypatch.setattr(app_mod, "AUTO_PROVISION", False)

    sub_id = "20260708-000000_tester_abc123"
    (tmp_path / f"{sub_id}.json").write_text(json.dumps(
        {"id": sub_id, "payment_status": "pending"}))

    payload = json.dumps({
        "id": "evt_1", "object": "event", "api_version": "2025-05-28.basil",
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_1", "object": "checkout.session",
            "client_reference_id": sub_id,
            "customer": "cus_123", "subscription": "sub_123",
        }},
    })
    resp = client.post("/stripe/webhook", data=payload,
                       headers=_signed(payload, secret))
    assert resp.status_code == 200

    after = json.loads((tmp_path / f"{sub_id}.json").read_text())
    assert after["payment_status"] == "paid"
    assert after["stripe_customer"] == "cus_123"
    assert after["stripe_subscription"] == "sub_123"


def test_signed_event_for_unknown_submission_is_acknowledged(client, monkeypatch, tmp_path):
    """A completed checkout referencing no stored submission (or none at all)
    must still 200 so Stripe doesn't retry forever."""
    secret = "whsec_test"
    _configure(monkeypatch, stripe_key="sk_test_x", webhook_secret=secret)
    monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)

    payload = json.dumps({
        "id": "evt_2", "object": "event", "api_version": "2025-05-28.basil",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test_2", "object": "checkout.session",
                            "client_reference_id": None,
                            "customer": None, "subscription": None}},
    })
    resp = client.post("/stripe/webhook", data=payload,
                       headers=_signed(payload, secret))
    assert resp.status_code == 200
