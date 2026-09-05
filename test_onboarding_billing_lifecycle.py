"""Tests for the Stripe BILLING LIFECYCLE — everything after the first payment.

Marking the first checkout paid is only the opening move of a subscription
business. These tests cover the rest of the money path, each one standing in for
a way FlipPulse could previously have lost money or shipped a bot for free:

  • a checkout that completes but has NOT been paid (delayed payment method)
    must not provision a bot;
  • a 100%-coupon signup (payment_status="no_payment_required" — the Founder-100
    offer) must provision, since it IS a real customer;
  • a payment we cannot tie to a submission must raise an operator alert rather
    than a silent 200 — that is the one failure that charges a real person and
    leaves nobody looking;
  • Stripe retries must not be processed twice, and a handler that throws must
    release its claim so the retry is a real second attempt;
  • failed renewals, cancellations, refunds and chargebacks must be recorded and
    alerted — and a churned customer's bot must never be resurrected by the
    provisioning boot sweep.

Every webhook here is driven through a genuinely SIGNED payload so it goes
through stripe.Webhook.construct_event and the handlers see real StripeObjects
(which, on stripe >= 8, do not support .get()).

Run: pytest test_onboarding_billing_lifecycle.py
"""

import hashlib
import hmac
import json
import time

import pytest

import onboarding.app as app_mod
import onboarding.provisioner as prov_mod

SECRET = "whsec_test"
SUB_ID = "20260904-000000_tester_abc123"


# ── harness ───────────────────────────────────────────────────────────────────
def _signed(payload: str) -> dict:
    ts = int(time.time())
    sig = hmac.new(SECRET.encode(), f"{ts}.{payload}".encode(),
                   hashlib.sha256).hexdigest()
    return {"Stripe-Signature": f"t={ts},v1={sig}"}


class _Env:
    """A configured onboarding app with an isolated submissions dir, captured
    operator alerts, and a stubbed provisioning queue."""

    def __init__(self, tmp_path, monkeypatch):
        self.dir = tmp_path
        self.client = app_mod.app.test_client()
        self.alerts: list[str] = []
        self.enqueued: list[str] = []

        monkeypatch.setattr(app_mod, "STRIPE_SECRET_KEY", "sk_test_x")
        monkeypatch.setattr(app_mod, "STRIPE_WEBHOOK_SECRET", SECRET)
        monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)
        monkeypatch.setattr(app_mod, "AUTO_PROVISION", True)
        monkeypatch.setattr(app_mod, "_send_operator_message", self.alerts.append)
        monkeypatch.setattr(prov_mod, "SUBMISSIONS_DIR", tmp_path)
        monkeypatch.setattr(prov_mod, "is_configured", lambda: True)
        monkeypatch.setattr(prov_mod, "enqueue",
                            lambda sid, require_paid=True: self.enqueued.append(sid))

    def submission(self, **fields) -> dict:
        d = {"id": SUB_ID, "full_name": "Test Customer",
             "email": "test@example.com", "handle": "tester",
             "trading_format": "balanced", "starting_balance": 1000.0,
             "payment_status": "pending"}
        d.update(fields)
        (self.dir / f"{d['id']}.json").write_text(json.dumps(d))
        return d

    def stored(self, sub_id: str = SUB_ID) -> dict:
        return json.loads((self.dir / f"{sub_id}.json").read_text())

    def send(self, event_type: str, obj: dict, event_id: str = "evt_test_1"):
        payload = json.dumps({
            "id": event_id, "object": "event", "api_version": "2025-05-28.basil",
            "type": event_type, "data": {"object": obj},
        })
        return self.client.post("/stripe/webhook", data=payload,
                                headers=_signed(payload))

    def alerts_text(self) -> str:
        return "\n".join(self.alerts)


@pytest.fixture
def env(tmp_path, monkeypatch):
    return _Env(tmp_path, monkeypatch)


