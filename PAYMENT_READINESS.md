# FlipPulse — Payment Readiness Validation

**Date:** 2026-09-04 · **Scope:** the money path only — `onboarding/app.py`,
`onboarding/provisioner.py`, `onboarding/admin_cli.py`, Stripe configuration and
the operator runbooks. Trading logic is out of scope (covered by
`AUDIT_TRADE_LOGIC_2026-07.md` and `AUDIT_PRODUCTION_READINESS.md`).

**Verdict: not ready as found. Six defects fixed here; four operator actions
remain before the first live charge.** The signup-and-first-payment path was
sound. Everything *after* the first payment did not exist.

---

## 1. The headline finding

The service handled exactly **one** Stripe event: `checkout.session.completed`.

That is enough to take a customer's first payment. It is not enough to run a
subscription business. A customer who cancelled, was refunded, charged back, or
whose card simply expired kept a **fully provisioned, indefinitely running bot**
— and nothing anywhere in the system would ever have told you. The only signal
was money quietly not arriving in Stripe.

`payment_status` was written once, at checkout, and never revisited. It is
therefore not a statement about whether someone is a paying customer; it is a
record that they paid *once*. The boot-time reconciliation sweep
(`reconcile_pending`) read that stale field, so a redeploy would happily
**re-provision a churned customer's bot**.

The service now handles eleven events and tracks billing state for the life of
the customer.

---

## 2. Defects found and fixed

| # | Severity | Defect | Fix |
|---|---|---|---|
| **P-1** | **Critical** | **No subscription lifecycle at all.** Cancellations, failed renewals, refunds and chargebacks were invisible. A cancelled customer kept a free running bot forever. | Ten further Stripe events handled, each recording a `billing` block on the submission and alerting the operator (`_EVENT_HANDLERS`, `app.py`). |
| **P-2** | **Critical** | **A payment that matched no submission returned a silent `200`.** A real person could be charged with no record, no bot and nobody looking. | Unmatched checkouts now raise a 🚨 operator Telegram alert carrying the Stripe customer/subscription ids for reconciliation. |
| **P-3** | **High** | **`checkout.session.completed` was treated as paid unconditionally.** Stripe completes the session *before* funds clear for delayed payment methods (`payment_status: "unpaid"`) — that shipped a bot for money that might never arrive. | Only `paid` / `no_payment_required` provision. `unpaid` parks as `awaiting_payment` and deploys later on `checkout.session.async_payment_succeeded`. A 100%-coupon signup (the Founder-100 offer) still provisions correctly. |
| **P-4** | **High** | **No webhook replay protection.** Stripe retries any delivery it does not see a 2xx for, and can duplicate regardless. A retry re-ran the whole paid path and could double-enqueue provisioning. | Atomic `O_EXCL` per-event-id ledger, durable across gunicorn workers and restarts. A handler that throws **releases its claim** and returns 500, so Stripe's retry is a real second attempt rather than a lost money event. |
| **P-5** | **High** | **The boot sweep could resurrect a churned customer's bot**, because it gated on the never-updated `payment_status`. | `provision()` and `reconcile_pending()` now also refuse `canceled` / `unpaid` / `refunded` / `disputed`. The operator override still deploys deliberately. |
| **P-6** | **Medium** | **`/healthz` reported `ok: true` with no `ONBOARDING_FERNET_KEY`** — every signup would be refused at the final step, *after* the customer had pasted their Kalshi private key. | `ok` now also requires the encryption key and a writable submissions dir; `submissions_durable` is reported separately. |

Two API-compatibility hazards were fixed alongside these, both of which would
have silently orphaned every renewal event on a current Stripe account:

* Stripe's 2025 API versions moved `invoice.subscription` to
  `invoice.parent.subscription_details.subscription`. Both shapes are read.
* Expanded `customer` / `subscription` fields arrive as nested objects rather
  than id strings; storing the object would have made every later lookup miss.
  All Stripe references are normalised to bare ids.

---

## 3. Two deliberate behaviours

These are judgement calls, not oversights, and they are worth agreeing with
before go-live:

**Nothing is ever auto-deprovisioned.** A cancellation, refund or chargeback
records the state and alerts you; it never deletes the customer's service. That
bot may be holding open positions with the customer's own money, and tearing it
down from a webhook could strand them mid-trade. You run
`python admin_cli.py deprovision <id>` once they have flattened. The alert tells
you exactly that, with the command.

