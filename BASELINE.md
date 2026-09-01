# BASELINE — FlipPulse / Johnny5 audit (Phase 0)

**Read-only audit. No code was changed in this phase.**

- Repo state: `bot.py` v10.3.3, branch `claude/johnny5-learning-loop-3p4349`, HEAD `e578b02`.
- Runtime: single Python worker on Railway (`railway.toml` → `python bot.py`), state on a
  volume mounted at `/data`.
- Strategy: Kalshi `KXBTC15M` 15-minute BTC binaries, one position at a time, held to
  settlement.

---

## 1. File map — where each responsibility lives

The engine is one 5,205-line module. There is no package structure; everything below is in
`bot.py` unless stated.

| Responsibility | Location |
|---|---|
| **Main loop / scheduling** | `bot.py:4922` `main()` — `while not _shutdown_requested`, `time.sleep(POLL_INTERVAL)` (30s). Settlement + stale-cancel run every 3rd cycle (`bot.py:5139`). |
| **Market selection** | `bot.py:3669` `get_active_market()`; expiry maths `bot.py:3709` `minutes_to_expiry()` |
| **BTC price feed** | `bot.py:2426` `fetch_btc_price()`, `bot.py:2462` `ingest_btc_price()`; deques `btc_prices` / `btc_returns` at `bot.py:1303-1304` |
| **Regime detection** | `bot.py:2497` `compute_regime()` (linear regression `bot.py:2479`) |
| **Momentum** | `bot.py:2572` `compute_momentum()`, gate `bot.py:2613` `momentum_gate_ok()` |
| **Order-book analysis** | `bot.py:2654` `analyze_order_book()`, trend persistence `bot.py:2729` `check_ob_trend()` |
| **Signal generation (probability)** | `bot.py:2788` `bayesian_win_prob()` → `bot.py:2923` `market_anchored_win_prob()` |
| **Confidence score** | `bot.py:2844` `compute_confidence()` |
| **Edge** | `bot.py:2896` `calc_edge()`, `bot.py:2911` `edge_return_on_risk()` |
| **Sizing** | `bot.py:3016` `kelly_bet()` (Kelly used **only as a sign test**; the stake is a flat % of balance) → `bot.py:2291` `active_trade_size()` → `bot.py:2951` `size_contracts()` (dollars → whole contracts) |
| **Decision orchestration (all gates, in order)** | `bot.py:4566` `run_decision()` |
| **Order placement** | `bot.py:4046` `place_order()` — `POST /portfolio/events/orders` |
| **Exits** | **There are none.** Every position is held to settlement (`bot.py:3309` `resolve_open_orders()`). The only order-lifecycle intervention is `bot.py:3594` `cancel_stale_orders()`, which cancels *unfilled resting* orders at `STALE_ORDER_TIMEOUT` (300s). |
| **Guards — pre-signal** | `spread_check` `bot.py:4001`, `expiry_guard` `bot.py:4008`, `cooldown_check` `bot.py:4015`, `session_quality_check` `bot.py:4023`, `streak_check` `bot.py:4032`, `session_stop_check` `bot.py:3725`, `daily_profit_target_check` `bot.py:3767`, `performance_guard` `bot.py:3084`, `check_vol_circuit` `bot.py:2538`, `depth_covers_order` `bot.py:3000` |
| **Sizing-mode state machines** | `RecoveryState` `bot.py:1397`, `ProbationState` `bot.py:1643`, `BucketStats` `bot.py:1857`, `LifetimeStats` `bot.py:2094`, `BillingState` `bot.py:1952` |
| **Risk-posture presets** | `formats.py` — `apply_format()` seeds a named bundle of env values via `setdefault` before the config block reads them |
| **Telegram** | `telegram_utils.py`; alert wrappers `bot.py:4204-4266`; scheduled briefing `ReportScheduler` `bot.py:4374` |
| **Observability / IPC** | `write_status_snapshot()` `bot.py:4452`; `command_bot.py` (`/status`, `/health-log`, `/risk`); `dashboard.py` (web UI). Both are decoupled — file IPC over `/data`, no engine import. |