def _session(**over) -> dict:
    d = {"id": "cs_test_1", "object": "checkout.session",
         "client_reference_id": SUB_ID, "customer": "cus_123",
         "subscription": "sub_123", "payment_status": "paid"}
    d.update(over)
    return d


# ── checkout: only a genuinely paid session gets a bot ────────────────────────
def test_unpaid_checkout_session_does_not_provision(env):
    """A delayed payment method completes Checkout BEFORE the funds clear
    (payment_status="unpaid"). Marking that paid ships a bot for money that may
    never arrive, so it must park as awaiting_payment and provision nothing."""
    env.submission()
    assert env.send("checkout.session.completed",
                    _session(payment_status="unpaid")).status_code == 200

    stored = env.stored()
    assert stored["payment_status"] == "awaiting_payment"
    assert stored["billing"]["status"] == "awaiting_payment"
    assert env.enqueued == []
    assert "has NOT cleared" in env.alerts_text()


def test_full_discount_checkout_still_provisions(env):
    """The Founder-100 coupon makes the first invoice $0, so Stripe reports
    payment_status="no_payment_required". That is a real customer — provision."""
    env.submission()
    assert env.send("checkout.session.completed",
                    _session(payment_status="no_payment_required")).status_code == 200

    stored = env.stored()
    assert stored["payment_status"] == "paid"
    assert stored["billing"]["status"] == "active"
    assert env.enqueued == [SUB_ID]


def test_paid_checkout_records_stripe_ids_and_provisions(env):
    env.submission()
    assert env.send("checkout.session.completed", _session()).status_code == 200

    stored = env.stored()
    assert stored["payment_status"] == "paid"
    assert stored["stripe_customer"] == "cus_123"
    assert stored["stripe_subscription"] == "sub_123"
    assert env.enqueued == [SUB_ID]


def test_expanded_stripe_ids_are_stored_as_bare_ids(env):
    """An expanded customer/subscription arrives as a nested object. Storing the
    object would make every later lookup by id silently miss, orphaning the
    customer's whole billing lifecycle."""
    env.submission()
    env.send("checkout.session.completed",
             _session(customer={"id": "cus_123", "object": "customer"},
                      subscription={"id": "sub_123", "object": "subscription"}))

    stored = env.stored()
    assert stored["stripe_customer"] == "cus_123"
    assert stored["stripe_subscription"] == "sub_123"


def test_payment_for_unknown_submission_alerts_the_operator(env):
    """Money moved and we cannot tie it to anyone. This is the only failure mode
    that leaves a real person charged with no bot and no record, so it must never
    be a quiet 200."""
    assert env.send("checkout.session.completed",
                    _session(client_reference_id="does-not-exist")).status_code == 200

    text = env.alerts_text()
    assert "NO matching submission" in text
    assert "cus_123" in text and "sub_123" in text
    assert env.enqueued == []


def test_async_payment_succeeded_provisions_late(env):
    """The delayed payment finally cleared — now the customer is really paid."""
    env.submission(payment_status="awaiting_payment")
    assert env.send("checkout.session.async_payment_succeeded",
                    _session()).status_code == 200

    assert env.stored()["payment_status"] == "paid"
    assert env.enqueued == [SUB_ID]


def test_async_payment_failed_leaves_no_bot(env):
    env.submission(payment_status="awaiting_payment")
    env.send("checkout.session.async_payment_failed", _session(payment_status="unpaid"))

    stored = env.stored()
    assert stored["payment_status"] == "pending"
    assert stored["billing"]["status"] == "payment_failed"
    assert env.enqueued == []
    assert "payment FAILED" in env.alerts_text()


def test_expired_checkout_marks_the_signup_abandoned(env):
    """An abandoned cart should stop showing as an eternally 'pending' signup."""
    env.submission()
    env.send("checkout.session.expired", _session(payment_status="unpaid"))
    assert env.stored()["payment_status"] == "abandoned"


