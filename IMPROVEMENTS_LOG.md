# FlipPulse — Functionality Improvements Log

A running log of proposed functionality improvements. This is a **tracking document only** —
nothing here is implemented until explicitly approved. Add ideas as they come up; status
moves from `Proposed` → `Approved` → `In Progress` → `Done` (or `Rejected`).

> ⚠️ No code changes are made from items in this log without explicit sign-off.

---

## How to use this log

- Add a new row to the table for each improvement idea.
- Keep the one-line summary tight; put detail in the **Notes / Details** section below.
- Use the ID (e.g. `IMP-001`) to cross-reference in commits, PRs, and discussion.

**Status values:** `Proposed` · `Approved` · `In Progress` · `Done` · `Rejected` · `Deferred`
**Priority values:** `High` · `Medium` · `Low`

---

## Improvements

| ID      | Date Added | Area | Summary | Priority | Status   |
|---------|------------|------|---------|----------|----------|
| IMP-001 | 2026-07-08 | command bot / sizing | Telegram `/risk` command lets a customer change their full-size stake % at runtime | Medium | Done |
| IMP-002 | 2026-07-08 | dashboard / sizing / telegram | Self-service web dashboard (login) to change risk %, trading format, Telegram alerts, and set-aside reserve | High | Done |
| IMP-004 | 2026-07-08 | provisioning / dashboard | Autoprovision the dashboard: generate the Railway public domain + stable password and surface URL/password to the operator; docs (`DASHBOARD.md`) | High | Done |
| IMP-005 | 2026-07-08 | dashboard / command bot / engine | Paper↔live flip from the dashboard and Telegram (`/live confirm` · `/paper`), confirmation-gated, applied by a clean auto-restart when flat | High | In Progress |
| IMP-006 | 2026-08-01 | engine / sizing | Daily +3% profit target halts trading for the day; laddering disabled so risk stays a flat % of balance | High | Done |
| IMP-007 | 2026-08-01 | engine / sizing / liquidity | Balance-independence audit: make the rules identical at $20 and $20,000 (round-down sizing, no dollar cutoff, order-relative liquidity gate) | High | Done |
| IMP-008 | 2026-08-04 | engine / risk | Daily +3% halt survives a restart: the day's opening balance, realized P&L and halt state persist to `/data` and are restored at boot | High | Done |

---

## Notes / Details

### IMP-001 — Telegram `/risk` command to change stake percentage
- **Added:** 2026-07-08
- **Area:** command bot / position sizing
- **Priority:** Medium
- **Status:** In Progress (PR on `claude/telegram-risk-change`)
- **Problem / motivation:** Customers could only *view* state over Telegram; changing
  their risk (full-size stake %) meant an env change + redeploy.
- **Change:** New `/risk` command in `command_bot.py` — `/risk` shows the current %,
  `/risk <percent>` sets it (e.g. `/risk 8`), `/risk reset` restores the default. The
  command validates and clamps the value, then drops it into `RISK_OVERRIDE_PATH` on
  the `/data` volume. The engine reads it back at the sizing chokepoint
  (`bot.effective_normal_trade_pct`), re-clamped into `[RISK_MIN_TRADE_PCT, MAX_TRADE_PCT]`.
- **Impact / risk:** Touches the safety-critical sizing path. Mitigated by: hard
  floor/ceiling clamp in BOTH the command and the engine; recovery/probation
  de-risking and all guardrails still layer on top; command_bot stays decoupled
  (file-based IPC, no engine import). Covered by `test_command_bot.py`.

### IMP-002 — Self-service customer dashboard
- **Added:** 2026-07-08
- **Area:** dashboard (new `dashboard.py`) / sizing / telegram
- **Priority:** High
- **Status:** Done (merged from `claude/user-dashboard`)
- **Problem / motivation:** Customers could only view state / change risk over Telegram.
  They needed a proper login-protected place to fine-tune their setup.
- **Change:** Each bot now serves its own login-protected web dashboard (stdlib
  `http.server`, no new deps, daemon thread — mirrors `command_bot.py`). Password +
  signed session cookie (`DASHBOARD_PASSWORD`). Lets the customer change:
  **risk %** (reuses `risk_override.json`), **set-aside reserve** (new
  `reserve_override.json`; engine subtracts it from the tradeable balance at the
  `active_trade_size` chokepoint), **Telegram alerts** (new `telegram_prefs.json`;
  mutes routine entry/win/loss alerts, safety/halt alerts stay on), and **trading
  format** (new `format_override.json`, applied at next boot). Fully decoupled —
  the dashboard never imports the engine; it reads the status snapshot and writes
  `/data` override files the engine re-validates/clamps on its side.