---

## 2. Every tunable, with file, line, and current value

### 2a. Env-var-backed, with the **default that ships** (all in `bot.py`)

The defaults below are what runs when the env var is unset. `TRADING_FORMAT` (`formats.py`)
overrides a subset before these are read; explicit Railway env vars beat both.

| Parameter | Line | Default | Notes |
|---|---|---|---|
| `POLL_INTERVAL_SECS` | 645 | `30` | main-loop cadence |
| `NORMAL_TRADE_PCT` | 662 | `0.10` | full stake, fraction of balance |
| `RECOVERY_TRADE_PCT` | 663 | `0.03` | reduced stake (inert while `RECOVERY_NO_STAKE_CHANGE=true`) |
| `MAX_TRADE_PCT` | 664 | `0.15` | **hard ceiling — risk-increasing** |
| `RISK_MIN_TRADE_PCT` | 680 | `0.01` | floor for the `/risk` command |
| `RECOVERY_NO_STAKE_CHANGE` | 735 | `True` | |
| `RECOVERY_WINRATE_RESTORE_ENABLED` | 752 | `True` | |
| `RECOVERY_WINRATE_RESTORE_PCT` | 753 | `0.70` | |
| `RECOVERY_WINRATE_MIN_TRADES` | 754 | `5` | |
| `DAILY_PROFIT_TARGET_ENABLED` | 784 | `True` | |
| `DAILY_PROFIT_TARGET_PCT` | 785 | `0.03` | halts the day at +3% of the opening balance |
| `PROBATION_RAMP_ENABLED` | 823 | `False` | ramp is off in all three formats |
| `PROBATION_WIN_STREAK` | 825 | `2` | |
| `PROBATION_WIN_RATE_MIN` | 828 | `0.60` | |
| `PROBATION_WINRATE_MIN_TRADES` | 829 | `4` | |
| `PROBATION_RUNG_STEP_PCT` | 841 | `0.035` | |
| `PERF_FEE_PCT` | 893 | `0.0` | disabled placeholder |
| `SESSION_STOP_FRACTION` | 934 | `0.40` | **catastrophic backstop — risk-increasing if raised** |
| `MAX_CONSEC_LOSSES` | 935 | `2` | **consecutive-loss breaker** |
| `STREAK_PAUSE_SECS` | 936 | `1800` | |
| `STALE_ORDER_TIMEOUT` | 937 | `300` | |
| `MAX_CONCURRENT_POS` | 938 | `1` | **risk-increasing** |
| `MIN_SAMPLE_TRADES` | 939 | `20` | perf-guard minimum sample |
| `MIN_ORDER_ROUNDUP` | 987 | `False` | |
| `MIN_DEPTH_STAKE_MULT` | 1006 | `3.0` | book must cover 3× the order |
| `PERF_GUARD_WINDOW` | 1022 | `20` | |
| `PERF_GUARD_PAUSE_SECS` | 1023 | `21600` | 6h |
| `R2_TREND_THRESHOLD` | 1029 | `0.65` | |
| `VOLATILITY_CAP_PCT` | 1030 | `0.18` | |
| `VOL_CIRCUIT_BREAKER` | 1031 | `0.40` | |
| `TREND_LOOKBACK` | 1032 | `12` | samples (~6 min at 30s) |
| `MIN_PRICES_FOR_REGIME` | 1033 | `10` | |
| `MIN_OB_DEPTH_DOLLARS` | 1039 | `75.0` | |
| `OB_IMBALANCE_THRESH` | 1040 | `0.70` | |
| `MOMENTUM_THRESH_PCT` | 1041 | `0.15` | |
| `MOMENTUM_LOOKBACK` | 1048 | `6` | |
| `MOMENTUM_R2_MIN` | 1055 | `0.55` | |
| `MIN_EDGE_PCT` | 1057 | `0.06` | |
| `MIN_CONFIDENCE` | 1058 | `65` | |
| `MIN_WIN_PROB` | 1059 | `0.60` | |
| `MARKET_ANCHOR_ENABLED` | 1096 | `True` | |
| `MAX_MODEL_EDGE_PP` | 1097 | `0.08` | ceiling on model lift over the market price |
| `MIN_EDGE_ROR` | 1105 | `0.0` (off) | |
| `OB_IMBALANCE_MAX` | 1116 | `0.95` | |
| `MIN_MINUTES_TO_EXPIRY` | 1117 | `6.0` | |
| `MAX_MINUTES_TO_EXPIRY` | 1122 | `20.0` | |
| `YES_BREAKEVEN_PRICE` | 1123 | `67` | |
| `REQUIRE_AGREE_MOMENTUM` | 1129 | `True` | |
| `MIN_SESSION_SCORE` | 1138 | `60` | |
| `BUCKET_GROUP_HOURS` | 1161 | `3` | |
| `BUCKET_PRIOR_FULL_N` | 1164 | `30` | |
| `OB_BASE_ACCURACY` | 1167 | `0.635` | |
| `MOMENTUM_ACCURACY_LIFT` | 1168 | `0.045` | |
| `NEUTRAL_ACCURACY_DRAG` | 1173 | `0.02` | |
| `BTC_STALE_MAX_SECS` | 2459 | `180` | |

