# FlipPulse — Production Readiness Audit (2026-07-02)

> **Fix status (updated 2026-07-02).** Resolved since this audit was written:
> C-1, C-2, C-3 (PR #15) · H-1, H-2, H-3, H-8 (PR #16) · H-5, M-1, M-2, M-3,
> M-5, M-6, L-3, the B.1 dead-config/dead-code inventory, the B.2 requirements
> split, quick wins #5/#7/#9, consistency items #3 (rename), #4 (heartbeat
> label) and #5 (marker comments), plus first engine test coverage for H-4
> (`test_bot_engine.py` — settlement reconstruction, PEM normalization, sizing,
> edge math). Still open: H-4 beyond the pure functions, M-4 (submission write
> lock), C.1/C.2 logger + env-prefix consolidation, B.2 repo/media split, the
> `bot.py` changelog-header move, and L-1/L-2/L-4.

Full-system audit ahead of the customer-acquisition launch. Scope: every file in
the repository, the onboarding flow end-to-end, and production hardening for
24/7 unattended operation at scale.

**Verification done during this audit:** the full test suite passes (20/20),
`bot.py` boots in paper mode with a generated key, `--list-formats` works, and
the `PAPER_BALANCE` crash below was reproduced live.

---

## A. Executive Summary

**Overall health: good bones, launch-blocking edges.** The core architecture is
sound and unusually well-documented for its size: one bot per customer, all
sizing percentage-based and resolved at a single chokepoint, secrets encrypted
at rest, signup-time validation of both the Kalshi key and the customer's
Telegram bot (which kills the #1 historical onboarding failure before it can
ship), and an idempotent, resumable, tested provisioning state machine. State
persistence is atomic (`os.replace`) everywhere. Error handling in the alerting
path is genuinely defensive.

**The biggest risks before marketing launch, in order:**

1. **The bot can die silently and never come back** (C-1). Boot-time aborts
   `return` with exit code 0, and Railway's `restartPolicyType = "ON_FAILURE"`
   only restarts non-zero exits. A transient Kalshi outage during a deploy
   leaves that customer's bot permanently down.
2. **The revenue → provisioning pipeline has a silent no-op mode** (C-2). If
   `STRIPE_WEBHOOK_SECRET` is unset (documented as *optional*), the webhook
   returns 200 and does nothing: paid customers are never marked paid and never
   provisioned, with no alert anywhere.
3. **Every push to `main` redeploys every customer bot at once** (C-3). All
   provisioned services track `jchristadore-ux/FlipPulse@main`. One bad merge
   bricks the entire fleet simultaneously; there is no release pinning.
4. **Provisioning jobs are lost if the onboarding service restarts** (H-1). The
   queue is in-memory and nothing sweeps for paid-but-unprovisioned
   submissions on boot.
5. **Customers see the wrong product name** (H-3). Every Telegram boot/halt/stop
   message says "MarkeyMachine", not FlipPulse.

None of these require large changes. The four code fixes among them are each
under ~30 lines.

---

## B. Cleanup Plan

### B.1 Dead code to remove (safe — verified unreferenced by any active path)

