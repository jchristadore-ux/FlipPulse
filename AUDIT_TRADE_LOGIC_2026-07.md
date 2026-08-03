# Trade Logic Audit — entries, exits, sizing

**Evidence:** 25,000 Railway log lines, `2026-07-23 16:59` → `2026-07-26 18:04` UTC (3.05 days,
8,711 main-loop cycles). Live mode, Trading Format **aggressive**
(`NORMAL_TRADE_PCT=20%`, `RECOVERY=5%`, `MAX=30%`, ladder ON, `OB_IMBALANCE_THRESH=0.65`,
`MIN_CONFIDENCE=60`, `MIN_EDGE_PCT=0.05`, `MIN_WIN_PROB=0.58`, `MAX_CONSEC_LOSSES=3`).
Code audited at `bot.py` v10.0.0.

**Headline:** the entry logic was not the main problem — the **sizing floor** was. For three of
the four audited days the bot could not buy a single contract, and the 15% of signals that did
get through were selected *by price*, not by edge. Separately, the win-probability model was
measurably worse than simply believing the quoted price.

---

## 1. What actually happened over the window

| | |
|---|---|
| Main-loop cycles | 8,711 |
| Signals that passed every entry gate | **65** |
| Signals silently discarded at sizing | **55 (84.6%)** |
| Orders actually sent | **10** |
| Orders that filled and settled | 8 (3W / 5L) |
| Orders cancelled unfilled | 2 |
| Balance | $16.67 → $14.83 (**−11.0%**) |

Per day:

| Day | Signals | Killed at sizing | Orders sent |
|---|---|---|---|
| 07-23 | 6 | 0 | 6 |
| 07-24 | 26 | 25 | **1** |
| 07-25 | 25 | 22 | 3 |
| 07-26 | 8 | 8 | **0** |

Every entry gate was working and was well exercised — session quality blocked 2,049 cycles,
regime 1,949, expiry 891+623, order book 378+134+36, regime/OB conflict 223, momentum 83.
The funnel was healthy right up to the last step.

---

## 2. Findings

### F1 — CRITICAL: the size floor silently discarded 85% of signals

`place_order` sized with `count = int(bet_dollars * 100 / limit_cents)`. When that floored to
zero it logged one INFO line and returned `None` — **after** `📋 EDGE JUSTIFICATION` had already
been logged and pushed to Telegram. 55 of 65 signals died there. The log reads like a bot that
was hunting and choosing; it had in fact been unable to place an order since 07-24 08:02.

The stake had collapsed to **$0.37** through independent de-riskers multiplying:

```
NORMAL_TRADE_PCT           20%     of balance
  → probation rung 1        5%     re-armed from the floor at EVERY UTC midnight
  → ladder tier T1        ×0.50    on a 43.3% rolling win rate
  = 2.5% of $14.83      = $0.37
```

At $0.37 the floor divide can only afford a contract priced **≤ 37c**. So the sizing floor
became an unintended *strategy filter*, and a self-locking one: escaping T1 needs wins, wins
need trades, trades need stake, stake needs wins. The probation ramp compounds it — it needs
2 consecutive wins per rung across 5 rungs to reach full size but resets to rung 1 every
midnight, and the bot averages ~2 trades/day. **`NORMAL_TRADE_PCT=20%` was mathematically
unreachable.**

### F2 — CRITICAL: the surviving 15% was adversely selected

Because `count = floor(stake / price)`, the only signals that survived were the cheapest.

* Signals ordered: mean **44.8c** — `[29, 30, 34, 36, 38, 40, 48, 60, 65, 68]`
* Signals killed: mean **57.1c**

And the cheap half is where the money went: entries **below 50c went 1W–4L**, entries above
50c went 2W–1L.

### F3 — CRITICAL: `win_prob` was not a probability, and "edge" was just "cheapness"

Across the 65 signals `bayesian_win_prob` returned mean **70.4%, sd 4.3pp** — a near-constant
that barely moved with price (corr = +0.37). `calc_edge` then compared that flat number against
the price, so:

```
corr(price, edge) = −0.88
```

"Edge" was not a measure of mispricing. It was a measure of how far below 70c the contract
traded. The model never saw the price at all.

On the 8 settled trades:

| | Model | Just believing the price | Realized |
|---|---|---|---|
| Mean P(win) | 72.5% | 46.0% | **37.5%** |
| Brier score | 0.342 | **0.217** | — |

**The market beat the model on the model's own trade selection.** P(≤3 wins in 8 | the model's
own 72.5%) = **4.1%**. Realized ROI on cash staked: **−18.5%**.

Two structural reasons it could not have worked:

1. `regime_adj` carries an unconditional `+0.02` and `depth_adj` a flat `+0.02` for any book
   over $500 — so **~4pp of every reported "edge" is a constant, not a measurement.** A 5–6%
   `MIN_EDGE_PCT` gate against that almost never bound (28 rejections in 8,711 cycles).