### 2b. **Genuinely hardcoded — no env var, no override path**

These are the ones with no escape hatch at all. Several are load-bearing strategy filters.

| Value | Line | What it does |
|---|---|---|
| `SESSION_QUALITY` table (24 hourly scores, 10–95) | 1132–1137 | Time-of-day gate, compared against `MIN_SESSION_SCORE`. **The whole time-of-day filter is a hardcoded literal table.** |
| `if not (25 <= contract_price <= 75)` | 4694 | **Hard price band.** Rejects every contract outside 25c–75c. Undocumented, never mentioned in `.env.example`. |
| `if abs(limit_price - contract_price) > 8` | 4758 | Limit-drift rejection, 8 cents |
| `mid > 85 or mid < 15` | 4009 | `expiry_guard` near-certainty band |
| `elapsed < 60` | 4016 | 60s inter-trade cooldown |
| `wlb < 0.50` | 3120 | Perf-guard break-even floor |
| `z = 1.645` / `z = 1.96` | 3041 / 3051 | Wilson bound confidence levels |
| `max(0.50, min(0.92, ...))` | 2824 | Clamp on `bayesian_win_prob` output |
| `(win_prob - 0.50) / 0.42 * 15.0` | 2876 | Probability→confidence-points mapping |
| `now - placed_at < 900` | 3323 | Paper-mode simulated settlement delay |
| `now - placed_at > 1200` | 3580 | Phantom-order purge |
| `resolve_cycle % 3` | 5139 | Settlement polling cadence (every 90s) |
| `deque(maxlen=60)` / `maxlen=59` | 1303–1304 | BTC price/return history depth (30 min at 30s) |
| `deque(maxlen=500)` | 1308 | In-memory trade history |
| `top_c = 85` | 4175 | Sizing-feasibility report assumption |

### 2c. Format presets (`formats.py`)

Each of `conservative` / `balanced` / `aggressive` hardcodes 16 values (`formats.py:78-160`):
`NORMAL/RECOVERY/MAX_TRADE_PCT`, `OB_IMBALANCE_THRESH`, `MIN_OB_DEPTH_DOLLARS`,
`R2_TREND_THRESHOLD`, `MIN_CONFIDENCE`, `MIN_EDGE_PCT`, `MIN_WIN_PROB`, `MAX_CONCURRENT_POS`,
`MAX_CONSEC_LOSSES`, `SESSION_STOP_FRACTION`, `YES_BREAKEVEN_PRICE`, plus toggles. This is a
**second, parallel source of truth** for the same parameters.

**Count: ~57 env-backed tunables + 16 hardcoded literals + 3 × 16 preset values across two files.**

---

## 3. What is logged today, and what survives a restart

