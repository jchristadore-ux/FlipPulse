# FlipPulse

15-Minute BTC Up/Down automated trading bot — **single-customer template**.

This repo is a clean, one-bot-per-customer template for deploying the Kalshi
trading bot. You clone it once per customer; each customer gets their own repo
(or Railway project from a shared template), their own Kalshi key, their own
Telegram bot, and their own environment variables. There is **no** multi-tenant
dashboard, signup, or supervisor here — that lives elsewhere.

## Quick start

New customer? Follow **[CUSTOMER_ONBOARDING.md](CUSTOMER_ONBOARDING.md)** — it
walks through creating the Railway project, attaching the state volume, setting
the ~7 env vars, making the customer's Telegram bot, deploying, and verifying.

Every customer starts in **paper mode** (`DEMO_MODE=true`). Going live is a
deliberate later step.

## Repo layout

```
FlipPulse/
├── bot.py                  # entrypoint — Railway runs `python bot.py`   [from markeymachine]
├── ladder.py               # ladder strategy engine                      [from markeymachine]
├── formats.py              # trading format definitions                  [from markeymachine]
├── telegram_utils.py       # Telegram alerts + command handling          [from markeymachine]
├── requirements.txt        # Python deps                                 [from markeymachine]
├── railway.toml            # Railway deploy config (python bot.py)       ✅ in this repo
├── .env.example            # annotated per-customer env vars             ✅ in this repo
├── .gitignore                                                            ✅ in this repo
├── CUSTOMER_ONBOARDING.md  # per-customer runbook                        ✅ in this repo
└── docs/
    ├── TRADING_DOCTRINE.md                                               [from markeymachine]
    └── LADDER_STRATEGY.md                                                [from markeymachine]
```

## Configuration

The bot reads everything from environment variables. See
[`.env.example`](.env.example) for the full annotated list:

- `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PEM` — the customer's Kalshi key
- `DEMO_MODE` (`true` = paper, default), `PAPER_BALANCE`
- `TRADING_FORMAT`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — the customer's own Telegram bot
- `*_STATE_PATH` vars — default to the `/data` Railway volume

## Self-monitoring

Each customer's bot sends its own trade alerts via Telegram and should answer
`/status` (current mode/balance/positions) and `/health-log` (recent activity
tail). Operator oversight is just: add yourself as a second alert recipient on
each customer's bot — see the "Operator oversight" section in the onboarding
runbook. No central dashboard required.

## Code status

> **The trading code (`bot.py`, `ladder.py`, `formats.py`, `telegram_utils.py`,
> `requirements.txt`, and the two docs) is copied unchanged from the
> `markeymachine` repo (branch `main`), leaving everything under `dashboard/`
> behind.** Once those files are in place, confirm which Telegram commands
> `bot.py` already answers and, if `/status` / `/health-log` aren't present,
> add them (and list the real command set in CUSTOMER_ONBOARDING.md step 5).

## Out of scope (by design)

Signup/login · multi-tenant supervisor · running many bots on one box ·
central dashboard · billing.