2. `MIN_EDGE_PCT` is denominated per *contract* (per $1 of payout), not per dollar staked. The
   same 5% threshold passed a 30c contract at p ≥ 0.36 but demanded p ≥ 0.71 at 65c. That
   asymmetry *is* a cheapness tilt, on top of F2's.

### F4 — HIGH: one signal counted four times

`compute_regime` (12 BTC samples) and `compute_momentum` (6 BTC samples) read the **same
deque over overlapping windows**. That single reading is then applied as:

1. a hard gate (`regime_agrees`), 2. a second hard gate (`momentum_gate_ok` requiring AGREE),
3. `regime_adj + momentum_adj` inside `win_prob`, and 4. `regime_pts (20–25) + momentum_pts (15)`
inside `confidence`.

The result is a confidence score that measures almost nothing but order-book imbalance
(corr(OB%, conf) = **+0.92**) and does not discriminate outcomes at all:

* mean confidence of winners: **79.0**
* mean confidence of losers: **77.4**
* the single highest-confidence trade of the window (95) was the **largest loss**

### F5 — HIGH: extreme order-book imbalance was scored as maximum conviction

`analyze_order_book` rejected only a *literally empty* opposite side (`ghost book`). A 99.8% /
0.2% book passed, and since confidence scores imbalance linearly it drew **Conf=95**, the
window's **largest stake ($2.14, 5 contracts)**, and lost all of it. On a thin 15-minute market
a 99% one-sided book means one stale level on the far side — a liquidity artifact, not
conviction. There was no upper bound.

### F6 — HIGH: there are no exits

Every position is held to settlement. No stop, no take-profit, no scratch, no re-quote. The
only thing resembling an exit is `cancel_stale_orders`, which cancels *unfilled resting orders*
at 300s — and it cancelled 2 of the 10 orders (07-23 20:16 YES@48c, 07-25 13:00 YES@38c). Both
markets were then locked out by `session_traded_tickers`, so a live signal was abandoned with
no re-quote and no record either way.

Holding a 15-minute binary to expiry is a defensible design choice and is **not** changed here —
but it should be a deliberate one, and the abandonment path was a bug (fixed, see below).

### F7 — MEDIUM: the 404 stale-cancel leak

`cancel_stale_orders` caught the exception and left the order in `open_orders`, so a **filled**
order 404s and is retried every cycle until the 1200s purge — 22 identical warnings in the
window. Worse, `open_orders` gates `MAX_CONCURRENT_POS` *and* the paper↔live flip, so a phantom
order blocks new entries and blocks a mode change.

### F8 — MEDIUM: the statistical circuit breaker was dead code

`performance_guard` read `live_wins/live_losses`, which `maybe_roll_session_day` zeroes at every
UTC midnight, and required `MIN_SAMPLE_TRADES=20` before evaluating. At ~2 trades/day the counter
never reached 3. **The Wilson floor was never evaluated once** — every settle line logged
`LB=0.0%`. The one statistical protection in the engine did nothing.

### F9 — LOW: log lines that cost trust

* `✅ ORDER │ 5 @ 40c │ $2.14` reported the *stake*, not the $2.00 actually committed.
* `📋 EDGE JUSTIFICATION` fired before sizing — 55 phantom "trades" in the log.
* `Portfolio │ Prior=0.635` is frozen: `_live_prior` needs 10 same-day settlements.
* Two win rates in the same log that disagree — the settle line's `WR=x/y` resets daily, the
  ladder's `WR% n=30` spans weeks.
* `LADDER │ lossStreak=4 │ tier T1-CONSERVATIVE clean` — "clean" during a 4-loss streak, because
  0.50 is already the floor and the demote is a no-op.

**Working correctly and left alone:** settlement PnL reconstruction (every settled $ reconciles
against the balance deltas exactly), the BTC staleness gate, the vol circuit, the per-bucket
learned prior (genuinely learning: 0.621–0.644 at n=27–29), day rollover, session-stop, all
persistence.

---

## 3. What changed (v10.1.0)

Everything below is env-gated. All of it is *subtractive* on entry quality except the sizing
round-up, which is the one change that lets the bot trade at all.