| Sink | Written by | Content | Survives restart? |
|---|---|---|---|
| **stdout** (Railway logs) | `logging` (`bot.py:477`) | Everything — every gate rejection, `Anchor │`, `📋 EDGE JUSTIFICATION`, settlements | **No.** Railway retention only; not queryable, not structured, not on the volume. |
| **`/data/health.log`** | `command_bot.attach_health_log` (`command_bot.py:98`) | Mirror of the same stream | **Partially.** On the volume, but `RotatingFileHandler(maxBytes=512_000, backupCount=1)` → ~1 MB total. At 30s polls this wraps in **well under a day**. Nothing older is recoverable. |
| **`/data/lifetime_stats.json`** | `LifetimeStats` (`bot.py:2094`) | Aggregate `wins`, `losses`, `pnl` per paper/live bucket — **three numbers** | Yes |
| **`/data/bucket_stats.json`** | `BucketStats` (`bot.py:1857`) | Per-3h-bucket `{wins, losses}` — 8 buckets/day | Yes |
| **`/data/daily_state.json`** | `save_daily_state` (`bot.py:3845`) | Today's opening balance, realized P&L, halt flag | Yes (day-scoped, overwritten at UTC rollover) |
| `/data/recovery_state.json`, `/data/probation_state.json`, `/data/report_state.json`, `/data/billing_state.json` | respective classes | Mode state machines | Yes |
| **`/data/status_snapshot.json`** | `write_status_snapshot` (`bot.py:4452`) | One-cycle snapshot | Overwritten every cycle — no history |
| `/data/billing.log` | `BillingState._append_log` (`bot.py:2046`) | One JSONL row **per month** | Yes |
| **`trade_history`** | in-memory `deque(maxlen=500)` (`bot.py:1308`) | The only per-trade record that exists | **No.** Lost on every restart, redeploy and paper↔live flip. |

### The gap, stated plainly

**No per-decision record is persisted anywhere.** A taken trade exists only as an in-memory
dict and a stdout line. A **skipped** signal exists only as a `last_signal_desc` string that is
overwritten on the next cycle, plus one INFO line in a log that rotates away within a day.
There is no timestamped, queryable row for either.

Additional consequences:
- **Fees are never recorded.** `fee_cost` is read from Kalshi's settlement record inside
  `_extract_realized_dollars` (`bot.py:3220`) purely to net it out of P&L, then discarded.
- **Slippage is never recorded.** The limit price is logged at entry; the fill price is never
  compared against it.
- **Model probability is never scored.** `win_prob` is logged as text and thrown away. There
  is no stored (predicted, realized) pair anywhere, so calibration cannot be computed.
- `/data` is in `.gitignore` and is a Railway volume — it survives redeploys **only while the
  volume stays mounted at that path**. `verify_daily_state_path()` (`bot.py:3803`) exists
  precisely because that has failed before.

---

## 4. Current performance from existing data

**There is no live performance data available to this audit.**

The repository contains zero trade records: no `data/`, no `reports/`, no committed JSONL or
CSV of trading activity (`.gitignore` excludes `/data/`, `*_state.json`, `health.log`). The
container holds a fresh clone. Everything in §3 that persists lives on the Railway volume,
which is not reachable from here, and even if it were it holds only aggregate counters — not
the per-trade rows needed for expectancy, profit factor, drawdown or fee drag.

The only quantitative trading data that exists anywhere in the repo is the
**2026-07-23 → 2026-07-26 window** reconstructed from 25,000 Railway log lines in
`AUDIT_TRADE_LOGIC_2026-07.md`. That window is **five weeks stale**, predates v10.1.0–v10.3.3
(the market anchor, round-up removal, relative liquidity gate, daily profit target, recovery
re-anchoring), and n=8 settlements.

