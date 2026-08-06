# Migrating MarkeyMachine into the FlipPulse environment

Moves the MarkeyMachine bot out of its own Railway project and into the FlipPulse
project as a sibling service, running **FlipPulse's `bot.py`** — the same code every
customer bot runs. After this, there is one trading codebase to maintain.

**Cutover is straight to live.** There is no paper dry run, so the config has to be
right the first time. That is what `tools/migrate_markeymachine.py` is for: it does the
unit conversions by rule rather than by hand, and prints everything it changed.

---

## What actually changes

MarkeyMachine and FlipPulse forked apart. The migration reconciles three things.

### 1. Sizing units — dollars become percentages

MarkeyMachine stakes a **dollar amount**. FlipPulse stakes a **fraction of the live
balance**. This is the single most dangerous part of the move: pasting `50` from
`NORMAL_TRADE_SIZE` into `NORMAL_TRADE_PCT` does not mean "$50", it means **5000% of
balance**.

| MarkeyMachine | FlipPulse | Conversion |
|---|---|---|
| `NORMAL_TRADE_SIZE` (or legacy `TRADE_SIZE_DOLLARS`) | `NORMAL_TRADE_PCT` | ÷ balance |
| `RECOVERY_TRADE_SIZE` | `RECOVERY_TRADE_PCT` | ÷ balance |
| `PROBATION_RUNG_STEP` | `PROBATION_RUNG_STEP_PCT` | ÷ balance |
| `PROBATION_RUNGS` (list) | `PROBATION_RUNGS` (list) | ÷ balance, elementwise |
| `MAX_BET_FRACTION` | `MAX_TRADE_PCT` | **none** — already a fraction |

### 2. Guardrails FlipPulse deleted

FlipPulse removed `MAX_DAILY_LOSS_PCT`, `MAX_DAILY_LOSS_DOLLARS` and
`MIN_BALANCE_FLOOR` as dead config in v9.4.0. Left under their old names they would be
read by nothing and the account would trade **uncapped**. The two that still have a live
consumer are re-pointed at `ladder.py`:

- `MAX_DAILY_LOSS_DOLLARS` → `LADDER_MAX_DAILY_LOSS_DOLLARS`
- `MAX_DAILY_LOSS_PCT` → `LADDER_MAX_DAILY_LOSS_PCT`
- `MIN_BALANCE_FLOOR` → **no equivalent.** The nearest survivor is
  `SESSION_STOP_FRACTION` (halts the day when balance falls below that fraction of the
  session open).

### 3. Behaviour that does not survive the move

These are MarkeyMachine-only. Consolidating onto FlipPulse's `bot.py` means **giving
them up** — this is the list to read before flipping live, not after.

| Feature | Gone | Nearest FlipPulse behaviour |
|---|---|---|
| **Profit lock** (`PROFIT_LOCK_*`) | arms at a gain, halts on give-back | `DAILY_PROFIT_TARGET_PCT` — halts the day at +3%, but never re-arms on give-back |
| **Trade window** (`TRADE_WINDOW`, `WINDOW_EXTEND_UNTIL_GOAL`) | trading restricted to 04:00–07:30 ET | none — **FlipPulse trades all day** |
| **Temp stake override** (`TEMP_OVERRIDE_*`) | streak-driven temporary stake ladder | `RISK_OVERRIDE_PATH` (manual `/risk`, not automatic) |
| **Kelly sizing** (`KELLY_FRACTION`) | edge-proportional stake | fixed `NORMAL_TRADE_PCT` |
| **Ladder daily goal** (`DAILY_TARGET_LADDER_ENABLED`) | keeps trading until the goal is met | none |
| **High-stake gate** (`HIGH_STAKE_*`) | extra gate above a stake size | `MAX_TRADE_PCT` ceiling only |

> The widest behaviour change is the trade window. MarkeyMachine trades a 3.5-hour
> morning session; FlipPulse trades continuously. Expect materially more trades per day.

### What FlipPulse adds

Scheduled 9am/9pm Telegram reports, exchange-side reconciliation of the day's realized
P&L, a login-protected self-service dashboard, lifetime stats that survive redeploys,
recovery anchored to trade P&L (a withdrawal can no longer trigger recovery), and the
`/data` state paths wired up by default.

---

## State files

| File | Handling |
|---|---|
| `bucket_stats.json` | **Copied verbatim.** Identical class and schema — hourly priors are preserved. |
| `recovery_state.json` | **Carried at schema 1.** FlipPulse's loader reads MarkeyMachine's `target_balance` natively and converts it to a deficit at `reconcile_on_boot`, using a real balance. Only `period_wins`/`period_losses` are renamed to `wins`/`losses`. |
| `probation_state.json` | **Converted.** Same schema number, different units — `rungs`/`full_size` are dollars there and fractions here. The file that looks safe to copy and is not. Skipped when the ramp is inactive. |
| `profit_lock_state.json` | **Not migrated** — no consumer. |
| `temp_override_state.json` | **Not migrated** — no consumer. |
| `daily_state.json`, `lifetime_stats.json`, `billing_state.json`, `report_state.json` | **Not created.** The bot writes them on first boot. A hand-made `daily_state.json` with a wrong `session_start_balance` would mis-arm the +3% daily halt on day one. |