- **Decisions (confirmed with owner):** embedded per-bot dashboard (not central);
  password + session-cookie login; **max-loss deferred** (daily-loss caps were
  removed by doctrine in v9.4.0 — needs a separate decision, see IMP-003 below).
- **Impact / risk:** Touches the safety-critical sizing path (reserve) and the
  alert path. Mitigated by double-clamping, snapshot-based decoupling, safety
  alerts never mutable, and dashboard disabled unless `DASHBOARD_PASSWORD` is set.
  Covered by `test_dashboard.py` (settings I/O, session tokens, live HTTP flow,
  reserve sizing, format override, telegram gating).
- **Follow-ups:** (a) ~~auto-generate a Railway public domain at provision time~~ —
  done in IMP-004; (b) live trading-format switch without a restart; (c) IMP-003:
  revisit the customer "max loss" control / doctrine.

### IMP-004 — Autoprovision the dashboard (domain + password + docs)
- **Added:** 2026-07-08
- **Area:** onboarding provisioner / dashboard
- **Priority:** High
- **Status:** In Progress (PR on `claude/dashboard-provisioning`)
- **Problem / motivation:** The dashboard shipped (IMP-002) but reaching it needed a
  manual Railway "Generate Domain" step, and the operator had no URL/password to give
  the customer.