| Metric | Value | Source / status |
|---|---|---|
| Window | 3.05 days, 8,711 cycles | audit doc |
| Signals passing all gates | 65 | audit doc |
| Orders sent | 10 | audit doc |
| Orders filled + settled | **8 (3W / 5L)** | audit doc |
| Win rate | **37.5%** | audit doc |
| Balance | $16.67 → $14.83 (**−11.0%**) | audit doc |
| ROI on cash staked | **−18.5%** | audit doc |
| Model mean P(win) vs realized | 72.5% vs 37.5% | audit doc |
| Brier score — model vs market price | **0.342 vs 0.217** | audit doc |
| **Expectancy per trade** | **insufficient data** | needs per-trade P&L; only the aggregate −$1.84 exists |
| **Profit factor** | **insufficient data** | needs gross win $ and gross loss $ separately |
| **Max drawdown** | **insufficient data** | needs a per-trade equity curve |
| **Fee drag (% of gross P&L)** | **insufficient data** | `fee_cost` is netted out and discarded (`bot.py:3220`); never stored |
| **Slippage vs expected** | **insufficient data** | fill price never compared to limit price |
| **Calibration by decile** | **insufficient data** | requires ≥ ~200 stored (predicted, realized) pairs; zero are stored |
| **Any post-v10.1.0 performance** | **insufficient data** | no logging survived the window |

### Exactly what logging is missing to close this

1. A durable per-decision row for **every evaluated opportunity, taken and skipped** — with
   `model_probability`, `market_yes_price`, `computed_edge`, `spread`, `minutes_to_expiry`,
   `size_contracts`, `decision`, `skip_reason`.
2. **Fill price** captured at settlement and stored alongside the limit price → slippage.
3. **`fees_paid`** stored as its own field rather than netted into P&L → fee drag.
4. **Per-trade realized P&L** as a durable row (not an aggregate counter) → expectancy,
   profit factor, equity curve, max drawdown.
5. **Outcome-at-expiry backfill for skipped signals** → the counterfactual.
6. **BTC realized volatility** at decision time — computed at `bot.py:2513` and discarded.
7. **`params_version`** on every row, so a change can be attributed.

Phases 1–2 of this project supply exactly items 1–7.

---

## 5. Three most likely causes of recent underperformance — ranked

### #1 — The model has no measured edge; the ±8pp cap is doing the work

**Evidence (measured, `AUDIT_TRADE_LOGIC_2026-07.md` §2 F3 and §5.2):**
- `bayesian_win_prob` returned mean 70.4%, sd 4.3pp across 65 signals — a near-constant.
- Model Brier 0.342 vs 0.217 for simply believing the quoted price. The market beat the model
  **on the model's own trade selection**.