| Location | What | Why it's dead | Risk of removal |
|---|---|---|---|
| `bot.py:457` | `MAX_BET_FRACTION` | v9.4.1 removed Kelly down-scaling; read, never used | None |
| `bot.py:459` | `KELLY_RECOVERY_MULT` | v9.4.0 removed recovery Kelly multiplier | None |
| `bot.py:570` | `MIN_BALANCE_FLOOR` | v9.4.0 removed `balance_floor_check()` | None |
| `bot.py:571,577` | `MAX_DAILY_LOSS`, `MAX_DAILY_LOSS_PCT` | v9.4.0 removed the daily-loss caps (bot.py copy only — **ladder.py still reads `MAX_DAILY_LOSS_DOLLARS`**, see H-2) | None (bot.py only) |
| `bot.py:674–680` | `RECOVERY_TRIGGER_PCT`, `RECOVERY_EXIT_TRADES`, `RECOVERY_WIN_RATE_MIN`, `RECOVERY_MAX_SECS` | Entire "Recovery protocol" config block feeds `update_session_state()`, which is a no-op | None |
| `bot.py:2053` | `update_session_state()` | Explicit no-op, still called every cycle | None |
| `bot.py:827–830, 3097–3099, 3251, 3258` | `recovery_trades`, `recovery_entry_wins`, `recovery_entry_losses` | Zeroed at boot, never incremented; the `(rec+N)` log branch can never fire because `session_state` never becomes `RECOVERY` | None |
| `bot.py:357–360` | `SessionState.RECOVERY`, `SessionState.HALTED` | Unreachable states (only `ACTIVE` is ever assigned); keep the enum, delete the members or the enum entirely | Low — snapshot/`/status` display the value; keep the string `"ACTIVE"` |
| `bot.py:458` | `KELLY_FRACTION` | Display-only (boot banner + Telegram boot message). Actively **misleading**: implies Kelly-scaled sizing, but sizing is pure percentage-of-balance since v10.0.0 | None — also remove the `Kelly=0.30` lines from `telegram_boot()` and the boot banner |
| `telegram_utils.py:44` | `_int_env()` | Never called | None |
| `telegram_utils.py:368` | `notify()` | Never called; docstring references a "dashboard watchdog" that does not exist in this repo | None |
| `formats.py:169–219` | `ALLOWED_PARAM_KEYS`, `coerce_param()` | Built for "a future dashboard/command"; no caller anywhere | None — or keep deliberately, but then say so in one line, not "may be overridden" |
| `command_bot.py:12–13` | Docstring reference to `dashboard/telegram_bot.py` | File does not exist in this repo (legacy markeymachine reference) | None |

### B.2 Files to refactor

| File | What | Recommendation |
|---|---|---|
| `bot.py:1–305` | 300-line boxed changelog docstring (v9.0.7 → v10.0.0) | Move to `CHANGELOG.md`. It is valuable history but it means the first 3 screens of the entrypoint are prose, and it drifts (it still documents dollar-based vars that no longer exist) |
| `onboarding/app.py:_deploy_env` + `onboarding/admin_cli.py:_env_pairs` + `onboarding/provisioner.py:deploy_variables` | **Three copies** of the customer env-var mapping | Consolidate into one function in `provisioner.py` and import it. They have already diverged: the admin/CLI variants omit the eight `/data` state-path vars the provisioner sets, so a manual deploy that pastes `admin_cli.py show` output gets ephemeral state (wiped every redeploy) unless the operator remembers a footnote |
| `requirements.txt` (root) | Ships `flask`, `gunicorn`, `pytest` into **every customer bot image** | Bot needs only `requests`, `cryptography`, `cffi`. Move test deps to a `requirements-dev.txt`; flask/gunicorn already live in `onboarding/requirements.txt` |
| `bot.py:326` | `List` used in annotations but never imported from `typing` | Works only because of `from __future__ import annotations`; breaks any tool that resolves hints. Add the import (1 line) |
| Repo root | `IMG_7262.jpeg` (logo, referenced by `marketing/build_demo.py` and `business/build_onepager.py`) | Not orphaned, but a camera-roll filename at repo root. Rename/move to `marketing/assets/logo.jpeg` and update the two references |
| Repo layout | ~10 MB of media (`marketing/*.mp4`, PDFs, guide assets) plus the **business financial model** ship inside every customer bot container | Nixpacks copies the whole repo per deploy. Either split marketing/business into a separate repo, or add a `.railwayignore`/`.dockerignore`. Also a hygiene question: the deploy repo contains your P&L model |

### B.3 Quick wins (each under 1 hour)