- **Change:** `onboarding/provisioner.py` now (1) generates a strong `DASHBOARD_PASSWORD`
  once and persists it in the provisioning checkpoint so it's STABLE across
  resumes/reconciles (previously `deploy_variables` minted a new one every call, which
  `variables_upsert` would re-apply — silently rotating the customer's login); (2) adds
  a `create_domain` step calling Railway `serviceDomainCreate` targeting `DASHBOARD_PORT`
  (8080), best-effort so a domain failure never blocks the bot from trading; (3) injects
  `DASHBOARD_PORT`; (4) puts the dashboard URL + password in the operator success alert.
  New `DASHBOARD.md` documents the customer access steps and operator setup, linked from
  `CUSTOMER_ONBOARDING.md`.
- **Impact / risk:** Provisioning-only; the bot/engine is unchanged. Domain creation is
  non-fatal and the password is stable. Covered by new `test_provisioner.py` cases
  (domain + password surfaced, password stable across resume, domain failure non-fatal).

### IMP-005 — Paper↔live flip (dashboard + Telegram)
- **Added:** 2026-07-08
- **Area:** dashboard / command bot / engine
- **Priority:** High
- **Status:** In Progress (PR on `claude/paper-live-flip`)
- **Problem / motivation:** Going live required an operator env change + redeploy; the
  owner wanted customers to self-serve the switch from the dashboard and Telegram.
- **Decisions (confirmed with owner):** customer + operator may flip (behind a
  confirmation); the flip auto-restarts the bot to apply.
- **Change:** `DEMO_MODE` is boot-time and gates the whole trading path, so a flip is
  applied safely by (1) writing the desired mode to `MODE_OVERRIDE_PATH` on `/data`
  (dashboard "Trading mode" card, gated by a confirm checkbox; Telegram `/live confirm`
  and `/paper`), and (2) the engine restarting into it via `_maybe_restart_for_mode_change()`
  **only once flat** (no open position) — so an in-flight trade is never abandoned. Exit
  is non-zero → Railway `ON_FAILURE` boots a fresh process that reads the new mode at
  startup (`_boot_demo_mode()`). Snapshot carries `pending_demo_mode`; `/status`, `/mode`
  and the dashboard show the armed flip. Provisioner injects `MODE_OVERRIDE_PATH`.
- **Impact / risk:** Reverses the prior "going live is manual" invariant (owner-approved).
  Mitigated by: mandatory confirmation for live; restart only when flat; reverting to
  paper is always one tap/`/paper`; dashboard/command_bot stay decoupled (file-only IPC).
  Covered by `test_dashboard.py` + `test_command_bot.py` (confirm gating, pending state,
  boot-mode override, flat-only restart trigger).

### IMP-006 — Daily 3% profit target + flat risk (laddering disabled)
- **Added:** 2026-08-01
- **Area:** engine / position sizing
- **Priority:** High
- **Status:** Done (v10.2.0)
- **Problem / motivation (owner directive):** the day should have a defined goal — make
  3%, then stop — and the amount at risk should not jump around. The laddering overlay
  could scale a stake to 2× on a hot rolling win rate, and the probation ramp stepped the
  base fraction up rung by rung (re-armed from the floor every UTC midnight), so the
  dollars at risk moved for reasons unrelated to the balance.
- **Change:**
  - **Daily profit target.** `DAILY_PROFIT_TARGET_PCT` (default `0.03`) × the balance the
    day OPENED with (`session_start_balance`) is the day's goal. `daily_profit_target_check()`
    latches the existing `_session_halted` the moment today's **realized** P&L reaches it —
    checked at settlement (so the trade that crosses the line stops the day immediately) and
    again as a pre-entry guard. Realized dollars only, never a balance delta, so an open
    position's outlay can't fake progress. The UTC rollover clears the halt and re-bases the
    goal, so yesterday's profit compounds into today's target. A distinct 🎯 Telegram notice
    (not the emergency `telegram_halt` copy), a `halt_reason` in the status snapshot, and
    goal progress in `/status` and the dashboard.
  - **Flat risk.** `ladder.py` is unwired from `bot.py` (no import, no `stake_ladder`, no
    `ladder_record`); `LADDER_ENABLED` / `RECOVERY_LADDER_PAUSE_TRADES` / `LADDER_STATE_PATH`
    are no longer read and the provisioner no longer seeds them. `PROBATION_RAMP_ENABLED`
    now defaults **false** and `RECOVERY_NO_STAKE_CHANGE` defaults **true**, so the stake is
    always `NORMAL_TRADE_PCT` (or the `/risk` override) of the current balance, bounded by
    `MAX_TRADE_PCT`. No format re-enables laddering.
  - While halted, the main loop keeps resolving settlements and cancelling stale orders, so a
    position open when the target lands still settles the same day.
- **Impact / risk:** trading stops earlier on good days by design — fewer trades, and profit
  above 3% is deliberately left on the table. Recovery and probation code remain in place and
  switchable (`RECOVERY_NO_STAKE_CHANGE=false`, `PROBATION_RAMP_ENABLED=true`) for anyone who
  wants the older behaviour. Every downside guardrail (streak pause, session stop, perf guard,
  vol circuit, `MAX_TRADE_PCT`) is unchanged. Covered by `test_daily_target.py` plus new
  `/status` and dashboard cases; `ladder.py` and `test_ladder.py` stay green in isolation.

### IMP-007 — Balance independence: same rules at $20 and $20,000
- **Added:** 2026-08-01
- **Area:** engine / position sizing / liquidity
- **Priority:** High
- **Status:** Done (v10.3.0)
- **Problem / motivation (owner directive):** "validate that balance is irrelevant — the
  same rules apply across the board." Audited by running the real engine functions over
  ten balances ($5–$100,000) x the whole tradeable price band (15c–85c). Every entry gate
  already read no balance, and the percentage rules (3% daily goal, 40% session stop,
  the stake fraction) were exact at every size — but three dollar-denominated mechanics
  were not. At a configured 10% stake the risk ACTUALLY taken was 6.00–13.40% at $5,
  6.70–9.75% at $20, and exactly 10.00% at $20,000.
- **Change:**
  - **Round-down sizing.** `MIN_ORDER_ROUNDUP` now defaults false. Rounding a sub-contract
    stake UP was bounded by `MAX_TRADE_PCT`, not by the CONFIGURED fraction, and is only
    reachable on a small balance — the one path that could risk more than asked ($5 @ 67c
    took 13.40% on a 10% config). Sizing now always rounds down, so the configured
    percentage is a true ceiling everywhere. The v10.1.0 deadlock it guarded against was
    fixed at the source in v10.2.0 (the ladder + probation de-riskers that collapsed the
    stake to $0.37 are both gone).
  - **Removed the `bet < 0.25` Kelly floor** — the last raw-dollar rule in the entry path,
    which blocked every account under ~$2.50 outright. Redundant: `size_contracts` already
    rejects an unaffordable stake against `MAX_TRADE_PCT`, a percentage.
  - **Order-relative liquidity gate** (`MIN_DEPTH_STAKE_MULT`, default 3.0, via the new
    pure `depth_covers_order()`). `MIN_OB_DEPTH` demanded the same $75 of book depth
    whether the order was $2 or $10,000 — 133x cover for a $20 account, 0.0075x for a
    $100,000 one, so only large accounts carried partial-fill/slippage risk. The book must
    now absorb a multiple of the actual order. `MIN_OB_DEPTH` stays as the absolute
    "is this market worth trading at all" floor.
  - **Boot feasibility line** (`log_size_feasibility`) says plainly when a balance is too
    small to reach the configured percentage across the whole price band, instead of
    leaving it to be found in a log audit.
- **What could NOT be fixed:** contracts are integral and priced in cents, so a $20 account
  wanting $2.00 of a 67c contract gets $1.34 (6.7%, not 10%). That is the market. Rounding
  down makes it always an UNDER-risk, and it converges to exact by roughly $5,000.
- **Impact / risk:** small accounts now skip trades they cannot afford at full size rather
  than over-risking them (fewer trades under ~$50), and the liquidity gate will reject some
  signals on thin books at every size — most visibly on large accounts, which is the point.
  `MIN_ORDER_ROUNDUP=true` and `MIN_DEPTH_STAKE_MULT=0` restore the prior behaviour.
  Covered by `test_balance_independence.py`, which pins the invariants (ceiling never
  exceeded at any balance/price, no dollar cutoff, liquidity requirement identical at every
  size, granularity converges and is never an over-risk).

### IMP-008 — The daily +3% halt survives a restart
- **Added:** 2026-08-04
- **Area:** engine / risk
- **Priority:** High
- **Status:** Done (v10.3.1)
- **Problem / motivation (owner directive):** "validate that the daily 3% profit halt is
  engaged, in full mode or auto mode." Log audit of the 2026-08-03 → 2026-08-04 live run
  (Railway, `balanced`, LIVE): the halt itself is correct end to end. The UTC rollover
  re-based the day at `$59.27` and set the goal to `$1.78`; two wins (`+$1.23`, `+$0.74`)
  banked `+$1.97` and the engine latched at 13:01:11 UTC —
  `DAILY TARGET │ realized $+1.97 ≥ target $1.78 (3.0% of $59.27)` — then took no further
  entry for the remaining 2.5 hours of log, only settlement bookkeeping. Both settlement
  paths (paper and live) and the pre-entry gate call the same check, so the halt is
  mode-agnostic and identical across all three trading formats.
- **The hole the audit found:** every piece of the day's state (`_session_halted`,
  `session_start_balance`, `paper_daily_pnl` / `live_daily_realized`) lived in process
  memory only. Boot re-based the opening balance to the CURRENT balance and zeroed today's
  realized P&L, so any restart after the target was banked — a Railway redeploy, an
  OOM/crash restart, or the paper↔live flip in `_maybe_restart_for_mode_change()` (which is
  reachable *while halted*) — silently cleared the halt and started a SECOND +3% hunt on
  the same UTC day, with the session-stop floor re-armed 3% higher. Same class as the
  v9.7.0 daily-loss latch bug. It did not fire in this log (one continuous container run),
  but nothing prevented it.
