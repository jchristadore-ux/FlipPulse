# FlipPulse

15-Minute BTC Up/Down automated trading bot — **single-customer template**.

All position sizing is **percentage-based** (a fraction of the current balance),
so one template fits every customer regardless of their starting balance and the
stake compounds as the account grows.

This repo is a clean, one-bot-per-customer template for deploying the Kalshi
trading bot. You clone it once per customer; each customer gets their own repo
(or Railway project from a shared template), their own Kalshi key, their own
Telegram bot, and their own environment variables. There is **no** multi-tenant
dashboard, signup, or supervisor here — that lives elsewhere.

## Quick start

Deploying a new customer? Follow
**[ADMINISTRATOR_ONBOARDING.md](ADMINISTRATOR_ONBOARDING.md)** — it walks through
creating the Railway project, attaching the state volume, setting the env vars
(including the customer's chosen `TRADING_FORMAT` and starting balance), making the
Telegram bot, deploying, and verifying. The customer-facing PDFs live in `docs/`
(see [CUSTOMER_ONBOARDING.md](CUSTOMER_ONBOARDING.md) for the map).

Every customer starts in **paper mode** (`DEMO_MODE=true`). Going live is a
deliberate later step.

## Repo layout

```
FlipPulse/
├── bot.py                       # entrypoint — Railway runs `python bot.py` (percentage sizing)
├── ladder.py                    # ladder stake overlay engine
├── formats.py                   # trading format definitions (conservative/balanced/aggressive)
├── telegram_utils.py            # Telegram alerts (+ operator fan-out)
├── command_bot.py               # /status + /health-log command listener
├── requirements.txt             # Python deps
├── railway.toml                 # Railway deploy config (python bot.py)
├── .env.example                 # annotated per-customer env vars
├── .gitignore
├── ADMINISTRATOR_ONBOARDING.md  # deploy-a-new-customer runbook (admin)
├── CUSTOMER_ONBOARDING.md       # map of the onboarding docs
└── docs/
    ├── FlipPulse_Customer_Onboarding.pdf   # customer: how it works + pick a format
    ├── FlipPulse_Customer_Onboarding.html  # (source for the PDF)
    ├── FlipPulse_Customer_Setup.pdf        # customer: send-us-your-details sheet
    ├── customer-setup.html                 # (source for the setup PDF)
    ├── TRADING_DOCTRINE.md
    └── LADDER_STRATEGY.md
```

## Configuration

The bot reads everything from environment variables. See
[`.env.example`](.env.example) for the full annotated list:

- `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PEM` — the customer's Kalshi key
- `DEMO_MODE` (`true` = paper, default), `PAPER_BALANCE`
- `TRADING_FORMAT` — `conservative` | `balanced` | `aggressive` (the branded risk
  modes; run `python formats.py` for the full breakdown)
- `NORMAL_TRADE_PCT`, `RECOVERY_TRADE_PCT`, `MAX_TRADE_PCT` — **percentage** sizing
  (fractions of the current balance); optional per-customer overrides of the format
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — the customer's own Telegram bot
- `TELEGRAM_OPERATOR_CHAT_ID` — optional; also fans alerts out to you (operator)
- `*_STATE_PATH`, `STATUS_SNAPSHOT_PATH`, `HEALTH_LOG_PATH` — pre-pointed at the
  `/data` Railway volume so state, the status snapshot, and the health log
  persist across redeploys (keep them set; the code's unset fallback is
  ephemeral)

## Self-monitoring

Each customer's bot sends its own alerts via Telegram (boot, 15-min heartbeat,
trade entry, win/loss, daily summary) and answers three read-only commands
(`command_bot.py`, started by `bot.py` on boot):

- **`/status`** — mode (paper/live), format, balance, session PnL, W/L record,
  ladder/recovery/probation mode + size, open positions, session state, last
  signal, and last-tick time.
- **`/health-log [n]`** — tails the recent health/activity log.
- **`/help`** — lists the commands.

The commands never change trading — no order placement, no `DEMO_MODE` flip.
Operator oversight is just setting `TELEGRAM_OPERATOR_CHAT_ID` to your own chat
id so every alert also reaches you — see "Operator oversight" in the onboarding
runbook. No central dashboard required.

## Code status

> **The trading strategy (`bot.py`, `ladder.py`, `telegram_utils.py`) derives from
> the `markeymachine` repo, converted here to PERCENTAGE-BASED sizing** (v10.0.0):
> every stake is a fraction of the current balance resolved at one chokepoint
> (`active_trade_size`), so the template scales to any starting balance and
> compounds. The owner-specific hardcoded stake override and the fixed-dollar
> high-stake balance gate were removed. On top of that, this repo adds a thin
> single-customer layer: `command_bot.py` (answers `/status` and `/health-log`,
> started from `bot.py`'s entrypoint) and operator fan-out in `telegram_utils.py`
> (`TELEGRAM_OPERATOR_CHAT_ID`). Paper-only by default (`DEMO_MODE=true`); nothing
> here enables live trading.

## Out of scope (by design)

Signup/login · multi-tenant supervisor · running many bots on one box ·
central dashboard · billing.
