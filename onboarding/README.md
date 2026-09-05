# FlipPulse — Digital Onboarding Service

A small Flask app that gives new customers a single **web form** to sign up. On
submit it:

1. **Encrypts** the customer's secrets (Kalshi PEM + API key id, Telegram bot
   token) at rest and writes a **submission file** to `submissions/` — the backend
   admin file you open to deploy.
2. **Alerts you** (the operator) on Telegram with a non-secret summary.
3. Launches **Stripe Checkout** to collect the **$150 setup fee** and start the
   **$99/mo subscription**, keeping the card on file for any future invoices.
4. **Provisions the customer's bot automatically** once Stripe confirms payment:
   the built-in provisioner (`provisioner.py`) creates the Railway project,
   service, `/data` volume, injects every variable, deploys, and verifies the
   boot logs — then tells you on Telegram. See
   [`../AUTOMATED_PROVISIONING.md`](../AUTOMATED_PROVISIONING.md).

Manual fallback: `admin_cli.py show <id>` still prints the exact env vars for
deploying by hand per [`../ADMINISTRATOR_ONBOARDING.md`](../ADMINISTRATOR_ONBOARDING.md).

```
onboarding/
├── app.py            # Flask server (form + submit + Stripe + operator alert)
├── provisioner.py    # automated Railway provisioning (webhook → running bot)
├── admin_cli.py      # list/show/env/provision/status/deprovision
├── templates/        # form.html, success.html, cancelled.html
├── submissions/      # runtime submission files (git-ignored, encrypted)
└── requirements.txt
```

## 1. Configure

Generate an encryption key once and keep it secret (it decrypts every
submission):

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Environment variables:

| Variable | Required | Purpose |
|---|---|---|
| `ONBOARDING_FERNET_KEY` | **yes** | Encrypts/decrypts submission secrets. The form refuses to store secrets without it. |
| `ONBOARDING_TELEGRAM_BOT_TOKEN` | recommended | Operator-alert bot (a bot you own). |
| `ONBOARDING_TELEGRAM_CHAT_ID` | recommended | Your chat id for signup alerts. |
| `STRIPE_SECRET_KEY` | for payment | Stripe secret key (`sk_live_...` / `sk_test_...`). |
| `STRIPE_MONTHLY_PRICE_ID` | for payment | Recurring $99/mo **Price** id (`price_...`). If you paste a **Product** id (`prod_...`) by mistake — the id the Stripe dashboard shows most prominently — the service auto-resolves it to that product's default price so checkout still works. |
| `STRIPE_SETUP_PRICE_ID` | for payment | One-time $150 setup **Price** id (`price_...`); a `prod_...` is auto-resolved to its default price too. |
| `STRIPE_WEBHOOK_SECRET` | **required with Stripe** | Verifies every webhook — the checkout that marks a submission **paid** (triggering auto-provisioning) and the whole billing lifecycle after it (see [§1a](#1a-stripe-webhook-events--required)). Without it, paid customers are never marked paid and never provisioned — the app logs an ERROR at boot, `/healthz` reports `ok: false`, and the webhook returns 500 so Stripe flags the endpoint. |
| `FOUNDING_COUPON_ID` | optional | A Stripe **coupon** id (e.g. the "Founder 100" `$249-off-once` coupon, id like `10xGeLZu`) auto-applied to **every** signup — no code for the customer to type. When the coupon is exhausted/expired, checkout retries once at full price so signups never break; unset it to end the offer. Mutually exclusive with `STRIPE_ALLOW_PROMO_CODES`. |
| `STRIPE_ALLOW_PROMO_CODES` | optional | `true` shows an "Add promotion code" box on the Stripe Checkout page so customers can type a code (e.g. `FOUNDER100`). Ignored when `FOUNDING_COUPON_ID` is set (Stripe rejects a session using both). |
| `ADMIN_TOKEN` | optional | Enables the operator dashboard at `/admin`. Unset = dashboard disabled (routes 404). |
| `PUBLIC_BASE_URL` | optional | Public https URL (for Stripe success/cancel redirects). Defaults to the request host. |
| `SUBMISSIONS_DIR` | optional | Where submission files are written. **Set this to `/data/submissions` on a mounted volume whenever Stripe is live** — the default `./submissions` is inside the code checkout, which Railway destroys on every redeploy, taking payment status, Stripe ids, billing history and encrypted credentials with it. The app logs an ERROR at boot in that combination, and `/healthz` reports `submissions_durable: false`. |
| `ONBOARDING_PRICE_SETUP` / `ONBOARDING_PRICE_MONTHLY` | optional | Display-only pricing on the form (default `150` / `99`). |
| `ONBOARDING_PERF_PCT` | optional | Placeholder for a future performance fee; default `0` and **not shown** on the form. |
| `RAILWAY_API_TOKEN` | for auto-provisioning | Railway account/workspace token — enables zero-touch bot deployment on payment. |
| `RAILWAY_PROJECT_ID` / `RAILWAY_ENVIRONMENT_ID` | auto on Railway | The project + environment customer bots are deployed into as sibling services. Railway injects both into the onboarding service; set them only when running outside Railway. |
| `AUTO_PROVISION` | optional (default `true`) | Provision automatically on `checkout.session.completed`. `false` = use the `/admin` button or CLI. |
| `PROVISION_REPO` / `PROVISION_REPO_BRANCH` | optional | Repo/branch every customer bot deploys from (default `jchristadore-ux/FlipPulse` @ `release` — the pinned fleet branch; promote with `git push origin main:release`). |
| `BOT_OPERATOR_CHAT_ID` | recommended | Injected into every provisioned bot as `TELEGRAM_OPERATOR_CHAT_ID` so all customer-bot alerts fan out to you. |

Full provisioning reference (all knobs, failure handling, architecture):
[`../AUTOMATED_PROVISIONING.md`](../AUTOMATED_PROVISIONING.md).

If Stripe is not configured the form still works — it stores the submission,
alerts you, and shows a local success page (you collect payment manually).

## 1a. Stripe webhook events — required

Create one endpoint in the Stripe dashboard (**Developers → Webhooks → Add
endpoint**) pointing at `POST https://<your-host>/stripe/webhook`, and enable
**all** of the events below. Stripe only sends what you select: an event you
leave off is not an error anywhere, it is simply a part of the money path that
silently never happens.

| Event | What it does | Cost of leaving it off |
|---|---|---|
| `checkout.session.completed` | Marks the submission **paid**, stores the Stripe customer/subscription ids, provisions the bot | Nobody is ever marked paid; no bot is ever deployed |
| `checkout.session.async_payment_succeeded` | Provisions after a **delayed** payment method finally clears | Customers paying by bank debit pay and never get a bot |
| `checkout.session.async_payment_failed` | Records the failure, keeps the signup unprovisioned | A declined delayed payment looks identical to a pending one |
| `checkout.session.expired` | Marks an abandoned cart `abandoned` | `/admin` fills with signups stuck on "pending" forever |
| `invoice.paid` *(or `invoice.payment_succeeded`)* | Records each renewal; clears `past_due` when a card is fixed | A customer who fixes their card stays flagged past due |
| `invoice.payment_failed` | Flags `past_due` and alerts you while Stripe retries the card | You learn about churn only after the money has stopped |
| `customer.subscription.updated` | Tracks status and a pending end-of-period cancellation | No warning before a cancellation lands |
| `customer.subscription.deleted` | Flags `canceled` and alerts you to deprovision | **Cancelled customers keep a running bot for free, indefinitely** |
| `charge.refunded` | Flags `refunded` | A refunded customer keeps their bot |
| `charge.dispute.created` | Urgent alert with the stored consent evidence | A chargeback is **lost by default** if you miss the evidence deadline |

Two deliberate behaviours worth knowing:

* **Nothing is ever auto-deprovisioned.** A cancellation, refund or chargeback
  records the state and alerts you — it never deletes the customer's service,
  because that bot may be holding open positions with the customer's own money.
  You run `python admin_cli.py deprovision <id>` once they have flattened.
* **`past_due` keeps trading.** While Stripe is still retrying the card the
  customer has not left; killing a live trading bot over one failed retry is
  worse than carrying them for a few days. Only `canceled` / `unpaid` /
  `refunded` / `disputed` block a (re-)deployment.

Verify with **Stripe CLI** before going live:

```bash
stripe listen --forward-to localhost:8080/stripe/webhook
stripe trigger checkout.session.completed
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted
```

## 2. Run

```bash
pip install -r requirements.txt
# local
python app.py                      # http://localhost:8080
# production (Railway/any host — MUST be HTTPS, the form collects a private key)
gunicorn app:app --bind 0.0.0.0:$PORT
```

Deploy it as its **own** Railway service (separate from each customer's bot):

1. **New Project → Deploy from GitHub repo →** pick the FlipPulse repo.
2. Service → **Settings → Source → Root Directory** = `onboarding`. Railway then
   reads [`onboarding/railway.toml`](railway.toml) (which sets the gunicorn start
   command) instead of the repo-root `railway.toml` that runs `python bot.py`.
3. **Variables** tab → add the env vars from the table above.
4. **Networking → Generate Domain** for a public https URL; set `PUBLIC_BASE_URL`
   to it.
5. Mount a **Volume** at `/data` and set `SUBMISSIONS_DIR=/data/submissions` so
   submissions survive redeploys.

> Because `onboarding/railway.toml` sets the start command, you do **not** need to
> type a Custom Start Command in the Railway UI (that field is otherwise locked by
> the repo-root config).

## 3. Process a signup

**Operator dashboard (easiest).** Set `ADMIN_TOKEN` and open
`https://<your-host>/admin?token=<ADMIN_TOKEN>` — that sets an httponly cookie, lists
every signup with its payment status, and each row links to a **deploy view** that shows
the ready-to-paste Railway variables (decrypted server-side). Operator-only; the routes
404 without the token.

**CLI (equivalent).**

```bash
ONBOARDING_FERNET_KEY=... python admin_cli.py list
ONBOARDING_FERNET_KEY=... python admin_cli.py show 20260701-120000_jane_ab12cd
```

Both print the ready-to-paste Railway variables (the customer's `TRADING_FORMAT`,
`PAPER_BALANCE`, and the decrypted keys). Follow the administrator runbook from there.

## Security notes

- Secrets are **encrypted at rest** (Fernet) and are **never logged** or sent to
  Telegram. Only `ONBOARDING_FERNET_KEY` can decrypt them.
- Serve **only over HTTPS**. The form transmits a Kalshi private key.
- Submission files are `chmod 600` and git-ignored.

### ⚠️ Fernet key backup and recovery

`ONBOARDING_FERNET_KEY` is a **single point of failure**. Losing it makes every
stored submission secret permanently unreadable, including paid customers who
have not yet been provisioned. Store a copy in a password manager or secure
secrets vault (ideally with a second authorized backup); never commit it to git,
place it in a submission file, or paste it into logs or chat.

There is no automatic key rotation. If rotation is ever required, plan a
maintenance window: retain the old key securely, decrypt each submission's
`secrets_encrypted` values with the old key, re-encrypt them with a newly
 generated key, verify the files, then swap the environment variable and
redeploy. Destroy the old key only after recovery has been verified. Do not
attempt rotation without a tested backup and an operator-approved procedure.
- Funds stay on Kalshi — this service never touches customer money; it only
  collects setup/subscription payment via Stripe.