def test_expired_checkout_never_downgrades_a_paid_signup(env):
    """Stripe can deliver an expiry for an earlier abandoned session after the
    customer succeeded on a second one. That must not un-pay them."""
    env.submission(payment_status="paid")
    env.send("checkout.session.expired", _session(payment_status="unpaid"))
    assert env.stored()["payment_status"] == "paid"


# ── replay protection ─────────────────────────────────────────────────────────
def test_retried_event_is_processed_once(env):
    """Stripe re-delivers any event it doesn't see a 2xx for, and can deliver
    duplicates regardless. Without a ledger the retry re-runs the paid path and
    double-enqueues provisioning."""
    env.submission()
    for _ in range(3):
        assert env.send("checkout.session.completed", _session(),
                        event_id="evt_dup").status_code == 200
    assert env.enqueued == [SUB_ID]


def test_a_failing_handler_releases_its_claim_for_the_retry(env, monkeypatch):
    """If a handler throws (transient disk error, say), the claim must be
    released and a 500 returned — otherwise Stripe's retry hits an already-claimed
    marker and the money event is lost forever behind a 200."""
    calls = {"n": 0}

    def flaky(session, event_type):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("disk hiccup")
        app_mod._handle_checkout_completed(session, event_type)

    env.submission()
    monkeypatch.setitem(app_mod._EVENT_HANDLERS, "checkout.session.completed", flaky)

    assert env.send("checkout.session.completed", _session(),
                    event_id="evt_flaky").status_code == 500
    assert env.stored()["payment_status"] == "pending"

    # Stripe's retry of the SAME event id must actually run the handler again.
    assert env.send("checkout.session.completed", _session(),
                    event_id="evt_flaky").status_code == 200
    assert env.stored()["payment_status"] == "paid"


def test_unhandled_event_types_are_quietly_acknowledged(env):
    """Enabling extra events in the Stripe dashboard must never 500 the endpoint
    (which would flag it as failing and start retrying everything)."""
    assert env.send("customer.created", {"id": "cus_123"}).status_code == 200


# ── renewals and dunning ──────────────────────────────────────────────────────
def _paid_customer(env, **over):
    return env.submission(payment_status="paid", stripe_customer="cus_123",
                          stripe_subscription="sub_123", **over)


def test_failed_renewal_flags_past_due_and_alerts(env):
    """A declined renewal is the start of churn. The bot deliberately keeps
    running (Stripe is still retrying the card), but the operator must know."""
    _paid_customer(env)
    env.send("invoice.payment_failed", {
        "id": "in_1", "object": "invoice", "customer": "cus_123",
        "subscription": "sub_123", "amount_due": 9900, "currency": "usd",
        "attempt_count": 2})

    billing = env.stored()["billing"]
    assert billing["status"] == "past_due"
    assert billing["failed_attempts"] == 2
    text = env.alerts_text()
    assert "renewal payment FAILED" in text
    assert "99.00 USD" in text


def test_failed_renewal_matches_the_2025_invoice_shape(env):
    """Stripe's 2025 API versions moved invoice.subscription under
    invoice.parent.subscription_details.subscription. Reading only the old field
    would leave every renewal event unmatched on a current account."""
    _paid_customer(env)
    env.send("invoice.payment_failed", {
        "id": "in_2", "object": "invoice", "customer": "cus_999",
        "parent": {"subscription_details": {"subscription": "sub_123"}},
        "amount_due": 9900, "currency": "usd", "attempt_count": 1})

    assert env.stored()["billing"]["status"] == "past_due"


def test_a_recovered_card_clears_past_due(env):
    """The customer fixed their card — they must not stay flagged past_due."""
    _paid_customer(env, billing={"status": "past_due", "failed_attempts": 2})
    env.send("invoice.paid", {
        "id": "in_3", "object": "invoice", "customer": "cus_123",
        "subscription": "sub_123", "amount_paid": 9900, "currency": "usd"})

    billing = env.stored()["billing"]
    assert billing["status"] == "active"
    assert billing["failed_attempts"] == 0


