# FlipPulse — Digital Onboarding Service

A small Flask app that gives new customers a single **web form** to sign up. On
submit it:

1. **Encrypts** the customer's secrets (Kalshi PEM + API key id, Telegram bot
   token) at rest and writes a **submission file** to `submissions/` — the backend
   admin file you open to deploy.
2. **Alerts you** (the operator) on Telegram with a non-secret summary.
3. Launches **Stripe Checkout** to collect the **$99 setup fee** and start the
   **$99/mo subscription**, saving the card on file so the monthly **20%
   performance fee** can be invoiced later.

You then run `admin_cli.py show <id>` to get the exact env vars and deploy the
bot per [`../ADMINISTRATOR_ONBOARDING.md`](../ADMINISTRATOR_ONBOARDING.md).

```
onboarding/
├── app.py            # Flask server (form + submit + Stripe + operator alert)
├── admin_cli.py      # list/show/env — turn a submission into deploy env vars
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
| `STRIPE_MONTHLY_PRICE_ID` | for payment | Recurring $99/mo Price id (`price_...`). |
| `STRIPE_SETUP_PRICE_ID` | for payment | One-time $99 setup Price id. |
| `STRIPE_WEBHOOK_SECRET` | optional | Verify `checkout.session.completed` to mark a submission **paid**. |
| `ADMIN_TOKEN` | optional | Enables the operator dashboard at `/admin`. Unset = dashboard disabled (routes 404). |
| `PUBLIC_BASE_URL` | optional | Public https URL (for Stripe success/cancel redirects). Defaults to the request host. |
| `SUBMISSIONS_DIR` | optional | Where submission files are written (default `./submissions`; put on a Railway volume to persist). |
| `ONBOARDING_PRICE_SETUP` / `ONBOARDING_PRICE_MONTHLY` / `ONBOARDING_PERF_PCT` | optional | Display-only pricing on the form (default `99` / `99` / `20`). |

If Stripe is not configured the form still works — it stores the submission,
alerts you, and shows a local success page (you collect payment manually).

## 2. Run

```bash
pip install -r requirements.txt
# local
python app.py                      # http://localhost:8080
# production (Railway/any host — MUST be HTTPS, the form collects a private key)
gunicorn app:app --bind 0.0.0.0:$PORT
```

Deploy it as its **own** Railway service (separate from each customer's bot).
Mount a volume at, say, `/data` and set `SUBMISSIONS_DIR=/data/submissions` so
submissions survive redeploys.

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
- Submission files are `chmod 600` and git-ignored. Rotate `ONBOARDING_FERNET_KEY`
  by re-encrypting existing submissions if it is ever exposed.
- Funds stay on Kalshi — this service never touches customer money; it only
  collects setup/subscription payment via Stripe.