1. **`sys.exit(1)` instead of `return` on the two boot-abort paths**
   (`bot.py:3151, 3155`) so Railway's ON_FAILURE policy restarts the bot. This
   is the single highest-value line-level change in the repo (see C-1).
2. **Parse `PAPER_BALANCE` defensively** (`bot.py:3092`): strip `$`/`,` or use
   `_env_float`. Verified: `PAPER_BALANCE=1,000` crash-loops the bot today.
3. **Rebrand customer-facing strings**: `telegram_boot()`, the halt/stop
   messages, and the Telegram validation message all say "MarkeyMachine".
4. **Mark `STRIPE_WEBHOOK_SECRET` as required** in `onboarding/README.md` when
   `AUTO_PROVISION` is on, add `"webhook_secret": bool(...)` to `/healthz`, and
   log an ERROR at boot when Stripe is configured without it.
5. **Align `STATUS_SNAPSHOT_PATH` defaults**: `bot.py` defaults to `""` (no
   snapshot) while `command_bot.py` defaults to `/data/status_snapshot.json` —
   with the env unset, `/status` reports "no snapshot yet" forever. Default
   both to the same value.
6. **Delete the B.1 dead-config block** (~40 lines, zero behavior change).
7. **Prune `_prev_ob`**: a new ticker exists every 15 minutes (~35k entries per
   year) and the dict is never cleaned; same for `_processed_settlement_ids`.
   Evict entries older than ~1h / cap the set (see M-3).
8. **Add `ProxyFix` to the Flask app** so `request.is_secure` and
   `request.host_url` are correct behind Railway's TLS-terminating proxy
   (admin cookie `Secure` flag; https Stripe redirect URLs when
   `PUBLIC_BASE_URL` is unset).
9. **Document `POLL_INTERVAL_SECS`** in `.env.example` (read by the code,
   documented nowhere) and reconcile the `PAPER_BALANCE` default (code `25.0`
   vs `.env.example` `1000`).

---

## C. Consistency Fix List

Things that would confuse a new engineer, none individually urgent:

1. **Product naming is split three ways.** Logger names: `MarkeyMachine`,
   `MarkeyMachine.telegram`, `MarkeyMachine.ladder` vs `FlipPulse.command_bot`,
   `FlipPulse.formats` vs `flippulse.onboarding`, `flippulse.provisioner`
   (three casings, two brands). Customer-visible Telegram copy says
   MarkeyMachine. Pick `flippulse.*` everywhere; keep one alias note in the
   README for the markeymachine lineage.
2. **Env-var prefixes are inconsistent.** `ONBOARDING_*` vs bare
   (`ADMIN_TOKEN`, `AUTO_PROVISION`, `SUBMISSIONS_DIR`) vs `PROVISION_*` vs
   `BOT_OPERATOR_CHAT_ID` (which becomes `TELEGRAM_OPERATOR_CHAT_ID` on the
   bot side). At minimum, document the mapping in one table; ideally converge
   on `ONBOARDING_*` for the web service.
3. **`daily_loss_check()` no longer checks daily loss** — it is the 40%
   session-stop backstop only. Rename to `session_stop_check()` or the next
   log review will mislead someone.
4. **Heartbeat "Trades today"** counts the whole `trade_history` deque
   (win/loss/pending since boot, up to 500), not today. Rename the label or
   filter by day.