| # | Change | Default |
|---|---|---|
| F1 | `size_contracts()` — sizing resolved **before** the signal is announced; a signal that cannot be sized is rejected with an explicit reason instead of a phantom log line | — |
| F1 | `MIN_ORDER_ROUNDUP` — round up to 1 contract when the stake can't afford one, **only** if one contract fits inside `MAX_TRADE_PCT` *and* tradeable cash. Breaks the deadlock; never breaches the hard ceiling; honours the customer reserve | `true` |
| F3 | `MARKET_ANCHOR_ENABLED` / `MAX_MODEL_EDGE_PP` — `anchored_p = market_p + clamp(model_p − model_base, ±8pp)`. The quoted price becomes the base rate; the model may only move it by the incremental information its signals added | `true` / `0.08` |
| F3 | `MIN_EDGE_ROR` — expected value per **dollar staked** rather than per contract | `0.0` (off) |
| F5 | `OB_IMBALANCE_MAX` — reject one-sided books instead of scoring them max confidence | `0.95` |
| F8 | `PERF_GUARD_WINDOW` / `PERF_GUARD_PAUSE_SECS` — rolling window that survives day boundaries; trips → blocks 6h → clears its window and re-samples. Blocks, cools off, re-tests; never latches | `20` / `6h` |
| F7 | 404 on stale-cancel is terminal — stop retrying, keep the record for settlement matching | — |
| F6 | A cancel that **succeeds** means the order never filled → release the market from `session_traded_tickers` so it can be re-quoted | — |
| F9 | `✅ ORDER` logs committed cost; `EDGE JUSTIFICATION` carries `count @ price = $cost`, model vs anchored probability, edge in pp, and RoR | — |

### Why anchoring makes `MIN_EDGE_PCT` mean something

`calc_edge(price/100 + lift, price) == lift` **exactly, at every price**. So with the anchor on,
`MIN_EDGE_PCT` reads directly as *"percentage points of claimed advantage over the market"* — the
same bar at 30c and at 65c. That single identity removes the F3 asymmetry.

### Consequence to be aware of

`MIN_WIN_PROB` now applies to a real probability, which puts a hard price floor at roughly
`MIN_WIN_PROB − MAX_MODEL_EDGE_PP` ≈ **50c** at current config. That is intended — it is the
direct answer to F2 — but it is a genuine behaviour change and it is the knob to turn if you
want long shots back.

---

## 4. Replay against the 65 real signals

New gates applied to the actual logged features. **This is a filter check on n=8 settlements,
not a backtest** — it cannot tell you the strategy is profitable.

```
65 signals →  2 rejected (one-sided book)
             12 rejected (anchored p < 0.58)
              1 rejected (edge < 5pp)
             50 survive  → 36 distinct markets ≈ 11/day
```

Throughput goes **up** (10 orders → ~36 sized entries over the same window) while entry quality
goes up, because the binding constraint was never the entry gates — it was the sizing floor.

Of the 8 trades that actually settled:

| Market | Result | Price | New logic |
|---|---|---|---|
| 231515 | WIN +$0.70 | 31c | **blocked** (p=0.39) |
| 231600 | LOSS −$0.68 | 69c | taken |
| 231615 | WIN +$0.35 | 65c | taken |
| 231745 | WIN +$0.80 | 61c | taken |
| 231830 | LOSS −$2.00 | 41c | **blocked** (OB 99.8% one-sided) |
| 241745 | LOSS −$0.29 | 30c | **blocked** (p=0.38) |
| 251015 | LOSS −$0.38 | 36c | **blocked** (p=0.44) |
| 251215 | LOSS −$0.34 | 35c | **blocked** (p=0.40) |

3W–5L / **−$0.83** → 2W–1L / **+$0.47**. It correctly refuses the biggest loss and four of the
five losses, at the cost of one win. n=8 — treat as directional, not as evidence.

---

## 5. Still open — deliberately not changed

1. **F4 (double-counting) is not fixed.** The regime/momentum signal still enters the score four
   times. Fixing it means retuning `MIN_CONFIDENCE`, which needs data this window can't provide.
   Until then, treat `Conf` as an order-book-imbalance readout, not a conviction score.
2. **The model still barely discriminates.** In the replay the lift saturates the ±8pp cap on 47
   of 50 survivors, so the *cap* is doing the work, not the model. Anchoring makes the number
   honest; it does not create alpha. Constants first: kill the unconditional `regime_adj +0.02`
   and flat `depth_adj +0.02` so the lift reflects measurement.
3. **F6 (no exits) is a design gap, not a bug.** If you want exits on a 15-minute binary, that is
   a new feature and should be specified deliberately.
4. **Probation ramp vs ladder run on different clocks** (daily reset vs 30-trade window) and
   multiply. Consider `PROBATION_RUNGS` with fewer, wider rungs, or dropping the daily re-arm.
5. **`MAX_CONSEC_LOSSES=3` never fired** in 3 days because the bot rarely got 3 trades off.
   Re-check once throughput recovers.

## 6. Recommended rollout

1. Run **paper mode for 3–5 days** first. Throughput goes from ~2.5 to ~11 entries/day; that
   change deserves observation before it touches real money.
2. Watch `Anchor │ model=… lift=… → p=…` and `Sizing │ …` — those two lines now explain every
   decision the bot makes.
3. `PERF_GUARD_WINDOW=20` will now actually fill in ~2 days at the new rate. Expect it to
   evaluate for the first time ever.
4. Revert path: `MARKET_ANCHOR_ENABLED=false`, `MIN_ORDER_ROUNDUP=false`, `OB_IMBALANCE_MAX=1.0`
   restores pre-10.1.0 behaviour without a redeploy of code.