- P(≤3 wins in 8 | the model's own 72.5% claim) = 4.1%.
- Two of the terms feeding the lift are constants, not measurements: `regime_adj` carries an
  unconditional `+0.02` and `depth_adj` a flat `+0.02` for any book over $500 — so **~4pp of
  every reported "edge" is a constant**.
- In the v10.1.0 replay the anchored lift **saturated the ±8pp cap on 47 of 50 survivors**.

**Why it explains a degradation now:** the market anchor (v10.1.0) made the number *honest*
without creating alpha. If the lift saturates its cap on essentially every signal, then
`MIN_EDGE_PCT = 0.06` is not a filter — a saturated 8pp lift clears a 6pp bar every time. The
edge gate, the win-prob gate and the confidence gate are all downstream of the same saturated
quantity, so all three pass together or fail together. The bot is effectively trading on the
order-book imbalance alone, which §2 F4 measured as `corr(OB%, confidence) = +0.92` and which
**did not discriminate outcomes at all** (winners' mean confidence 79.0; losers' 77.4; the
single highest-confidence trade of the window was the largest loss).

**Confidence in this ranking: high on the mechanism, low on the magnitude** — the mechanism is
measured, the current live magnitude is not.

### #2 — Fees and slippage are unmeasured and are structurally large relative to the edge

**Evidence:** `fee_cost` is subtracted inside `_extract_realized_dollars` (`bot.py:3220`) and
never stored. Slippage is never computed at all. Meanwhile the claimed edge is capped at 8pp
(`MAX_MODEL_EDGE_PP`) and gated at 6pp (`MIN_EDGE_PCT`), and the strategy trades **only inside
25c–75c** (`bot.py:4694`), where Kalshi's fee on a $1 payout is a material fraction of a 6–8pp
edge. Entries are placed as marketable limits one cent inside the touch
(`bot.py:4750-4754`), so slippage is real, not theoretical.

**Why it explains a degradation:** an edge of 6–8pp gross that is not measured net of fees is
not established as positive at all. A strategy sitting near break-even gross goes negative net
without any change in the model, and nothing in the current instrumentation would show it.

**Status: insufficient data — this is a structural argument, not a measurement.** Confirming
it requires stored `fees_paid` and `slippage_vs_expected` (Phase 1). It is ranked #2 because
the arithmetic is unavoidable, not because it has been observed.

### #3 — Guard interaction has cut throughput to a level where nothing can be learned or recovered

**Evidence (measured):**
- The bot averaged **~2 trades/day** over the audited window (§2 F8), and 3 of the 4 days
  produced 6, 1, 3 and **0** orders (§1 table).
- `MAX_CONSEC_LOSSES=3` "never fired in 3 days because the bot rarely got 3 trades off" (§5.5).
- `performance_guard` "was never evaluated once" at that rate (§2 F8) — the only statistical
  circuit breaker in the engine was dead code, now fixed but still needing ~20 settlements.
- Current config stacks: session-quality (blocked 2,049 cycles), regime (1,949), expiry
  (891+623), order book (378+134+36), regime/OB conflict (223), momentum (83) — then, on top,
  the post-audit additions: `OB_IMBALANCE_MAX=0.95`, the `MIN_WIN_PROB=0.60` floor which
  the audit notes "puts a hard price floor near 50c", the undocumented 25c–75c band, the
  `DAILY_PROFIT_TARGET` halt at +3%, and `MIN_DEPTH_STAKE_MULT=3.0`.

**Why it explains a degradation:** at 1–3 trades/day, a handful of losses is the entire
sample. The daily +3% halt is asymmetric — it caps the good days at +3% while leaving the bad
days uncapped except by the 40% session stop — so low throughput plus a truncated right tail
produces exactly the shape of "was working, now bleeding" without any model change. It also
means the per-bucket learned prior (`BUCKET_PRIOR_FULL_N=30`, 8 buckets/day) needs **months**
to reach full trust in any single bucket.

**Confidence: medium.** The throughput figures are measured; the causal link to recent P&L is
inference, because no post-v10.1.0 trade data survived.

### Honest summary

All three causes rest on a five-week-old n=8 window. **The most important finding of this
audit is that the current bot cannot be diagnosed at all** — it emits a rich decision trace
to a log that rotates away within a day, persists nothing per-decision, discards fees,
slippage and every model probability, and keeps only three aggregate counters. Ranking these
three causes is the best that can be done with what exists; distinguishing between them
requires Phase 1 to be in place first.

---

## 6. Notes carried into later phases

- **Storage decision (Phase 1):** `DATABASE_URL` is not referenced anywhere in the repo and
  `requirements.txt` has no Postgres driver. `/data` is gitignored and volume-backed. This
  needs a decision at Phase 1 — a JSONL committed on write conflicts with `.gitignore`, and
  adding a Postgres driver is a dependency change requiring sign-off per the global rules.
- **Two sources of truth:** Phase 2 must reconcile `formats.py` presets with
  `config/params.json`, or the presets will silently re-seed values the optimizer thinks it
  owns.
- **`tunable: false` candidates identified here:** `MAX_TRADE_PCT`, `SESSION_STOP_FRACTION`,
  `MAX_CONSEC_LOSSES`, `MAX_CONCURRENT_POS`, `RISK_MIN_TRADE_PCT`, `DAILY_PROFIT_TARGET_*`,
  `MIN_ORDER_ROUNDUP`, `VOL_CIRCUIT_BREAKER`, `PERF_GUARD_*`, and all credentials/paths.
- **Replay feasibility (Phase 4):** replay can only reproduce realized P&L once Phase 1 rows
  carry `fill_price` and `fees_paid`. Until then the 2% reproduction gate is unmeetable — the
  harness would be reconstructing P&L from a limit price that was not the fill price.
- **No exits exist.** The Phase 1 `exit_reason` field will only ever take `EXPIRY` or `HALT`
  under current logic; `TP` / `SL` are unreachable. Flagging rather than adding exits, which
  would be a strategy change outside Phase 0–3 scope.