5. **Provisioning verify markers are exact log strings** from `bot.py`
   (`"✅ RSA private key loaded."`, `"Sizing (% of balance)"`). Reword either
   log line and provisioning starts failing at `verify` for every new
   customer. Add a comment on both `bot.py` log lines ("provisioner boot
   marker — keep in sync with provisioner.LOG_MARKERS") and/or a unit test
   asserting the markers appear in `telegram_boot`-adjacent log output.
6. **Duplicate PEM-normalization logic**: `bot.py:_normalize_pem` and
   `onboarding/app.py:_pem_looks_valid` implement the same tolerant parsing
   independently. Acceptable across service boundaries, but note the coupling
   — if one grows a fix, mirror it.
7. **Folder structure** is otherwise clear and scales fine: `bot.py` +
   satellites at root (deploy unit), `onboarding/` (web service, own
   railway.toml — good pattern), `docs/`, `marketing/`, `business/`. The only
   structural oddity is tests for `onboarding/*` living at repo root
   (`test_provisioner.py` imports `onboarding.provisioner`) while no test
   covers `bot.py` at all (see H-4).

---

## D. Production Blockers (fix before onboarding goes live)

Severity-ranked. **Critical = will lose a customer or revenue silently.**

### CRITICAL

**C-1. Boot aborts exit 0 → Railway never restarts → bot silently dead.**
`bot.py:3146–3155`: if the starting-balance fetch fails (transient Kalshi/API
outage during deploy) or reads $0, `main()` logs, sends one Telegram message,
and `return`s. Exit code 0. `railway.toml` uses `restartPolicyType =
"ON_FAILURE"`, which only restarts **non-zero** exits. A customer whose deploy
raced a 30-second Kalshi blip has a dead bot until a human notices.
*Fix:* `sys.exit(1)` on both paths (Railway then retries up to 10×), or retry
the balance fetch with backoff before giving up. One of the two, ideally both.

**C-2. Missing `STRIPE_WEBHOOK_SECRET` turns the paid→provisioned pipeline
into a silent no-op.** `onboarding/app.py:356–361`: no secret → return 200,
do nothing. The README calls the variable "optional". Result at launch: cards
are charged, submissions stay `pending`, auto-provisioning never fires, no
alert fires, and the paid gate (`require_paid=True`) later *blocks* the
recovery path too. *Fix:* treat the secret as required whenever
`STRIPE_SECRET_KEY` is set (boot-time ERROR + `/healthz` field), and alert the
operator on any webhook that can't be verified.

**C-3. The whole fleet tracks `main`.** Every provisioned customer service
deploys `jchristadore-ux/FlipPulse@main` (`PROVISION_REPO_BRANCH` default) and
Railway auto-deploys on push. Once there are N customers, any push to `main` —
including a broken one — restarts and potentially bricks all N bots at the same
moment. There is no staging bot, no canary, no pinning. *Fix:* create a
`release` branch (or tags), point `PROVISION_REPO_BRANCH` at it, keep one
in-house canary bot on `main`, and promote `main → release` only after the
canary has traded through at least one session.

### HIGH

**H-1. Provisioning queue is in-memory; no reconciliation sweep.**
`provisioner.py:486–516`: Stripe gets its 200, the job sits in a
`queue.Queue`. If the onboarding service restarts (deploy, crash, Railway
maintenance) before the worker finishes, the job is gone; the submission is
left `paid` + unprovisioned (or `in_progress` with a stale lock, self-clearing
only after 45 min), and Stripe will not retry an acknowledged event. *Fix:* on
app boot, scan `SUBMISSIONS_DIR` for `payment_status == "paid"` with
`provisioning.status not in ("provisioned", "in_progress")` and re-enqueue;
alert the operator for anything stuck `in_progress` older than the lock TTL.
~20 lines, closes the biggest onboarding gap.

**H-2. Ladder drawdown guard is still a fixed $15.**
`ladder.py:86,105`: `max_daily_loss` defaults to `$15` via
`MAX_DAILY_LOSS_DOLLARS` — a leftover from the fixed-dollar era that v10.0.0
explicitly deleted from `bot.py`. The ladder is ON for every **aggressive**
format customer (20% stakes). A customer with a $5k balance loses ~$1,000 on
one full-size loss → `daily_pnl ≤ -15` → the drawdown guard reverts the ladder
to 1× for the rest of the day, permanently, for every aggressive customer with
a non-toy balance. The advertised "up to 2×" ladder effectively cannot engage.
*Fix:* make it a fraction of balance (consistent with v10 philosophy) or seed
it from the format; at minimum raise the default and document it.

**H-3. Customer-facing branding says MarkeyMachine.** `telegram_boot()`,
halt/stop messages, and the connectivity-test message. Customers signed up for
FlipPulse; the first message their bot sends them is
"🤖 MarkeyMachine 10.0.0 STARTED". Trust-eroding at exactly the moment you're
scaling intake. *Fix:* one string constant, used everywhere.

**H-4. The 3,300-line trading engine has zero tests.** The periphery
(provisioner, telegram_utils, onboarding validation) is well-tested; `bot.py` —
settlement reconciliation (`_extract_realized_dollars`, the function with the
richest bug history in the changelog), recovery/probation transitions, sizing
clamps — has none. Every historical incident in the header changelog lives in
that file. *Fix (pragmatic):* extract-and-test just the pure functions
(`_extract_realized_dollars`, `_probation_rungs`, `active_trade_size`,
`calc_edge`, `wilson_lower_bound`, `_normalize_pem`) — a day of work, covers
the money paths.

**H-5. Stripe Checkout failure shows the customer a success page.**
`app.py:336–343`: if `_start_stripe_checkout` raises (Stripe down, bad price
id), the submission is saved and the customer is redirected to `/success` —
which tells them they're in. No payment was collected, nothing distinguishes
this from the deliberate Stripe-less mode, and only the `pending` status in
`/admin` records it. *Fix:* on checkout exception, show a "we'll send you a
payment link" variant and alert the operator explicitly.

### MEDIUM

**M-1. No staleness gate on the BTC price feed.** `bot.py:1521–1557`: if both
Kraken and Coinbase fail, `fetch_btc_price` backs off 5 minutes, but
`btc_prices` keeps its old samples with no timestamps. Regime and momentum are
then computed over stale data and can still authorize a trade against a market
that has since moved. *Fix:* record the last-ingest timestamp and have
`compute_regime()` return `UNKNOWN` when it exceeds ~2× the poll interval.

**M-2. Flask app lacks `ProxyFix`, rate limiting, and a body-size cap.**
Behind Railway's proxy, `request.is_secure` is False (admin cookie loses
`Secure`) and `request.host_url` is `http://` (Stripe redirect fallback). The
public form has no rate limit or CAPTCHA and no `MAX_CONTENT_LENGTH` —
marketing traffic includes bots, each junk submission writes disk, calls the
Telegram API twice, and pings the operator. *Fix:* ProxyFix (2 lines),
`MAX_CONTENT_LENGTH = 64 KB` (1 line), and a simple per-IP submit throttle.

