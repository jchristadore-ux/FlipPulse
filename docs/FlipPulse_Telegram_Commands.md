# FlipPulse — Your Telegram Command Guide

Your FlipPulse bot lives in Telegram. It **sends** you alerts (a message when a
trade is entered and when it settles, plus a **P&L + win-rate summary at 9am and
9pm**), and it also **answers commands** so you can check on it and tune it
yourself — no dashboard, no login, just message your bot.

Just open the chat with your bot and type a command. Commands are **not
case-sensitive** (`/WinRate` and `/winrate` both work).

---

## 📊 Check how you're doing

| Command | What it does |
|---|---|
| `/status` | The full picture — paper/live mode, balance, P&L, win rate, **progress toward today's goal**, open positions, and recovery state. |
| `/winrate` | Your win rate **today**, **this week**, and **all-time**. |
| `/winrate day` | Just today's win rate. |
| `/winrate week` | Just this week's win rate (rolling 7 days). |
| `/pnl` | Your profit/loss **today**, **this week**, and **all-time**. |
| `/pnl day` | Just today's P&L. |
| `/pnl week` | Just this week's P&L. |
| `/balance` | Your current balance and P&L at a glance. |
| `/health-log` | The last 20 lines of the bot's activity log. Add a number for more, e.g. `/health-log 40`. |

> Twice a day, at **9:00am and 9:00pm (US Eastern)**, the bot messages you a
> short briefing: balance, today's P&L, today's win rate, and your all-time
> figures — so you get a rhythm without having to ask.

### 🎯 Today's goal: +3%

Your bot trades toward a **daily profit target of 3%** of the balance the day
started with. The moment it books that, it **stops trading for the day** and
messages you — a quiet chat after a 🎯 message means the goal is banked, not that
something broke. `/status` shows how far along you are (e.g.
`Daily goal: $+12.50 / $30.00`).

Trading restarts automatically at the next trading day (UTC midnight), and the
goal is recalculated from your new balance — so profit compounds into tomorrow's
target. Any position still open when the goal is hit settles normally.

---

## 🎚 Tune your bot

| Command | What it does |
|---|---|
| `/risk` | Shows your current stake size (as a % of balance per trade). |
| `/risk 8` | Sets your full-size stake to 8% of balance. (Kept inside safe limits automatically.) |
| `/risk reset` | Back to your configured default. |
| `/recoverynostakechange on` | **Recovery Mode — No Stake Change** ON (see below). |
| `/recoverynostakechange off` | Turns it back off (standard recovery). |
| `/recoverynostakechange` | Shows whether it's currently on or off. |

### What is "Recovery Mode — No Stake Change"?

Normally, after a full-size losing trade the bot enters **recovery mode** and
*shrinks* your stake while it earns that loss back, then returns to full size
once you're back to even.

> **Withdrawals don't put you in recovery.** The claw-back counts only what
> *trades* lost, so moving money in or out of Kalshi never adds to it (and never
> clears it either). `/status` shows the dollars of trade losses still to earn
> back; the balance target next to it re-bases when you deposit or withdraw.

With **No Stake Change ON**, recovery still triggers and tracks the claw-back,
but it **keeps your stake exactly where it was** — no stake reduction, and no jump
back up when recovery ends. Flip it anytime; it takes effect immediately, even in
the middle of a recovery.

> **This is ON by default.** Your stake stays the same percentage of your balance
> at all times, so the amount at risk moves only when your balance does.

> **Automatic win-rate restore:** if you turn No Stake Change *off* and your stake
> is being held below its normal size during recovery, a recovery win rate of
> **70%** returns you straight to the full stake — so a hot streak doesn't get
> stuck grinding at a small size.

---

## 🔴 Paper vs. Live

| Command | What it does |
|---|---|
| `/mode` | Shows whether you're in **paper** (practice) or **live** (real money). |
| `/live confirm` | Switches to **live** trading with real money. Requires the word `confirm`. |
| `/paper` | Switches back to paper trading. |

Mode changes apply as soon as the bot has no open position.

---

## ❓ Anything else

| Command | What it does |
|---|---|
| `/help` | Lists every command. |

Type `/help` any time you forget one. If a command ever says the bot is "still
booting," give it a minute after a restart and try again.