---

## The steps

### 1. Record the balance

Open MarkeyMachine's Telegram and send `/status`. **Write down the account balance.**
Every dollar→percentage conversion divides by this number, so an inaccurate figure
rescales every stake in the account. Use the live balance, not the starting one.

### 2. Export the current config

Railway → **MarkeyMachine project** → bot service → **Variables** → **Raw Editor** →
select all → copy. Save it locally as `markeymachine.env`.

> This file contains your Kalshi private key. Keep it off shared drives and delete it
> when the migration is done.

### 3. Generate the FlipPulse config

```bash
git clone https://github.com/jchristadore-ux/FlipPulse
cd FlipPulse

python tools/migrate_markeymachine.py \
    --env-in    ~/markeymachine.env \
    --balance   <balance from step 1> \
    --env-out   ~/flippulse.env
```

To migrate the state volume too, add `--state-in ./mm-data --state-out ./fp-data` (see
step 7 for getting the files off the old volume).

**Read the report it prints.** Every section matters, but two decide whether the bot
trades correctly:

- **RESCALED** — confirm each percentage matches what you expect in dollars. If
  `NORMAL_TRADE_PCT=0.05` on a $1,000 balance, the bot will stake $50 per trade.
- **⚠️ ACTION REQUIRED** — these are blockers. Nothing here may be left unresolved.

The script never contacts Railway. Its output is a plain file you can review, edit, and
re-generate as many times as you like.

### 4. Fill in the blanks

The generated file has empty values for what the script cannot know. `KALSHI_API_KEY_ID`
and `KALSHI_PRIVATE_KEY_PEM_B64` are already filled from your export (the PEM is
base64-encoded automatically, so a newline cannot be mangled in the Railway form).

| Variable | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | MarkeyMachine's existing BotFather token |
| `TELEGRAM_CHAT_ID` | MarkeyMachine's existing chat id |
| `TELEGRAM_OPERATOR_CHAT_ID` | your operator chat id |
| `DASHBOARD_PASSWORD` | a strong new password |

Keep `DEMO_MODE=false` only if you intend the bot to trade live the moment it boots.

### 5. Create the service in the FlipPulse project

Railway → **FlipPulse project** → **New → GitHub Repo → `jchristadore-ux/FlipPulse`**.

- Name it **`markeymachine-bot`**.
- **Leave Root Directory blank.** This is the make-or-break setting — the repo-root
  `railway.toml` (`python bot.py`) has to apply.
- Set the deploy branch to **`release`**, the pinned fleet branch. Do not track `main`:
  Railway redeploys every tracking service on push, so a bad merge to `main` would
  restart this bot along with the customer fleet.

### 6. Add the volume and variables

1. Service → **Volumes → New Volume**, mount path **`/data`**.
2. Service → **Variables → Raw Editor** → paste the whole contents of
   `flippulse.env` → Save.

Do not deploy yet.

### 7. Move the state (optional but recommended)

Skipping this is safe — the bot rebuilds from scratch. You lose the hourly win-rate
priors in `bucket_stats.json`, which the bot re-learns over roughly a week, and any
in-flight recovery claw-back.

To carry it over, copy the old volume's files down (Railway shell on the **old** service:
`cat /data/bucket_stats.json`, etc.), run the script with `--state-in`/`--state-out`,
then write the converted files into the new service's `/data` — either through a Railway
shell on the new service, or by attaching the volume and uploading.

### 8. Stop the old bot, start the new one

**Order matters.** Both bots share one Kalshi account; running them together means two
bots placing orders against the same balance.

1. Old MarkeyMachine service → **Settings → Remove/Pause**. Confirm in Telegram that it
   has stopped.
2. New `markeymachine-bot` service → **Deploy**.

### 9. Verify the boot

Watch the new service's deploy logs for both markers:

```
✅ RSA private key loaded.
Sizing (% of balance)
```

Then confirm:

- [ ] The boot alert arrives in Telegram.
- [ ] `/status` replies, and the **balance matches** the figure from step 1.
- [ ] The stake shown in `/status` is the dollar amount you expected — this is the
      check that catches a bad `--balance`.
- [ ] `DEMO_MODE` is what you intend. **The bot is trading real money if it is `false`.**
- [ ] The old service is definitely stopped.

If the stake is wrong, **pause the service immediately** — it is live. Fix
`NORMAL_TRADE_PCT` in Variables and redeploy; no state is lost.

### 10. Clean up

Delete the old Railway project once you are satisfied (keep it stopped for a few days
first — it costs nothing paused and it is your rollback). Delete the local
`markeymachine.env` and `flippulse.env`; both contain your private key.

---

## Rollback

Nothing about this is one-way. The old project, its volume, and its variables are
untouched by the migration. To roll back: pause `markeymachine-bot`, restart the old
service. The only lost ground is trades taken in between — the old bot's state files are
exactly as it left them.
