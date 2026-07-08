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