def test_invoice_event_falls_back_to_the_customer_id(env):
    """Renewal invoices for a customer whose subscription id we never stored
    still have to find their submission."""
    env.submission(payment_status="paid", stripe_customer="cus_123")
    env.send("invoice.payment_failed", {
        "id": "in_4", "object": "invoice", "customer": "cus_123",
        "amount_due": 9900, "currency": "usd", "attempt_count": 1})

    assert env.stored()["billing"]["status"] == "past_due"


def test_subscription_metadata_matches_when_stripe_ids_are_missing(env):
    """We stamp the submission id onto the subscription at checkout, so billing
    still reconciles for a submission restored from a backup without its ids."""
    env.submission(payment_status="paid")
    env.send("customer.subscription.deleted", {
        "id": "sub_123", "object": "subscription", "customer": "cus_123",
        "status": "canceled", "metadata": {"submission_id": SUB_ID}})

    assert env.stored()["billing"]["status"] == "canceled"


# ── churn, refunds, chargebacks ───────────────────────────────────────────────
def test_cancellation_is_recorded_and_alerted_but_never_auto_deletes(env):
    """A cancelled customer's bot may hold open positions with their own money.
    Tearing it down from a webhook could strand them, so the operator is told
    exactly what to run instead."""
    _paid_customer(env, provisioning={"status": "provisioned"})
    env.send("customer.subscription.deleted", {
        "id": "sub_123", "object": "subscription", "customer": "cus_123",
        "status": "canceled"})

    stored = env.stored()
    assert stored["billing"]["status"] == "canceled"
    assert stored["provisioning"]["status"] == "provisioned"   # untouched
    text = env.alerts_text()
    assert "CANCELLED" in text
    assert f"deprovision {SUB_ID}" in text


def test_pending_cancellation_is_surfaced_before_it_takes_effect(env):
    _paid_customer(env, billing={"status": "active"})
    env.send("customer.subscription.updated", {
        "id": "sub_123", "object": "subscription", "customer": "cus_123",
        "status": "active", "cancel_at_period_end": True})

    assert env.stored()["billing"]["cancel_at_period_end"] is True
    assert "CANCEL at period end" in env.alerts_text()


def test_subscription_going_unpaid_is_alerted_once(env):
    """Stripe has exhausted its card retries. The bot is still running, so this
    needs an alert — but repeated updates in the same state must not spam."""
    _paid_customer(env, billing={"status": "past_due"})
    payload = {"id": "sub_123", "object": "subscription", "customer": "cus_123",
               "status": "unpaid"}
    env.send("customer.subscription.updated", payload, event_id="evt_u1")
    env.send("customer.subscription.updated", payload, event_id="evt_u2")

    assert env.stored()["billing"]["status"] == "unpaid"
    assert env.alerts_text().count("now UNPAID") == 1


def test_refund_is_recorded(env):
    _paid_customer(env)
    env.send("charge.refunded", {
        "id": "ch_1", "object": "charge", "customer": "cus_123",
        "amount_refunded": 24900, "currency": "usd"})

    assert env.stored()["billing"]["status"] == "refunded"
    assert "249.00 USD" in env.alerts_text()


def test_chargeback_alerts_with_the_stored_consent_evidence(env):
    _paid_customer(env, consent={"terms_version": "2026-07-09",
                                 "accepted_at": "2026-09-01T00:00:00+00:00",
                                 "ip": "203.0.113.7"})
    env.send("charge.dispute.created", {
        "id": "dp_1", "object": "dispute", "customer": "cus_123",
        "charge": "ch_1", "amount": 24900, "currency": "usd",
        "reason": "fraudulent"})

    assert env.stored()["billing"]["status"] == "disputed"
    text = env.alerts_text()
    assert "DISPUTED" in text and "fraudulent" in text
    assert "evidence deadline" in text


