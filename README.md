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
├── telegram_utils.py       # Telegram alerts (+ operator fan-out)         [from markeymachine]
├── command_bot.py          # /status + /health-log command listener       ✅ in this repo
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

> **The trading code (`bot.py`, `ladder.py`, `formats.py`, `telegram_utils.py`,
> `requirements.txt`, and `docs/TRADING_DOCTRINE.md` + `docs/LADDER_STRATEGY.md`)
> is copied unchanged from the `markeymachine` repo (branch `main`), leaving
> everything under `dashboard/` behind.** On top of that copy, this repo adds a
> thin single-customer layer: `command_bot.py` (answers `/status` and
> `/health-log`, started from `bot.py`'s entrypoint) and operator fan-out in
> `telegram_utils.py` (`TELEGRAM_OPERATOR_CHAT_ID`). Paper-only by default
> (`DEMO_MODE=true`); nothing here enables live trading.

## Out of scope (by design)

Signup/login · multi-tenant supervisor · running many bots on one box ·
central dashboard · billing.
