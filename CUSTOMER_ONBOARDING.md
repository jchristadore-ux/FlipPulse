# Onboarding — where each guide lives

FlipPulse onboarding is split into a **customer-facing** part and an
**administrator (deployment)** part. This file used to hold the deployment runbook;
that content now lives in the administrator guide below.

## The signup flow (digital form)

Customers sign up through the **digital onboarding form** —
[`onboarding/`](onboarding/README.md) (Flask). On submit it encrypts their keys into a
backend submission file, alerts you on Telegram, and takes payment via Stripe ($99 setup
+ $99/mo, card on file for the 20% performance fee). You then run
`onboarding/admin_cli.py show <id>` to get the deploy variables — see the administrator
guide.

## For the customer (branded leave-behind)

- **[`docs/FlipPulse_Customer_Onboarding.pdf`](docs/FlipPulse_Customer_Onboarding.pdf)**
  — how FlipPulse works, the feature/why/pricing overview, and the **Trading Format**
  breakdown (Conservative / Balanced / Aggressive) with a box to **pick one**.
- **[`docs/FlipPulse_Customer_Setup.pdf`](docs/FlipPulse_Customer_Setup.pdf)** — the
  short "send us your details" sheet (Kalshi API key + PEM, Telegram bot token + chat
  id, starting balance).

## For the administrator (deploy a new environment)

- **[`ADMINISTRATOR_ONBOARDING.md`](ADMINISTRATOR_ONBOARDING.md)** — the full runbook:
  create the Railway project, attach the `/data` volume, set the env vars (including the
  customer's chosen `TRADING_FORMAT` and `PAPER_BALANCE`), create the Telegram bot,
  deploy, verify, set up operator oversight, and later go live.

> **Sizing is percentage-based.** You don't set per-customer dollar stakes — you set the
> customer's starting balance (`PAPER_BALANCE`) and their chosen format, and every trade
> is sized as a percentage of the live balance. See §1 of the administrator guide.