def test_unmatched_chargeback_still_alerts(env):
    """A dispute has a response deadline and is lost by default if ignored — so
    it is alerted even when it matches no submission."""
    assert env.send("charge.dispute.created", {
        "id": "dp_2", "object": "dispute", "customer": "cus_unknown",
        "charge": "ch_2", "amount": 24900, "currency": "usd",
        "reason": "product_not_received"}).status_code == 200
    assert "DISPUTED" in env.alerts_text()


# ── the churn gate on provisioning ────────────────────────────────────────────
def test_provision_refuses_a_churned_customer(env):
    """payment_status stays "paid" from the first invoice forever, so it alone
    cannot gate deployment. A cancelled or charged-back customer must not get a
    bot — including from a resume after a partial failure."""
    env.submission(payment_status="paid", billing={"status": "canceled"})
    with pytest.raises(prov_mod.ProvisionError) as exc:
        prov_mod.provision(SUB_ID)
    assert exc.value.step == "billing"


def test_operator_override_can_still_deploy_a_churned_customer(env, monkeypatch):
    """require_paid=False is the operator's explicit decision (the /admin button
    and admin_cli provision) — it must not be blocked by the churn gate."""
    env.submission(payment_status="paid", billing={"status": "canceled"})
    monkeypatch.setattr(prov_mod, "RAILWAY_PROJECT_ID", "")     # stop at locate_project
    monkeypatch.setattr(prov_mod, "RAILWAY_ENVIRONMENT_ID", "")
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: None)
    with pytest.raises(prov_mod.ProvisionError) as exc:
        prov_mod.provision(SUB_ID, client=object(), require_paid=False)
    assert exc.value.step == "locate_project"                   # got past billing


def test_boot_sweep_never_resurrects_a_churned_customers_bot(env, monkeypatch):
    """The restart sweep re-enqueues every paid-but-unprovisioned submission. A
    customer who charged back is still payment_status=paid, so without the
    billing check a redeploy would hand them a free bot."""
    requeued: list[str] = []
    monkeypatch.setattr(prov_mod, "enqueue",
                        lambda sid, require_paid=True: requeued.append(sid))
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: None)

    env.submission(payment_status="paid", billing={"status": "disputed"})
    (env.dir / "keep.json").write_text(json.dumps(
        {"id": "keep", "payment_status": "paid", "billing": {"status": "active"}}))

    assert prov_mod.reconcile_pending() == ["keep"]
    assert requeued == ["keep"]


def test_past_due_customers_are_still_served(env, monkeypatch):
    """Stripe is still retrying the card. Killing a live trading bot over one
    failed retry is worse than carrying the customer for a few days."""
    requeued: list[str] = []
    monkeypatch.setattr(prov_mod, "enqueue",
                        lambda sid, require_paid=True: requeued.append(sid))
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: None)

    env.submission(payment_status="paid", billing={"status": "past_due"})
    assert prov_mod.reconcile_pending() == [SUB_ID]


# ── readiness ─────────────────────────────────────────────────────────────────
def test_healthz_requires_encryption_key(env, monkeypatch):
    """Without ONBOARDING_FERNET_KEY every signup is refused at the last step —
    after the customer has already pasted their Kalshi private key. That is not
    a healthy service, whatever Stripe's state."""
    monkeypatch.setattr(app_mod, "FERNET_KEY", "")
    assert env.client.get("/healthz").get_json()["ok"] is False


def test_healthz_reports_storage_durability(env, monkeypatch):
    """Submissions are the only record that a customer paid. On Railway anything
    outside a mounted volume is destroyed by the next redeploy."""
    monkeypatch.setattr(app_mod, "FERNET_KEY", "x" * 44)
    health = env.client.get("/healthz").get_json()
    assert health["ok"] is True                     # heuristic never fails the check
    assert health["submissions_writable"] is True
    assert health["submissions_durable"] is True    # tmp_path is outside the checkout