**M-3. Slow memory growth in a 24/7 process.** `_prev_ob` gains an entry per
15-minute market forever (~35k/year); `_processed_settlement_ids` grows
unboundedly in live mode. Months-scale, not weeks-scale, but the process is
supposed to never restart. *Fix:* time-evict `_prev_ob` (entries older than
10 min are already ignored by the logic); cap the settlement-id set.

**M-4. Concurrent read-modify-write of submission files.** The Stripe webhook
(`app.py`) and `provisioner._checkpoint` both do load→mutate→write on the same
JSON with no shared lock (the provisioning lockfile only serializes
provision-vs-provision). An admin-button provision racing a webhook can lose
the `payment_status` or `stripe_customer` write. Low probability, annoying to
debug. *Fix:* reuse the lockfile for all submission writes, or write via a
single helper with `fcntl` locking.

**M-5. `BTC_SERIES` fallback can trade non-15-minute markets.**
`bot.py:2513`: if `KXBTC15M` returns no open markets, discovery falls through
to `KXBTCD`/`KXBTC` (daily-horizon series) and applies 15-minute doctrine
(6-min expiry floor, 15-min momentum windows) to them. If intentional, it is
undocumented; if not, it's a mis-trade waiting for a quiet market. *Fix:*
either drop the fallbacks or gate on `close_time − now ≤ 20 min`.

