# Customer Onboarding Runbook

This is the checklist for standing up **one new customer** on FlipPulse. Every
customer gets their own Railway project, their own Kalshi key, and their own
Telegram bot. There is no shared dashboard, no signup, and no multi-tenant
supervisor — one repo/template → one Railway project → one bot per customer.

Every customer starts in **paper mode** (`DEMO_MODE=true`). Going live is a
separate, deliberate step (see the last section).

Budget ~15 minutes per customer.

---

## 0. Prerequisites (collect before you start)

- [ ] The customer's **Kalshi API key** — the API Key ID and the RSA private
      key PEM. (Customer creates these in Kalshi → Settings → API Keys, or you
      create them on their behalf on their account.)
- [ ] A short customer handle for naming, e.g. `acme` — used for the Railway
      project name and the Telegram bot name.

---

## 1. Create the Railway project from the template

You can clone either way; pick one and stay consistent:

**Option A — GitHub template repo (recommended):**
1. On GitHub, use this repo as a template ("Use this template" → new repo named
   `flippulse-<customer>`), or clone it into the customer's own repo.
2. In Railway: **New Project → Deploy from GitHub repo →** pick
   `flippulse-<customer>`.

**Option B — Railway template:**
1. In Railway: **New Project → Deploy from Template →** select the saved
   FlipPulse template.

Railway reads `railway.toml`, builds with Nixpacks, and runs `python bot.py`.
It will fail/crash-loop on first boot until env vars are set (step 3) — that's
expected.

---

## 2. Attach a volume for state

The bot writes its recovery/probation/ladder/bucket/status files to `/data` so
they survive redeploys.

1. In the Railway service → **Volumes → New Volume**.
2. Mount path: **`/data`**.
3. Small is fine (1 GB).

The `.env.example` `*_STATE_PATH` variables are already pointed at `/data/...`,
so as long as the mount path is exactly `/data` you just copy them in (step 3)
and state persists. (If you leave them unset, the bot falls back to a
container-local file that is wiped on every redeploy — so keep them set.)

---

## 3. Set the environment variables

In the Railway service → **Variables**, set the following (see `.env.example`
for the full annotated list):

| Variable | Value |
|---|---|
| `KALSHI_API_KEY_ID` | The customer's Kalshi API Key ID |
| `KALSHI_PRIVATE_KEY_PEM` | The full PEM, pasted as a multi-line value (include BEGIN/END lines) |
| `DEMO_MODE` | `true` (always start in paper) |
| `PAPER_BALANCE` | e.g. `1000` |
| `TRADING_FORMAT` | The format this customer runs (see `docs/LADDER_STRATEGY.md`) |
| `TELEGRAM_BOT_TOKEN` | From BotFather in step 4 |
| `TELEGRAM_CHAT_ID` | The customer's chat id (step 4) |
| `TELEGRAM_OPERATOR_CHAT_ID` | *(optional)* your own chat id to also receive every alert — see step 6 |

Copy the `*_STATE_PATH`, `STATUS_SNAPSHOT_PATH`, and `HEALTH_LOG_PATH` values
from `.env.example` as-is (they point at `/data`). Do **not** leave them blank —
the code's fallback writes to a container-local file that is lost on redeploy.
Only change them if you mounted the volume somewhere other than `/data`.

---

## 4. Create the customer's Telegram bot (BotFather)

Each customer gets a dedicated bot so their alerts and commands are isolated.

1. In Telegram, open **@BotFather → `/newbot`**.
2. Name it, e.g. `FlipPulse <Customer>` with username `flippulse_<customer>_bot`.
3. BotFather returns a **token** → that's `TELEGRAM_BOT_TOKEN` (step 3).
4. Have the customer open a chat with their new bot and send any message
   (e.g. `/start`).
5. Get the **chat id**:
   - Easiest: message the bot, then visit
     `https://api.telegram.org/bot<TOKEN>/getUpdates` and read
     `result[].message.chat.id`, **or**
   - use a helper bot like `@userinfobot`.
6. Put that value in `TELEGRAM_CHAT_ID` (step 3).

> To also receive every customer's alerts yourself, see **Operator oversight**
> below before finishing.

---

## 5. Deploy & verify

1. After setting all variables, trigger a redeploy (Railway → **Deploy**).
2. Watch the deploy logs until the bot boots cleanly (Kalshi auth OK, Telegram
   connected, no crash loop).
3. In the customer's Telegram chat, run the self-monitoring check. The bot
   answers these commands (added in `command_bot.py`, which `bot.py` starts on
   boot):
   - **`/status`** — current mode (paper/live), trading format, balance and
     session PnL, win/loss record, ladder/recovery/probation mode and trade
     size, open positions (with tickers), session state, last signal, and the
     last-tick time. Reads the JSON snapshot the bot writes to
     `STATUS_SNAPSHOT_PATH` each cycle.
   - **`/health-log [n]`** — tails the last *n* lines (default 20, max 40) of the
     health/activity log at `HEALTH_LOG_PATH`.
   - **`/help`** — lists the commands.

   > The bot only *answers* these read-only commands; it also *sends* alerts on
   > its own (boot, 15-min heartbeat, trade entry, win/loss, daily summary). It
   > does **not** accept any command that changes trading — there is no way to
   > place a trade or flip `DEMO_MODE` from Telegram, by design.

4. You should see a startup/heartbeat message arrive in Telegram. If you set
   `TELEGRAM_OPERATOR_CHAT_ID` (Operator oversight), confirm it reached you too.

A green verify = bot booted, Kalshi authenticated in paper mode, and Telegram
`/status` responds.

---

## 6. Operator oversight (watching all customers)

No central dashboard is needed. The simplest approach: **you receive every
customer's Telegram alerts too.**

Pick one:

- **Operator chat id (simplest, recommended):** set `TELEGRAM_OPERATOR_CHAT_ID`
  to your own chat id (comma-separated for several operators). `telegram_utils.py`
  fans every alert out to the customer chat *and* each operator chat — no shared
  group needed. Your operator commands (`/status`, `/health-log`) are answered
  too, since operator chat ids are authorized alongside the customer's.
- **Shared group:** create a Telegram group per customer, add the customer's
  bot and both of you, and set `TELEGRAM_CHAT_ID` to the group's id. All alerts
  land in the shared group.

Either way, alerts and `/status` reach you, so you can eyeball every customer's
bot from your own Telegram without any extra infrastructure.

---

## 7. Going live (later, deliberate step)

Do **not** do this during initial onboarding. When the customer is ready:

1. Confirm the customer's Kalshi account is funded and the key has trade
   permissions.
2. Set `DEMO_MODE=false` in Railway Variables.
3. Redeploy and immediately verify via `/status` that it reports **live** mode.
4. Watch the first few trades / alerts closely.

---

## Out of scope (by design)

- Signup / login
- Multi-tenant supervisor or running many bots on one box
- Central monitoring dashboard
- Billing

One customer = one repo/template clone = one Railway project = one bot.