**`past_due` keeps trading.** While Stripe is still retrying the card the
customer has not left. Killing a live trading bot over one failed retry is worse
for them and for you than carrying them for a few days. You are alerted on the
first failure and again if the subscription goes `unpaid`.

---

## 4. What is now visible to you

Billing state surfaces in all three operator surfaces, so churn is never
something you have to go looking for in Stripe:

* **Telegram** — alerts for failed renewals, pending cancellations,
  cancellations, refunds, and chargebacks (the last marked urgent: a dispute is
  lost by default if you miss the evidence deadline).
* **`/admin`** — a Billing column in the list; a Billing panel on each customer
  with a direct link to the Stripe subscription. For a chargeback it surfaces the
  stored consent record (terms version, timestamp, IP) — that is your evidence.
* **`admin_cli.py`** — `list` gained a BILLING column; `status <id>` prints the
  full billing block and the Stripe ids.

---

## 5. Before the first live charge — four operator actions

These are configuration, not code. The code cannot do them for you, and each one
is silent when wrong.

1. **Enable every webhook event.** Stripe sends only what you select, and an
   unselected event is not an error anywhere — it is a part of the money path
   that never happens. The full table with the cost of omitting each one is in
   [`onboarding/README.md` §1a](onboarding/README.md#1a-stripe-webhook-events--required).
   Missing `customer.subscription.deleted` alone reinstates the headline bug.

2. **Put `SUBMISSIONS_DIR` on a mounted volume** (`/data/submissions`). The
   default is inside the code checkout, which Railway destroys on every
   redeploy — taking payment status, Stripe ids, billing history and the
   encrypted customer credentials with it. There is no second copy. The app now
   logs an ERROR at boot in this combination and `/healthz` reports
   `submissions_durable: false`.

3. **Rehearse in Stripe test mode**, end to end, with the CLI:
   ```bash
   stripe listen --forward-to localhost:8080/stripe/webhook
   stripe trigger checkout.session.completed
   stripe trigger invoice.payment_failed
   stripe trigger customer.subscription.deleted
   ```
   Confirm: a bot deploys, the failed renewal alerts, the cancellation alerts and
   flips the badge in `/admin`.

4. **Confirm `/healthz` returns `ok: true`** on the deployed service, with
   `stripe_webhook: true` and `submissions_durable: true`.

---

## 6. Recommended next, not blocking

* **Stripe Customer Portal.** Customers currently have no way to update a card
  or cancel without emailing you. Self-serve cancellation measurably reduces
  chargebacks — and a chargeback costs the disputed amount plus a fee, on top of
  the refund. This is the highest-value follow-up.
* **Sales tax / VAT.** Nothing in the checkout collects or remits tax. Whether
  that matters depends on where you sell; worth a decision before volume.
* **Dunning emails.** Stripe can email customers on a failed renewal
  (Settings → Subscriptions → Manage failed payments). Currently only *you* are
  told.
* **The performance fee remains a disabled placeholder** (`PERF_FEE_PCT=0`), by
  design — see `REENABLE_PERFORMANCE_FEE.md`. Nothing here changes that.

---

## 7. Verification

`pytest` — **326 passing** (297 before; 29 added, covering every fix above).

The new suite is `test_onboarding_billing_lifecycle.py`. Every webhook in it is
driven through a genuinely **signed** payload so it goes through
`stripe.Webhook.construct_event` and the handlers see real `StripeObject`s —
which, on stripe ≥ 8, do not support `.get()`. That distinction is not
theoretical here: it previously 500'd every real completed checkout while the
mocked tests stayed green.

Each new guard was mutation-tested — the guard was disabled in the source and
the suite re-run — to confirm the tests fail without it rather than passing
vacuously:

| Guard disabled | Test that failed |
|---|---|
| the `payment_status` check | `test_unpaid_checkout_session_does_not_provision` |
| the replay ledger | `test_retried_event_is_processed_once` |
| the churn gate | `test_provision_refuses_a_churned_customer`, `test_boot_sweep_never_resurrects_a_churned_customers_bot` |
| the 2025 invoice shape | `test_failed_renewal_matches_the_2025_invoice_shape` |

All four mutations were reverted and the full suite re-run green.
