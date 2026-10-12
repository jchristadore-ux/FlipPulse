# RAIM — Gate 1: Requirements Specification

| | |
|---|---|
| Status | **DRAFT — awaiting owner approval** |
| Date | 2026-10-12 |
| Phase | AgenKit phases 1–2 (Orient → Brainstorm/Spec) |
| Next gate | Gate 2: Architecture. No code is written until this document is approved. |
| Mode | Design only. No trading code exists. Live order placement is not built and stays disabled. |

> This is a requirements document, not a trading system. No performance claim appears anywhere in it. The only numbers here come from one ~3-minute public spread sample, which is linked in §3. Market making can lose money quickly. Nothing here is financial advice.

---

## 0. Orient: findings and contradictions in the brief

| # | Finding | Evidence | Resolution proposed |
|---|---|---|---|
| O1 | The "supplied RAIM research" is not in the repo or the conversation. | `grep -ri raim` over the repo found nothing relevant. | The prompt itself is treated as the governing design. **Owner: supply the research document if it exists.** |
| O2 | AgenKit is a licensed npm product (`npx agenkit activate <key>`, `npx agenkit install engineering-kit`). It is not installed in this environment. | agenkit.xyz | I run its six phases by hand: Orient, Spec, Architecture, test-first Build, two-pass Review (spec, then quality), Ship. I stop at each gate. If you want the real kit, install it yourself with your license key. |
| O3 | The brief says to pin tradingview-mcp **v3.3.x**. No such version exists. | PyPI `tradingview-mcp-server`: releases 0.3.0 … **0.8.1** (2026-08-24), `requires_python >=3.10,<3.14`. The README badge shows 0.9.0, which is not on PyPI. | Pin `tradingview-mcp-server==0.8.1` with Python 3.13 and record the hash in a lockfile. |
| O4 | The brief gives the error envelope as `{"error":"<code>","retry":<bool>}`. The README shows a nested object with `code`, `message` and `retryable`, plus batch fields. It also says only the scanner tools use it so far; the rest are migrating (issue #76). | README, `core/errors.py` (named, not yet read) | The parser accepts both shapes. Any response it does not recognise, including a non-JSON or a plain-text error, is treated as **non-retryable** and confidence decays. This gets a contract test against the pinned version. |
| O5 | tradingview-mcp crypto coverage is Binance (global), KuCoin and Bybit, not Binance.US, Coinbase or Kraken. | README | The slow brain's crypto context comes from a different venue than the one we trade. That is fine for regime context (TrendAlign, VolExpansion) but it is not a price input. VIX comes from `yahoo_price` (`^VIX`). Whether `^VIX` is supported is **unknown**; test it with one call after install. |
| O6 | The current repo is FlipPulse, an unrelated Kalshi bot product. | repo tree | RAIM goes in a self-contained `raim/` package that never imports FlipPulse code. **Recommendation: a dedicated repo.** Owner decision at Gate 2. |
| O7 | Every Coinbase and Kraken pair sampled fails Gate 0 at retail fee tiers by more than 10×. | §3 | Binance.US is the only Gate 0 candidate. See §3. |

---

## 1. Scope

**In scope (through PAPER mode):**
- Market-data capture
- Order-book reconstruction
- Feature pipeline
- Regime engine
- Quoting engine
- Simulated order manager
- Deterministic risk governor
- Slow brain
- Tick-level simulator
- Walk-forward research harness
- Reporting
- Audit log
- Parameter registry

**Out of scope until you explicitly approve it in writing:**
- Live order placement. The live adapter's `place` and `cancel` methods raise `LiveTradingDisabled` unless all three hold: an env flag is set, a signed approval file exists, and a config hash matches.
- The stat-arb legs. Specified here only as an interface and a kill condition (FR-R8). Not built until single-venue market making has positive out-of-sample net edge.
- The second venue adapter. It is an empty, labelled slot that raises `NotImplementedError("ADAPTER SLOT 2 — UNIMPLEMENTED")`.

## 2. Mode progression

| Mode | What runs | Entry criteria |
|---|---|---|
| CAPTURE | WebSocket recording only | Gate 2 approved |
| SIMULATION | Replay of captured data through the full fast body and the simulator | ≥ 7 days of clean capture, including ≥ 1 weekend and ≥ 1 high-volatility day. Book-reconstruction checksum tests pass. |
| PAPER | Live data, simulated fills against the live book, no orders sent | Gate 0 passed on captured data. Out-of-sample walk-forward net edge > 0 under the 2×-latency stress, with a confidence interval excluding 0 (FR-V5). All risk tests green. |
| LIVE | — | Not specified. Requires explicit written approval, a separate gate, and a separate document. |

## 3. Gate 0: venue viability

**Criterion:** `maker_fee + E[adverse_selection] < 0.5 × typical_spread`, evaluated per instrument.

**Definitions** (all to be measured, none assumed):
- `typical_spread`: the time-weighted median quoted spread in bps over the capture window. It is reported per hour-of-day and per regime, because a pass only during quiet hours is not a pass.
- `E[adverse_selection]`: the volume-weighted mean signed mid-price markout against a hypothetical passive fill. For each aggressor trade that would have hit our quote at the touch, compute `side × (mid_{t+h} − fill_price)/mid_t`. Report it at h ∈ {1 s, 5 s, 30 s, 60 s}. **h = 5 s is the decision horizon until justified otherwise.** This upper-bounds a queue-agnostic maker. Queue-position-aware fills come in SIMULATION.
- `maker_fee`: the fee actually charged to your account tier. It is read from the authenticated fee endpoint or a confirmed fill, not from marketing pages.

**Preliminary evidence:** [`raim/research/evidence/2026-10-12_spread_probe.md`](../research/evidence/2026-10-12_spread_probe.md)

| Venue | NJ access | Retail maker fee | Widest half-spread sampled | Gate 0 status |
|---|---|---|---|---|
| Coinbase Advanced | Believed available. **Unverified: confirm in your account.** | ~40 bps (secondary sources; Coinbase changed tiers 2026-09-16 per one report). **Unverified.** | ~1.75 bps (DOGE-USD) | **FAIL**: the fee alone is more than 20× the half-spread |
| Kraken Pro | **Unverified** | 40 bps tier 1, 2 bps at $5M+, 0 bps at $10M+ (kraken.com fee schedule) | ~0.75 bps (LINKUSD) | **FAIL** at any tier we can realistically reach |
| Binance.US | NJ is listed as supported (support.binance.us article 9842798). **Re-verify on the live page.** | 0% maker, 0.02% taker on spot (Binance.US announcement 2026-04-22, "subject to change") | ~3.2 bps (AVAXUSDT); ~2.3 bps (DOGE/LINK USDT) | **OPEN**: passes only if E[AS] < ~2.2–3.2 bps. Unmeasured. |

**Binance.US risks the spread numbers do not capture:**
- Thin depth. AVAXUSDT had about $2.3k per side within 10 bps.
- Likely price-follower dynamics. Arbitrageurs pick off stale quotes when Coinbase or Binance global moves.
- USDT quote-currency exposure.
- Venue and counterparty risk: custody and banking history.
- Fees can change without notice.

Each is listed in §9.

**Gate 0 decision rule (FR-G0):** Gate 0 passes for an instrument only if all four hold on ≥ 7 days of captured data:
1. The 5 s markout plus fee is below the half-spread in the aggregate.
2. The same holds in ≥ 2 of 3 time-of-day buckets.
3. The 95% block-bootstrap CI upper bound of (fee + AS) is below the half-spread.
4. The result holds when markouts are measured against **Coinbase mid** as well as the local mid. This catches lead-lag toxicity.

Otherwise, **stop** and select another instrument or venue.

---

## 4. Functional requirements

Each requirement has an ID and a test. "T:" names the acceptance test written *before* the code (test-first).

### 4.1 Data and venue adapter (FAST BODY)

- **FR-D1 Adapter interface.** A pluggable `VenueAdapter` exposes:
  - `connect`, `subscribe_book`, `subscribe_trades`, `snapshot`
  - `fees()` (authenticated, cached, timestamped)
  - `place` and `cancel` (hard-disabled; see §1)
  - `health()`

  Slot 1 is Binance.US, provisionally, pending Gate 0. Slot 2 is an explicit unimplemented stub.
  T: an interface conformance test suite runs against a fake adapter and slot 1. Slot 2 raises on every method.
- **FR-D2 Order-book reconstruction.** Build the L2 book from REST snapshot + diff stream with sequence-gap detection.
  - The Binance.US mechanics are expected to be: `depth` diff stream with `U`/`u` update ids; REST snapshot with `lastUpdateId`; drop events with `u ≤ lastUpdateId`; first applied event must satisfy `U ≤ lastUpdateId+1 ≤ u`. **To be verified against docs.binance.us at Gate 2.**
  - Any gap → mark the book INVALID, cancel all quotes, resync.

  T: replay fixtures with an injected gap, duplicate, out-of-order event and stale snapshot. Every one must end INVALID and emit a cancel-all signal.
- **FR-D3 Trade tape** with exchange timestamp, local receive timestamp (monotonic and wall clock), and aggressor side.
- **FR-D4 Capture.** Store raw messages append-only, compressed and partitioned by day, with message-level SHA-256 chaining for tamper evidence. Replay must reproduce the book byte-for-byte. T: round-trip capture → replay → book-hash equality.
- **FR-D5 Timestamp discipline.**
  - Every derived record carries `exchange_ts`, `recv_ts` and `available_ts` (when the system could first have acted on it).
  - Features may only use records with `available_ts ≤ decision_ts`.
  - Clock skew between exchange and local time is estimated and logged. Skew > 250 ms (initial threshold, registry param) raises an alarm.

  T: look-ahead property tests (FR-V2).
- **FR-D6 Stale feed.** No book update for > `stale_ms` (registry; initial 1500 ms for liquid, tuned per instrument) or a heartbeat miss → cancel-all, quoting suspended until the book is VALID for `resume_ms`.

### 4.2 Features

| ID | Feature | Definition / source | Notes |
|---|---|---|---|
| FR-F1 | Micro-price | Stoikov (2018), imbalance-adjusted mid; start with the 1-step weighted-mid approximation, upgrade to the estimated G-function only if OOS markout improves | fair value input |
| FR-F2 | OFI | Cont, Kukanov & Stoikov (2014), multi-level, normalised by depth | predictiveness measured as rolling OOS R² of OFI → Δmid |
| FR-F3 | Bipower variation σ | Barndorff-Nielsen & Shephard; robust to jumps | plus realized variance; jump = RV − BV |
| FR-F4 | VPIN | Easley, López de Prado & O'Hara (2012), volume buckets, bulk-volume classification **or** tape aggressor side (use the tape since we have it) | toxicity |
| FR-F5 | Variance ratio | Lo–MacKinlay at multiple horizons | mean-reversion vs trend |
| FR-F6 | Hawkes branching ratio n = α/β | exponential-kernel MLE on trade arrivals, rolling window | n → 1 = endogenous/critical |
| FR-F7 | Spread, depth, imbalance | top-N levels | |
| FR-F8 | Cross-venue lead | Coinbase mid return lead over local mid (read-only public feed) | **Critical for toxicity on a follower venue**; adds a read-only second data feed (not a trading adapter) |

Every feature carries:
- a declared lookback
- a declared `available_ts` rule
- a unit test against a hand-computed fixture
- a leakage test (FR-V2)

### 4.3 Regime engine

- **FR-R1** A 4-state Gaussian-mixture or Student-t emission HMM:
  - R1 calm / mean-reverting
  - R2 trending / informed flow
  - R3 high-vol / stress
  - R4 toxic / event / illiquid

  Observations are §4.2 features, standardised with training-window statistics only. Fitted offline with Baum-Welch on training folds only. The state labels are assigned post hoc by a documented rule (e.g., R3 = highest σ, R4 = highest VPIN × lowest depth). The label mapping is persisted and versioned.
- **FR-R2** Online forward filter `p_t(j) ∝ f_j(x_t) Σ_i p_{t−1}(i) π_ij`, computed in the log domain with underflow guards.
- **FR-R3** Slow-state tilt: `π(t) = normalise(π_base ⊙ exp(Γ · s_t))`, where s_t = (z_VIX, EventRisk). Γ is constrained so the tilt can only **raise** transition mass into R3/R4.
- **FR-R4** BOCPD (Adams & MacKay 2007) runs on standardised returns and spread. A change-point alarm forces `p(R3∪R4) ≥ floor_cp` for `cp_hold` updates.
- **FR-R5** Parameter blending `θ = Σ_k p(k) θ_k`, with a conservative bias: risk-increasing parameters (size, aggressiveness) use `min` over the posterior-weighted and R3-weighted values; spread uses `max`.
- **FR-R6** Hysteresis:
  - Pull quotes when `p(R4) > 0.7` for `N` consecutive updates (registry; initial N = 5).
  - Release only after `p(R4) < 0.4` for `N_release` consecutive updates **and** the book is VALID.
  - T: synthetic posterior sequences, including oscillation at 0.69/0.71, never flap.
- **FR-R7** Regime behaviours:

| Regime | Quoting | Size | Inventory reversion |
|---|---|---|---|
| R1 | two-sided, tight (spread floor = tick or fee-implied floor) | normal | base κ |
| R2 | skew with flow (micro-price + OFI); widen or drop the side facing informed flow | reduced on the adverse side | elevated |
| R3 | wider (σ-scaled) | smaller | fast |
| R4 | cancel all, stand down | 0 | unwind only by passive orders unless limits breached, then by the deterministic flatten rule |

- **FR-R8** Stat-arb legs (future): auto-disabled when the rolling Engle-Granger / Johansen test fails at the registry threshold, or when the half-life exceeds its bound. Interface only.

### 4.4 Quoting

- **FR-Q1** The quote model is Avellaneda–Stoikov (2008) with Guéant–Lehalle–Fernandez-Tapia (2013) closed-form inventory-bounded approximations.
  - Reservation price: `r = s_micro − q γ σ² τ`
  - Half-spread: `δ = (1/γ) ln(1 + γ/k) + ½ γ σ² τ`, with the GLFT inventory-bounded variant.
  - **Published γ and k are priors only.** k (order-arrival decay) is estimated from our own fill-intensity vs distance-from-mid data, per regime.
- **FR-Q2** Quotes are clamped to:
  - post-only (never cross)
  - tick and lot size
  - the minimum notional
  - a fee-aware floor: never quote a half-spread below `maker_fee + AS_estimate(regime)`

  If the floor exceeds the regime's maximum spread, **that side is not quoted**.
- **FR-Q3** Side disablement: a side whose rolling OOS markout-adjusted PnL < 0 over `W_side` fills is disabled until re-validated in SIMULATION.
- **FR-Q4** Message discipline:
  - Requote only when the price moves ≥ 1 tick or the size moves ≥ `min_size_delta`.
  - Respect venue rate limits with headroom (registry: use ≤ 50% of the published limit).
  - No order is placed with intent to cancel before execution. This is the anti-spoofing and anti-layering rule (§7).

### 4.5 Order manager (simulated through PAPER)

- **FR-O1** A state machine: NEW → ACK → PARTIAL → FILLED / CANCELED / REJECTED. Every transition is idempotent, keyed by client order id. Unknown states trigger a cancel-all and reconcile.
- **FR-O2** Reconciliation runs every `recon_s`. Local open orders and position are compared with the venue (PAPER: compared with the simulator). Any mismatch → halt and alert.

### 4.6 Risk governor (deterministic, outside every model and the LLM)

All limits live in a signed, versioned config. The governor is the last component before the adapter. Nothing else can bypass it.

| ID | Limit | Rule |
|---|---|---|
| FR-K1 | Inventory cap | `Qmax = min(B / (z · σ · √h_unwind), c · depth)`, where B = loss budget for the unwind, z = 2.33 initial, σ is from BV, h_unwind is estimated from depth and taker cost, and c = 0.1 of the top-N depth initially (all registry params) |
| FR-K2 | Max gross exposure | absolute USD notional cap across instruments |
| FR-K3 | Drawdown halt | intraday and rolling peak-to-trough limits → cancel-all + flatten + HALT. A halt needs a manual reset through a CLI command with a reason, which is logged. |
| FR-K4 | Stale feed | cancel-all (FR-D6) |
| FR-K5 | Reject / message rate | reject ratio > threshold or rate-limit headroom < threshold → exponential backoff; repeated → HALT |
| FR-K6 | Loss streak | k consecutive losing round-trips (markout-defined) → widen ×w; k₂ → pause for `pause_s` |
| FR-K7 | Stat-arb kill | FR-R8 |
| FR-K8 | Multiplier | `m_applied = min(m_LLM_effective, m_rules)`. m_LLM_effective = 1 when the slow brain is absent; it never exceeds m_rules. Applied as a multiplier to size and Qmax and as a divisor to aggressiveness. |
| FR-K9 | Loosen-attempt detection | Any slow-brain output that would raise a limit if applied directly is logged as `LLM_LOOSEN_ATTEMPT` and alerted. It is then clamped. A counter of these events is part of every report and of final-check question 5. |
| FR-K10 | Kill switch | file or env flag checked every loop → cancel-all + HALT within one loop iteration |

T: a property-based test (hypothesis) checks that for any slow-state input (valid, malformed or adversarial), every applied limit is ≤ the rules-only limit. A fault-injection test covers each halt path.

### 4.7 Slow brain

- **FR-S1** A separate process. It polls the pinned tradingview-mcp (`uvx --python 3.13 --from tradingview-mcp-server==0.8.1 tradingview-mcp`). Polling is at most about 1 call/s total and respects the server's 60 s cache, the TA concurrency limit of 4 and ≥ 0.8 s spacing. It never runs in the tick loop and has no import path into the fast body.
- **FR-S2** Claude (`claude-opus-5-5`) is called with structured outputs to produce a schema-validated `SlowState`:
  - `z_VIX: float`
  - `TrendAlign ∈ [−1, 1]`
  - `VolExpansion ∈ {0, 1}`
  - `EventRisk ∈ {0, 1}`
  - `UniverseScore: float`
  - `m ∈ [0, 1]`
  - `c ∈ [0, 1]`
  - `as_of`
  - `sources[]`
  - `model_id`
  - `prompt_hash`

  Schema validation failure → discard the output and keep the last good state, with decay.
- **FR-S3** The state is delivered over a one-way channel (a file or socket the fast body only reads). The fast body treats a missing, stale or malformed state as "absent" → m_LLM_effective = 1 (no tightening, no loosening), and the rules alone govern.
- **FR-S4** Error handling:
  - Retryable → exponential backoff with jitter, keeping the last good state.
  - Non-retryable or unknown → `c = c₀ · exp(−age/τ)`. Tightening outputs decay toward 1 (neutral), never below the rules.
- **FR-S5** Claude never receives order-entry tools and never prices, places or cancels orders. No component holding exchange credentials is reachable from the slow-brain process; they run as separate OS users or containers.
- **FR-S6** Fast-body-survives-outage test: kill the slow brain mid-replay. The fast body keeps quoting under rules-only limits with a byte-identical decision trace to a rules-only run from that point.
- **FR-S7** Supply chain: install tradingview-mcp only from PyPI `tradingview-mcp-server` or the upstream GitHub repo, with a hash-pinned lockfile. **Never install any npm "tradingview-mcp" package.** Optional `MARKETAUX_API_TOKEN` (free tier is 100 requests/day per the README) comes from env only.

### 4.8 Simulator

- **FR-M1** A tick-level, event-driven simulator driven by captured data. It models:
  - queue position: FIFO at price level; our order joins the back; the queue ahead depletes only by trades at that level and by cancels allocated pro-rata (assumption is configurable; alternatives are a pessimistic "cancels come from behind" and an optimistic "from ahead" bracket)
  - partial fills
  - ack latency and cancel latency, from an empirical distribution plus jitter
  - fees and rebates from config
  - slippage on taker unwinds via walking the book
  - self-trade prevention
- **FR-M2** The latency distribution is measured in PAPER from real round-trips of a no-op endpoint. Until then it is a registry prior, flagged UNVALIDATED. Every result is also reported at **2× latency**.
- **FR-M3** Determinism: identical seed and data → an identical event log hash.
- **FR-M4** The simulator's own validation: fill-rate and markout predictions are compared with PAPER fills when available. Material divergence invalidates prior SIMULATION results in the registry.

### 4.9 Validation and reporting

- **FR-V1** Purged and embargoed walk-forward (López de Prado). The purge is ≥ the longest feature lookback plus the longest label horizon. The embargo is ≥ 1 h initially. The HMM, scalers and all estimated parameters are refit on the train fold only.
- **FR-V2** Leakage checks:
  - Each feature recomputed with data truncated at t must equal the streaming value at t.
  - A future-shuffled label control must show zero edge.
  - Timestamp monotonicity and skew checks.
  - Survivorship: the instrument universe is fixed ex ante per fold, and delisted or halted periods are kept, not dropped.
- **FR-V3** Per-regime PnL attribution covers spread capture, adverse selection (markout), inventory PnL, fees, and rebates. It is reported per instrument, side, regime and hour-of-day.
- **FR-V4** Markout reports at 1 / 5 / 30 / 60 s against local mid and Coinbase mid.
- **FR-V5** Edge acceptance: the net PnL per unit of notional has a 95% block-bootstrap CI excluding 0, on OOS folds, at 2× latency, under the **pessimistic** queue assumption. It must also be ≥ 0 in R2 and R3 combined, not only R1 (final-check question 3).
- **FR-V6** Every run writes a manifest: git SHA, config hash, data partition hashes, seed and environment lockfile. Reports without a manifest are invalid.

### 4.10 Audit, ops and secrets

- **FR-A1** Append-only, hash-chained audit log of decisions:
  - quotes, cancels and fills
  - limit changes and halts
  - slow-state ingests
  - loosen attempts
- **FR-A2** Secrets come from env or a secret manager only. They are never logged; a redacting log filter has a test. API key scope is trade-only, with withdrawals disabled. IP allowlisting, **if the venue supports it, is to be verified**, and must be configured before PAPER is accepted. PAPER needs read-only keys at most.
- **FR-A3** Rollback: config and model artifacts are versioned and content-addressed. `raim rollback <version>` is tested.
- **FR-A4** Alerts on halt, loosen attempt, reconcile mismatch, feed loss and clock skew. Delivered on a channel to be chosen at Gate 2.

---

## 5. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-1 | Fast-body decision latency: p99 < 5 ms from book update to quote decision on commodity hardware (Python + NumPy; profile before considering Rust or Cython). Network latency to Binance.US: **unknown**, measure it. |
| NFR-2 | Python 3.12 or 3.13, typed (mypy strict on core), `pytest` + `hypothesis`; ≥ 90% branch coverage on the risk governor, book builder and order manager |
| NFR-3 | No network in unit tests; recorded fixtures only |
| NFR-4 | Reproducible: the lockfile and a pinned container image |
| NFR-5 | The fast body runs with the slow brain absent (a hard architectural invariant, tested) |

## 6. Gate exit criteria (what you approve, in order)

1. **Gate 1 (this doc):** requirements, Gate 0 rule, venue shortlist.
2. **Gate 2: Architecture.** Module diagram, process isolation, data schemas, adapter contract verified against Binance.US docs, risk-governor design, test plan.
3. **Gate 3: Plan.** Ordered, test-first milestones: M1 capture plus book, M2 Gate 0 report, M3 features plus leakage suite, M4 simulator, M5 baseline AS/GLFT without HMM, M6 HMM plus BOCPD, M7 slow brain, M8 PAPER harness.
4. **Gate 4: Build.** Per milestone, with a review after each.
5. **Gate 5: Independent review.** Spec compliance, then code quality and a security review.
6. **Gate 6: Release validation.** The final check in §8, answered from run artifacts only.

**The baseline comes before the complexity.** M5 is a plain AS/GLFT quoter with the risk governor and no regime model. The HMM is adopted only if it beats M5 out of sample on FR-V5 metrics. The same rule applies to every later addition: micro-price G-function, Hawkes, VPIN, slow brain.

## 7. Compliance requirements

- No spoofing, layering or wash trading. Self-trade prevention is enabled. Quotes are bona fide; the message-discipline rules are in FR-Q4.
- Before PAPER, verify:
  - venue terms of service on automated trading and market making
  - NJ residency eligibility (live page)
  - account fee tier from the authenticated endpoint
  - tax-lot record keeping (fills export)
- Legality and tax treatment are your own responsibility. I can list what to check but cannot give legal advice.

## 8. Final check (to be answered from artifacts at Gate 6, not before)

1. Is edge still positive after fees, adverse selection, slippage and realistic queue fills?
2. Is the alpha predictive out of sample?
3. Does each regime behave as intended, and does the system still make money outside R1?
4. Can it survive feed failures, volatility spikes, adverse inventory and structural breaks?
5. Is the slow brain isolated from execution, and did the LLM ever loosen a limit?
6. What could we be wrong about? (§9 is the starting list.)

## 9. Unknowns and what-could-be-wrong register

| # | Unknown / risk | How to test |
|---|---|---|
| U1 | Gate 0 may fail on every reachable venue. This is the most likely outcome given §3. | FR-G0 measurement on ≥ 7 days of capture |
| U2 | Binance.US fees and NJ eligibility may have changed | Authenticated fee endpoint; live support page; account onboarding |
| U3 | Adverse selection on a follower venue is dominated by cross-venue arbitrage | Markouts vs Coinbase mid (FR-F8, FR-V4) |
| U4 | The queue model is wrong, so simulated fills are optimistic | Bracket with pessimistic and optimistic assumptions; validate against PAPER |
| U5 | Our latency to the venue is uncompetitive | Measure the RTT distribution; 2× stress |
| U6 | The HMM states are unstable across refits (label switching) or don't map to the intended semantics | Refit stability across folds; confusion vs label rule; HMM must beat the baseline |
| U7 | Hawkes and VPIN are too noisy at our data rate to help | Ablation in walk-forward |
| U8 | tradingview-mcp breaking changes or outages | Pinned version, contract tests, outage test (FR-S6) |
| U9 | Whether tradingview-mcp's `yahoo_price` serves `^VIX` | One call after install |
| U10 | Venue and custody risk (Binance.US) | Not testable by us. Cap capital at venue, accept, or choose another venue. **Owner decision.** |
| U11 | A 3-minute Sunday-night sample is not representative | 7-day capture |
| U12 | Binance.US IP allowlisting and API key scopes | Read the API key management docs and check the account UI |

## 10. Decisions requested at this gate

1. **Approve** this requirements spec, or mark changes.
2. **Venue for Gate 0 measurement:** Binance.US (DOGE, LINK, AVAX, SOL vs USDT and USD), with Coinbase as a read-only reference feed. Or name an alternative.
3. **Repo location:** a dedicated `raim` repo (recommended) or the `raim/` folder in FlipPulse.
4. **AgenKit:** proceed with the hand-run phases, or install the licensed kit yourself.
5. **Supply the RAIM research document**, if one exists (O1).

---
**Sources**
- [agenkit.xyz](https://agenkit.xyz)
- [tradingview-mcp README](https://github.com/atilaahmettaner/tradingview-mcp)
- [PyPI tradingview-mcp-server](https://pypi.org/project/tradingview-mcp-server/)
- [Kraken fee schedule](https://www.kraken.com/features/fee-schedule)
- [Binance.US 0% maker announcement](https://blog.binance.us/zero-fee-trading/)
- [Binance.US supported states](https://support.binance.us/en/articles/9842798-list-of-supported-and-unsupported-states-and-regions)
- [Coinbase fees (secondary: BrokerChooser)](https://brokerchooser.com/news/coinbase-vs-kraken-fee-structures-and-trading-features-compared--bbeea493)
- [Coinbase 2026-09-16 tier change (secondary: Diario Bitcoin)](https://www.diariobitcoin.com/exchanges/coinbase-reduce-sus-comisiones-de-advanced-y-baja-el-umbral-inicial-a-usd-10-000/)

**Papers**
- Avellaneda & Stoikov (2008)
- Guéant, Lehalle & Fernandez-Tapia (2013)
- Cont, Kukanov & Stoikov (2014)
- Stoikov (2018)
- Easley, López de Prado & O'Hara (2012)
- Adams & MacKay (2007)
- Barndorff-Nielsen & Shephard (2004)
- Lo & MacKinlay (1988)
- López de Prado (2018)
