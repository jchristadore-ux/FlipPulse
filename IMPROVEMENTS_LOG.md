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
| IMP-001 | 2026-07-08 | command bot / sizing | Telegram `/risk` command lets a customer change their full-size stake % at runtime | Medium | In Progress |

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
