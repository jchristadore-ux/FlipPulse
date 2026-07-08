# FlipPulse — Digital Onboarding Service

A small Flask app that gives new customers a single **web form** to sign up. On
submit it:

1. **Encrypts** the customer's secrets (Kalshi PEM + API key id, Telegram bot
   token) at rest and writes a **submission file** to `submissions/` — the backend
   admin file you open to deploy.
2. **Alerts you** (the operator) on Telegram with a non-secret summary.
3. Launches **Stripe Checkout** to collect the **$99 setup fee** and start the
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
| `STRIPE_SETUP_PRICE_ID` | for payment | One-time $99 setup **Price** id (`price_...`); a `prod_...` is auto-resolved to its default price too. |
| `STRIPE_WEBHOOK_SECRET` | **required with Stripe** | Verifies `checkout.session.completed` so a submission is marked **paid** (which triggers auto-provisioning). Without it, paid customers are never marked paid and never provisioned — the app logs an ERROR at boot, `/healthz` reports `ok: false`, and the webhook returns 500 so Stripe flags the endpoint. |
| `ADMIN_TOKEN` | optional | Enables the operator dashboard at `/admin`. Unset = dashboard disabled (routes 404). |
| `PUBLIC_BASE_URL` | optional | Public https URL (for Stripe success/cancel redirects). Defaults to the request host. |
| `SUBMISSIONS_DIR` | optional | Where submission files are written (default `./submissions`; put on a Railway volume to persist). |
| `ONBOARDING_PRICE_SETUP` / `ONBOARDING_PRICE_MONTHLY` | optional | Display-only pricing on the form (default `99` / `99`). |
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
- Submission files are `chmod 600` and git-ignored. Rotate `ONBOARDING_FERNET_KEY`
  by re-encrypting existing submissions if it is ever exposed.
- **Back up `ONBOARDING_FERNET_KEY` the day you generate it** (password manager, at
  minimum two places). It is a single point of failure: lose it and every stored
  submission — including paying customers not yet provisioned — is permanently
  unreadable. Rotation procedure: generate a new key, decrypt each submission's
  `secrets_encrypted` values with the old key and re-encrypt with the new one,
  swap the env var, redeploy, then destroy the old key.
- Funds stay on Kalshi — this service never touches customer money; it only
  collects setup/subscription payment via Stripe.