**M-6. `ONBOARDING_FERNET_KEY` is a single point of failure with no
documented backup.** Lose it and every submission (including customers not yet
provisioned) is unrecoverable; there is also no documented rotation procedure
beyond one sentence. *Fix:* document key backup + rotation in
`onboarding/README.md`; consider storing a second copy in a password manager
as an operational runbook step.

### LOW

- **L-1.** `/admin?token=` in the query string lands in proxy logs; the cookie
  then stores the raw token. Acceptable for a single operator; consider a
  session cookie derived from the token instead.
- **L-2.** `command_bot` and `telegram_utils._log_config_diagnostic` can both
  call `getUpdates` on the same token; Telegram allows one consumer (409 on
  the loser). Diagnostic is one-shot/best-effort, so worst case is a lost
  diagnostic — but don't add more `getUpdates` callers.
- **L-3.** `.gitignore` covers the state JSONs but not `health.log` /
  `billing.log` (both normally on `/data`, so only local runs are affected).
- **L-4.** Heartbeat interval (900s), halt-poll sleep (300s), stale-order purge
  (1200s), and the DEMO settle window (900s) are hardcoded; fine as defaults,
  but the 24/7 doctrine says make at least the heartbeat configurable since
  it's the operator's liveness signal.

---

## Onboarding flow — end-to-end trace (reference)

```
form GET /            → static, no deps
POST /submit          → validates: required fields, format whitelist, balance>0,
                        PEM parses (real key-load), Telegram getMe + live sendMessage
                        → Fernet-encrypts secrets → submissions/<id>.json (0600)
                        → operator Telegram (best-effort)
                        → Stripe Checkout (or local success)          [H-5 gap]
Stripe webhook        → signature check [C-2 gap] → mark paid → enqueue
provisioner (thread)  → lockfile → project → service(+vars) → volume →
                        vars upsert → redeploy → poll deploy → verify boot logs
                        → checkpoint each step (resumable)            [H-1 gap]
customer bot boots    → formats seed env → PEM load (B64 path) → balance fetch
                        [C-1 gap] → Telegram validate (self-heals) → trade loop
```

External dependencies and their failure handling:

| Dependency | Used by | Retry/recovery | Gap |
|---|---|---|---|
| Kalshi API | bot | balance cached on failure; resolution wrapped; host probe has fallback | boot-time fetch aborts with exit 0 (C-1) |
| Kraken/Coinbase | bot BTC feed | dual-source + 5-min backoff | no staleness gate (M-1) |
| Telegram (customer bot) | alerts + commands | 3 attempts/recipient, transient/permanent classification, boot self-heal thread | solid |
| Telegram (operator) | onboarding + provisioner | single attempt, best-effort | acceptable (non-critical path) |
| Stripe | checkout + webhook | Stripe retries unacknowledged webhooks | success-page-on-failure (H-5); secret optional (C-2) |
| Railway GraphQL | provisioner | 4 tries, exponential backoff, resumable checkpoints, tested | in-memory queue (H-1) |

---

## Suggested fix order (one sitting each)

1. C-1 + quick-win #2 (`sys.exit(1)`, `PAPER_BALANCE` parse) — 15 min.
2. C-2 (webhook secret required + healthz) — 30 min.
3. H-1 (boot re-enqueue sweep) — 1 h.
4. H-3 + C-cleanup naming pass (branding strings) — 30 min.
5. C-3 (release branch + repoint `PROVISION_REPO_BRANCH`) — 30 min + process.
6. H-2 (ladder drawdown scaling) — 1 h.
7. H-5, M-1, M-2 — one afternoon.
8. B.1 dead-code deletion + B.2 requirements split — 1 h, zero risk.
9. H-4 pure-function tests — 1 day, do it before the first live-money customer.