- **Change:** the day's state is written to `DAILY_STATE_PATH` (`/data/daily_state.json`,
  atomic replace) every main-loop cycle — including while halted — and again the instant a
  halt latches, so a crash between cycles cannot lose it. At boot it is restored only when
  the record is for TODAY (UTC) **and** the same trading mode; a stale day or the other
  book's record is ignored and the bot boots fresh as before. The restore brings back the
  day's opening balance (so the goal is not re-based upward), the session-stop floor
  derived from it, today's realized P&L, and any latched halt. The UTC rollover overwrites
  the record immediately, so a finished day can never be resurrected. A restart that lands
  on a halted day says so in the boot Telegram message. `DAILY_STATE_PERSIST=false`
  restores the old in-memory-only behaviour.
- **Impact / risk:** write-only side effect on the hot path (one small JSON per cycle, same
  pattern as the status snapshot); every failure is caught and logged, never raised, so
  persistence can't stop trading. Covered by 13 new cases in `test_daily_target.py`
  (latch-is-written, restart resumes a banked day, opening balance and stop floor not
  re-based, mid-day restart below target keeps trading, stale-day and other-mode records
  ignored, rollover overwrites, corrupt/missing/unwritable paths, persistence off).

<!--
Template for a detailed entry — copy below when an item needs more than one line.

### IMP-001 — <short title>
- **Added:** YYYY-MM-DD
- **Area:** <e.g. bot engine, onboarding, ladder, provisioning>
- **Priority:** <High/Medium/Low>
- **Status:** Proposed
- **Problem / motivation:** What's missing or could be better.
- **Proposed change:** What we'd do.
- **Impact / risk:** Who/what it touches.
- **Notes:** Open questions, links, references.
-->
