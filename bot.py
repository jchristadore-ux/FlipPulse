"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  FLIPPULSE (FlipPulse core)  v10.3.1  —  Production Build                ║
║  "No disassemble."                                                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.3.1 — THE DAY'S HALT SURVIVES A RESTART.                                ║
║                                                                              ║
║  AUDIT (owner directive "validate the daily 3% halt is engaged"): the halt   ║
║  itself is correct in both modes — verified live on 2026-08-04, the day      ║
║  opened at $59.27, two wins banked $+1.97 ≥ the $1.78 goal and the bot       ║
║  latched at 13:01 UTC and took no further entry. But ALL of the day's state  ║
║  (`_session_halted`, `session_start_balance`, the realized accumulators)     ║
║  lived in process memory only. Boot re-based the opening balance to the      ║
║  CURRENT balance and zeroed today's realized P&L, so any restart after the   ║
║  target was banked — Railway redeploy, crash restart, or the paper↔live      ║
║  flip in _maybe_restart_for_mode_change() — silently cleared the halt and    ║
║  started a SECOND +3% hunt on the same UTC day (and re-armed the session-    ║
║  stop floor 3% higher). Same class as the v9.7.0 daily-loss latch bug.       ║
║                                                                              ║
║  FIX: the day's state is written to DAILY_STATE_PATH every cycle and at the  ║
║  instant each halt latches, and restored at boot when the record is for      ║
║  TODAY (UTC) and the SAME mode — a stale day or the other book's record is   ║
║  ignored, falling through to a normal fresh-day boot. The UTC rollover       ║
║  overwrites it, so nothing can resurrect a finished day.                     ║
║  RAILWAY: DAILY_STATE_PATH (/data/daily_state.json), DAILY_STATE_PERSIST.    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.3.0 — BALANCE INDEPENDENCE: the same rules at $20 and $20,000.          ║
║                                                                              ║
║  AUDIT (owner directive "validate that balance is irrelevant"): every entry  ║
║  gate already reads no balance, and the percentage rules (3% daily goal, 40% ║
║  session stop, the stake fraction) are exact at every size. Three dollar-    ║
║  denominated mechanics were not, so the risk actually taken differed by      ║
║  account size. Measured at a configured 10% stake: a $5 balance took 6.00%   ║
║  to 13.40% depending on contract price; $20 took 6.70%–9.75%; $20,000 took   ║
║  10.00% at every price. Fixes:                                               ║
║                                                                              ║
║  1. SUB-CONTRACT ROUND-UP OFF (MIN_ORDER_ROUNDUP now false). Rounding a      ║
║     stake UP to one contract was bounded by MAX_TRADE_PCT, not by the        ║
║     CONFIGURED fraction, and is only reachable on a small balance — the one  ║
║     path that could risk more than asked ($5 @ 67c took 13.40% on a 10%      ║
║     config). Sizing now always rounds DOWN, so the configured percentage is  ║
║     a true ceiling everywhere. Small accounts skip trades they cannot afford ║
║     at full size rather than over-risking them; the v10.1.0 deadlock this    ║
║     guarded against is gone at the source (the ladder + probation de-riskers ║
║     that collapsed the stake to $0.37 were both retired in v10.2.0).         ║
║                                                                              ║
║  2. THE $0.25 KELLY FLOOR IS GONE. `if bet < 0.25: return` was the last raw- ║
║     dollar rule in the entry path and blocked every account under ~$2.50     ║
║     outright. Redundant: size_contracts already rejects an unaffordable      ║
║     stake, against MAX_TRADE_PCT — a percentage.                             ║
║                                                                              ║
║  3. LIQUIDITY GATE IS NOW RELATIVE TO THE ORDER (MIN_DEPTH_STAKE_MULT, 3.0). ║
║     MIN_OB_DEPTH demanded the same $75 of book depth whether the order was   ║
║     $2 or $10,000 — cover of 133x for a $20 account and 0.0075x for a        ║
║     $100,000 one, so only large accounts carried partial-fill and slippage   ║
║     risk. The book must now absorb MIN_DEPTH_STAKE_MULT × the order about to ║
║     be placed. MIN_OB_DEPTH stays as the absolute "is this market worth      ║
║     trading at all" floor. Set the multiplier to 0 to disable.               ║
║                                                                              ║
║  What CANNOT be fixed: contracts are integral and priced in cents, so a $20  ║
║  account wanting $2.00 of a 67c contract gets $1.34 (6.7%, not 10%). The     ║
║  granularity error converges to zero by roughly $5,000 of balance. Rounding  ║
║  down means it is always an UNDER-risk, never an over-risk.                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.2.0 — DAILY 3% PROFIT TARGET + FLAT RISK (owner directive).             ║
║                                                                              ║
║  TWO CHANGES, both about keeping risk boring and banking the day:            ║
║                                                                              ║
║  1. DAILY PROFIT TARGET — the goal every day is +3% on the balance the day   ║
║     opened with. The moment today's REALIZED P&L reaches                     ║
║     DAILY_PROFIT_TARGET_PCT × session_start_balance (default 0.03), trading  ║
║     HALTS for the rest of the UTC day: no new entries, open positions are    ║
║     still resolved and reported, and the existing UTC rollover clears the    ║
║     halt automatically (same machinery as the session stop — no redeploy).   ║
║     Checked at settlement (so the winning trade that crosses the line halts  ║
║     immediately) and again as a pre-entry guard. Realized dollars only —     ║
║     an open position's cash outlay never counts toward the target.           ║
║     RAILWAY: DAILY_PROFIT_TARGET_PCT (0.03), DAILY_PROFIT_TARGET_ENABLED.    ║
║                                                                              ║
║  2. LADDERING DISABLED — the stake no longer steps UP for any reason. It is  ║
║     always the configured risk FRACTION of the current balance, so the       ║
║     dollar risk moves only when the balance does:                            ║
║       • The ladder overlay (ladder.py, 0.5×–2×) is unwired from sizing.      ║
║         LADDER_ENABLED / RECOVERY_LADDER_PAUSE_TRADES are no longer read;    ║
║         ladder.py stays in-tree as a retired, unreferenced module.           ║
║       • The probation ramp / daily slow-roll (the sub-full rung ladder) now  ║
║         defaults OFF — PROBATION_RAMP_ENABLED=true restores it.              ║
║       • Recovery defaults to "No Stake Change" (RECOVERY_NO_STAKE_CHANGE     ║
║         now true): it still tracks and reports the claw-back, but never      ║
║         drops the stake — so there is no snap-back increase on exit either.  ║
║     Net effect: one flat percentage of balance per trade, bounded by the     ║
║     hard MAX_TRADE_PCT ceiling, with every downside guard unchanged.         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.0.0 — PERCENTAGE SIZING: every stake is now a FRACTION OF THE CURRENT   ║
║  BALANCE, so one config scales to any starting balance and compounds.        ║
║                                                                              ║
║  WHY: each customer funds a different bankroll, so fixed-dollar stakes could  ║
║  never be shared. All sizing knobs are now percentages resolved to dollars   ║
║  at ONE chokepoint (active_trade_size = active fraction × balance):          ║
║    • NORMAL_TRADE_PCT   — full stake fraction (default 0.10 = 10%).          ║
║    • RECOVERY_TRADE_PCT — reduced fraction while clawing back (default 0.03).║
║    • MAX_TRADE_PCT      — hard ceiling on any one trade (default 0.15); the  ║
║                           ladder overlay can never push past it.             ║
║  The probation ramp climbs sub-full FRACTIONS (PROBATION_RUNG_STEP_PCT);     ║
║  recovery targets stay absolute balances and keep working. REMOVED: the      ║
║  owner-specific hardcoded TEMP stake override and the fixed-dollar high-stake ║
║  balance gate (percentages self-de-risk, so it is redundant). Trading Formats ║
║  (conservative/balanced/aggressive) seed these percentages; an explicit env  ║
║  var always wins. RAILWAY: NORMAL_TRADE_PCT, RECOVERY_TRADE_PCT, MAX_TRADE_PCT.║
║  Older dollar vars (NORMAL_TRADE_SIZE / TRADE_SIZE_DOLLARS / HIGH_STAKE_*)   ║
║  are no longer read.                                                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.8.0 — BALANCE-GATED $1000 CEILING: the slow-roll ramp can now climb to   ║
║  $750 and $1000, but only once the book can absorb it.                       ║
║                                                                              ║
║  The daily ramp ($100 → $250 → $500) now extends to $100 → $250 → $500 →     ║
║  $750 → $1000 (auto-built in $250 steps up to NORMAL_TRADE_SIZE; owner sets  ║
║  the $1000 top via TRADE_SIZE_DOLLARS=1000). The top rungs are balance-gated:║
║  stakes above HIGH_STAKE_GATE_SIZE ($500) require equity ≥ HIGH_STAKE_MIN_   ║
║  BALANCE ($5000). Enforced twice — a hard ceiling re-checked every trade at  ║
║  sizing time (so a balance that dips back under the line caps the next stake ║
║  to $500) AND at ramp-advance time (high rungs are earned one at a time after║
║  crossing $5000, never jumped into). Below $5000 the effective ceiling stays ║
║  $500, unchanged from v9.7.0. RAILWAY: TRADE_SIZE_DOLLARS=1000,              ║
║  HIGH_STAKE_MIN_BALANCE (5000), HIGH_STAKE_GATE_SIZE (500).                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.7.0 — DAILY SLOW-ROLL: re-arm the probation ramp at each new trading day.║
║                                                                              ║
║  The $100 → $250 → $500 ramp existed but only ever fired AFTER a recovery    ║
║  exit, so on an ordinary day the bot opened cold at full $500 (2026-06-30:   ║
║  first trade $499.80). Owner intent is for the FIRST trade of every day to   ║
║  start small and scale up. FIX: the UTC daily rollover now re-arms the ramp  ║
║  from the floor (skipped while RECOVERY is active, which is the deeper tier), ║
║  and a restart that crosses midnight re-arms on boot via a persisted arm-    ║
║  date. The advance gate is unchanged (2-win streak OR ≥60% win rate; step    ║
║  down on a loss). Disable with PROBATION_RAMP_ENABLED=false (every day stays ║
║  full size, as before).                                                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.6.0 — PROBATION RAMP: graduated re-entry after recovery (log-review fix).║
║                                                                              ║
║  2026-06-29 logs: the book grinds back up $100 at a time but loses $500 at a ║
║  time — one full-size loss wiped ~5 small wins and re-armed recovery. Two    ║
║  defects vs. intent ("stay small until the edge re-proves"):                 ║
║    1. Recovery EXIT snapped the base straight $100 → $500 on the next trade. ║
║       RECOVERY_LADDER_PAUSE_TRADES only held the ladder *multiplier* at 1×,  ║
║       never the base, so the stake was never kept small.                     ║
║    2. The ladder LEAKED through recovery: a $100 base × 2.0 tier placed a    ║
║       $200 trade while "in recovery."                                        ║
║                                                                              ║
║  FIX: on recovery exit the bot no longer jumps to full size — it climbs a    ║
║  ProbationState ramp of sub-full base sizes (default $100 → $250 → $500),    ║
║  advancing ONE rung on a short win streak OR a rolling win-rate threshold    ║
║  (whichever fires first) and stepping ONE rung down on any loss. Reaching    ║
║  full size graduates back to normal. Throughout recovery AND the ramp the    ║
║  laddering overlay is capped at the active base (it may size DOWN, never UP) ║
║  — closing the $200 leak. State persists to PROBATION_STATE_PATH and         ║
║  reconciles on boot. RAILWAY: PROBATION_RAMP_ENABLED (default true),         ║
║  PROBATION_WIN_STREAK (2), PROBATION_WIN_RATE_MIN (0.60), PROBATION_RUNGS    ║
║  (explicit override, e.g. "100,250"). Set PROBATION_RAMP_ENABLED=false to    ║
║  restore the old immediate snap-back to full size.                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.5.0 — RECOVERY MODE: two-tier position sizing (owner directive).         ║
║                                                                              ║
║  After a FULL-SIZE (normal-mode) trade settles a LOSS, the bot drops from    ║
║  NORMAL_TRADE_SIZE to RECOVERY_TRADE_SIZE and sets a recovery target = the    ║
║  realized balance recorded IMMEDIATELY BEFORE that losing trade. It keeps     ║
║  trading at the reduced size until the realized balance climbs back to the    ║
║  target, then auto-resumes full size. State {active, target} is persisted to  ║
║  RECOVERY_STATE_PATH (atomic JSON) and reconciled on boot, so an in-container ║
║  restart resumes mid-recovery and can never wedge.                           ║
║                                                                              ║
║  Sizing is derived from the mode via active_trade_size() — never read raw    ║
║  from a single env var at the sizing call. Entry is event-driven (a settled  ║
║  full-size loss → exact pre-trade target); exit is balance-driven and checked ║
║  every cycle AND on boot. A further loss while already recovering does NOT    ║
║  move the target. Entry filters / halts / streak logic unchanged.            ║
║                                                                              ║
║  RAILWAY: NORMAL_TRADE_SIZE (defaults to TRADE_SIZE_DOLLARS, so existing      ║
║  configs keep working), RECOVERY_TRADE_SIZE (default 100). For redeploy-      ║
║  durable recovery state, mount a Railway Volume and set RECOVERY_STATE_PATH   ║
║  to a path on it (e.g. /data/recovery_state.json).                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.4.1 — FLAT $500 STAKE (owner directive): $500 trades fire regardless of  ║
║  balance.                                                                    ║
║                                                                              ║
║  v9.4.0 lifted the caps but the bet was still Kelly-scaled                   ║
║  (full_kelly × KELLY_FRACTION × balance), so $500 was only reachable around  ║
║  a $4–5k balance. kelly_bet() now uses Kelly ONLY as an edge gate (positive  ║
║  full_kelly = positive expectancy) and stakes the full TRADE_SIZE_CAP on     ║
║  every qualifying trade — no balance/Kelly/MAX_BET_FRACTION down-scaling.    ║
║  The sole clamp is cash on hand (cannot stake more than the account holds),  ║
║  so below a $500 balance the bot goes all-in. MAX_BET_FRACTION is now dead   ║
║  config. Entry-quality gates are unchanged.                                  ║
║                                                                              ║
║  RAILWAY: TRADE_SIZE_DOLLARS=500 is the flat stake (still required).         ║
║  MAX_BET_FRACTION no longer affects sizing.                                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.4.0 — $500 STAKE + LOSS-STOP REMOVAL (owner directive, explicit          ║
║  authority to overwrite prior risk doctrine).                                ║
║                                                                              ║
║  INTENT: run $500 per trade and leave the consecutive-loss streak pause as   ║
║  the ONLY active auto-hold. The daily-loss governors and the balance floor   ║
║  no longer fit a $500-stake book and were removed; RECOVERY mode is gone so   ║
║  drawdown never shrinks the stake.                                          ║
║                                                                              ║
║  CODE CHANGES:                                                              ║
║  1. daily_loss_check(): the % and $ daily-loss caps are removed. The 40%     ║
║     SESSION_STOP_FRACTION halt is RETAINED as a catastrophic backstop.       ║
║  2. balance_floor_check() removed (function + run_decision call). No floor.  ║
║  3. RECOVERY removed: kelly_bet() no longer applies KELLY_RECOVERY_MULT and  ║
║     update_session_state() is a no-op, so the session stays ACTIVE.          ║
║  4. Entry-quality gates (AGREE/NEUTRAL, OB/R²/confidence/edge/Wilson) are    ║
║     UNCHANGED — they decide IF a trade exists, not its size.                 ║
║                                                                              ║
║  $500/trade is bankroll-gated, not a switch: bet = min(full_kelly ×          ║
║  KELLY_FRACTION × balance, TRADE_SIZE_CAP, MAX_BET_FRACTION × balance). With  ║
║  KELLY_FRACTION=0.30 the Kelly leg only reaches $500 around a $4–5k balance.  ║
║                                                                              ║
║  RAILWAY ENV VAR CHANGES REQUIRED (owner sets these in the Railway UI):      ║
║    - TRADE_SIZE_DOLLARS : 5    → 500                                         ║
║    - MAX_BET_FRACTION   : 0.04 → 1.0                                         ║
║    - MAX_CONSEC_LOSSES  : 2    → 3                                           ║
║    - LADDER_ENABLED     : confirm false (default)                           ║
║  MAX_DAILY_LOSS_DOLLARS / MAX_DAILY_LOSS_PCT / MIN_BALANCE_FLOOR /           ║
║  RECOVERY_TRIGGER_PCT are now dead config (no longer read by any guard).     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.3.3 — MOMENTUM R² ALIGNMENT: magnitude gate still mislabeled trends.     ║
║                                                                              ║
║  DIAGNOSIS (2026-06-24 LIVE, v9.3.2): still ZERO trades. 13 cycles reached   ║
║  the gate fully aligned (e.g. KXBTC15M-...1815 climbing 74→83¢, regime       ║
║  TRENDING_UP R²=0.74–0.92, OB YES 77–97%) yet momentum returned NEUTRAL on   ║
║  every one. Root cause is structural, not the window: compute_regime() flags ║
║  TRENDING by R² (trend CONSISTENCY), but compute_momentum() required raw     ║
║  %-MAGNITUDE ≥0.15%/3min. A smooth, gentle drift has high R² but a small     ║
║  %-move, so it passes regime and fails momentum. Widening 3→6 (v9.3.2) was   ║
║  not enough; 0.15%/3min is a large move for the calm trends in these books.  ║
║                                                                              ║
║  FIX: momentum now treats a trend as REAL when EITHER the regression R² over ║
║  its window ≥ MOMENTUM_R2_MIN (default 0.55) OR the magnitude clears         ║
║  MOMENTUM_THRESH_PCT — and takes DIRECTION from the regression slope, like   ║
║  compute_regime(). BTC is "flat"/NEUTRAL only when BOTH inconsistent (low    ║
║  R²) AND small (sub-threshold) — genuine chop the doctrine still rejects.    ║
║  Set MOMENTUM_R2_MIN=2.0 to restore pure-magnitude (v9.3.2) behavior.        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.3.2 — MOMENTUM WINDOW FIX: the AGREE gate was unsatisfiable, 0 trades.   ║
║                                                                              ║
║  DIAGNOSIS (2026-06-23 LIVE session, v9.3.1): ZERO trades fired all day.     ║
║  - compute_regime() flags TRENDING over TREND_LOOKBACK=12 samples (~6 min,   ║
║    R²≥0.65). compute_momentum() measured BTC over only prices[-1] vs [-4] —  ║
║    3 samples (~90s) — and required |move|≥0.15%. A clean ~6-min trend almost ║
║    never has a single 90s slice ≥0.15%, so momentum read NEUTRAL and the     ║
║    v9.3.0 AGREE gate rejected every setup.                                   ║
║  - Logs: 34 cycles had OB depth aligned with a real trend; momentum returned ║
║    NEUTRAL on ALL of them, AGREE/CONFLICT zero times. The gate was a wall.   ║
║                                                                              ║
║  FIX: momentum lookback is now MOMENTUM_LOOKBACK (default 6 ≈ 3 min), env-   ║
║  tunable. A genuine multi-minute trend now yields AGREE; flat BTC still      ║
║  reads NEUTRAL, so the doctrine intent ("never trade flat BTC") is intact —  ║
║  only the timescale momentum is measured over changed. Set MOMENTUM_LOOKBACK ║
║  =3 to restore the old window. MOMENTUM_THRESH_PCT (0.15%) unchanged.        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v9.3.1 — PHANTOM DAILY-LOSS FIX: open-position cash outlay halted on a WIN  ║
║                                                                              ║
║  DIAGNOSIS (2026-06-23 LIVE session, v9.3.0, single trade):                 ║
║  - 08:15:23 ORDER  NO -26JUN230430-30  169 @ 59c  $100.00  (cost $99.71).   ║
║    Fully doctrine-clean entry: TREND_DOWN R²=0.751, OB=74.2%, BTC=AGREE,    ║
║    Conf=68, WinP=78.9%. Exactly the kind of trade the doctrine permits.     ║
║  - 08:16:25 Portfolio  $1378.03  PnL=$-99.71  WR=0/0  — i.e. the open       ║
║    position's CASH OUTLAY (169 × $0.59 = $99.71) was reported as daily PnL  ║
║    while nothing had settled. Kalshi debits contract cost at fill, so       ║
║    (balance − session_start_balance) reads as a full-stake loss until the   ║
║    payout returns at settlement.                                           ║
║  - 08:30:30 DAILY LOSS  $99.71 ≥ cap $88.66 — halted.  (cap = 6% of equity, ║
║    which is CORRECT; the input was wrong.)                                  ║
║  - 08:30:31 SETTLED  WIN  +$69.29  WR=1/1.  The trade WON. The halt had     ║
║    latched one second earlier off the pre-settlement cash mark, then idled  ║
║    the bot until UTC rollover (~4.5h, 56 halt log lines).                   ║
║                                                                              ║
║  ROOT CAUSE — the LIVE daily-loss circuit breaker consumed an UNREALIZED    ║
║  cash-balance delta, not realized PnL. An open position is cash-out / zero- ║
║  marked, so any single in-flight trade ≥ the daily cap trips the breaker    ║
║  before it can settle. This is the mirror image of the v9.3.0 phantom-WIN   ║
║  fix in _extract_realized_dollars: same class of defect (unreconciled mark  ║
║  treated as realized), opposite sign.                                      ║
║                                                                              ║
║  FIX (accounting only — NO guardrail was loosened):                        ║
║    1. New accumulator live_daily_realized; resolve_open_orders() adds the   ║
║       reconciled _extract_realized_dollars() result of each MATCHED settled ║
║       trade to it. Open/unsettled positions contribute 0.                  ║
║    2. daily_loss_check() reads live_daily_realized in LIVE mode (was the    ║
║       balance−start cash delta). DEMO path (paper_daily_pnl) was already    ║
║       realized-only and unchanged.                                         ║
║    3. live_daily_realized resets with daily_pnl on UTC rollover and boot.   ║
║    4. Portfolio/heartbeat lines now report realized PnL as the PnL figure   ║
║       and show the cash delta separately as "cash=", so an open position    ║
║       can never again look like a daily loss in the logs.                  ║
║                                                                              ║
║  The 6% daily cap, $-dollar cap, SESSION_STOP_FRACTION, MAX_CONSEC_LOSSES,  ║
║  the AGREE/NEUTRAL gate, and OB/R²/confidence thresholds are UNCHANGED.     ║
║  No Railway env var changes are required for this fix.                     ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  v9.3.0 — DOCTRINE RESTORE: stop the NEUTRAL-momentum bleed                  ║
║                                                                              ║
║  DIAGNOSIS (2026-06-20→22 LIVE session, v9.2.0, ~2.7 days):                 ║
║  - 6 trades fired, ALL on BTC=NEUTRAL. Balance $1586.73 → ~$1396, WR 1/4+.  ║
║      06-20 08:00 NO @47c  TREND_DOWN  OB70.9% NEUTRAL  Edge"24.5%" $100      ║
║      06-20 08:30 NO @47c  TREND_DOWN  OB67.3% NEUTRAL  Edge"24.1%" $100 WIN  ║
║      06-21 08:02 YES@60c  TREND_UP    OB74.4% NEUTRAL  Edge"14.9%" $100 LOSS ║
║      06-21 08:31 NO @43c  TREND_DOWN  OB88.9% NEUTRAL  Edge"29.4%" $100      ║
║      06-21 09:00 YES@63c  TREND_UP    OB73.1% NEUTRAL  Edge"11.1%" $100 LOSS ║
║      06-22 08:32 NO @49c  TREND_DOWN  OB85.7% NEUTRAL  Edge"25.0%" $100 HALT ║
║                                                                              ║
║  ROOT CAUSE — three doctrine guards had drifted open (all from the v9.0.6   ║
║  "throughput" push, retained through v9.2.0). Together they manufacture a    ║
║  fake 25% edge on what is really a coin flip, then bet the full per-trade    ║
║  cap on it:                                                                  ║
║    1. run_decision() had NO NEUTRAL gate. Only CONFLICT was blocked; the     ║
║       v9.1.0 note "removed the RECOVERY AGREE gate" left ZERO momentum       ║
║       confirmation in ANY state. Trading on OB alone is doctrine "What This  ║
║       Bot Will Never Do" item 1 — the exact setup post-mortemed in v6.0.0    ║
║       (50% loss, 2026-03-27/28).                                            ║
║    2. NEUTRAL_ACCURACY_DRAG=0.0 → win_prob never discounted flat BTC, so a   ║
║       coin-flip market scored 0.72–0.75 (logs: mom=-0.000). "Edge" =         ║
║       win_prob − price was therefore fictional.                            ║
║    3. compute_confidence() gave NEUTRAL +8 pts. The 06-20 08:30 trade        ║
║       scored Conf=65 EXACTLY on mom=8.0; at the doctrine value of 2.0 it is  ║
║       59 < 65 and never trades.                                            ║
║                                                                              ║
║  FIX (restore, do not engineer around — zero-trade calm sessions are        ║
║  CORRECT per the doctrine):                                                 ║
║    1. momentum_gate_ok(): doctrine Layer 7. REQUIRE_AGREE_MOMENTUM (default  ║
║       true) rejects NEUTRAL and CONFLICT in EVERY session state. Applied in  ║
║       run_decision() right after the momentum verdict.                      ║
║    2. NEUTRAL_ACCURACY_DRAG default 0.0 → 0.02 (honest win_prob if the gate  ║
║       is ever disabled).                                                     ║
║    3. compute_confidence(): NEUTRAL 8.0 → 2.0 (doctrine Layer 8: momentum    ║
║       only scores when AGREE).                                              ║
║    4. Restore drifted thresholds to doctrine: OB_IMBALANCE_THRESH 0.64→0.70, ║
║       R2_TREND_THRESHOLD 0.62→0.65, MIN_CONFIDENCE 60→65,                    ║
║       YES_BREAKEVEN_PRICE 78→67.                                            ║
║                                                                              ║
║  The recovery deadlock that justified removing the AGREE gate is ALREADY     ║
║  solved independently by update_session_state()'s balance-heal exit and     ║
║  RECOVERY_MAX_SECS wall-clock backstop, so re-blocking NEUTRAL cannot        ║
║  relock recovery.                                                           ║
║                                                                              ║
║  RAILWAY ENV VAR CHANGES REQUIRED (an env override beats these defaults):    ║
║    - REQUIRE_AGREE_MOMENTUM : set true (or leave unset)                      ║
║    - NEUTRAL_ACCURACY_DRAG  : set 0.02 (or delete)                          ║
║    - OB_IMBALANCE_THRESH    : set 0.70 (or delete)                          ║
║    - R2_TREND_THRESHOLD     : set 0.65 (or delete)                          ║
║    - MIN_CONFIDENCE         : set 65   (or delete)                          ║
║    - YES_BREAKEVEN_PRICE    : set 67   (or delete)                          ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  v9.1.0 — RECOVERY DEADLOCK (real fix) + RISK TIGHTENING                     ║
║                                                                              ║
║  DIAGNOSIS (2026-06-18 LIVE session, v9.0.9, 3.5h slice, ZERO trades):      ║
║  - Status byte-identical all window:                                        ║
║      $1722.52 │ PnL=$-246.87 │ WR=1/4 │ RECOVERY (rec+1)                     ║
║  - Drawdown 12.5% (> 10% trigger). v9.0.9's balance-heal exit needs the     ║
║    drawdown to recover to ≤10%, but the drawdown cannot heal without        ║
║    trading, and the AGREE gate blocks every NEUTRAL-momentum scan. The      ║
║    v9.0.7/8/9 patches each fixed a symptom; the self-referential lock       ║
║    survived at any drawdown that did not pre-heal below the trigger.        ║
║                                                                              ║
║  FIX (deadlock):                                                            ║
║  1. RECOVERY no longer FORCES momentum==AGREE as a *recovery-only* extra     ║
║     gate (the doctrine Layer-7 AGREE requirement now applies uniformly to    ║
║     every state via momentum_gate_ok, so recovery is not special-cased).     ║
║  2. RECOVERY_MAX_SECS hard timeout in update_session_state() — force back    ║
║     to ACTIVE if recovery cannot clear in the window. The state machine      ║
║     can no longer lock permanently.                                        ║
║                                                                              ║
║  FIX (risk — a normal 1W/4L streak cost 12.5% of bankroll):                 ║
║  3. MAX_BET_FRACTION 0.08 → 0.04 (cap a single binary bet at 4% of bank).   ║
║  4. MAX_DAILY_LOSS_PCT (6%) — daily stop now halts on the tighter of the    ║
║     fixed dollar cap and a fraction of the session-start balance, so the    ║
║     mis-scaled $15 default can no longer be silently out-scaled.            ║
║                                                                              ║
║  ─────────────────────────────────────────────────────────────────────     ║
║  v9.0.8 — PERF-GUARD DEADLOCK FIX (boot-time settlement gate)               ║
║  Account-wide settlement history was counted toward live W/L with no time   ║
║  gate, seeding a sub-50% Wilson LB the bot could never escape. _is_post_boot ║
║  now gates the unmatched-settlement branch to records settled at/after boot. ║
║                                                                              ║
║  v9.0.7 — SETTLEMENT SCHEMA CORRECTED                                        ║
║  _extract_realized_dollars rewritten against the real KXBTC15M schema:       ║
║    pnl = (revenue/100) - yes_total_cost_dollars - no_total_cost_dollars      ║
║          - fee_cost                                                           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

BOT_VERSION = "10.3.1"

import base64
import json
import logging
import math
import os
import random
import re
import signal
import sys
import time
import uuid
from collections import deque
from datetime import datetime, timezone, timedelta
from enum import Enum
try:                                         # stdlib since 3.9; needs tzdata on slim images
    from zoneinfo import ZoneInfo
except Exception:                            # pragma: no cover - ancient runtime
    ZoneInfo = None                          # type: ignore
from typing import List, Optional, Set, Tuple

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

import telegram_utils as tg

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("flippulse.bot")


# ─────────────────────────────────────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class Regime(Enum):
    TRENDING_UP   = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING       = "RANGING"
    HIGH_VOL      = "HIGH_VOL"
    UNKNOWN       = "UNKNOWN"


class SessionState(Enum):
    ACTIVE    = "ACTIVE"
    RECOVERY  = "RECOVERY"
    HALTED    = "HALTED"


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

def _require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        raise EnvironmentError(f"Required env var missing: {key}")
    return val


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(key: str, default: bool) -> bool:
    raw = os.environ.get(key, "").lower().strip()
    if not raw:
        return default
    return raw in ("true", "1", "yes")


def _env_dollars(key: str, default: float) -> float:
    """Tolerant dollar-amount parse: accepts human formatting like '$1,000' or
    ' 1000.50 '. A malformed value falls back to the default with a WARNING —
    a bad paste must never crash-loop a customer deploy at boot."""
    raw = os.environ.get(key, "").strip()
    if not raw:
        return default
    try:
        return float(raw.replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        log.warning("%s=%r is not a number — using default %.2f", key, raw, default)
        return default


# ── Trading Format preset overlay ─────────────────────────────────────────────
# A "Trading Format" is a named bundle of the env values below (sizing posture,
# gate strictness, ladder/recovery toggles). apply_format() seeds the selected
# preset's values into the environment with setdefault BEFORE the config block
# reads them, so the whole posture switches with one knob (TRADING_FORMAT) while
# any explicit env var still wins. See formats.py. Must run before the first
# _require()/_env_* read. `--list-formats` is handled here so it works without
# Kalshi credentials (the _require() calls below would otherwise abort import).
from formats import apply_format, print_formats  # noqa: E402

if "--list-formats" in sys.argv:
    print_formats()
    raise SystemExit(0)
for _arg in sys.argv[1:]:
    if _arg.startswith("--format="):
        os.environ.setdefault("TRADING_FORMAT", _arg.split("=", 1)[1])


def _boot_trading_format() -> str:
    """The format to boot with: the customer's dashboard choice (persisted to the
    /data volume) when present, otherwise the TRADING_FORMAT env var provisioned at
    signup. The dashboard writes {"trading_format": "..."} to FORMAT_OVERRIDE_PATH;
    because a format bundles gate thresholds read once here at startup, a change
    only takes effect on the next boot. Best-effort — a missing/corrupt file just
    falls back to the env value."""
    path = os.environ.get("FORMAT_OVERRIDE_PATH", "").strip() or "/data/format_override.json"
    try:
        with open(path) as f:
            chosen = str(json.load(f).get("trading_format", "")).strip()
        if chosen:
            return chosen
    except (OSError, ValueError, TypeError):
        pass
    return os.environ.get("TRADING_FORMAT", "balanced")


TRADING_FORMAT = apply_format(_boot_trading_format())

KALSHI_API_KEY_ID   = _require("KALSHI_API_KEY_ID")


def _load_raw_pem() -> str:
    """The private key, from either input:
      • KALSHI_PRIVATE_KEY_PEM_B64 — the whole PEM base64-encoded into ONE line
        (recommended: a single line of A–Z/a–z/0–9/+// can't be mangled by the
        newline/space/quote problems that break a pasted multi-line PEM), or
      • KALSHI_PRIVATE_KEY_PEM — the raw multi-line PEM (still supported).
    The B64 form wins when both are set."""
    b64 = os.environ.get("KALSHI_PRIVATE_KEY_PEM_B64", "").strip().strip('"').strip("'")
    if b64:
        try:
            return base64.b64decode(re.sub(r"\s+", "", b64)).decode("utf-8")
        except Exception as e:
            raise ValueError(
                "KALSHI_PRIVATE_KEY_PEM_B64 is set but is not valid base64 of a key. "
                "Copy the whole single-line value from your onboarding /admin deploy view "
                f"(nothing cut off). Underlying error: {e}") from e
    return _require("KALSHI_PRIVATE_KEY_PEM")


_RAW_PEM            = _load_raw_pem()

# ── Paper ↔ live mode override (dashboard / Telegram) ─────────────────────────
# DEMO_MODE gates the whole trading path and is fixed for a process run, so a
# customer/operator flip between paper and live is applied by (1) writing the
# desired mode to MODE_OVERRIDE_PATH on the /data volume and (2) the running bot
# restarting cleanly into that mode the next time it is FLAT (no open position) —
# see _maybe_restart_for_mode_change() in the main loop. The override wins over the
# provisioned DEMO_MODE env var; deleting the file falls back to it. Going LIVE
# always requires an explicit confirmation on the dashboard / via `/live confirm`.
MODE_OVERRIDE_PATH  = os.environ.get("MODE_OVERRIDE_PATH", "").strip() or "/data/mode_override.json"


def _read_mode_override() -> "bool | None":
    """The customer/operator's desired DEMO_MODE from MODE_OVERRIDE_PATH, or None if
    no valid override is present. Best-effort — a missing/corrupt file means 'no
    override, use the env default'."""
    try:
        with open(MODE_OVERRIDE_PATH) as f:
            val = json.load(f).get("demo_mode")
    except (OSError, ValueError, TypeError):
        return None
    return bool(val) if isinstance(val, bool) else None


def _boot_demo_mode() -> bool:
    """The mode to boot in: the persisted override when set, else the DEMO_MODE env
    var provisioned at signup (defaults to paper)."""
    override = _read_mode_override()
    return override if override is not None else _env_bool("DEMO_MODE", True)


DEMO_MODE           = _boot_demo_mode()
POLL_INTERVAL       = _env_int("POLL_INTERVAL_SECS", 30)
# Operational polling intervals are read once at startup; defaults preserve the
# historical timing while allowing deployments to tune load/recovery behavior.
HEARTBEAT_INTERVAL_SECS = _env_int("HEARTBEAT_INTERVAL_SECS", 900)
HALT_POLL_INTERVAL_SECS = _env_int("HALT_POLL_INTERVAL_SECS", 300)
STALE_ORDER_PURGE_INTERVAL_SECS = _env_int("STALE_ORDER_PURGE_INTERVAL_SECS", 1200)
DEMO_SETTLE_INTERVAL_SECS = _env_int("DEMO_SETTLE_INTERVAL_SECS", 900)

# ── Capital & sizing (PERCENTAGE-BASED — v10.0.0) ─────────────────────────────
# Every stake is a FRACTION OF THE CURRENT BALANCE, resolved to dollars at the
# single sizing chokepoint active_trade_size(balance). Nothing here is a fixed
# dollar figure, so one config scales to ANY starting balance and compounds as
# the account grows (and auto-de-risks as it shrinks). The ACTIVE fraction is
# derived from the current mode, never read raw at the sizing call:
#   • NORMAL_TRADE_PCT   — the full stake fraction in normal operation.
#   • RECOVERY_TRADE_PCT — the reduced fraction while clawing back a full loss.
#   • MAX_TRADE_PCT      — a HARD ceiling on any single trade (the "max trade"
#                          knob); nothing may size past it.
# Values are fractions (0.10 = 10% of balance). A Trading Format seeds these
# (see formats.py); an explicit env var always wins.
# v10.2.0: nothing scales the resolved stake up any more — the laddering overlay
# is retired and the probation ramp is off by default, so the dollars at risk are
# simply the active fraction of the current balance on every single trade.
NORMAL_TRADE_PCT   = _env_float("NORMAL_TRADE_PCT", 0.10)
RECOVERY_TRADE_PCT = _env_float("RECOVERY_TRADE_PCT", 0.03)
MAX_TRADE_PCT      = _env_float("MAX_TRADE_PCT", 0.15)

# ── Customer risk-percentage override (Telegram /risk) ────────────────────────
# The customer can retune their full-size stake fraction at runtime by messaging
# their bot "/risk <percent>" (see command_bot.py). command_bot validates the
# request and drops the chosen fraction into RISK_OVERRIDE_PATH on the /data
# volume; the trading loop reads it back here at the sizing chokepoint. This keeps
# command_bot fully decoupled from the engine — it never imports bot.py, it just
# writes a file, the mirror image of the status snapshot the engine writes for it.
# The override is a clamped substitute for NORMAL_TRADE_PCT ONLY: RECOVERY sizing,
# the hard MAX_TRADE_PCT ceiling, and every downside guardrail still apply on top
# of it unchanged. Deleting the file (or /risk reset) falls back to NORMAL_TRADE_PCT.
RISK_OVERRIDE_PATH = os.environ.get("RISK_OVERRIDE_PATH", "").strip() or "/data/risk_override.json"
# A customer-typed value is clamped into [RISK_MIN_TRADE_PCT, MAX_TRADE_PCT] before
# it can ever reach sizing, so a fat-finger "/risk 90" can neither exceed the sane
# ceiling nor drop the stake to a dust amount that never fills.
RISK_MIN_TRADE_PCT = _env_float("RISK_MIN_TRADE_PCT", 0.01)

# ── Customer reserve / "set aside" (dashboard) ────────────────────────────────
# The customer can ring-fence a dollar amount of their balance from trading via
# the web dashboard (dashboard.py), which drops it into RESERVE_OVERRIDE_PATH on
# the /data volume. The engine subtracts it from the balance used for sizing at
# the single dollar-resolution point (active_trade_size), so the reserve is never
# staked — the bot trades only the balance ABOVE it and de-risks toward zero size
# as the tradeable remainder shrinks. Withdrawals still happen on Kalshi; this
# only tells the bot how much to leave untouched. Decoupled by file, like /risk.
RESERVE_OVERRIDE_PATH = os.environ.get("RESERVE_OVERRIDE_PATH", "").strip() or "/data/reserve_override.json"
# The customer's chosen Trading Format from the dashboard, persisted here so it
# survives redeploys and is applied at the NEXT boot (a format bundles gate
# thresholds read once at startup, so it takes effect on restart — see boot below).
FORMAT_OVERRIDE_PATH  = os.environ.get("FORMAT_OVERRIDE_PATH", "").strip() or "/data/format_override.json"
# NOTE: the fixed-dollar-era knobs MAX_BET_FRACTION, KELLY_FRACTION and
# KELLY_RECOVERY_MULT were removed in the v10 cleanup — sizing is purely the
# percentage knobs above (kelly math is used only as a positive-expectancy
# gate in kelly_bet, never as a stake scaler).

# ── Recovery Mode persistence ─────────────────────────────────────────────────
# Where the recovery state (active flag + target balance) is written so it
# survives an in-container process restart. NOTE: Railway's container filesystem
# is ephemeral across REDEPLOYS — mount a Railway Volume and point
# RECOVERY_STATE_PATH at it (e.g. /data/recovery_state.json) for the state to
# survive a redeploy. Without a Volume, a redeploy resets to NORMAL sizing
# (boot reconciliation makes this a safe, non-stuck default).
RECOVERY_STATE_PATH = os.environ.get("RECOVERY_STATE_PATH", "recovery_state.json")
RECOVERY_PERSIST    = _env_bool("RECOVERY_PERSIST", True)

# ── Recovery Mode: "No Stake Change" (owner directive) ────────────────────────
# WHY (owner, log-review feel): the standard recovery tier DROPS the stake to
# RECOVERY_TRADE_PCT while clawing back, grinds the balance up over a win streak,
# then on exit SNAPS back to the full stake (via the probation ramp) — and a
# single full-size loss right after wipes the whole grind. Deflating.
#
# When RECOVERY_NO_STAKE_CHANGE is ON, recovery still TRIGGERS and TRACKS exactly
# as before (it arms on a full-size loss, records the target balance, shows in
# /status and the reports, and clears when the balance heals) — but it does NOT
# touch sizing: the stake stays at the full NORMAL_TRADE_PCT (or the /risk
# override). Because nothing ever dropped, exiting recovery is a no-op on sizing
# — no probation ramp, no jump-back, so there is no grind to wipe out.
#
# v10.2.0: this is now the DEFAULT. The owner directive is that the dollar risk
# should track the configured percentage of balance and nothing else, so the
# stake must not step DOWN into a recovery tier and then step back UP on exit.
# Recovery still arms, tracks and reports the claw-back exactly as before — it
# just never moves the stake. Set RECOVERY_NO_STAKE_CHANGE=false to restore the
# two-tier behaviour (reduced stake while clawing back).
#
# Toggleable at runtime (Telegram /recoverynostakechange, dashboard) without a
# redeploy: the command writes {"enabled": bool} to RECOVERY_NSC_OVERRIDE_PATH and
# the engine reads it back here, exactly like the /risk override. The env var is
# the boot default; a present override file always wins. Deleting the file (or
# toggling back) falls to the env default.
RECOVERY_NO_STAKE_CHANGE     = _env_bool("RECOVERY_NO_STAKE_CHANGE", True)
RECOVERY_NSC_OVERRIDE_PATH   = os.environ.get("RECOVERY_NSC_OVERRIDE_PATH", "").strip() \
    or "/data/recovery_nsc_override.json"

# ── Recovery Mode: win-rate restore (owner directive) ─────────────────────────
# WHY (owner): if the stake is being held BELOW the full base (the standard
# recovery tier reduced it) but the claw-back is actually going well (a strong
# rolling win rate), don't keep grinding at the small stake. The moment the
# recovery-scoped win rate reaches RECOVERY_WINRATE_RESTORE_PCT (default 70%, over
# at least RECOVERY_WINRATE_MIN_TRADES settled recovery trades), snap straight back
# to the full/original stake — bypassing the slow probation ramp entirely. This is
# checked every cycle, right beside the balance-target exit. Set the % to 1.0
# (100%) or disable to turn the fast path off.
#
# v10.2.0 note: with RECOVERY_NO_STAKE_CHANGE on (the default) the stake is never
# held below base in the first place, so this path simply never fires. It stays
# wired for deployments that turn the two-tier recovery sizing back on.
RECOVERY_WINRATE_RESTORE_ENABLED = _env_bool("RECOVERY_WINRATE_RESTORE_ENABLED", True)
RECOVERY_WINRATE_RESTORE_PCT     = _env_float("RECOVERY_WINRATE_RESTORE_PCT", 0.70)
RECOVERY_WINRATE_MIN_TRADES      = _env_int("RECOVERY_WINRATE_MIN_TRADES", 5)


# ── Laddering stake overlay — RETIRED in v10.2.0 ──────────────────────────────
# The ladder scaled the stake by a rolling-win-rate multiplier (0.5×–2×). Owner
# directive: the dollar risk must stay in line with the configured PERCENTAGE of
# balance, so nothing may multiply the stake up. The overlay is unwired from
# sizing entirely — LADDER_ENABLED and RECOVERY_LADDER_PAUSE_TRADES are no longer
# read anywhere in the engine, and setting them has no effect. ladder.py is left
# in-tree (with its own unit tests) as a retired module, imported by nothing.

# ── DAILY PROFIT TARGET — the day's goal, then stop (owner directive) ─────────
# The goal every day is +3% on the balance the day OPENED with. The moment
# today's REALIZED P&L reaches DAILY_PROFIT_TARGET_PCT × session_start_balance,
# trading HALTS for the rest of the UTC day.
#
# Design notes:
#   • REALIZED dollars only (paper_daily_pnl / live_daily_realized — the same
#     accumulators the alerts and /pnl report). An open position's cash outlay
#     dips the raw balance and must never be read as progress toward the target;
#     this is the same trap v9.3.1 fixed for the daily-loss breaker.
#   • The baseline is session_start_balance, set at boot and re-based at every
#     UTC rollover — so the target is 3% of what the day started with, not a
#     moving 3% of a balance that is itself growing.
#   • The halt reuses the existing `_session_halted` machinery, so the UTC
#     rollover clears it automatically (no redeploy) and the main loop keeps
#     resolving open positions and sending the scheduled briefing while paused.
#   • Checked at SETTLEMENT (so the winning trade that crosses the line stops the
#     day immediately) and again as a pre-entry guard in run_decision.
# Set DAILY_PROFIT_TARGET_ENABLED=false (or the pct to 0) to trade the full day.
DAILY_PROFIT_TARGET_ENABLED = _env_bool("DAILY_PROFIT_TARGET_ENABLED", True)
DAILY_PROFIT_TARGET_PCT     = _env_float("DAILY_PROFIT_TARGET_PCT", 0.03)

# ── The day's state SURVIVES a restart (v10.3.1) ──────────────────────────────
# The halt, the day's opening balance and today's realized P&L all lived in
# process memory only. Boot re-based session_start_balance to the CURRENT
# balance and zeroed the realized accumulators, so any restart after the target
# was banked — a Railway redeploy, an OOM/crash restart, a paper↔live flip —
# silently cleared the halt and started a SECOND +3% hunt on the same UTC day
# (and re-armed the session-stop floor 3% higher). Exactly the class of bug
# v9.7.0 fixed for the daily-loss cap, still open on the profit target.
#
# The day's state is now written to DAILY_STATE_PATH on every cycle and at the
# moment of each halt latch, and restored at boot when — and only when — the
# record is for TODAY (UTC) and the SAME trading mode. A record from another
# day is stale, and a record from the other mode belongs to a different book
# (the paper day's P&L must never halt the live account, or vice-versa); both
# fall through to a normal fresh-day boot.
DAILY_STATE_PATH    = os.environ.get("DAILY_STATE_PATH", "").strip() or "/data/daily_state.json"
DAILY_STATE_PERSIST = _env_bool("DAILY_STATE_PERSIST", True)

# ── Post-recovery graduated re-entry ("probation ramp") — OFF by default ──────
# WHY (2026-06-29 log review): the book grinds back up a small step at a time but
# loses a full stake at a time. After recovery cleared, the OLD behavior snapped
# the base straight from RECOVERY_TRADE_PCT back to the full NORMAL_TRADE_PCT on
# the very next trade; a single full-size loss then wiped several small wins and
# re-armed recovery.
#
# The ramp re-enters at the recovery fraction and climbs a ladder of sub-full base
# FRACTIONS, advancing exactly one rung when the edge re-proves itself (a short win
# streak OR a rolling win-rate threshold — whichever fires first) and stepping one
# rung DOWN on any loss. Reaching the full fraction graduates back to normal mode.
#
# v10.2.0 — DISABLED BY DEFAULT. This is itself a laddering approach: it steps the
# risk fraction up rung by rung (and the v9.7.0 "daily slow-roll" re-armed it from
# the floor at every UTC midnight, which is what silently collapsed the stake to
# $0.37 in the 2026-07 audit). The owner directive is one flat percentage of
# balance per trade, so the ramp no longer runs. PROBATION_RAMP_ENABLED=true
# restores the graduated re-entry (and, with it, the daily slow-roll).
PROBATION_RAMP_ENABLED       = _env_bool("PROBATION_RAMP_ENABLED", False)
# Advance one rung after this many consecutive wins at the current base size.
PROBATION_WIN_STREAK         = _env_int("PROBATION_WIN_STREAK", 2)
# ...OR advance when the rolling win rate over the probation clears this, once at
# least PROBATION_WINRATE_MIN_TRADES have settled in the ramp. "Either" wins.
PROBATION_WIN_RATE_MIN       = _env_float("PROBATION_WIN_RATE_MIN", 0.60)
PROBATION_WINRATE_MIN_TRADES = _env_int("PROBATION_WINRATE_MIN_TRADES", 4)
# Explicit override for the ramp's sub-full base FRACTIONS, comma-separated
# (e.g. "0.03,0.06"). Empty → auto-build from RECOVERY_TRADE_PCT toward
# NORMAL_TRADE_PCT. Values are clamped to the [RECOVERY_TRADE_PCT,
# NORMAL_TRADE_PCT) half-open range; NORMAL_TRADE_PCT is the graduation target,
# never a rung.
PROBATION_RUNGS_RAW          = os.environ.get("PROBATION_RUNGS", "").strip()
PROBATION_STATE_PATH         = os.environ.get("PROBATION_STATE_PATH", "probation_state.json")
PROBATION_PERSIST            = _env_bool("PROBATION_PERSIST", True)
# Auto-built rungs step up in fixed PERCENTAGE-POINT increments from
# RECOVERY_TRADE_PCT to (exclusive) NORMAL_TRADE_PCT. With NORMAL=10%,
# RECOVERY=3%, STEP=0.035 this yields 3% → 6.5% (graduating to 10%).
PROBATION_RUNG_STEP_PCT      = _env_float("PROBATION_RUNG_STEP_PCT", 0.035)

# ── Lifetime (all-time) performance — PERSISTENT across redeploys ─────────────
# The session W/L (live_wins/live_losses) and the in-memory trade_history reset
# every restart, so the "all-time" win rate the customer sees kept resetting on a
# redeploy. LifetimeStats keeps an UNBOUNDED, persisted running tally of settled
# wins/losses and realized PnL, split by paper vs live so practice never dilutes
# the live record. It backs the "all-time" figures in the 9am/9pm report, the
# /winrate and /pnl commands, and the /status record line. Mount the /data volume
# and keep LIFETIME_STATS_PATH on it (default) so it survives redeploys.
LIFETIME_STATS_PATH = os.environ.get("LIFETIME_STATS_PATH", "").strip() or "/data/lifetime_stats.json"
LIFETIME_PERSIST    = _env_bool("LIFETIME_PERSIST", True)

# ── Dashboard / observability ─────────────────────────────────────────────────
# The bot writes a small JSON status snapshot here once per main-loop cycle
# (balance, PnL, W/L, active sizing mode, open positions, last signal); the
# /status Telegram command (command_bot.py) reads it.
# Default matches command_bot.py and the provisioned /data volume, so /status
# works even on a manual deploy that forgets the env var. On a local run with
# no /data the per-cycle write fails silently (caught in the writer) — harmless.
STATUS_SNAPSHOT_PATH = os.environ.get("STATUS_SNAPSHOT_PATH", "").strip() or "/data/status_snapshot.json"

# ── Scheduled Telegram report (twice-daily P&L + win rate) ─────────────────────
# The historical owner directive was "no periodic Telegram messages." This is the
# one deliberate exception: a concise briefing at fixed local times (default 9am
# and 9pm US Eastern) carrying balance, today's P&L, today's win rate, and the
# all-time (this-run) figures. Everything else stays event-driven. Fires from the
# main loop's wall-clock check (like the session-day / month rollovers), so no
# extra thread. The slot that last fired is persisted to REPORT_STATE_PATH so a
# redeploy near a scheduled time can't double-send, and a slot missed while the
# bot was down for longer than REPORT_MAX_LATE_SECS is skipped rather than sent
# stale. Turn the whole feature off with REPORT_SCHEDULE_ENABLED=false.
REPORT_SCHEDULE_ENABLED = _env_bool("REPORT_SCHEDULE_ENABLED", True)
# IANA timezone the report hours are interpreted in. Needs the tzdata package
# (in requirements.txt) on slim images; falls back to UTC if it can't be loaded.
REPORT_TIMEZONE   = os.environ.get("REPORT_TIMEZONE", "").strip() or "America/New_York"
# Comma-separated hours (0–23, in REPORT_TIMEZONE) to fire at. Default 9am & 9pm.
REPORT_HOURS_RAW  = os.environ.get("REPORT_HOURS", "").strip() or "9,21"
REPORT_STATE_PATH = os.environ.get("REPORT_STATE_PATH", "").strip() or "/data/report_state.json"
REPORT_PERSIST    = _env_bool("REPORT_PERSIST", True)
# A scheduled slot is only sent if the bot reaches it within this many seconds of
# the scheduled time; a slot the bot slept/was-down through for longer is skipped
# (marked consumed) so a stale briefing never lands hours late. Default 2h.
REPORT_MAX_LATE_SECS = _env_int("REPORT_MAX_LATE_SECS", 7200)

# ── Performance-fee billing (high-water mark) — PLACEHOLDER, DISABLED ──────────
# TEMPORARILY REMOVED: the performance fee is not currently charged, so this
# defaults to 0.0 (a placeholder) and the monthly billing report stays dormant
# (maybe_month_rollover no-ops while PERF_FEE_PCT <= 0). The whole engine below is
# left intact so the fee can be switched back on in ONE place later — set
# PERF_FEE_PCT (env) to e.g. 0.20. When >0 it reports (never charges) the fee on
# each customer's NEW monthly profit above their all-time high-water mark.
PERF_FEE_PCT       = _env_float("PERF_FEE_PCT", 0.0)   # placeholder — fee not charged
BILLING_STATE_PATH = os.environ.get("BILLING_STATE_PATH", "billing_state.json").strip()
BILLING_LOG_PATH   = os.environ.get("BILLING_LOG_PATH", "").strip()
BILLING_PERSIST    = _env_bool("BILLING_PERSIST", True)


def _probation_rungs() -> "list[float]":
    """Ascending list of sub-full base FRACTIONS the ramp climbs through. Each is
    in [RECOVERY_TRADE_PCT, NORMAL_TRADE_PCT); the full fraction is the graduation
    target, not a rung. Returns [] when there is no room to ramp (caller stays
    normal)."""
    lo, hi = RECOVERY_TRADE_PCT, effective_normal_trade_pct()
    if hi <= lo:
        return []
    if PROBATION_RUNGS_RAW:
        try:
            vals = sorted({round(float(x), 4) for x in PROBATION_RUNGS_RAW.split(",") if x.strip()})
        except ValueError:
            vals = []
        rungs = [v for v in vals if lo <= v < hi]
        if not rungs or rungs[0] > lo:
            rungs = [lo] + [r for r in rungs if r > lo]
        return rungs
    # Fixed-step ladder: floor, then every PROBATION_RUNG_STEP_PCT up to
    # (exclusive) the full fraction. NORMAL=10%, RECOVERY=3%, STEP=3.5pt → [3%, 6.5%].
    rungs = [lo]
    step  = PROBATION_RUNG_STEP_PCT if PROBATION_RUNG_STEP_PCT > 0 else hi
    v     = lo + step
    while v < hi:
        if v > lo:
            rungs.append(round(v, 4))
        v += step
    return rungs

# ── Risk controls ─────────────────────────────────────────────────────────────
# The v9.4.0 owner directive removed the daily-loss caps and balance floor
# (MIN_BALANCE_FLOOR / MAX_DAILY_LOSS_DOLLARS / MAX_DAILY_LOSS_PCT were dead
# config since then and are deleted). The active auto-holds are the
# consecutive-loss streak pause and the SESSION_STOP_FRACTION catastrophic
# backstop below. On the UPSIDE, the daily profit target halts the day once
# +DAILY_PROFIT_TARGET_PCT is banked (see daily_profit_target_check).
SESSION_STOP_FRACTION = _env_float("SESSION_STOP_FRACTION", 0.40)
MAX_CONSEC_LOSSES     = _env_int("MAX_CONSEC_LOSSES", 2)
STREAK_PAUSE_SECS     = _env_int("STREAK_PAUSE_SECS", 1800)
STALE_ORDER_TIMEOUT   = _env_int("STALE_ORDER_TIMEOUT", 300)
MAX_CONCURRENT_POS    = _env_int("MAX_CONCURRENT_POS", 1)
MIN_SAMPLE_TRADES     = _env_int("MIN_SAMPLE_TRADES", 20)

# ── v10.1.0 SIZING FLOOR — the silent 85% signal kill ────────────────────────
# WHY (2026-07-23→26 log audit): place_order sized with
# `count = int(bet_dollars * 100 / limit_cents)` and, when that floored to zero,
# logged one INFO line and returned None. Over the audited window that path
# swallowed 55 of 65 signals (84.6%) — 25 of 26 on 07-24, 22 of 25 on 07-25, and
# ALL 8 on 07-26 — while the "📋 EDGE JUSTIFICATION" line (and its Telegram
# twin) had already fired. The logs read like a bot that was hunting; it had in
# fact been unable to buy a single contract for three straight days.
#
# The stake had collapsed to $0.37 through a chain of independent de-riskers
# multiplying together: NORMAL_TRADE_PCT 20% → probation rung 1 (5%, re-armed
# from the floor at EVERY UTC midnight) → ladder tier T1 (×0.50 on a 43% rolling
# win rate) = 2.5% of a $14.83 balance. At $0.37 the floor divide can only ever
# afford a contract priced ≤ 37c, so the size floor silently became a STRATEGY
# FILTER that bought nothing but long shots — and it was self-locking: escaping
# it needs wins, wins need trades, trades need stake, stake needs wins.
#
# Two fixes, both here:
#  1. MIN_ORDER_ROUNDUP — when the stake cannot afford one contract but ONE
#     contract still fits inside the hard MAX_TRADE_PCT ceiling and the cash on
#     hand, take the single contract. Rounding UP to the tradeable minimum is
#     what breaks the deadlock; the hard ceiling is never breached, so this can
#     never size past what the risk config already permits.
#  2. When even that does not fit, the signal is rejected BEFORE the edge
#     justification is logged, with an explicit "under-capitalised" reason (see
#     size_contracts / run_decision) — so the log never again claims a trade the
#     bot could not place.
#
# v10.3.0 — ROUND-UP IS NOW OFF BY DEFAULT (balance-independence audit).
# The round-up is bounded by MAX_TRADE_PCT, not by the CONFIGURED stake, so it
# was the one path that could risk MORE than the customer asked for — and it is
# only ever reachable on a small balance. Measured: a $5 balance at a configured
# 10% took 13.40% on a 67c contract, while a $20,000 balance took exactly 10.00%
# at every price. Owner directive: the configured percentage is a ceiling at
# EVERY account size, so a stake that cannot buy a whole contract now skips the
# trade instead of rounding up.
#
# The v10.1.0 deadlock it was introduced for is addressed at the source instead:
# the de-riskers that multiplied the stake down to $0.37 (the probation ramp and
# the ladder overlay) are both gone as of v10.2.0, so the stake is a flat
# percentage of balance and no longer collapses. Fix #2 above still stands — an
# unaffordable signal is rejected BEFORE it is announced, with a real reason, so
# the log never claims a trade the bot could not place.
#
# Set MIN_ORDER_ROUNDUP=true to restore the old behaviour (small accounts trade
# more often, at up to MAX_TRADE_PCT rather than the configured fraction).
MIN_ORDER_ROUNDUP     = _env_bool("MIN_ORDER_ROUNDUP", False)

# ── Liquidity gate: the book must cover the ORDER, not a fixed dollar floor ───
# WHY (balance-independence audit): MIN_OB_DEPTH demands the same $75 of book
# depth whether the bot is about to buy $2 or $10,000. Measured against the
# default 10% stake, the order placed was 1.3x that required depth at a $1,000
# balance, 26.7x at $20,000 and 133x at $100,000 — so a large account routinely
# fired orders far bigger than the liquidity the gate had proved existed, taking
# partial-fill and slippage risk a small account never sees. Percentage sizing
# self-de-risks the BANKROLL, but says nothing about MARKET IMPACT (this is what
# v9.8.0's fixed-dollar HIGH_STAKE_GATE_SIZE was reaching for before v10.0.0
# removed it as redundant — it was redundant for bankroll risk, not for this).
#
# The fix expresses the gate RELATIVE TO THE ORDER: the visible book depth must
# be at least MIN_DEPTH_STAKE_MULT x the dollar cost of the order about to be
# placed. Identical rule at every balance — a $20 account and a $20,000 account
# must both find a book that can absorb their trade several times over.
# MIN_OB_DEPTH stays as the absolute floor for a market being worth trading at
# all. Set to 0 to disable the relative gate.
MIN_DEPTH_STAKE_MULT  = _env_float("MIN_DEPTH_STAKE_MULT", 3.0)

# ── v10.1.0 PERFORMANCE GUARD window ─────────────────────────────────────────
# WHY (same audit): performance_guard read live_wins/live_losses, which
# maybe_roll_session_day zeroes at every UTC midnight, and demanded
# MIN_SAMPLE_TRADES (20) settled trades before it would evaluate. The bot
# averages ~2 trades/day, so the counter never reached 3 — the Wilson floor was
# never once evaluated in the audited window ("LB=0.0%" on every settle line),
# and the bot's only statistical circuit breaker was dead code.
#
# The daily reset existed to stop the guard latching forever (blocked trading
# yields no new samples, so a sub-50% bound could never heal). A rolling window
# alone has that same deadlock, so the guard is now a TIME-BOUNDED breaker: it
# scores the last PERF_GUARD_WINDOW settled trades regardless of day boundaries,
# and when it trips it blocks for PERF_GUARD_PAUSE_SECS and then clears its own
# window so the bot re-samples. Blocks, cools off, re-tests — never latches.
PERF_GUARD_WINDOW     = _env_int("PERF_GUARD_WINDOW", 20)
PERF_GUARD_PAUSE_SECS = _env_int("PERF_GUARD_PAUSE_SECS", 21600)   # 6h

# ── Regime detection ──────────────────────────────────────────────────────────
# v9.3.0: restored 0.62 → 0.65 (doctrine §8). 0.62 was a v9.0.6 throughput
# relaxation; at 0.65 about 65% of price variance must be explained by the
# straight-line fit before the market counts as TRENDING.
R2_TREND_THRESHOLD    = _env_float("R2_TREND_THRESHOLD", 0.65)
VOLATILITY_CAP_PCT    = _env_float("VOLATILITY_CAP_PCT", 0.18)
VOL_CIRCUIT_BREAKER   = _env_float("VOL_CIRCUIT_BREAKER", 0.40)
TREND_LOOKBACK        = _env_int("TREND_LOOKBACK", 12)
MIN_PRICES_FOR_REGIME = _env_int("MIN_PRICES_FOR_REGIME", 10)

# ── Signal thresholds ─────────────────────────────────────────────────────────
# v9.3.0: OB_IMBALANCE_THRESH restored 0.64 → 0.70 (doctrine Layer 6).
# MIN_CONFIDENCE restored 60 → 65 (doctrine Layer 8). YES_BREAKEVEN_PRICE
# restored 78 → 67 (doctrine §3 — never pay past mathematical breakeven).
MIN_OB_DEPTH          = _env_float("MIN_OB_DEPTH_DOLLARS", 75.0)
OB_IMBALANCE_THRESH   = _env_float("OB_IMBALANCE_THRESH", 0.70)
MOMENTUM_THRESH_PCT   = _env_float("MOMENTUM_THRESH_PCT", 0.15)
# v9.3.2: momentum lookback (intervals back). The old fixed 3-sample (~90s)
# window measured a far shorter horizon than the regime's TREND_LOOKBACK (~6 min)
# trend it was meant to confirm, so genuine trends read NEUTRAL and the AGREE
# gate blocked EVERY trade (2026-06-23: 0 trades all day). ~6 intervals (~3 min
# at the 30s poll) confirms real trends without firing on 90s chop. Set to 3 to
# restore the pre-9.3.2 window.
MOMENTUM_LOOKBACK     = _env_int("MOMENTUM_LOOKBACK", 6)
# v9.3.3: a trend is "real" for momentum when EITHER the linear regression over
# the momentum window is consistent (local R² ≥ this) OR the magnitude clears
# MOMENTUM_THRESH_PCT. This aligns momentum's trend test with compute_regime's
# R²-based one: a smooth, gentle BTC drift has high R² but a small %-move, so the
# pure-magnitude gate kept mislabeling it NEUTRAL and blocked EVERY trade even
# after v9.3.2 (2026-06-23/24: 0 trades). Set to 2.0 to disable the R² path and
# restore pure-magnitude (pre-9.3.3) behavior.
MOMENTUM_R2_MIN       = _env_float("MOMENTUM_R2_MIN", 0.55)
MIN_EDGE_PCT          = _env_float("MIN_EDGE_PCT", 0.06)
MIN_CONFIDENCE        = _env_int("MIN_CONFIDENCE", 65)
MIN_WIN_PROB          = _env_float("MIN_WIN_PROB", 0.60)

# ── v10.1.0 MARKET ANCHOR — the contract price IS a probability ───────────────
# WHY (2026-07-23→26 log audit): bayesian_win_prob produced a near-constant
# ~0.70 (n=65 signals: mean 70.4%, sd 4.3pp) that barely moved with the contract
# price (corr = +0.37). calc_edge then compared that flat number to the price, so
# "edge" collapsed into "cheapness": corr(price, edge) = -0.88 over the same 65
# signals. The model was not finding mispriced contracts, it was ranking
# contracts by how far below 70c they traded — and the 10 trades that survived
# sizing were the CHEAPEST of the batch (mean 44.8c vs 57.1c for the rest).
# The realized damage: over the 8 settlements the model claimed a mean 72.5%
# win probability and delivered 37.5% (p = 0.04 against its own claim), with a
# Brier score of 0.342 against 0.217 for simply believing the quoted price. The
# market beat the model on its own trades.
#
# THE FIX: stop treating the model output as a standalone probability. A liquid
# quoted price is already the market's probability estimate, and it is a better
# one. So express the model as an ADJUSTMENT to that estimate:
#
#     anchored_p = market_p + clamp(model_p - model_base, ±MAX_MODEL_EDGE_PP)
#
# where market_p = contract_price/100 and model_base is the same bucket prior
# bayesian_win_prob started from — so the clamped term is exactly the incremental
# information the order book / trend / depth signals added on top of the base
# rate, and nothing else.
#
# This makes `edge` mean something real and PRICE-NEUTRAL. Algebraically,
# calc_edge(price/100 + lift, price) == lift exactly, so with the anchor on,
# MIN_EDGE_PCT reads directly as "percentage points of claimed advantage over the
# market" at every price — the same bar for a 30c contract and a 65c one. Before
# the anchor a 30c contract cleared a 5% edge gate at p ≥ 0.36 while a 65c one
# needed p ≥ 0.71; that asymmetry WAS the cheapness tilt.
#
# MAX_MODEL_EDGE_PP is the honest ceiling on how much a 15-minute order-book +
# trend read can be worth against a market maker. 8pp is already ambitious; the
# unanchored model was routinely claiming 30-43pp. Set MARKET_ANCHOR_ENABLED
# false to restore pre-10.1.0 behaviour (documented, not recommended).
MARKET_ANCHOR_ENABLED = _env_bool("MARKET_ANCHOR_ENABLED", True)
MAX_MODEL_EDGE_PP     = _env_float("MAX_MODEL_EDGE_PP", 0.08)

# ── Return-on-risk edge gate (secondary, opt-in) ──────────────────────────────
# MIN_EDGE_PCT is expected value per CONTRACT (per $1 of payout). This is the
# same expected value per DOLLAR STAKED — edge / (price/100) — which is what
# actually compounds a bankroll. Off by default (0.0) because the market anchor
# above already removes the price distortion MIN_EDGE_PCT had; turn it on to
# additionally require a minimum return on the cash at risk.
MIN_EDGE_ROR          = _env_float("MIN_EDGE_ROR", 0.0)

# ── Order-book imbalance UPPER bound ─────────────────────────────────────────
# WHY (same audit): analyze_order_book only rejected a LITERALLY empty opposite
# side ("ghost book", yes_lc == 0 or no_lc == 0). A book quoting 99.8% on one
# side still passed — and because compute_confidence scores imbalance linearly
# (corr(OB%, confidence) = +0.92 over the 65 signals), that book scored the
# session's highest confidence (95), drew the session's largest stake ($2.14, 5
# contracts) and lost all of it. A 99% one-sided book on a thin 15-minute market
# is a LIQUIDITY artifact — one stale level left on the other side — not a
# conviction signal. Reject above this ceiling instead of rewarding it.
OB_IMBALANCE_MAX      = _env_float("OB_IMBALANCE_MAX", 0.95)
MIN_MINUTES_TO_EXPIRY = _env_float("MIN_MINUTES_TO_EXPIRY", 6.0)
# The whole doctrine (momentum windows, expiry floor, session math) is built for
# 15-MINUTE markets. BTC_SERIES falls back to daily-horizon series when the 15M
# series has nothing open, so cap how far out a candidate may expire — otherwise
# a quiet moment could apply 15-minute logic to a market with hours left.
MAX_MINUTES_TO_EXPIRY = _env_float("MAX_MINUTES_TO_EXPIRY", 20.0)
YES_BREAKEVEN_PRICE   = _env_int("YES_BREAKEVEN_PRICE", 67)

# v9.3.0: DOCTRINE LAYER 7 — BTC momentum must explicitly AGREE with the OB
# direction. NEUTRAL (flat BTC) and CONFLICT are both rejections. Default ON.
# Setting this false re-enables the unconfirmed-OB experiment that produced the
# 2026-06-20→22 bleed and the 2026-03-27/28 50% loss — only do so deliberately.
REQUIRE_AGREE_MOMENTUM = _env_bool("REQUIRE_AGREE_MOMENTUM", True)

# ── Time-of-day session quality ───────────────────────────────────────────────
SESSION_QUALITY: dict = {
    0: 20, 1: 10, 2: 10, 3: 10, 4: 15, 5: 30,
    6: 45, 7: 50, 8: 60, 9: 65, 10: 70, 11: 75,
    12: 80, 13: 90, 14: 95, 15: 95, 16: 95, 17: 90,
    18: 90, 19: 85, 20: 80, 21: 75, 22: 65, 23: 45,
}
MIN_SESSION_SCORE = _env_int("MIN_SESSION_SCORE", 60)

# ── Time-of-day learned prior (per-bucket Bayesian calibration) ───────────────
# WHY (2026-06-29 log review + 4-day pattern): the bot runs ONE strategy —
# short-dated trend-continuation — and trend persistence is time-of-day
# dependent. The US morning→midday trends; the US afternoon (ET ~2–4pm /
# UTC ~18–21) is the post-lunch lull that mean-reverts, so the exact setups that
# win in the morning bleed in the afternoon. The win-prob prior was a single
# pooled number (`_live_prior`) that ALSO resets to OB_BASE_ACCURACY every boot
# (live_wins/live_losses are in-memory), so the book never "noticed" the
# repeating afternoon losses.
#
# Fix: learn a SEPARATE prior per time-of-day bucket, PERSISTED to disk so it
# accumulates across days/restarts (the morning bleed is a multi-day signal).
# A bucket with a poor realized win rate lowers win_prob → lowers edge → trips
# the existing MIN_EDGE_PCT / Kelly gates, so weak afternoon setups simply do
# not fire. Stake is untouched (gate, never sandbag size — owner directive).
# With no data the bucket prior == OB_BASE_ACCURACY, so behaviour is identical
# to today until real outcomes accumulate (backward-compatible rollout).
BUCKET_STATS_PATH    = os.environ.get("BUCKET_STATS_PATH", "bucket_stats.json")
BUCKET_PERSIST       = _env_bool("BUCKET_PERSIST", True)
# How many UTC hours each bucket spans. 3 → 8 buckets/day, coarse enough that
# samples accumulate fast enough to matter. Clamped to [1, 24].
BUCKET_GROUP_HOURS   = max(1, min(24, _env_int("BUCKET_GROUP_HOURS", 3)))
# Sample size at which a bucket's empirical win rate is fully trusted; below it
# the prior is shrunk toward OB_BASE_ACCURACY (same blend as update_live_prior).
BUCKET_PRIOR_FULL_N  = max(1, _env_int("BUCKET_PRIOR_FULL_N", 30))

# ── Bayesian priors ───────────────────────────────────────────────────────────
OB_BASE_ACCURACY       = _env_float("OB_BASE_ACCURACY", 0.635)
MOMENTUM_ACCURACY_LIFT = _env_float("MOMENTUM_ACCURACY_LIFT", 0.045)
# v9.3.0: restored 0.0 → 0.02. NEUTRAL BTC is NOT "no evidence" for a directional
# 15-min binary — it means the confirming signal is ABSENT, so the OB-only prior
# must be discounted. With the Layer-7 gate above, NEUTRAL no longer reaches the
# win-prob path at all; this keeps win_prob honest if the gate is disabled.
NEUTRAL_ACCURACY_DRAG  = _env_float("NEUTRAL_ACCURACY_DRAG", 0.02)

# NOTE: the old drawdown-triggered RECOVERY session state (RECOVERY_TRIGGER_PCT
# / RECOVERY_EXIT_TRADES / RECOVERY_WIN_RATE_MIN / RECOVERY_MAX_SECS) was
# removed by the v9.4.0 owner directive; those env vars were dead config and
# are deleted. Today's "recovery" is the two-tier RecoveryState sizing below
# (a settled full-size LOSS drops sizing to RECOVERY_TRADE_PCT until the
# balance heals), which never blocks trading — only shrinks the stake.


# ─────────────────────────────────────────────────────────────────────────────
# RSA AUTHENTICATION
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_pem(raw: str) -> str:
    # Tolerate the common paste mistakes: surrounding quotes, literal "\n", spaces
    # or missing line breaks. Anything left after this that still won't parse means
    # the key body is genuinely incomplete/altered (see the load error below).
    pem = raw.strip().strip('"').strip("'")
    pem = pem.replace("\\n", "\n").replace("\\r", "").replace("\r", "")
    if "\n" not in pem:
        for tag in ["PRIVATE KEY", "RSA PRIVATE KEY"]:
            pem = pem.replace(f"-----BEGIN {tag}-----", f"-----BEGIN {tag}-----\n")
            pem = pem.replace(f"-----END {tag}-----", f"\n-----END {tag}-----")
    lines  = [l.strip() for l in pem.strip().splitlines() if l.strip()]
    header = next((l for l in lines if l.startswith("-----BEGIN")), None)
    footer = next((l for l in lines if l.startswith("-----END")),   None)
    if not header or not footer:
        raise ValueError(
            "KALSHI_PRIVATE_KEY_PEM is missing its '-----BEGIN ...-----' / "
            "'-----END ...-----' lines. Paste the WHOLE key file, header to footer.")
    # Base64 body only, all whitespace removed, then re-wrapped at 64 cols.
    body    = re.sub(r"\s+", "", "".join(l for l in lines if not l.startswith("-----")))
    wrapped = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
    return f"{header}\n{wrapped}\n{footer}\n"


KALSHI_PRIVATE_KEY_PEM = _normalize_pem(_RAW_PEM)

try:
    _private_key = serialization.load_pem_private_key(
        KALSHI_PRIVATE_KEY_PEM.encode("utf-8"), password=None,
    )
    # Provisioner green-verify boot marker — keep this exact text in sync
    # with onboarding/provisioner.py LOG_MARKERS.
    log.info("✅ RSA private key loaded.")
except Exception as e:
    raise ValueError(
        "Could not read KALSHI_PRIVATE_KEY_PEM — the key value looks incomplete or "
        "altered (a common copy/paste problem). Re-paste the ENTIRE private key, every "
        "line from '-----BEGIN' through '-----END-----', with nothing cut off, no extra "
        f"characters, and no surrounding quotes. Underlying error: {e}") from e


def _sign(method: str, path: str) -> tuple:
    ts_ms = str(int(time.time() * 1000))
    msg   = (ts_ms + method.upper() + "/trade-api/v2" + path).encode("utf-8")
    sig   = _private_key.sign(
        msg,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return ts_ms, base64.b64encode(sig).decode("utf-8")


def _auth_headers(method: str, path: str) -> dict:
    ts, sig = _sign(method, path)
    return {
        "KALSHI-ACCESS-KEY":       KALSHI_API_KEY_ID,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "Content-Type":            "application/json",
    }


# ─────────────────────────────────────────────────────────────────────────────
# HTTP
# ─────────────────────────────────────────────────────────────────────────────

_http    = requests.Session()
BASE_URL = ""


def _get(path: str, params: Optional[dict] = None) -> dict:
    r = _http.get(BASE_URL + path, params=params,
                  headers=_auth_headers("GET", path), timeout=12)
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict) -> dict:
    r = _http.post(BASE_URL + path, json=body,
                   headers=_auth_headers("POST", path), timeout=12)
    r.raise_for_status()
    return r.json()


def _delete(path: str) -> dict:
    r = _http.delete(BASE_URL + path,
                     headers=_auth_headers("DELETE", path), timeout=12)
    r.raise_for_status()
    return r.json()


def init_base_url() -> None:
    global BASE_URL
    for host in ["https://api.elections.kalshi.com", "https://trading-api.kalshi.com"]:
        try:
            r = _http.get(host + "/trade-api/v2/exchange/status", timeout=6)
            if r.status_code == 200:
                BASE_URL = host + "/trade-api/v2"
                log.info("✅ API host: %s", host)
                return
        except Exception:
            continue
    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
    log.warning("Host probe failed — using default.")


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
#
# RULE: open_orders, active_tickers, trade_history, session_traded_tickers,
# _processed_settlement_ids, btc_prices, btc_returns, _prev_ob are module-level
# mutable containers. They are mutated IN-PLACE everywhere. They must NEVER
# appear in any function's `global` declaration — doing so causes Python to
# treat every reference inside that function as an unbound local variable,
# producing UnboundLocalError before any in-place mutation occurs.
# ─────────────────────────────────────────────────────────────────────────────

btc_prices:  deque = deque(maxlen=60)
btc_returns: deque = deque(maxlen=59)

open_orders:               dict     = {}
active_tickers:            set      = set()
trade_history:             deque    = deque(maxlen=500)
session_traded_tickers:    Set[str] = set()
# Insertion-ordered (dict) so it can be pruned oldest-first without ever
# re-processing: the settlements endpoint only returns the last ~100 records,
# so keeping the newest few thousand ids guarantees a pruned id can't reappear.
_processed_settlement_ids: "dict[str, None]" = {}
# Kalshi returns only a small recent settlement window. Keeping substantially
# more ids than that makes pruning safe: a pruned id cannot reappear in normal
# operation, so this bounds memory without double-settling old records.
PROCESSED_SETTLEMENT_IDS_MAX = 4000
PREV_OB_MAX = 96 * 28  # four weeks of 15-minute markets

paper_balance:          float = 25.0
paper_daily_pnl:        float = 0.0
session_start_balance:  float = 0.0
session_stop_threshold: float = 0.0
live_wins:              int   = 0
live_losses:            int   = 0
consecutive_losses:     int   = 0
streak_pause_until:     float = 0.0
running_pnl:            float = 0.0
daily_pnl:              float = 0.0
live_daily_realized:    float = 0.0   # v9.3.1: realized-only $ that feeds the LIVE daily-loss breaker
last_trade_ts:          float = -9999.0
last_signal_desc:       str   = "none yet"

session_state:         SessionState = SessionState.ACTIVE
_session_start_ts:     str          = ""
_session_day:          str          = ""
_session_halted:       bool         = False
# Why the day is halted: "" while trading, "session_stop" for the catastrophic
# backstop, "profit_target" once the daily +3% goal is banked. Only affects the
# copy the customer sees (a hit target is good news, a session stop is not) —
# both clear at the UTC rollover.
_halt_reason:          str          = ""
_shutdown_requested:   bool         = False
_last_known_balance:   float        = 0.0

_prev_ob: dict = {}

def _remember_prev_ob(ticker: str, value: tuple, now: float) -> None:
    """Store order-book state while retaining only recent market history."""
    _prev_ob[ticker] = value
    if len(_prev_ob) > PREV_OB_MAX:
        oldest = sorted(_prev_ob, key=lambda key: _prev_ob[key][2])
        for key in oldest[:len(_prev_ob) - PREV_OB_MAX]:
            del _prev_ob[key]

def _remember_settlement_id(rec_id: str) -> None:
    """Record a settlement id and prune oldest ids beyond the safety window."""
    _processed_settlement_ids[rec_id] = None
    excess = len(_processed_settlement_ids) - PROCESSED_SETTLEMENT_IDS_MAX
    if excess > 0:
        for key in list(_processed_settlement_ids)[:excess]:
            del _processed_settlement_ids[key]

_vol_circuit_open:  bool  = False
_vol_circuit_until: float = 0.0

# v10.1.0 performance guard: a rolling window of settled outcomes that does NOT
# reset at the UTC rollover (live_wins/live_losses do, which is why the guard
# reading them never once filled its sample — see performance_guard). Mutated
# in-place only, like every other module-level container here.
_perf_window: deque = deque(maxlen=max(1, PERF_GUARD_WINDOW))
_perf_guard_until: float = 0.0

_live_prior: float = OB_BASE_ACCURACY


# ─────────────────────────────────────────────────────────────────────────────
# RECOVERY MODE  (two-tier position sizing — v9.5.0)
#
# After a FULL-SIZE (normal-mode) trade settles a LOSS, the bot drops to the
# reduced RECOVERY_TRADE_PCT until the account balance climbs back to where it
# was IMMEDIATELY BEFORE that losing trade. Then it returns to NORMAL_TRADE_PCT
# automatically. The state (active flag + recovery target balance) is persisted
# to disk so an in-container restart resumes mid-recovery.
#
# Design guarantees (see also the edge-case notes in TRADING_DOCTRINE.md §6):
#   • Entry is event-driven (a settled full-size loss), so the target is the
#     exact recorded pre-trade balance — never reconstructed from PnL.
#   • Exit is balance-driven and checked every cycle AND on boot, so the bot can
#     never wedge in recovery once balance reaches the target even once.
#   • enter() is a no-op while already active → a further loss never moves the
#     target (the goal stays the original pre-loss balance).
#   • Single-threaded loop → mutate-then-persist is atomic w.r.t. sizing reads;
#     there is no race and no per-cycle oscillation (entry needs a settlement).
# This `recovery` object is mutated IN-PLACE only and must NEVER be reassigned
# (so it never appears in a function `global` statement — same rule as the other
# module-level mutable containers above).
# ─────────────────────────────────────────────────────────────────────────────

class RecoveryState:
    """Persistent two-tier sizing mode. Owns {active, target_balance}."""

    SCHEMA = 1

    def __init__(self, path: str, persist: bool) -> None:
        self.active:         bool  = False
        self.target_balance: float = 0.0
        # Recovery-scoped settled outcomes (trades entered WHILE in recovery),
        # feeding the win-rate restore. Reset on every entry.
        self.wins:           int   = 0
        self.losses:         int   = 0
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    # ── recovery-scoped win rate (feeds the win-rate restore) ─────────────────
    def record_result(self, won: bool) -> None:
        """Tally one settled trade that was ENTERED while recovery was active."""
        if not self.active:
            return
        if won:
            self.wins += 1
        else:
            self.losses += 1
        self._save()

    def winrate(self) -> float:
        n = self.wins + self.losses
        return (self.wins / n) if n else 0.0

    # ── transitions ──────────────────────────────────────────────────────────
    def enter(self, target_balance: float, current_balance: float) -> bool:
        """Activate recovery with the given target. No-op if already active or
        the target is not a usable, not-already-met value. Returns True on a
        real activation."""
        if self.active:
            return False
        if target_balance is None or target_balance <= 0.0:
            return False
        # If we are somehow already at/above the target, there is nothing to
        # recover — stay in normal mode rather than enter-then-instantly-exit.
        if current_balance >= target_balance:
            return False
        self.active         = True
        self.target_balance = round(float(target_balance), 2)
        self.wins = self.losses = 0            # fresh recovery-scoped win-rate count
        self._save()
        nsc = recovery_no_stake_change_enabled()
        log.warning("Recovery mode ACTIVATED after losing full-size trade.")
        log.warning("Previous balance: $%.2f", self.target_balance)
        log.warning("Recovery target: $%.2f", self.target_balance)
        if nsc:
            # "No Stake Change" mode: track the claw-back, but do NOT drop the stake.
            log.warning("No-Stake-Change mode ON — keeping trade size at %.1f%% "
                        "of balance.", effective_normal_trade_pct() * 100)
            tg.send_status_message(
                f"🛟 RECOVERY MODE ACTIVATED — No Stake Change\n"
                f"Recovery target: ${self.target_balance:.2f}\n"
                f"Trade size stays at {effective_normal_trade_pct()*100:.1f}% of "
                f"balance — no stake reduction, no jump-back on exit."
            )
        else:
            log.warning("Switching trade size to: %.1f%% of balance", RECOVERY_TRADE_PCT * 100)
            tg.send_status_message(
                f"🛟 RECOVERY MODE ACTIVATED\n"
                f"Recovery target: ${self.target_balance:.2f}\n"
                f"Trade size → {RECOVERY_TRADE_PCT*100:.1f}% of balance "
                f"(was {effective_normal_trade_pct()*100:.1f}%)"
            )
        return True

    def maybe_exit(self, current_balance: float) -> bool:
        """Deactivate recovery once balance has recovered to the target. Checked
        every cycle and on boot. Returns True on a real deactivation."""
        if not self.active:
            return False
        if current_balance < self.target_balance:
            return False
        reached = self.target_balance
        nsc = recovery_no_stake_change_enabled()
        self.active         = False
        self.target_balance = 0.0
        self.wins = self.losses = 0
        self._save()
        log.warning("Recovery target reached.")
        log.warning("Recovery mode DEACTIVATED.")
        if nsc:
            # Stake never dropped, so there is nothing to ramp back to — exit is
            # a clean no-op on sizing.
            log.info("No-Stake-Change mode — sizing already at full; no ramp.")
            tg.send_status_message(
                f"✅ RECOVERY COMPLETE — balance ${current_balance:.2f} ≥ target "
                f"${reached:.2f}\nStake never changed (No Stake Change mode) — "
                f"nothing to ramp back."
            )
            return True
        log.warning("Switching trade size back to: %.1f%% of balance", effective_normal_trade_pct() * 100)
        tg.send_status_message(
            f"✅ RECOVERY COMPLETE — balance ${current_balance:.2f} ≥ target "
            f"${reached:.2f}\nTrade size → {effective_normal_trade_pct()*100:.1f}% of balance"
        )
        return True

    def clear_for_restore(self) -> None:
        """Exit recovery WITHOUT the balance-target / probation-ramp path — used by
        the win-rate restore, which returns straight to the full base stake.
        Silent: the caller owns the log/Telegram copy."""
        self.active         = False
        self.target_balance = 0.0
        self.wins = self.losses = 0
        self._save()

    def reconcile_on_boot(self, current_balance: float) -> None:
        """Self-heal persisted state at startup so the bot can never resume into
        a stuck or nonsensical recovery."""
        if not self.active:
            return
        if self.target_balance <= 0.0:
            log.warning("Recovery boot │ corrupt target $%.2f — clearing.",
                        self.target_balance)
            self.active = False
            self._save()
            return
        if current_balance >= self.target_balance:
            log.info("Recovery boot │ balance $%.2f already ≥ target $%.2f — "
                     "exiting recovery.", current_balance, self.target_balance)
            self.maybe_exit(current_balance)
            return
        log.warning("Recovery boot │ RESUMING recovery. Balance $%.2f, target "
                    "$%.2f, trade size %.1f%% of balance.",
                    current_balance, self.target_balance, RECOVERY_TRADE_PCT * 100)

    def status_line(self, current_balance: float) -> str:
        n  = self.wins + self.losses
        wr = f" WR={self.winrate()*100:.0f}% ({self.wins}W/{self.losses}L)" if n else ""
        if recovery_no_stake_change_enabled():
            pct   = effective_normal_trade_pct()
            stake = pct * current_balance
            return (f"Recovery mode active (No Stake Change). Current balance: "
                    f"${current_balance:.2f}. Target: ${self.target_balance:.2f}. "
                    f"Trade size held at {pct*100:.1f}% (~${stake:.2f}).{wr}")
        stake = RECOVERY_TRADE_PCT * current_balance
        return (f"Recovery mode active. Current balance: ${current_balance:.2f}. "
                f"Target: ${self.target_balance:.2f}. "
                f"Trade size: {RECOVERY_TRADE_PCT*100:.1f}% (~${stake:.2f}).{wr}")

    # ── persistence (atomic JSON write) ────────────────────────────────────────
    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({
                    "schema":         self.SCHEMA,
                    "active":         self.active,
                    "target_balance": self.target_balance,
                    "wins":           self.wins,
                    "losses":         self.losses,
                }, f)
            os.replace(tmp, self._path)   # atomic on POSIX
        except OSError as e:
            log.warning("Recovery │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.active         = bool(d.get("active", False))
        self.target_balance = float(d.get("target_balance", 0.0) or 0.0)
        self.wins           = int(d.get("wins", 0) or 0)
        self.losses         = int(d.get("losses", 0) or 0)


recovery = RecoveryState(RECOVERY_STATE_PATH, RECOVERY_PERSIST)


# ─────────────────────────────────────────────────────────────────────────────
# PROBATION RAMP  (post-recovery graduated re-entry — log-review fix)
#
# Mutated IN-PLACE only, never reassigned (same rule as `recovery`). Coupled to
# recovery: it STARTS when recovery clears and is mutually exclusive with it
# (recovery only re-arms on a true full-size loss, which can only happen after
# the ramp has graduated back to normal). See the config block above for the why.
# ─────────────────────────────────────────────────────────────────────────────

class ProbationState:
    """Persistent graduated re-entry after a recovery exit. Owns the ramp of
    sub-full base sizes and advances/steps based on settled outcomes."""

    SCHEMA = 1

    def __init__(self, path: str, persist: bool) -> None:
        self.active:    bool        = False
        self.rungs:     List[float] = []     # ascending sub-full base sizes
        self.level:     int         = 0      # index into rungs
        self.full_size: float       = 0.0    # graduation target (NORMAL fraction)
        self.streak:    int         = 0      # consecutive wins at the current rung
        self.wins:      int         = 0      # cumulative settled wins this ramp
        self.losses:    int         = 0      # cumulative settled losses this ramp
        self.day:       str         = ""     # UTC date (YYYY-MM-DD) the ramp was armed
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    # ── transitions ──────────────────────────────────────────────────────────
    def start(self, rungs: List[float], full_size: float,
              reason: str = "Re-entering after recovery") -> bool:
        """Begin a ramp from rungs[0] up toward full_size. No-op (returns False)
        when the ramp is disabled or there is no sub-full room to climb — the
        caller then resumes full size directly, exactly as before. `reason` is a
        short human label for the log/Telegram copy so the post-recovery and the
        daily-warm-up triggers read differently."""
        if not PROBATION_RAMP_ENABLED:
            return False
        rungs = [round(float(r), 4) for r in rungs if r < full_size]
        if not rungs:
            return False
        self.active    = True
        self.rungs     = rungs
        self.level     = 0
        self.full_size = round(float(full_size), 4)
        self.streak    = 0
        self.wins      = 0
        self.losses    = 0
        self.day       = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self._save()
        _pct = lambda f: f"{f*100:.1f}%"
        log.warning("Probation ramp START (%s) │ base %s → full %s via %s",
                    reason, _pct(self.rungs[0]), _pct(self.full_size),
                    " → ".join(_pct(r) for r in self.rungs + [self.full_size]))
        tg.send_status_message(
            f"🪜 PROBATION RAMP STARTED\n"
            f"{reason}: re-entering at {_pct(self.rungs[0])} of balance; will climb "
            f"{' → '.join(_pct(r) for r in self.rungs + [self.full_size])} "
            f"as the edge re-proves itself.\n"
            f"Advance on {PROBATION_WIN_STREAK}-win streak or "
            f"≥{PROBATION_WIN_RATE_MIN*100:.0f}% win rate; step down on a loss."
        )
        return True

    def current_size(self) -> float:
        """The base stake FRACTION for the current rung (full fraction when
        inactive)."""
        if not self.active or not self.rungs:
            return self.full_size or effective_normal_trade_pct()
        return self.rungs[min(self.level, len(self.rungs) - 1)]

    def _gate_met(self) -> bool:
        if self.streak >= PROBATION_WIN_STREAK:
            return True
        n = self.wins + self.losses
        return (n >= PROBATION_WINRATE_MIN_TRADES
                and (self.wins / n) >= PROBATION_WIN_RATE_MIN)

    def record_result(self, won: bool, balance: "float | None" = None) -> None:
        """Fold one settled probation-mode trade into the ramp. `balance` is
        accepted for call-site symmetry but no longer gates advancement — because
        every rung is a FRACTION of the current balance, the stake already scales
        with equity and needs no separate high-stake dollar gate."""
        if not self.active:
            return
        if won:
            self.wins  += 1
            self.streak += 1
            if self._gate_met():
                self._advance()
        else:
            self.losses += 1
            self.streak  = 0
            self._step_down()
        if self.active:                 # _advance may have graduated (saved already)
            self._save()

    def _advance(self) -> None:
        if self.level >= len(self.rungs) - 1:
            self._graduate()
            return
        self.level += 1
        self.streak = 0                 # must re-prove the edge at the larger size
        log.warning("Probation ramp UP → base %.1f%% (rung %d/%d).",
                    self.current_size() * 100, self.level + 1, len(self.rungs))
        tg.send_status_message(
            f"🪜 PROBATION RAMP UP → {self.current_size()*100:.1f}% "
            f"(rung {self.level + 1}/{len(self.rungs)})"
        )

    def _step_down(self) -> None:
        if self.level == 0:
            log.info("Probation ramp │ loss at floor %.1f%% — holding.",
                     self.current_size() * 100)
            return
        self.level -= 1
        log.warning("Probation ramp DOWN → base %.1f%% (loss).", self.current_size() * 100)
        tg.send_status_message(
            f"🪜 PROBATION RAMP DOWN → {self.current_size()*100:.1f}% (loss)"
        )

    def _graduate(self) -> None:
        frac = self.full_size or effective_normal_trade_pct()
        self.active = False
        self.level  = 0
        self.rungs  = []
        self._save()
        log.warning("Probation ramp COMPLETE → full size %.1f%% restored.", frac * 100)
        tg.send_status_message(
            f"✅ PROBATION COMPLETE — full size {frac*100:.1f}% restored."
        )

    def cancel(self) -> None:
        """Drop the ramp (e.g. a deeper full-size loss re-arms recovery)."""
        if not self.active:
            return
        self.active = False
        self.level  = 0
        self.rungs  = []
        self.streak = self.wins = self.losses = 0
        self.day    = ""
        self._save()

    def reconcile_on_boot(self) -> None:
        if not self.active:
            return
        if not self.rungs or self.full_size <= 0.0:
            log.warning("Probation boot │ corrupt ramp — clearing.")
            self.cancel()
            return
        # A restart that crosses a UTC day boundary must re-arm the daily slow-roll
        # from the floor (matching the live midnight rollover), not resume
        # yesterday's progress. Recovery is the deeper claw-back and takes
        # priority, so leave its ramp alone. Same-day restarts resume unchanged.
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.day and self.day != today and not recovery.active:
            log.info("Probation boot │ new day (%s→%s) — re-arming ramp from floor.",
                     self.day, today)
            self.start(_probation_rungs(), effective_normal_trade_pct(), reason="Daily slow-roll")
            return
        self.level = max(0, min(self.level, len(self.rungs) - 1))
        log.info("Probation boot │ RESUMING ramp at base %.1f%% (rung %d/%d).",
                 self.current_size() * 100, self.level + 1, len(self.rungs))

    def status_line(self) -> str:
        n  = self.wins + self.losses
        wr = (self.wins / n * 100.0) if n else 0.0
        return (f"Probation ramp active. Base {self.current_size()*100:.1f}% "
                f"(rung {self.level + 1}/{len(self.rungs)}, target {self.full_size*100:.1f}%). "
                f"streak={self.streak} WR={wr:.0f}% n={n}.")

    # ── persistence (atomic JSON write) ────────────────────────────────────────
    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({
                    "schema":    self.SCHEMA,
                    "active":    self.active,
                    "rungs":     self.rungs,
                    "level":     self.level,
                    "full_size": self.full_size,
                    "streak":    self.streak,
                    "wins":      self.wins,
                    "losses":    self.losses,
                    "day":       self.day,
                }, f)
            os.replace(tmp, self._path)   # atomic on POSIX
        except OSError as e:
            log.warning("Probation │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.active    = bool(d.get("active", False))
        self.rungs     = [round(float(r), 4) for r in d.get("rungs", [])]
        self.level     = int(d.get("level", 0))
        self.full_size = float(d.get("full_size", 0.0) or 0.0)
        self.streak    = int(d.get("streak", 0))
        self.wins      = int(d.get("wins", 0))
        self.losses    = int(d.get("losses", 0))
        self.day       = str(d.get("day", "") or "")


probation = ProbationState(PROBATION_STATE_PATH, PROBATION_PERSIST)


# ─────────────────────────────────────────────────────────────────────────────
# TIME-OF-DAY LEARNED PRIOR  (per-bucket Bayesian calibration — afternoon fix)
#
# Persists realized {wins, losses} per time-of-day bucket so the win-prob prior
# can learn that some hours (the mean-reverting US afternoon) are worse than
# others. Keyed by UTC hour — consistent with SESSION_QUALITY — grouped into
# BUCKET_GROUP_HOURS-wide buckets. Mutated IN-PLACE only, never reassigned (same
# rule as `recovery`/`probation`). See the config block above for the why.
# ─────────────────────────────────────────────────────────────────────────────

class BucketStats:
    """Persistent per-time-of-day win/loss tally feeding a learned prior."""

    SCHEMA = 1

    def __init__(self, path: str, persist: bool) -> None:
        self._data:   dict = {}     # {bucket_key: {"wins": int, "losses": int}}
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    @staticmethod
    def key_for_hour(utc_hour: int) -> str:
        """Human-readable bucket key for a UTC hour, e.g. '18-20' for group=3."""
        h     = int(utc_hour) % 24
        start = (h // BUCKET_GROUP_HOURS) * BUCKET_GROUP_HOURS
        end   = min(start + BUCKET_GROUP_HOURS - 1, 23)
        return f"{start:02d}-{end:02d}"

    def key_now(self) -> str:
        return self.key_for_hour(datetime.now(timezone.utc).hour)

    def record(self, bucket_key: Optional[str], won: bool) -> None:
        """Tally one settled outcome into its ENTRY bucket. No-op on a missing
        key (e.g. an unmatched pre-restart trade whose entry bucket is unknown)."""
        if not bucket_key:
            return
        s = self._data.setdefault(bucket_key, {"wins": 0, "losses": 0})
        if won:
            s["wins"] = int(s.get("wins", 0)) + 1
        else:
            s["losses"] = int(s.get("losses", 0)) + 1
        self._save()

    def prior_for(self, bucket_key: Optional[str]) -> Tuple[float, int]:
        """Blended prior for a bucket and its sample size. Shrinks toward
        OB_BASE_ACCURACY when the sample is thin (identical blend to
        update_live_prior), so an empty/new bucket == today's behaviour."""
        s     = self._data.get(bucket_key or "", {})
        wins  = int(s.get("wins", 0))
        total = wins + int(s.get("losses", 0))
        if total <= 0:
            return OB_BASE_ACCURACY, 0
        empirical = wins / total
        weight    = min(1.0, total / BUCKET_PRIOR_FULL_N)
        prior     = OB_BASE_ACCURACY * (1.0 - weight) + empirical * weight
        return prior, total

    # ── persistence (atomic JSON write) ────────────────────────────────────────
    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({"schema": self.SCHEMA, "buckets": self._data}, f)
            os.replace(tmp, self._path)   # atomic on POSIX
        except OSError as e:
            log.warning("BucketStats │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        raw = d.get("buckets", {})
        if not isinstance(raw, dict):
            return
        clean: dict = {}
        for k, v in raw.items():
            if isinstance(v, dict):
                clean[str(k)] = {"wins":   int(v.get("wins", 0) or 0),
                                 "losses": int(v.get("losses", 0) or 0)}
        self._data = clean


bucket_stats = BucketStats(BUCKET_STATS_PATH, BUCKET_PERSIST)


# ─────────────────────────────────────────────────────────────────────────────
# PERFORMANCE-FEE BILLING  (high-water-mark monthly profit share)
#
# Tracks the account's all-time high-water mark (peak month-end balance) and, at
# each UTC month boundary, reports the performance fee to invoice:
#     billable_profit = max(0, month_end_balance − HWM_before)
#     fee             = PERF_FEE_PCT × billable_profit
# then advances HWM = max(HWM, month_end_balance). Because the fee is only ever
# charged on balance ABOVE the previous peak, a customer who dips and recovers is
# never billed twice for the same dollars. The bot does NOT move money — it emits
# the number (operator Telegram + optional billing log + status snapshot) so the
# operator can raise the invoice (Stripe). Mutated IN-PLACE only.
# ─────────────────────────────────────────────────────────────────────────────

class BillingState:
    """Persistent high-water mark + current-month anchor for the performance fee."""

    SCHEMA = 1

    def __init__(self, path: str, persist: bool) -> None:
        self.hwm:                 float = 0.0   # all-time peak month-end balance
        self.month:               str   = ""    # current UTC month, "YYYY-MM"
        self.month_start_balance: float = 0.0   # balance at the start of `month`
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    @staticmethod
    def _now_month() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m")

    def reconcile_on_boot(self, balance: float) -> None:
        """Seed the anchor on first ever run so the initial deposit is never billed
        as profit. A restart that crossed a month boundary is settled by the normal
        per-cycle rollover check (persisted month != current month)."""
        if self.month == "":
            self.month               = self._now_month()
            self.month_start_balance = round(float(balance), 2)
            if self.hwm <= 0.0:
                self.hwm = round(float(balance), 2)
            self._save()
            log.info("Billing boot │ seeded HWM $%.2f, month %s.", self.hwm, self.month)

    def maybe_month_rollover(self, balance: float) -> bool:
        """At each UTC month change, compute the performance fee for the month that
        just ended and advance the high-water mark. Returns True on a real rollover.
        Never raises — billing observability must not break trading."""
        if PERF_FEE_PCT <= 0.0:
            return False
        try:
            now_month = self._now_month()
            if self.month == "":
                self.reconcile_on_boot(balance)
                return False
            if now_month == self.month:
                return False

            ended          = self.month
            hwm_before     = self.hwm
            gross_change   = round(balance - self.month_start_balance, 2)
            billable       = round(max(0.0, balance - hwm_before), 2)
            fee            = round(PERF_FEE_PCT * billable, 2)

            self.hwm                 = round(max(hwm_before, balance), 2)
            self.month               = now_month
            self.month_start_balance = round(float(balance), 2)
            self._save()

            log.warning("💵 BILLING │ %s closed │ end $%.2f │ month Δ $%+.2f │ "
                        "billable(HWM) $%.2f │ fee(%.0f%%) $%.2f │ new HWM $%.2f",
                        ended, balance, gross_change, billable,
                        PERF_FEE_PCT * 100, fee, self.hwm)
            self._append_log({
                "month": ended, "closed_at": datetime.now(timezone.utc).isoformat(),
                "end_balance": round(balance, 2), "month_change": gross_change,
                "hwm_before": hwm_before, "billable_profit": billable,
                "perf_fee_pct": PERF_FEE_PCT, "performance_fee": fee,
                "hwm_after": self.hwm, "demo_mode": DEMO_MODE,
            })
            mode = "PAPER (not billable)" if DEMO_MODE else "LIVE"
            tg.send_status_message(
                f"💵 MONTHLY BILLING — {ended} [{mode}]\n"
                f"End balance: ${balance:,.2f}\n"
                f"Month change: ${gross_change:+,.2f}\n"
                f"Billable new profit (above HWM ${hwm_before:,.2f}): ${billable:,.2f}\n"
                f"Performance fee ({PERF_FEE_PCT*100:.0f}%): ${fee:,.2f}\n"
                f"New high-water mark: ${self.hwm:,.2f}"
                + ("" if not DEMO_MODE else "\n(paper mode — informational only)")
            )
            return True
        except Exception as e:            # never let billing break the trade loop
            log.warning("Billing rollover error: %s", e)
            return False

    def snapshot(self, balance: float) -> dict:
        """Live billing view for the status snapshot / dashboard."""
        billable = max(0.0, balance - self.hwm)
        return {
            "hwm": round(self.hwm, 2),
            "month": self.month,
            "month_change": round(balance - self.month_start_balance, 2),
            "billable_profit": round(billable, 2),
            "perf_fee_pct": PERF_FEE_PCT,
            "accrued_perf_fee": round(PERF_FEE_PCT * billable, 2),
        }

    # ── persistence (atomic JSON write) ────────────────────────────────────────
    def _append_log(self, row: dict) -> None:
        if not BILLING_LOG_PATH:
            return
        try:
            with open(BILLING_LOG_PATH, "a") as f:
                f.write(json.dumps(row) + "\n")
        except OSError as e:
            log.warning("Billing │ log append failed: %s", e)

    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({
                    "schema":              self.SCHEMA,
                    "hwm":                 self.hwm,
                    "month":               self.month,
                    "month_start_balance": self.month_start_balance,
                }, f)
            os.replace(tmp, self._path)   # atomic on POSIX
        except OSError as e:
            log.warning("Billing │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.hwm                 = float(d.get("hwm", 0.0) or 0.0)
        self.month               = str(d.get("month", "") or "")
        self.month_start_balance = float(d.get("month_start_balance", 0.0) or 0.0)


billing = BillingState(BILLING_STATE_PATH, BILLING_PERSIST)


# ─────────────────────────────────────────────────────────────────────────────
# LIFETIME STATS  (persistent all-time W/L + PnL — "stop the win rate resetting")
#
# Unbounded, disk-persisted tally of every settled trade, split by paper/live so
# practice never dilutes the live record. Mutated IN-PLACE only, never reassigned
# (same rule as `recovery`/`probation`). Survives redeploys when its path is on
# the /data volume, so the all-time win rate the customer sees never resets.
# ─────────────────────────────────────────────────────────────────────────────

class LifetimeStats:
    """Persistent all-time settled-trade tally, keyed by paper/live bucket."""

    SCHEMA = 1

    def __init__(self, path: str, persist: bool) -> None:
        self._data = {"paper": {"wins": 0, "losses": 0, "pnl": 0.0},
                      "live":  {"wins": 0, "losses": 0, "pnl": 0.0}}
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    @staticmethod
    def _bucket(demo_mode: bool) -> str:
        return "paper" if demo_mode else "live"

    def record(self, demo_mode: bool, won: bool, pnl: float) -> None:
        """Fold one SETTLED trade into the all-time tally for its mode. Called once
        per settlement. Never raises — an accounting write must not break trading."""
        try:
            d = self._data[self._bucket(demo_mode)]
            d["wins" if won else "losses"] += 1
            try:
                d["pnl"] = round(d["pnl"] + float(pnl), 4)
            except (TypeError, ValueError):
                pass
            self._save()
        except Exception as e:  # pragma: no cover - observability must not break trading
            log.debug("lifetime record failed: %s", e)

    def stats(self, demo_mode: bool) -> "tuple[int, int, float]":
        d = self._data[self._bucket(demo_mode)]
        return int(d["wins"]), int(d["losses"]), round(float(d["pnl"]), 2)

    def winrate(self, demo_mode: bool) -> float:
        w, l, _ = self.stats(demo_mode)
        n = w + l
        return (w / n) if n else 0.0

    # ── persistence (atomic JSON write) ────────────────────────────────────────
    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({"schema": self.SCHEMA, "buckets": self._data}, f)
            os.replace(tmp, self._path)   # atomic on POSIX
        except OSError as e:
            log.warning("Lifetime │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        buckets = d.get("buckets", {}) if isinstance(d, dict) else {}
        for key in ("paper", "live"):
            b = buckets.get(key, {}) if isinstance(buckets, dict) else {}
            if isinstance(b, dict):
                self._data[key] = {
                    "wins":   int(b.get("wins", 0) or 0),
                    "losses": int(b.get("losses", 0) or 0),
                    "pnl":    float(b.get("pnl", 0.0) or 0.0),
                }


lifetime = LifetimeStats(LIFETIME_STATS_PATH, LIFETIME_PERSIST)


# Cache the parsed risk override on the file's mtime so the sizing chokepoint can
# consult it every cycle without re-reading/parsing JSON on each call.
_risk_override_cache: "tuple[float, float] | None" = None  # (mtime, fraction)


def _read_risk_override() -> "float | None":
    """The customer's full-size stake fraction from RISK_OVERRIDE_PATH, or None if
    no valid override is present. Cached on the file's mtime. Never raises — a
    missing, empty, or corrupt file simply means 'no override, use the default'."""
    global _risk_override_cache
    try:
        mtime = os.path.getmtime(RISK_OVERRIDE_PATH)
    except OSError:
        _risk_override_cache = None
        return None
    if _risk_override_cache is not None and _risk_override_cache[0] == mtime:
        return _risk_override_cache[1]
    try:
        with open(RISK_OVERRIDE_PATH) as f:
            frac = float(json.load(f).get("normal_trade_pct"))
    except (OSError, ValueError, TypeError):
        _risk_override_cache = None
        return None
    if not frac > 0:                      # 0, negative, or NaN → treat as no override
        _risk_override_cache = None
        return None
    _risk_override_cache = (mtime, frac)
    return frac


# Cache the parsed "no stake change" override on the file's mtime, same pattern.
_recovery_nsc_cache: "tuple[float, bool] | None" = None  # (mtime, enabled)


def recovery_no_stake_change_enabled() -> bool:
    """Whether Recovery Mode is in "No Stake Change" mode: the runtime override
    (Telegram/dashboard) when present, otherwise the RECOVERY_NO_STAKE_CHANGE env
    default. Cached on the file's mtime. Never raises — a missing/corrupt file
    simply falls back to the env default."""
    global _recovery_nsc_cache
    try:
        mtime = os.path.getmtime(RECOVERY_NSC_OVERRIDE_PATH)
    except OSError:
        _recovery_nsc_cache = None
        return RECOVERY_NO_STAKE_CHANGE
    if _recovery_nsc_cache is not None and _recovery_nsc_cache[0] == mtime:
        return _recovery_nsc_cache[1]
    try:
        with open(RECOVERY_NSC_OVERRIDE_PATH) as f:
            enabled = bool(json.load(f).get("enabled"))
    except (OSError, ValueError, TypeError):
        _recovery_nsc_cache = None
        return RECOVERY_NO_STAKE_CHANGE
    _recovery_nsc_cache = (mtime, enabled)
    return enabled


def effective_normal_trade_pct() -> float:
    """The active full-size stake FRACTION: the customer's runtime /risk override
    when one is set, otherwise the NORMAL_TRADE_PCT default. Always clamped into
    the safe [RISK_MIN_TRADE_PCT, MAX_TRADE_PCT] band so no configured or typed
    value can push the base stake past the hard ceiling or below a fill-able floor.
    Recovery/probation de-risking and every guardrail still layer on top of this."""
    frac = _read_risk_override()
    if frac is None:
        frac = NORMAL_TRADE_PCT
    return max(RISK_MIN_TRADE_PCT, min(frac, MAX_TRADE_PCT))


# Cache the parsed reserve on the file's mtime, same pattern as the risk override.
_reserve_cache: "tuple[float, float] | None" = None  # (mtime, dollars)


def effective_reserve() -> float:
    """The dollar amount the customer has ring-fenced from trading via the
    dashboard (RESERVE_OVERRIDE_PATH), or 0.0 if none/invalid. Cached on the file's
    mtime. Never raises. Clamped to ≥ 0 — a negative reserve is meaningless and is
    treated as no reserve."""
    global _reserve_cache
    try:
        mtime = os.path.getmtime(RESERVE_OVERRIDE_PATH)
    except OSError:
        _reserve_cache = None
        return 0.0
    if _reserve_cache is not None and _reserve_cache[0] == mtime:
        return _reserve_cache[1]
    try:
        with open(RESERVE_OVERRIDE_PATH) as f:
            amt = float(json.load(f).get("reserve_dollars"))
    except (OSError, ValueError, TypeError):
        _reserve_cache = None
        return 0.0
    amt = amt if amt > 0 else 0.0         # negative/NaN/0 → no reserve
    _reserve_cache = (mtime, amt)
    return amt


def tradeable_balance(balance: float) -> float:
    """The balance the bot is allowed to stake: the live balance minus the
    customer's reserve, floored at 0. All sizing works off this, so the reserve is
    never risked and the stake auto-de-risks to 0 as the tradeable remainder does."""
    return max(0.0, balance - effective_reserve())


def active_trade_fraction() -> float:
    """The stake FRACTION of the current balance for the active mode. Single
    source of truth for sizing posture: recovery (deepest claw-back) → probation
    ramp → normal. The hard MAX_TRADE_PCT ceiling is applied when this fraction is
    resolved to dollars (active_trade_size / kelly_bet).

    Recovery Mode "No Stake Change" exception: when that toggle is on, recovery
    still tracks/labels but must NOT drop the stake — sizing stays at the full
    normal fraction so the claw-back happens at the same stake.

    v10.2.0: with the ladder retired, RECOVERY_NO_STAKE_CHANGE on and the
    probation ramp off (all defaults), this is simply effective_normal_trade_pct()
    on every call — one flat percentage of balance, exactly as the owner
    directive asks. The branches stay so the older tiers remain switchable."""
    if recovery.active and not recovery_no_stake_change_enabled():
        return RECOVERY_TRADE_PCT
    if probation.active:
        return probation.current_size()
    return effective_normal_trade_pct()


def active_trade_size(balance: float) -> float:
    """The DOLLAR stake for the current mode = active fraction × TRADEABLE balance,
    clamped by the hard MAX_TRADE_PCT ceiling and by cash on hand. The tradeable
    balance is the live balance minus the customer's reserve (set aside), so the
    reserve is never staked and the stake auto-de-risks to 0 as the tradeable
    remainder shrinks. Because the fraction is of the CURRENT balance, the stake
    re-scales on every trade — it compounds as the account grows and de-risks as it
    shrinks. Single dollar-resolution point; every position-sizing path derives
    from this."""
    usable = tradeable_balance(balance)
    frac = min(active_trade_fraction(), MAX_TRADE_PCT)
    return round(min(frac * usable, usable), 2)


def in_clawback() -> bool:
    """True while clawing back a loss at a REDUCED base (standard recovery OR
    probation ramp) — i.e. the stake is deliberately smaller than the configured
    full fraction. Both of those tiers are off by default in v10.2.0, so this is
    normally False; it stays as the single predicate for "sizing is currently
    reduced" for deployments that switch either tier back on.

    Recovery Mode "No Stake Change" is deliberately NOT a clawback state here: the
    stake never dropped, so nothing about sizing is reduced."""
    if recovery.active and not recovery_no_stake_change_enabled():
        return True
    return probation.active


def on_trade_settled(won: bool, trade_rec: dict, current_balance: float) -> None:
    """Recovery ENTRY hook, called once per settled trade. Activates recovery
    only when a normal-mode (full-size) trade loses and we are not already in
    recovery; the target is the balance recorded just before that trade. A
    full-size loss also cancels any in-flight probation ramp (we are dropping
    back into the deeper recovery tier)."""
    if won or recovery.active:
        return
    if (trade_rec or {}).get("mode_at_entry") != "normal":
        return  # recovery/probation-mode losses and un-attributable trades skip
    if recovery.enter((trade_rec or {}).get("balance_before"), current_balance):
        probation.cancel()


def probation_record(won: bool, trade_rec: dict, current_balance: "float | None" = None) -> None:
    """Probation RAMP hook, called once per settled trade. Only probation-mode
    trades (entered while the ramp was active) advance or step the ramp."""
    if (trade_rec or {}).get("mode_at_entry") != "probation":
        return
    probation.record_result(bool(won), current_balance)


def recovery_winrate_record(won: bool, trade_rec: dict) -> None:
    """Feed the recovery win-rate restore: tally a settled trade that was ENTERED
    while recovery was active (mode_at_entry == 'recovery'). The trade whose loss
    ARMED recovery is stamped 'normal', so it correctly does not count here."""
    if (trade_rec or {}).get("mode_at_entry") != "recovery":
        return
    recovery.record_result(bool(won))


def stake_below_base(balance: float) -> bool:
    """True when the current per-trade stake is being held BELOW the full/base
    normal stake, because the active-mode fraction is reduced (standard recovery
    drops it to RECOVERY_TRADE_PCT, the probation ramp to a sub-full rung). Used
    as the precondition for the recovery win-rate restore.

    `balance` is accepted for call-site symmetry with the other sizing helpers;
    the answer depends only on the fractions, not on the dollar amount."""
    return active_trade_fraction() < effective_normal_trade_pct() - 1e-9


def maybe_winrate_restore(current_balance: float) -> bool:
    """Recovery win-rate restore (owner directive). While recovery is active and
    the stake is being held below the base, a strong recovery-scoped win rate
    (≥ RECOVERY_WINRATE_RESTORE_PCT over ≥ RECOVERY_WINRATE_MIN_TRADES settled
    recovery trades) returns straight to the full/original stake — bypassing the
    slow probation ramp. Returns True when it fires."""
    if not RECOVERY_WINRATE_RESTORE_ENABLED or not recovery.active:
        return False
    n = recovery.wins + recovery.losses
    if n < RECOVERY_WINRATE_MIN_TRADES:
        return False
    wr = recovery.winrate()
    if wr < RECOVERY_WINRATE_RESTORE_PCT:
        return False
    if not stake_below_base(current_balance):
        return False
    wins, losses = recovery.wins, recovery.losses
    recovery.clear_for_restore()          # exit recovery, no probation ramp
    probation.cancel()                    # belt-and-suspenders: ensure no ramp
    pct = effective_normal_trade_pct() * 100
    log.warning("Recovery WIN-RATE RESTORE │ WR %.0f%% (%dW/%dL) ≥ %.0f%% — back to "
                "full stake %.1f%% (no ramp).",
                wr * 100, wins, losses, RECOVERY_WINRATE_RESTORE_PCT * 100, pct)
    tg.send_status_message(
        f"🚀 RECOVERY WIN-RATE RESTORE\n"
        f"Win rate {wr*100:.0f}% ({wins}W/{losses}L) over your recovery trades "
        f"hit the {RECOVERY_WINRATE_RESTORE_PCT*100:.0f}% mark.\n"
        f"Returning to the full stake ({pct:.1f}% of balance) — no slow grind, "
        f"no ramp-back."
    )
    return True


# ─────────────────────────────────────────────────────────────────────────────
# SIGTERM
# ─────────────────────────────────────────────────────────────────────────────

def _sigterm_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    log.info("SIGTERM — graceful shutdown.")


signal.signal(signal.SIGTERM, _sigterm_handler)


# ─────────────────────────────────────────────────────────────────────────────
# BTC PRICE FEED
# ─────────────────────────────────────────────────────────────────────────────

_btc_backoff_until: float = 0.0


def fetch_btc_price() -> Optional[float]:
    global _btc_backoff_until
    if time.time() < _btc_backoff_until:
        return None
    try:
        r = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSD", timeout=5)
        if r.status_code == 200:
            result = r.json().get("result", {})
            if result:
                key   = next(iter(result))
                price = float(result[key]["c"][0])
                if price > 1000:
                    return price
    except Exception:
        pass
    try:
        r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
        if r.status_code == 200:
            price = float(r.json()["data"]["amount"])
            if price > 1000:
                return price
    except Exception:
        pass
    _btc_backoff_until = time.time() + 300
    log.debug("BTC feed failed — backing off 5 min")
    return None


# Newest sample's arrival time. The deques carry no timestamps, so without this
# a feed outage (both sources down → 5-min backoff) left compute_regime()
# trending on frozen data and the bot could still authorize a trade against a
# market that had since moved. Older than BTC_STALE_MAX_SECS → regime UNKNOWN.
_btc_last_ingest_ts: float = 0.0
BTC_STALE_MAX_SECS = _env_int("BTC_STALE_MAX_SECS", 180)


def ingest_btc_price() -> None:
    global _btc_last_ingest_ts
    price = fetch_btc_price()
    if price is None:
        return
    if btc_prices:
        prev = btc_prices[-1]
        if prev > 0:
            btc_returns.append((price - prev) / prev * 100.0)
    btc_prices.append(price)
    _btc_last_ingest_ts = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# REGIME ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _linear_regression(ys: list) -> Tuple[float, float, float]:
    n = len(ys)
    if n < 3:
        return 0.0, ys[0] if ys else 0.0, 0.0
    xs    = list(range(n))
    mx    = (n - 1) / 2.0
    my    = sum(ys) / n
    ss_xx = sum((x - mx) ** 2 for x in xs)
    ss_xy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    ss_yy = sum((y - my) ** 2 for y in ys)
    if ss_xx == 0 or ss_yy == 0:
        return 0.0, my, 0.0
    slope     = ss_xy / ss_xx
    intercept = my - slope * mx
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)
    return slope, intercept, r_squared


def compute_regime() -> Tuple[Regime, float, float]:
    if len(btc_prices) < MIN_PRICES_FOR_REGIME:
        return Regime.UNKNOWN, 0.0, 0.0

    # Staleness gate: a dead feed keeps the deques frozen at their last values,
    # which would otherwise keep reporting yesterday's trend as live. UNKNOWN
    # blocks all trading until fresh samples arrive.
    age = time.time() - _btc_last_ingest_ts
    if _btc_last_ingest_ts and age > BTC_STALE_MAX_SECS:
        log.warning("Regime │ BTC feed STALE (%.0fs > %ds) — no trade until fresh data.",
                    age, BTC_STALE_MAX_SECS)
        return Regime.UNKNOWN, 0.0, 0.0

    prices  = list(btc_prices)[-TREND_LOOKBACK:]
    returns = list(btc_returns)[-(TREND_LOOKBACK - 1):]

    realized_vol = sum(abs(r) for r in returns) / len(returns) if returns else 0.0

    if returns and max(abs(r) for r in returns[-3:]) > VOL_CIRCUIT_BREAKER:
        log.warning("VOL CIRCUIT │ spike %.3f%%", max(abs(r) for r in returns[-3:]))
        return Regime.HIGH_VOL, 0.0, realized_vol

    if realized_vol > VOLATILITY_CAP_PCT:
        log.info("Regime │ HIGH_VOL (vol=%.4f%%)", realized_vol)
        return Regime.HIGH_VOL, 0.0, realized_vol

    slope, _, r_squared = _linear_regression(prices)

    if r_squared >= R2_TREND_THRESHOLD:
        regime = Regime.TRENDING_UP if slope > 0 else Regime.TRENDING_DOWN
        log.info("Regime │ %s (R²=%.3f)", regime.value, r_squared)
        return regime, r_squared, realized_vol

    log.info("Regime │ RANGING (R²=%.3f)", r_squared)
    return Regime.RANGING, r_squared, realized_vol


# ─────────────────────────────────────────────────────────────────────────────
# VOLATILITY CIRCUIT BREAKER
# ─────────────────────────────────────────────────────────────────────────────

def check_vol_circuit() -> bool:
    global _vol_circuit_open, _vol_circuit_until

    if _vol_circuit_open:
        if time.time() > _vol_circuit_until:
            _vol_circuit_open = False
            log.info("Vol circuit CLOSED — resuming.")
        else:
            log.info("Vol circuit OPEN — %.1f min remaining.",
                     (_vol_circuit_until - time.time()) / 60.0)
            return True

    if len(btc_returns) < 3:
        return False

    recent   = list(btc_returns)[-6:]
    max_move = max(abs(r) for r in recent)
    if max_move > VOL_CIRCUIT_BREAKER:
        _vol_circuit_open  = True
        _vol_circuit_until = time.time() + 1800
        log.warning("Vol circuit OPENED — %.3f%%", max_move)
        tg.send_telegram_message(
            f"⚡ VOL CIRCUIT BREAKER OPENED\n"
            f"Max move: {max_move:.3f}% — trading paused 30 min."
        )
        return True

    return False


# ─────────────────────────────────────────────────────────────────────────────
# MOMENTUM SIGNAL
# ─────────────────────────────────────────────────────────────────────────────

def compute_momentum(ob_direction: str) -> Tuple[str, float]:
    if len(btc_prices) < MOMENTUM_LOOKBACK + 1:
        return "NEUTRAL", -NEUTRAL_ACCURACY_DRAG

    window  = list(btc_prices)[-(MOMENTUM_LOOKBACK + 1):]
    earlier = window[0]
    recent  = window[-1]
    if earlier <= 0:
        return "NEUTRAL", -NEUTRAL_ACCURACY_DRAG

    move_pct = (recent - earlier) / earlier * 100.0
    slope, _, local_r2 = _linear_regression(window)
    ob_dir   = ob_direction.upper()

    # v9.3.3: a trend is REAL when BTC moves CONSISTENTLY (regression R² over the
    # momentum window) OR far enough in MAGNITUDE. compute_regime() flags TRENDING
    # by R² alone, so a smooth, gentle drift (high R², small %-move) is genuinely
    # trending — but the old pure-magnitude test mislabeled it NEUTRAL and the
    # AGREE gate blocked every trade (2026-06-23/24: 0 trades). BTC is "flat" only
    # when it is BOTH inconsistent (low R²) AND small (sub-threshold) — the chop
    # the doctrine rejects. This keeps that guarantee while confirming real trends.
    is_trending = (local_r2 >= MOMENTUM_R2_MIN) or (abs(move_pct) >= MOMENTUM_THRESH_PCT)
    if not is_trending:
        return "NEUTRAL", -NEUTRAL_ACCURACY_DRAG

    # Direction from the regression slope (consistent with compute_regime), with
    # the endpoint delta as a tiebreaker when the slope is exactly flat.
    if slope > 0 or (slope == 0 and move_pct > 0):
        btc_dir = "YES"
    elif slope < 0 or (slope == 0 and move_pct < 0):
        btc_dir = "NO"
    else:
        return "NEUTRAL", -NEUTRAL_ACCURACY_DRAG

    if btc_dir == ob_dir:
        magnitude_scale = min(2.0, abs(move_pct) / MOMENTUM_THRESH_PCT)
        return "AGREE", MOMENTUM_ACCURACY_LIFT * magnitude_scale

    return "CONFLICT", 0.0


def momentum_gate_ok(momentum_verdict: str) -> bool:
    """DOCTRINE LAYER 7 — the AGREE-required momentum gate.

    A trade requires BTC spot momentum to EXPLICITLY AGREE with the order-book
    direction. When REQUIRE_AGREE_MOMENTUM is true (default), both CONFLICT and
    NEUTRAL are rejections.

    NEUTRAL = flat BTC = no directional confirmation. Trading on the order book
    alone is doctrine "What This Bot Will Never Do" item 1 — the exact setup
    post-mortemed in v6.0.0 (50% loss, 2026-03-27/28) and the cause of the
    2026-06-20→22 bleed, in which all 6 trades fired on BTC=NEUTRAL.

    Applies in EVERY sizing mode — recovery included. Recovery's exit is
    balance-driven (RecoveryState.maybe_exit, checked every cycle), never a
    reason to trade unconfirmed setups. A calm, all-NEUTRAL session producing
    zero trades is correct behaviour.
    """
    if not REQUIRE_AGREE_MOMENTUM:
        return True
    return momentum_verdict == "AGREE"


# ─────────────────────────────────────────────────────────────────────────────
# ORDER BOOK ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def _parse_ob_levels(levels: list, lo: float, hi: float) -> Tuple[float, int]:
    depth = 0.0
    count = 0
    for entry in levels:
        try:
            price = float(entry[0])
            size  = float(entry[1])
            if lo <= price <= hi and size > 0:
                depth += size
                count += 1
        except Exception:
            pass
    return depth, count


def analyze_order_book(ob_data: dict, yes_mid: int) -> Optional[dict]:
    ob_fp      = ob_data.get("orderbook_fp", {})
    yes_levels = ob_fp.get("yes_dollars", [])
    no_levels  = ob_fp.get("no_dollars",  [])

    near  = 10
    y_lo  = (yes_mid - near) / 100.0
    y_hi  = (yes_mid + near) / 100.0
    n_mid = (100 - yes_mid) / 100.0
    n_lo  = n_mid - near / 100.0
    n_hi  = n_mid + near / 100.0

    yes_depth, yes_lc = _parse_ob_levels(yes_levels, y_lo, y_hi)
    no_depth,  no_lc  = _parse_ob_levels(no_levels,  n_lo, n_hi)
    total = yes_depth + no_depth

    if total < MIN_OB_DEPTH:
        log.info("OB │ depth $%.0f < min $%.0f", total, MIN_OB_DEPTH)
        return None

    if yes_lc == 0 or no_lc == 0:
        log.info("OB │ ghost book (YES:%d NO:%d levels)", yes_lc, no_lc)
        return None

    yr = yes_depth / total
    nr = no_depth  / total

    if total >= 5000:
        eff_thresh = max(0.58, OB_IMBALANCE_THRESH - 0.04)
    elif total >= 500:
        eff_thresh = max(0.58, OB_IMBALANCE_THRESH - 0.02)
    elif total < 20:
        eff_thresh = min(0.80, OB_IMBALANCE_THRESH + 0.08)
    else:
        eff_thresh = OB_IMBALANCE_THRESH

    # v10.1.0: an UPPER bound as well as a lower one. The pre-10.1.0 code only
    # rejected a literally empty opposite side (the ghost-book check above), so a
    # 99.8%/0.2% book passed — and compute_confidence scores imbalance linearly
    # (corr(OB%, conf) = +0.92 across the 65 audited signals), so that book drew
    # the audited window's highest confidence (95) and largest stake, and lost
    # all of it. Near-total one-sidedness on a thin 15-minute market means the
    # other side is one stale level, which is a liquidity condition, not
    # conviction. Reject it rather than rewarding it as maximum edge.
    if max(yr, nr) > OB_IMBALANCE_MAX:
        log.info("OB │ one-sided book %.1f%% > max %.1f%% — illiquid, not signal",
                 max(yr, nr) * 100, OB_IMBALANCE_MAX * 100)
        return None

    if yr >= eff_thresh:
        direction = "YES"
        imbalance = yr
    elif nr >= eff_thresh:
        direction = "NO"
        imbalance = nr
    else:
        log.info("OB │ no dominant side (YES:%.1f%% NO:%.1f%% thresh:%.1f%%)",
                 yr * 100, nr * 100, eff_thresh * 100)
        return None

    log.info("OB │ %s %.1f%% │ $%.0f │ thresh=%.1f%%",
             direction, imbalance * 100, total, eff_thresh * 100)

    return {
        "direction":   direction,
        "imbalance":   imbalance,
        "total_depth": total,
        "yes_depth":   yes_depth,
        "no_depth":    no_depth,
        "yes_lc":      yes_lc,
        "no_lc":       no_lc,
        "eff_thresh":  eff_thresh,
    }


def check_ob_trend(ticker: str, direction: str, imbalance: float) -> bool:
    now  = time.time()
    prev = _prev_ob.get(ticker)
    _remember_prev_ob(ticker, (direction, imbalance, now), now)

    if prev is None:
        return True

    prev_dir, prev_imb, prev_ts = prev
    if now - prev_ts > 600:
        return True

    if direction == prev_dir and imbalance < prev_imb - 0.10:
        log.info("OB trend │ fading %.1f%%→%.1f%% — blocking",
                 prev_imb * 100, imbalance * 100)
        return False

    return True


def regime_direction(regime: Regime) -> Optional[str]:
    """Map a trend regime to the contract side it favors.

    For these BTC "above-strike" markets a rising price (TRENDING_UP) settles
    YES and a falling price (TRENDING_DOWN) settles NO. Non-directional regimes
    (RANGING/HIGH_VOL/UNKNOWN) return None and never reach this check because
    run_decision already gates them out.
    """
    if regime == Regime.TRENDING_UP:
        return "YES"
    if regime == Regime.TRENDING_DOWN:
        return "NO"
    return None


def regime_agrees(regime: Regime, ob_direction: str) -> bool:
    """The order-book side must point the same way as the measured trend.

    The single largest source of losses (2026-06-19: both losing trades) was
    betting the order-book imbalance *against* the regression trend — NO in an
    uptrend, YES in a downtrend. Order-book imbalance on thin 15-minute crypto
    markets is a weak, often contrarian signal; the regression trend is the real
    driver of where price settles. When they conflict, stand aside.
    """
    favored = regime_direction(regime)
    return favored is None or favored == ob_direction.upper()


# ─────────────────────────────────────────────────────────────────────────────
# BAYESIAN PROBABILITY MODEL
# ─────────────────────────────────────────────────────────────────────────────

def bayesian_win_prob(
    ob: dict,
    momentum_verdict: str,
    momentum_adj: float,
    regime: Regime,
    r_squared: float,
    realized_vol: float,
) -> Tuple[float, float]:
    # Time-of-day learned prior: a bucket with a poor realized win rate (the
    # mean-reverting afternoon) supplies a lower prior, which flows straight
    # through to a lower edge and gates the trade out. Empty bucket ==
    # OB_BASE_ACCURACY, so behaviour is unchanged until outcomes accumulate.
    bucket          = bucket_stats.key_now()
    prior, bucket_n = bucket_stats.prior_for(bucket)

    if regime in (Regime.TRENDING_UP, Regime.TRENDING_DOWN):
        r2_bonus   = (r_squared - R2_TREND_THRESHOLD) * 0.10
        regime_adj = 0.02 + r2_bonus
    else:
        regime_adj = 0.0

    # v9.2.0: the order-book imbalance is the bot's primary directional signal,
    # yet it never fed the win-probability — win_prob was a near-constant ~0.68
    # every scan, so "edge" was driven purely by how cheap the contract was (a
    # 36c against-trend YES scored a fake 31% edge on 2026-06-19). Reward genuine
    # book dominance over the trigger threshold so a marginally-imbalanced book
    # scores lower than a lopsided one. Capped so it cannot dominate the prior.
    eff_thresh    = ob.get("eff_thresh", OB_IMBALANCE_THRESH)
    imbalance_adj = min(0.06, max(0.0, ob["imbalance"] - eff_thresh) * 0.30)

    depth_adj = 0.0
    if ob["total_depth"] > 500:
        depth_adj = min(0.02, math.log10(ob["total_depth"] / 500) * 0.02)

    vol_penalty = min(0.04, realized_vol / VOLATILITY_CAP_PCT * 0.04)

    win_prob = max(0.50, min(0.92,
        prior + momentum_adj + regime_adj + imbalance_adj + depth_adj - vol_penalty
    ))

    log.info("WinProb │ prior=%.3f mom=%.3f regime=%.3f imb=%.3f depth=%.3f vol=-%.3f → %.3f │ bucket=%s n=%d",
             prior, momentum_adj, regime_adj, imbalance_adj, depth_adj, vol_penalty,
             win_prob, bucket, bucket_n)
    # v10.1.0: the bucket prior is returned alongside so market_anchored_win_prob
    # can isolate what the SIGNALS contributed (win_prob - prior) from the base
    # rate they were layered onto. Note that `regime_adj` carries an
    # unconditional +0.02 and `depth_adj` a flat +0.02 for any book over $500, so
    # ~4pp of every "edge" this model reports is a constant, not a measurement —
    # which is most of why a 6% MIN_EDGE_PCT gate almost never bound.
    return win_prob, prior


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE SCORING
# ─────────────────────────────────────────────────────────────────────────────

def compute_confidence(
    ob: dict,
    regime: Regime,
    r_squared: float,
    momentum_verdict: str,
    win_prob: float,
    mins_remaining: float,
    session_score: int,
) -> float:
    thresh    = ob["eff_thresh"]
    imb_pts   = max(0.0, (ob["imbalance"] - thresh) / (1.0 - thresh)) * 25.0
    depth_pts = min(15.0, math.log10(max(1, ob["total_depth"] / MIN_OB_DEPTH)) * 10.0)

    regime_map = {
        Regime.TRENDING_UP:   20.0,
        Regime.TRENDING_DOWN: 20.0,
        Regime.RANGING:        0.0,
        Regime.HIGH_VOL:     -20.0,
        Regime.UNKNOWN:        0.0,
    }
    regime_pts = regime_map.get(regime, 0.0)
    if regime in (Regime.TRENDING_UP, Regime.TRENDING_DOWN):
        regime_pts += min(5.0, (r_squared - R2_TREND_THRESHOLD) * 15.0)

    # v9.3.0: NEUTRAL restored 8.0 → 2.0 (doctrine Layer 8: BTC momentum "only
    # counts if AGREE"). The v9.0.6 bump to 8.0 was the third leg of the
    # NEUTRAL bleed: the 2026-06-20 08:30 trade scored Conf=65 EXACTLY on
    # mom=8.0; at 2.0 it is 59 < 65 and never trades. With momentum_gate_ok
    # this is belt-and-suspenders, but it keeps the score truthful.
    momentum_map = {"AGREE": 15.0, "NEUTRAL": 2.0, "CONFLICT": -20.0}
    momentum_pts = momentum_map.get(momentum_verdict, 0.0)

    prob_pts = max(0.0, (win_prob - 0.50) / 0.42 * 15.0)

    time_pts = min(10.0, max(0.0,
        (mins_remaining - MIN_MINUTES_TO_EXPIRY) /
        max(0.1, 10.0 - MIN_MINUTES_TO_EXPIRY) * 10.0
    ))

    total = max(0.0, min(100.0,
        imb_pts + depth_pts + regime_pts + momentum_pts + prob_pts + time_pts
    ))

    log.info("Conf │ imb=%.1f depth=%.1f regime=%.1f mom=%.1f prob=%.1f time=%.1f → %.0f",
             imb_pts, depth_pts, regime_pts, momentum_pts, prob_pts, time_pts, total)
    return total


# ─────────────────────────────────────────────────────────────────────────────
# EDGE & SIZING
# ─────────────────────────────────────────────────────────────────────────────

def calc_edge(win_prob: float, contract_price_cents: int) -> float:
    """Expected value per contract, i.e. per $1 of payout.

    With MARKET_ANCHOR_ENABLED this is exactly the model's claimed advantage in
    percentage points over the quoted price: for win_prob = price/100 + lift the
    algebra collapses to `lift` at every price, which is what makes MIN_EDGE_PCT
    a price-neutral bar. See market_anchored_win_prob.
    """
    if contract_price_cents <= 0 or contract_price_cents >= 100:
        return 0.0
    net   = (100 - contract_price_cents) / 100.0
    stake = contract_price_cents / 100.0
    return (win_prob * net) - ((1.0 - win_prob) * stake)


def edge_return_on_risk(edge: float, contract_price_cents: int) -> float:
    """`edge` re-expressed per DOLLAR STAKED rather than per contract.

    calc_edge divides expected value by the payout ($1); this divides it by the
    cash actually at risk (the price). It is the figure that compounds a
    bankroll, and it is what MIN_EDGE_ROR gates on.
    """
    if contract_price_cents <= 0:
        return 0.0
    return edge / (contract_price_cents / 100.0)


def market_anchored_win_prob(model_prob: float, model_base: float,
                             contract_price_cents: int) -> float:
    """Re-express the model's output as an adjustment to the MARKET's own estimate.

    The quoted price of a liquid contract is a probability, and the 2026-07-23→26
    audit showed it was a better one than the model's: over the 8 settled trades
    the model's mean claim was 72.5% against a realized 37.5%, for a Brier score
    of 0.342 versus 0.217 for simply believing the price. So the price becomes
    the base rate and the model may only move it by the incremental information
    its signals actually added — `model_prob - model_base`, the sum of the
    momentum / regime / imbalance / depth terms bayesian_win_prob layered on top
    of the bucket prior — clamped to ±MAX_MODEL_EDGE_PP.

    Returns model_prob unchanged when the anchor is disabled. See the config
    block for the full rationale.
    """
    if not MARKET_ANCHOR_ENABLED:
        return model_prob
    if contract_price_cents <= 0 or contract_price_cents >= 100:
        return model_prob
    market_p = contract_price_cents / 100.0
    lift     = max(-MAX_MODEL_EDGE_PP, min(MAX_MODEL_EDGE_PP, model_prob - model_base))
    anchored = max(0.01, min(0.99, market_p + lift))
    log.info("Anchor │ model=%.3f base=%.3f lift=%+.3f │ market=%.2f → p=%.3f",
             model_prob, model_base, lift, market_p, anchored)
    return anchored


def size_contracts(bet_dollars: float, limit_cents: int,
                   balance: float) -> Tuple[int, str]:
    """Resolve a dollar stake into a whole number of contracts.

    Returns (count, reason). count == 0 means the signal is unsizeable and the
    caller must reject it BEFORE announcing a trade — the pre-10.1.0 code did
    this check inside place_order, after the edge justification had already been
    logged and pushed to Telegram, which is how 55 of 65 audited signals became
    phantom entries in the log.

    Contracts are integral, so a stake below one contract's price floors to zero.
    Rounding DOWN is what keeps the configured stake percentage a true ceiling at
    every account size: the order is always ≤ the intended stake, so a small
    balance can never be pushed into risking more than was asked for. The cost is
    granularity — a $20 balance wanting $2.00 of a 67c contract gets 2 contracts
    ($1.34, 6.7% not 10%), while a $20,000 balance lands on 10.00% exactly. That
    is the market (you cannot buy 2.98 contracts), not a policy choice.

    MIN_ORDER_ROUNDUP (default OFF since v10.3.0) restores the old behaviour of
    rounding a sub-contract stake UP to a single contract whenever it still fits
    inside the hard MAX_TRADE_PCT ceiling and the cash on hand. That trades more
    often on small balances, but it is the one path that can risk MORE than the
    configured fraction — see the config note above.
    """
    if limit_cents <= 0:
        return 0, "no limit price"

    unit_cost = limit_cents / 100.0
    count     = int((bet_dollars * 100) / limit_cents)
    if count >= 1:
        return count, "sized"

    if not MIN_ORDER_ROUNDUP:
        return 0, (f"stake ${bet_dollars:.2f} < 1 contract @ {limit_cents}c — "
                   f"rounding up would risk {unit_cost/max(bet_dollars, 1e-9)*100:.0f}% "
                   f"of the configured stake")

    ceiling = round(MAX_TRADE_PCT * tradeable_balance(balance), 2)
    if unit_cost > ceiling:
        return 0, (f"1 contract @ {limit_cents}c = ${unit_cost:.2f} > "
                   f"max {MAX_TRADE_PCT*100:.0f}% ceiling ${ceiling:.2f}")
    if unit_cost > tradeable_balance(balance):
        return 0, (f"1 contract @ {limit_cents}c = ${unit_cost:.2f} > "
                   f"tradeable ${tradeable_balance(balance):.2f}")

    return 1, (f"rounded up to 1 contract (${unit_cost:.2f}); "
               f"stake ${bet_dollars:.2f} under one contract @ {limit_cents}c")


def depth_covers_order(total_depth: float, order_cost: float) -> bool:
    """Can the visible book absorb this order MIN_DEPTH_STAKE_MULT times over?

    The balance-independence half of the liquidity gate. MIN_OB_DEPTH is an
    absolute floor answering "is this market worth trading at all"; this answers
    "is it worth trading at OUR size", and because it is stated as a multiple of
    the order it is the identical rule for a $2 trade and a $10,000 one. Without
    it, the flat $75 floor gave a $20 account 37x cover and a $100,000 account
    0.01x — only the large account ever carried fill risk.

    MIN_DEPTH_STAKE_MULT <= 0 disables the check (always True)."""
    if MIN_DEPTH_STAKE_MULT <= 0:
        return True
    return total_depth >= order_cost * MIN_DEPTH_STAKE_MULT


def kelly_bet(win_prob: float, contract_price_cents: int, balance: float) -> float:
    if contract_price_cents <= 0 or contract_price_cents >= 100:
        return 0.0
    b          = (100 - contract_price_cents) / float(contract_price_cents)
    full_kelly = max(0.0, (b * win_prob - (1.0 - win_prob)) / b)
    # v10.0.0: PERCENTAGE stake. Kelly is used ONLY as an edge gate — a positive
    # full_kelly means the bet has positive expectancy. The stake itself is the
    # active-mode FRACTION of the current balance (active_trade_size), so it
    # compounds up as the account grows and de-risks as it shrinks. The clamps are
    # the hard MAX_TRADE_PCT ceiling and the cash on hand.
    if full_kelly <= 0.0:
        return 0.0
    #
    # v10.2.0: this IS the stake. The laddering overlay that used to scale it by a
    # rolling-win-rate multiplier (up to 2×) is retired — nothing multiplies the
    # stake up any more, so the dollars at risk move only when the balance does.
    size       = active_trade_size(balance)   # fraction × balance, ≤ MAX_TRADE_PCT
    max_dollars = round(MAX_TRADE_PCT * balance, 2)
    return round(min(size, max_dollars, balance), 2)


# ─────────────────────────────────────────────────────────────────────────────
# STATISTICAL PERFORMANCE GUARD
# ─────────────────────────────────────────────────────────────────────────────

def wilson_lower_bound(wins: int, total: int, z: float = 1.645) -> float:
    if total < 10:
        return 0.0
    p      = wins / total
    denom  = 1.0 + z ** 2 / total
    center = (p + z ** 2 / (2.0 * total)) / denom
    spread = (z * (p * (1.0 - p) / total + z ** 2 / (4.0 * total ** 2)) ** 0.5) / denom
    return max(0.0, center - spread)


def wilson_confidence(wins: int, total: int, z: float = 1.96) -> Tuple[float, float, float]:
    if total == 0:
        return 0.0, 0.0, 0.0
    p      = wins / total
    denom  = 1.0 + z ** 2 / total
    center = (p + z ** 2 / (2.0 * total)) / denom
    spread = (z * (p * (1.0 - p) / total + z ** 2 / (4.0 * total ** 2)) ** 0.5) / denom
    return (round(p * 100, 1),
            round(max(0, center - spread) * 100, 1),
            round(min(1, center + spread) * 100, 1))


def update_live_prior() -> None:
    global _live_prior
    total = live_wins + live_losses
    if total < 10:
        return
    empirical   = live_wins / total
    weight      = min(1.0, total / 50.0)
    _live_prior = OB_BASE_ACCURACY * (1.0 - weight) + empirical * weight
    log.debug("Prior → %.3f (n=%d)", _live_prior, total)


def perf_guard_record(won: bool) -> None:
    """Feed one settled outcome to the performance guard's rolling window.

    Separate from live_wins/live_losses on purpose: those are DAILY state that
    maybe_roll_session_day zeroes at every UTC midnight, which is why the guard
    that read them never once reached its 20-trade sample in the audited window.
    """
    _perf_window.append(bool(won))


def performance_guard() -> bool:
    """Block new entries while the realized win rate is statistically bad — a
    Wilson lower bound below 50% over the last PERF_GUARD_WINDOW settled trades.

    Pre-10.1.0 this scored live_wins/live_losses, which reset at every UTC
    rollover. At the bot's ~2 trades/day that counter never approached
    MIN_SAMPLE_TRADES (20), so across 2026-07-23→26 the bound was never
    evaluated once — every settle line logged "LB=0.0%" and the only statistical
    circuit breaker in the engine was, in practice, dead code.

    The window here is rolling and survives day boundaries, so it actually fills.
    The daily reset it replaces was there to stop the guard latching forever
    (a blocked bot takes no trades, so a sub-50% bound could never heal), and a
    rolling window on its own has exactly that deadlock. So the guard is a
    TIME-BOUNDED breaker instead: tripping it blocks for PERF_GUARD_PAUSE_SECS,
    after which the window is cleared and the bot re-samples from scratch.
    Blocks, cools off, re-tests — it can slow the bot down but never wedge it.
    """
    global _perf_guard_until

    now = time.time()
    if _perf_guard_until:
        if now < _perf_guard_until:
            log.info("PERF GUARD │ paused %.0f min remaining",
                     (_perf_guard_until - now) / 60.0)
            return False
        _perf_guard_until = 0.0
        _perf_window.clear()          # fresh sample, or the block would latch
        log.warning("PERF GUARD │ cool-off over — resampling.")
        return True

    total = len(_perf_window)
    if total < min(MIN_SAMPLE_TRADES, PERF_GUARD_WINDOW):
        return True
    wins = sum(1 for w in _perf_window if w)
    wlb  = wilson_lower_bound(wins, total)
    if wlb < 0.50:
        _perf_guard_until = now + PERF_GUARD_PAUSE_SECS
        log.warning("PERF GUARD │ Wilson LB %.1f%% < 50%% over last %d "
                    "(%dW/%dL) — pausing %.1fh.",
                    wlb * 100, total, wins, total - wins,
                    PERF_GUARD_PAUSE_SECS / 3600.0)
        tg.send_telegram_message(
            f"🛑 PERFORMANCE GUARD\n"
            f"Win rate {wins}/{total} over the last {total} settled trades — the "
            f"95% lower bound is {wlb*100:.0f}%, below the 50% break-even floor.\n"
            f"Pausing new entries for {PERF_GUARD_PAUSE_SECS/3600:.0f}h, then "
            f"re-sampling from scratch."
        )
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# SESSION QUALITY
# ─────────────────────────────────────────────────────────────────────────────

def get_session_score() -> int:
    return SESSION_QUALITY.get(datetime.now(timezone.utc).hour, 50)


# ─────────────────────────────────────────────────────────────────────────────
# PORTFOLIO / BALANCE
# ─────────────────────────────────────────────────────────────────────────────

def get_live_balance(allow_cached_zero: bool = True) -> float:
    global _last_known_balance
    try:
        data  = _get("/portfolio/balance")
        bal_d = data.get("balance_dollars")
        if bal_d is not None:
            try:
                bal = float(bal_d)
            except Exception:
                bal = (data.get("balance", 0) or 0) / 100.0
        else:
            bal = (data.get("balance", 0) or 0) / 100.0
        _last_known_balance = bal
        return bal
    except Exception as e:
        if not allow_cached_zero and _last_known_balance <= 0.0:
            log.error("Balance fetch failed, no cache: %s", e)
            raise
        log.warning("Balance fetch failed: %s — cached $%.2f", e, _last_known_balance)
        return _last_known_balance


def _coerce_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None


def _extract_realized_dollars(rec: dict, trade_cost: Optional[float] = None) -> Optional[float]:
    """
    Extract realized PnL in dollars from a Kalshi settlement record.

    v9.0.7: REWRITTEN against the actual KXBTC15M settlement schema observed in
    the 2026-06-08 live logs. The real record has NO realized_pnl/profit field.
    Its keys are:
        event_ticker, fee_cost, market_result, no_count_fp,
        no_total_cost_dollars, revenue, settled_time, ticker, value,
        yes_count_fp, yes_total_cost_dollars

    Reconstruction:
        pnl = (revenue / 100) - yes_total_cost_dollars - no_total_cost_dollars - fee_cost

    `revenue` is returned in CENTS by the Kalshi settlements endpoint (same unit
    as the balance endpoint which requires /100). The *_dollars cost fields and
    fee_cost are returned in dollars. Dividing revenue by 100 before subtracting
    the dollar-denominated costs prevents the ~100× profit inflation bug.

    Direct PnL fields are still tried first in case Kalshi adds them later.
    """
    # 1) Direct PnL fields (future-proofing; absent in current schema)
    for k in ("realized_pnl_dollars", "settlement_pnl_dollars", "pnl_dollars"):
        v = _coerce_float(rec.get(k))
        if v is not None:
            return v
    for k in ("realized_pnl_cents", "realized_pnl", "settlement_pnl", "pnl"):
        v = _coerce_float(rec.get(k))
        if v is not None:
            # legacy integer-cent fields divided by 100; dollar fields handled above
            return v / 100.0 if k.endswith("_cents") else v

    # 2) Real KXBTC15M reconstruction: revenue - total cost - fees
    # Kalshi settlement API returns revenue in cents (same as balance endpoint);
    # cost/fee fields named *_dollars are already in dollars.
    revenue = _coerce_float(rec.get("revenue"))
    if revenue is not None:
        revenue /= 100.0
        yes_cost = _coerce_float(rec.get("yes_total_cost_dollars")) or 0.0
        no_cost  = _coerce_float(rec.get("no_total_cost_dollars"))  or 0.0
        fee      = _coerce_float(rec.get("fee_cost")) or 0.0
        total_cost = yes_cost + no_cost
        if total_cost > 0:
            return round(revenue - total_cost - fee, 4)
        # No cost recorded on either side. If revenue is also 0 this is an
        # unfilled/expired maker order (no position taken) → return 0.0 so the
        # caller's NO-FILL branch handles it instead of counting a phantom loss.
        if revenue == 0.0:
            return 0.0
        # Cost missing but revenue present — fall back to the matched trade cost.
        if trade_cost is not None and trade_cost > 0:
            return round(revenue - trade_cost - fee, 4)
        # Revenue present, no cost anywhere: treat as win for W/L counting only.
        return 1.0

    # 3) market_result as a final win/loss signal when no economics present
    mr = str(rec.get("market_result", "")).lower()
    if mr in ("yes", "no"):
        # Without held-side info here we can only flag presence; caller matches side.
        # Return None so the caller logs missing economics rather than miscounting.
        return None

    return None


def _extract_ticker(rec: dict) -> str:
    for k in ("market_ticker", "ticker", "event_ticker"):
        v = rec.get(k)
        if v:
            return str(v)
    return ""


def _is_post_boot(rec: dict) -> bool:
    """
    True if a settlement record was created at/after this process's boot time.

    v9.0.8: the /portfolio/settlements endpoint ignores created_since and always
    returns the account-wide last 100 settlements. The unmatched-settlement
    branch in resolve_open_orders() counts these toward live_wins/live_losses so
    RECOVERY can exit on pre-restart trades — but with no time gate it ingests
    days of account history on every boot. In the 2026-06-11 LIVE session this
    seeded WR=28/70 (Wilson LB 30.9%), permanently failing performance_guard()'s
    50% floor and freezing the bot: 1307 PERF GUARD warnings, zero trades.

    Gate: only count a settlement whose timestamp is >= _session_start_ts. A
    pre-restart trade still in flight settles AFTER boot, so it is preserved;
    trades settled entirely before this boot (account history) are excluded.
    Records with a missing/unparseable timestamp are treated as NOT post-boot
    (conservative — never back-count ambiguous history).
    """
    if not _session_start_ts:
        return False
    rec_ts = (rec.get("settled_time") or rec.get("created_time")
              or rec.get("timestamp") or "")
    if not rec_ts:
        return False
    try:
        rec_ts = str(rec_ts).replace("Z", "+00:00")
        boot_ts = _session_start_ts.replace("Z", "+00:00")
        return datetime.fromisoformat(rec_ts) >= datetime.fromisoformat(boot_ts)
    except Exception:
        return False


def _fetch_settled_records(since_ts: str) -> list:
    try:
        data = _get("/portfolio/settlements", {"limit": 100})
        recs = data.get("settlements") or data.get("market_settlements") or []
        if recs:
            return recs
    except Exception as e:
        log.debug("Settlements endpoint failed: %s", e)
    try:
        data = _get("/portfolio/positions", {
            "limit": 100,
            "settlement_status": "settled",
            "created_since": since_ts,
        })
        return data.get("market_positions", [])
    except Exception as e:
        log.warning("Both settlement endpoints failed: %s", e)
        return []


# ─────────────────────────────────────────────────────────────────────────────
# RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def resolve_open_orders() -> None:
    global paper_balance, paper_daily_pnl, consecutive_losses
    global running_pnl, live_wins, live_losses, streak_pause_until
    global live_daily_realized

    if not open_orders and not DEMO_MODE:
        pass
    elif not open_orders and DEMO_MODE:
        return

    if DEMO_MODE:
        now = time.time()
        for oid in list(open_orders.keys()):
            trade = open_orders[oid]
            if now - trade.get("placed_at", now) < DEMO_SETTLE_INTERVAL_SECS:
                continue
            open_orders.pop(oid)
            ticker    = trade.get("ticker", "")
            active_tickers.discard(ticker)
            count     = trade.get("count", 0)
            cost      = trade.get("cost", 0.0)
            side      = trade.get("side", "YES").upper()
            entry_btc = trade.get("btc_entry_price", 0)
            cur_btc   = fetch_btc_price()

            if entry_btc > 0 and cur_btc and cur_btc > 1000:
                btc_up = cur_btc > entry_btc
                won    = btc_up if side == "YES" else not btc_up
                sim    = "btc"
            else:
                won = random.random() < _live_prior
                sim = "rng"

            if won:
                paper_balance   += count
                trade_pnl        = round(count - cost, 2)
                paper_daily_pnl += trade_pnl
            else:
                trade_pnl        = round(-cost, 2)
                paper_daily_pnl += trade_pnl

            running_pnl += trade_pnl
            result = "win" if won else "loss"
            for t in trade_history:
                if t.get("order_id") == oid:
                    t["result"] = result
                    t["pnl"]    = round(trade_pnl, 4)
                    break

            if won:
                consecutive_losses = 0
                live_wins += 1
                tg.send_win_notification(
                    profit=trade_pnl, balance=paper_balance,
                    daily_pnl=paper_daily_pnl,
                    ticker=ticker, direction=trade.get("side", "?"),
                    wins=live_wins, losses=live_losses,
                )
            else:
                consecutive_losses += 1
                live_losses += 1
                if consecutive_losses >= MAX_CONSEC_LOSSES:
                    streak_pause_until = time.time() + STREAK_PAUSE_SECS
                tg.send_loss_notification(
                    loss=abs(trade_pnl), balance=paper_balance,
                    daily_pnl=paper_daily_pnl,
                    ticker=ticker, direction=trade.get("side", "?"),
                    streak=consecutive_losses,
                    wins=live_wins, losses=live_losses,
                )

            perf_guard_record(won)
            bucket_stats.record(trade.get("entry_bucket"), won)
            lifetime.record(DEMO_MODE, won, trade_pnl)   # persistent all-time tally
            # Recovery ENTRY hook: a full-size loss arms recovery (uses this
            # trade's recorded pre-trade balance as the target). paper_balance is
            # already updated above for this settlement.
            on_trade_settled(won, trade, paper_balance)
            # Probation RAMP hook: a probation-mode trade advances/steps the ramp.
            probation_record(won, trade, paper_balance)
            # Recovery win-rate restore feed: tally trades taken WHILE in recovery.
            recovery_winrate_record(won, trade)

            log.info("📋 PAPER SETTLED │ %s │ %s │ %s │ sim=%s │ bal=$%.2f",
                     ticker[-15:], side, result.upper(), sim, paper_balance)

            # The day's goal is checked HERE, on the settlement that banks the
            # profit, so the target halt lands the moment it is hit rather than
            # one poll interval later.
            daily_profit_target_check(paper_balance)

        update_live_prior()
        return

    # ── Live ──────────────────────────────────────────────────────────────────
    try:
        since_ts = _session_start_ts or (
            datetime.now(timezone.utc) - timedelta(hours=2)
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        records = _fetch_settled_records(since_ts)
        log.info("RESOLVE │ %d settled, %d open, %d processed",
                 len(records), len(open_orders), len(_processed_settlement_ids))

        ticker_to_oid: dict = {}
        for oid, trade in open_orders.items():
            tk = trade.get("ticker", "")
            if tk:
                ticker_to_oid[tk]         = oid
                ticker_to_oid[tk.upper()] = oid

        for rec in records:
            rec_ticker  = _extract_ticker(rec)
            rec_created = (rec.get("created_time") or rec.get("settled_time")
                           or rec.get("timestamp", ""))
            rec_id      = f"{rec_ticker}:{rec_created}"

            if rec_id in _processed_settlement_ids:
                continue

            matched_oid = (ticker_to_oid.get(rec_ticker)
                           or ticker_to_oid.get(rec_ticker.upper()))
            if not matched_oid:
                for oid, trade in list(open_orders.items()):
                    if trade.get("ticker", "").upper() == rec_ticker.upper():
                        matched_oid = oid
                        break

            _remember_settlement_id(rec_id)

            if not matched_oid:
                # Pre-restart trade: count toward W/L so RECOVERY can exit.
                # v9.0.8: ONLY if settled at/after boot. The settlements endpoint
                # returns account-wide history (created_since is ignored), so an
                # ungated count here ingests days of stale W/L and deadlocks the
                # Wilson performance guard. In-flight pre-restart trades settle
                # after boot and are still counted; account history is skipped.
                if not _is_post_boot(rec):
                    continue
                pnl_d = _extract_realized_dollars(rec)
                if pnl_d is not None and pnl_d != 0.0:
                    if pnl_d > 0:
                        live_wins += 1
                        log.info("UNMATCHED WIN │ %s │ $%.2f (pre-restart)",
                                 rec_ticker[-15:], pnl_d)
                    else:
                        live_losses += 1
                        consecutive_losses += 1
                        if consecutive_losses >= MAX_CONSEC_LOSSES:
                            streak_pause_until = time.time() + STREAK_PAUSE_SECS
                        log.info("UNMATCHED LOSS │ %s │ $%.2f (pre-restart)",
                                 rec_ticker[-15:], pnl_d)
                    # It settled today, so it belongs in today's realized P&L
                    # (the figure the alerts, /pnl, and the daily report show).
                    live_daily_realized += pnl_d
                    perf_guard_record(pnl_d > 0)
                    lifetime.record(DEMO_MODE, pnl_d > 0, pnl_d)   # persistent all-time
                    update_live_prior()
                continue

            trade = open_orders.pop(matched_oid)
            active_tickers.discard(rec_ticker)
            active_tickers.discard(trade.get("ticker", ""))

            # v9.0.6: pass trade cost to _extract_realized_dollars so it can
            # reconstruct PnL from revenue fields when direct PnL fields absent.
            trade_cost = trade.get("cost")
            pnl_d = _extract_realized_dollars(rec, trade_cost=trade_cost)
            if pnl_d is None:
                log.warning("RESOLVE │ %s — no pnl field. Keys: %s",
                            rec_ticker[-15:], list(rec.keys()))
                continue

            if pnl_d == 0.0:
                log.info("NO-FILL │ %s", rec_ticker[-15:])
                for t in trade_history:
                    if t.get("order_id") == matched_oid:
                        t["result"] = "unfilled"
                        t["pnl"]    = 0.0
                        break
                continue

            won    = pnl_d > 0
            pnl    = round(pnl_d, 2)
            result = "win" if won else "loss"
            for t in trade_history:
                if t.get("order_id") == matched_oid:
                    t["result"] = result
                    t["pnl"]    = pnl
                    break

            balance        = get_live_balance()
            running_pnl   += pnl
            # v9.3.1: realized-only daily accumulator for the daily-loss breaker.
            # `pnl` is the reconciled _extract_realized_dollars() result for a
            # MATCHED, SETTLED trade — never an open-position mark.
            live_daily_realized += pnl
            # Display value for Telegram alerts: report the realized daily total
            # (same figure the breaker uses), not the cash-balance delta.
            live_daily_pnl = live_daily_realized

            if won:
                consecutive_losses = 0
                live_wins += 1
            else:
                consecutive_losses += 1
                live_losses += 1
                if consecutive_losses >= MAX_CONSEC_LOSSES:
                    streak_pause_until = time.time() + STREAK_PAUSE_SECS

            perf_guard_record(won)
            bucket_stats.record(trade.get("entry_bucket"), won)
            lifetime.record(DEMO_MODE, won, pnl)   # persistent all-time tally
            # Recovery ENTRY hook: `balance` was fetched (realized) above for
            # this settled trade.
            on_trade_settled(won, trade, balance)
            # Probation RAMP hook: a probation-mode trade advances/steps the ramp.
            probation_record(won, trade, balance)
            # Recovery win-rate restore feed: tally trades taken WHILE in recovery.
            recovery_winrate_record(won, trade)

            wlb = wilson_lower_bound(live_wins, live_wins + live_losses)
            log.info("✅ SETTLED │ %s │ %s │ $%.2f │ WR=%d/%d │ LB=%.1f%%",
                     rec_ticker[-15:], result.upper(), pnl,
                     live_wins, live_wins + live_losses, wlb * 100)

            if won:
                tg.send_win_notification(
                    profit=pnl, balance=balance, daily_pnl=live_daily_pnl,
                    ticker=rec_ticker, direction=trade.get("side", "?"),
                    wins=live_wins, losses=live_losses,
                )
            else:
                tg.send_loss_notification(
                    loss=abs(pnl), balance=balance, daily_pnl=live_daily_pnl,
                    ticker=rec_ticker, direction=trade.get("side", "?"),
                    streak=consecutive_losses,
                    wins=live_wins, losses=live_losses,
                )

            # The day's goal is checked HERE, on the settlement that banks the
            # profit, so the target halt lands the moment it is hit rather than
            # one poll interval later.
            daily_profit_target_check(balance)

        update_live_prior()

        try:
            canceled     = _get("/portfolio/orders", {"status": "canceled", "limit": 100})
            canceled_ids = {o["order_id"] for o in canceled.get("orders", [])}
            for oid in list(open_orders.keys()):
                if oid in canceled_ids:
                    trade = open_orders.pop(oid)
                    active_tickers.discard(trade.get("ticker", ""))
                    log.info("Order canceled │ %s", oid[:12])
        except Exception:
            pass

        now   = time.time()
        stale = [oid for oid, t in open_orders.items()
                 if now - t.get("placed_at", now) > STALE_ORDER_PURGE_INTERVAL_SECS]
        for oid in stale:
            trade = open_orders.pop(oid)
            active_tickers.discard(trade.get("ticker", ""))
            log.info("Stale purged │ %s", trade.get("ticker", "?")[-15:])

    except Exception as e:
        log.warning("Resolution error: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# STALE ORDER CANCELLATION
# ─────────────────────────────────────────────────────────────────────────────

def cancel_stale_orders() -> None:
    global paper_balance
    now = time.time()
    for oid in list(open_orders.keys()):
        trade = open_orders[oid]
        if now - trade.get("placed_at", now) < STALE_ORDER_TIMEOUT:
            continue
        ticker = trade.get("ticker", "")
        cost   = trade.get("cost", 0.0)
        # v10.1.0: a 404 already told us this order is not resting. Never ask
        # again — see the handler below.
        if trade.get("cancel_unresolved"):
            continue
        if DEMO_MODE:
            open_orders.pop(oid)
            active_tickers.discard(ticker)
            session_traded_tickers.discard(ticker)
            paper_balance += cost  # refund only — no daily_pnl touch
            for t in trade_history:
                if t.get("order_id") == oid:
                    t["result"] = "canceled"
                    t["pnl"]    = 0.0
                    break
            log.info("Stale cancel (paper) │ %s │ $%.2f", ticker[-15:], cost)
        else:
            try:
                _delete(f"/portfolio/events/orders/{oid}")
                open_orders.pop(oid)
                active_tickers.discard(ticker)
                # v10.1.0: a cancel that SUCCEEDS means the order never filled,
                # so there is no position and no P&L — it must not burn the
                # session's one-entry-per-market slot. Two of the ten orders in
                # the audited window (07-23 20:16 YES@48c, 07-25 13:00 YES@38c)
                # were cancelled unfilled and then locked out of their own market
                # by the session guard, so a live signal was abandoned with no
                # re-quote and no record either way.
                session_traded_tickers.discard(ticker)
                log.info("Stale cancel (live) │ %s │ %s — unfilled, market "
                         "re-armed", ticker[-15:], oid[:12])
            except Exception as e:
                # v10.1.0: a 404 is TERMINAL, not transient — the order is not
                # resting, which on this venue almost always means it already
                # filled. The pre-10.1.0 handler left it in open_orders and
                # retried every cycle until the 1200s purge in
                # resolve_open_orders, producing 22 identical warnings in the
                # audited window AND holding a phantom slot against
                # MAX_CONCURRENT_POS (and against the paper↔live flip, which only
                # restarts when open_orders is empty).
                #
                # Keep the record in open_orders so resolve_open_orders can still
                # match its settlement — just stop asking the venue to cancel it.
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status == 404:
                    trade["cancel_unresolved"] = True
                    log.info("Stale cancel │ %s %s — 404, not resting (likely "
                             "filled); awaiting settlement.",
                             ticker[-15:], oid[:12])
                else:
                    log.warning("Stale cancel failed %s: %s", oid[:12], e)


# ─────────────────────────────────────────────────────────────────────────────
# MARKET DISCOVERY
# ─────────────────────────────────────────────────────────────────────────────

BTC_SERIES = ["KXBTC15M", "KXBTCD", "KXBTC"]


def _to_cents(val) -> int:
    try:
        return int(round(float(val) * 100))
    except Exception:
        return 0


def get_active_market() -> Optional[dict]:
    for series in BTC_SERIES:
        try:
            data    = _get("/markets", {"series_ticker": series, "status": "open", "limit": 20})
            markets = data.get("markets", [])
            if not markets:
                continue
            valid = []
            for m in markets:
                # Horizon gate: never hand a daily-series market (a fallback in
                # BTC_SERIES) to the 15-minute doctrine. minutes_to_expiry()
                # returns its 999.0 sentinel when close_time is missing — treat
                # that as unknown rather than too-far, so an API field change
                # can't silently stop all trading.
                mins = minutes_to_expiry(m)
                if mins != 999.0 and mins > MAX_MINUTES_TO_EXPIRY:
                    continue
                bid = _to_cents(m.get("yes_bid_dollars"))
                ask = _to_cents(m.get("yes_ask_dollars"))
                if bid > 0 and ask > 0 and bid < ask:
                    m["yes_bid"] = bid
                    m["yes_ask"] = ask
                    m["yes_mid"] = (bid + ask) // 2
                    valid.append(m)
            if not valid:
                continue
            valid.sort(key=lambda m: abs(m["yes_mid"] - 50))
            m0 = valid[0]
            log.info("Market │ %s bid=%dc mid=%dc ask=%dc",
                     m0.get("ticker"), m0["yes_bid"], m0["yes_mid"], m0["yes_ask"])
            return m0
        except Exception as e:
            log.warning("Market discovery %s: %s", series, e)
    return None


def get_order_book(ticker: str) -> dict:
    return _get(f"/markets/{ticker}/orderbook")


def minutes_to_expiry(market: dict) -> float:
    ct = market.get("close_time")
    if not ct:
        return 999.0
    try:
        close_dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        delta    = (close_dt - datetime.now(timezone.utc)).total_seconds() / 60.0
        return max(0.0, delta)
    except Exception:
        return 999.0


# ─────────────────────────────────────────────────────────────────────────────
# GUARD STACK
# ─────────────────────────────────────────────────────────────────────────────

def session_stop_check(balance: float) -> bool:
    """The catastrophic session backstop (formerly misnamed daily_loss_check —
    the per-day loss caps were removed by the v9.4.0 owner directive; the only
    other auto-hold is the consecutive-loss streak pause in streak_check).
    Halts the day when balance falls below SESSION_STOP_FRACTION of the
    session-start balance; the UTC rollover clears the halt."""
    global _session_halted, _halt_reason
    if _session_halted:
        return False
    if session_stop_threshold > 0 and balance < session_stop_threshold:
        _session_halted = True
        _halt_reason    = "session_stop"
        log.warning("SESSION STOP │ $%.2f < $%.2f — halted.", balance, session_stop_threshold)
        save_daily_state()   # latch survives a restart
        telegram_halt(f"Session stop at ${balance:.2f}", balance)
        return False
    return True


# ── Daily profit target: make the day's 3%, then stop ─────────────────────────

def today_realized_pnl() -> float:
    """Today's REALIZED (settled) P&L in dollars, for the active mode. Realized
    only, never a balance delta: an open position's cash outlay leaves the
    balance before the trade settles, so balance − session_start would read a
    live position as a loss (the v9.3.1 phantom-daily-loss bug) and, on the way
    back, as profit that has not actually been banked."""
    return paper_daily_pnl if DEMO_MODE else live_daily_realized


def daily_profit_target_dollars() -> float:
    """The dollar profit that ends the day: DAILY_PROFIT_TARGET_PCT of the balance
    the day OPENED with (session_start_balance, re-based at every UTC rollover).
    0.0 when the target is disabled, unset, or there is no session baseline yet —
    callers treat that as "no target, keep trading"."""
    if not DAILY_PROFIT_TARGET_ENABLED or DAILY_PROFIT_TARGET_PCT <= 0:
        return 0.0
    if session_start_balance <= 0:
        return 0.0
    return round(DAILY_PROFIT_TARGET_PCT * session_start_balance, 2)


def daily_profit_target_check(balance: float) -> bool:
    """The day's goal. Returns True while the bot may still open trades.

    Once today's realized P&L reaches the target, the day is halted: no new
    entries until the UTC rollover re-bases the baseline and clears the halt
    (maybe_roll_session_day). Open positions are unaffected — they still resolve
    and report normally — and the profit that settles them is already counted.

    Idempotent: the Telegram notice fires once, on the transition."""
    global _session_halted, _halt_reason
    if _session_halted:
        return False
    target = daily_profit_target_dollars()
    if target <= 0:
        return True
    realized = today_realized_pnl()
    if realized < target:
        return True
    _session_halted = True
    _halt_reason    = "profit_target"
    log.warning("DAILY TARGET │ realized $%+.2f ≥ target $%.2f (%.1f%% of "
                "$%.2f) — trading halted until UTC rollover.",
                realized, target, DAILY_PROFIT_TARGET_PCT * 100,
                session_start_balance)
    # Write the latch immediately: a redeploy/crash between here and the next
    # cycle's save must not resurrect the day and start a second +3% hunt.
    save_daily_state()
    telegram_profit_target(realized, target, balance)
    return False


# ── The day's state across restarts ───────────────────────────────────────────

DAILY_STATE_SCHEMA = 1


def save_daily_state() -> None:
    """Persist today's risk state (atomic JSON write). Called once per main-loop
    cycle — including while halted — and again the instant a halt latches, so a
    crash between cycles can never lose the halt. Never raises: persistence is
    observability, it must not be able to stop trading."""
    if not DAILY_STATE_PERSIST:
        return
    try:
        tmp = f"{DAILY_STATE_PATH}.tmp"
        with open(tmp, "w") as f:
            json.dump({
                "schema":                DAILY_STATE_SCHEMA,
                "day":                   _session_day,
                "demo_mode":             DEMO_MODE,
                "session_start_balance": round(session_start_balance, 4),
                "halted":                _session_halted,
                "halt_reason":           _halt_reason,
                "paper_daily_pnl":       round(paper_daily_pnl, 4),
                "live_daily_realized":   round(live_daily_realized, 4),
                "consecutive_losses":    consecutive_losses,
            }, f)
        os.replace(tmp, DAILY_STATE_PATH)   # atomic on POSIX
    except OSError as e:
        log.warning("Daily state │ save failed: %s", e)


def restore_daily_state(current_balance: float) -> bool:
    """Restore today's risk state at boot. Returns True when a record was
    adopted.

    Only a record written TODAY (UTC) in the SAME mode is adopted — anything
    else is stale or belongs to the other book, and the caller's fresh-day
    values stand. Restores the day's OPENING balance (so the +3% goal is not
    re-based upward by the restart), the session-stop floor derived from it,
    today's realized P&L for the active mode, and any latched halt.
    """
    global session_start_balance, session_stop_threshold, consecutive_losses
    global paper_daily_pnl, live_daily_realized, _session_halted, _halt_reason
    if not DAILY_STATE_PERSIST:
        return False
    try:
        with open(DAILY_STATE_PATH) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return False
    if not isinstance(d, dict):
        return False
    if d.get("day") != _session_day or bool(d.get("demo_mode")) != DEMO_MODE:
        return False
    try:
        opening = float(d.get("session_start_balance", 0.0) or 0.0)
        if opening > 0:
            session_start_balance  = opening
            session_stop_threshold = opening * SESSION_STOP_FRACTION
        paper_daily_pnl     = float(d.get("paper_daily_pnl", 0.0) or 0.0)
        live_daily_realized = float(d.get("live_daily_realized", 0.0) or 0.0)
        consecutive_losses  = int(d.get("consecutive_losses", 0) or 0)
        _session_halted     = bool(d.get("halted", False))
        _halt_reason        = str(d.get("halt_reason", "") or "")
    except (TypeError, ValueError) as e:
        log.warning("Daily state │ corrupt record ignored: %s", e)
        return False
    realized = today_realized_pnl()
    if _session_halted:
        log.warning("Daily state │ RESUMING today's halt (%s) — realized $%+.2f, "
                    "day opened at $%.2f (goal $%.2f). Paused until UTC rollover.",
                    _halt_reason or "halted", realized, session_start_balance,
                    daily_profit_target_dollars())
    else:
        log.info("Daily state │ restored today's session — opened at $%.2f, "
                 "realized $%+.2f, balance now $%.2f.",
                 session_start_balance, realized, current_balance)
    return True


def spread_check(bid: int, ask: int) -> bool:
    if ask - bid <= 0:
        log.info("Spread │ zero/crossed")
        return False
    return True


def expiry_guard(mid: int) -> bool:
    if mid > 85 or mid < 15:
        log.info("Expiry │ %dc near-certain", mid)
        return False
    return True


def cooldown_check() -> bool:
    elapsed = time.time() - last_trade_ts
    if elapsed < 60:
        log.info("Cooldown │ %.0fs remaining", 60 - elapsed)
        return False
    return True


def session_quality_check() -> bool:
    score = get_session_score()
    utc_h = datetime.now(timezone.utc).hour
    if score < MIN_SESSION_SCORE:
        log.info("Session quality │ UTC%d score=%d < %d", utc_h, score, MIN_SESSION_SCORE)
        return False
    return True


def streak_check() -> bool:
    global consecutive_losses
    if consecutive_losses >= MAX_CONSEC_LOSSES:
        if time.time() < streak_pause_until:
            log.info("Streak pause │ %d consec losses", consecutive_losses)
            return False
        consecutive_losses = 0
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ORDER EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def place_order(ticker: str, direction: str, bet_dollars: float,
                limit_cents: int, win_prob: float, edge: float,
                balance_before: float = 0.0,
                count: Optional[int] = None) -> Optional[str]:
    """Place one order. `count` is normally resolved by the caller via
    size_contracts() so an unsizeable signal is rejected BEFORE it is announced;
    it is left optional so any other call site still sizes correctly here."""
    global last_trade_ts, paper_balance

    if limit_cents <= 0:
        return None
    if count is None:
        count, size_reason = size_contracts(bet_dollars, limit_cents,
                                            balance_before or bet_dollars)
        if count < 1:
            log.warning("Order │ unsizeable — %s", size_reason)
            return None
    cost      = (limit_cents * count) / 100.0
    client_id = f"mm-{uuid.uuid4().hex[:10]}"
    btc_entry = list(btc_prices)[-1] if btc_prices else 0
    # v9.5.0: stamp the sizing mode + the realized balance immediately BEFORE
    # this trade so settlement can (a) tell a full-size loss from a recovery-size
    # loss and (b) set the recovery target to the exact pre-trade balance.
    entry_mode = ("recovery" if recovery.active
                  else "probation" if probation.active
                  else "normal")
    # Stamp the time-of-day bucket at ENTRY so settlement scores the bucket the
    # trade was opened in (a 13:46-ET entry into a 14:00 market is afternoon),
    # not the bucket it happened to settle in.
    entry_bucket = bucket_stats.key_now()

    if DEMO_MODE:
        paper_balance -= cost
        last_trade_ts  = time.time()
        active_tickers.add(ticker)
        session_traded_tickers.add(ticker)
        rec = {
            "time": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker, "side": direction,
            "price": limit_cents, "count": count, "cost": cost,
            "order_id": client_id, "result": "pending",
            "placed_at": time.time(), "btc_entry_price": btc_entry,
            "mode_at_entry": entry_mode, "balance_before": round(balance_before, 2),
            "entry_bucket": entry_bucket,
        }
        trade_history.append(rec)
        open_orders[client_id] = rec
        log.info("🟡 PAPER │ %s %s │ %d @ %dc │ $%.2f │ bal=$%.2f",
                 direction, ticker[-15:], count, limit_cents, cost, paper_balance)
        tg.send_trade_entry_notification(
            ticker=ticker, direction=direction, cost=cost,
            price_cents=limit_cents, balance=paper_balance,
            ob_pct=win_prob * 100, edge_pct=edge * 100,
        )
        return client_id

    # Kalshi V2 single-book order model (POST /portfolio/events/orders).
    # The legacy /portfolio/orders endpoint was deprecated and now returns
    # HTTP 410. V2 quotes a single YES book: side="bid" buys YES, side="ask"
    # buys NO (buying NO at L cents == selling YES at (100 - L) cents). Price
    # and count are fixed-point dollar/contract strings, and time_in_force and
    # self_trade_prevention_type are required.
    is_yes     = direction.upper() == "YES"
    yes_cents  = limit_cents if is_yes else (100 - limit_cents)
    body: dict = {
        "ticker":                     ticker,
        "client_order_id":            client_id,
        "side":                       "bid" if is_yes else "ask",
        "count":                      str(count),
        "price":                      f"{yes_cents / 100:.4f}",
        "time_in_force":              "good_till_canceled",
        "self_trade_prevention_type": "taker_at_cross",
    }

    try:
        resp     = _post("/portfolio/events/orders", body)
        order_id = (resp.get("order", {}).get("order_id")
                    or resp.get("order_id") or client_id)
        last_trade_ts = time.time()
        rec = {
            "time": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker, "side": direction,
            "price": limit_cents, "count": count, "cost": cost,
            "order_id": order_id, "result": "pending",
            "placed_at": time.time(), "btc_entry_price": btc_entry,
            "mode_at_entry": entry_mode, "balance_before": round(balance_before, 2),
            "entry_bucket": entry_bucket,
        }
        trade_history.append(rec)
        open_orders[order_id] = rec
        active_tickers.add(ticker)
        session_traded_tickers.add(ticker)
        # v10.1.0: report `cost` (what was actually committed), not `bet_dollars`
        # (the stake the sizer started from). They differ by the integer rounding
        # — the 2026-07-23 22:16 entry logged "5 @ 40c │ $2.14" against a real
        # $2.00 — so the log overstated capital at risk on every multi-contract
        # fill and never reconciled against the settlement PnL.
        log.info("✅ ORDER │ %s %s │ %d @ %dc │ $%.2f │ %s",
                 direction, ticker[-15:], count, limit_cents, cost, order_id[:12])
        live_bal = get_live_balance()
        tg.send_trade_entry_notification(
            ticker=ticker, direction=direction, cost=cost,
            price_cents=limit_cents, balance=live_bal,
            ob_pct=win_prob * 100, edge_pct=edge * 100,
        )
        return order_id
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "???"
        body_t = e.response.text[:300] if e.response is not None else str(e)
        log.error("Order failed │ HTTP %s │ %s", status, body_t)
        return None
    except Exception as e:
        log.error("Order failed │ %s", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

def log_size_feasibility(balance: float) -> None:
    """Say plainly, at boot, whether this balance can actually honour the
    configured stake percentage — the balance-independence audit's operator-
    facing half.

    Sizing rounds DOWN to whole contracts, so the configured fraction is always a
    ceiling; what varies with account size is how much of it a small balance can
    reach. Below one contract at a given price the signal is skipped entirely, so
    an under-funded account silently trades only the cheap end of the book. This
    logs the crossover instead of leaving it to be discovered in a log audit.
    Never raises — observability must not stop the bot booting."""
    try:
        stake = active_trade_size(balance)
        # expiry_guard only lets mids 15c–85c through, so 85c is the priciest
        # contract the strategy can ever try to buy.
        top_c = 85
        if stake <= 0:
            log.warning("  Sizing feasibility: stake is $0 — nothing tradeable "
                        "(check balance and any set-aside reserve).")
            return
        if stake >= top_c / 100.0:
            log.info("  Sizing feasibility: stake $%.2f covers the whole 15c–85c "
                     "band — the configured %% is reachable at every price.",
                     stake)
            return
        affordable = int(stake * 100)
        need = round(top_c / 100.0 / max(active_trade_fraction(), 1e-9), 2)
        log.warning(
            "  Sizing feasibility: stake $%.2f only affords contracts ≤ %dc. "
            "Signals above that are SKIPPED (never up-sized), so this account "
            "trades the cheap end of the book only. ~$%.2f of balance would "
            "cover the full band at %.1f%%.",
            stake, affordable, need, active_trade_fraction() * 100)
    except Exception as e:  # pragma: no cover - never block boot
        log.debug("size feasibility check skipped: %s", e)


def telegram_boot(balance: float) -> None:
    mode = "📋 PAPER" if DEMO_MODE else "🔴 LIVE"
    target = daily_profit_target_dollars()
    goal   = (f"Today's goal: +{DAILY_PROFIT_TARGET_PCT*100:.1f}% "
              f"(${target:.2f}) — trading stops when it's hit\n"
              if target > 0 else "Daily profit target: OFF\n")
    # A restart that lands on a day already halted says so, or the customer sees
    # a "STARTED" message and expects trading that (correctly) will not resume
    # until the UTC rollover.
    if _session_halted:
        goal += ("🎯 Today's goal is already banked — paused until the UTC "
                 "rollover.\n" if _halt_reason == "profit_target"
                 else "⏸️ Today is halted (session stop) — paused until the UTC "
                      "rollover.\n")
    tg.send_status_message(
        f"🤖 FlipPulse {BOT_VERSION} STARTED\n"
        f"{mode} │ State: {session_state.value}\n"
        f"Balance: ${balance:.2f}\n"
        f"{goal}"
        f"Size={active_trade_fraction()*100:.1f}% (~${active_trade_size(balance):.0f}) "
        f"(normal={NORMAL_TRADE_PCT*100:.1f}%/recovery={RECOVERY_TRADE_PCT*100:.1f}%/max={MAX_TRADE_PCT*100:.1f}%"
        f"{' • RECOVERING→$%.0f' % recovery.target_balance if recovery.active else ''}) | "
        f"MaxConsecL={MAX_CONSEC_LOSSES}\n"
        f"MinConf={MIN_CONFIDENCE} | MinWinP={MIN_WIN_PROB*100:.0f}% | R²≥{R2_TREND_THRESHOLD}\n"
        f"OBDepth≥${MIN_OB_DEPTH:.0f} | OBImb≥{OB_IMBALANCE_THRESH*100:.0f}%\n"
        f"AGREE-gate={'ON' if REQUIRE_AGREE_MOMENTUM else 'OFF'} | "
        f"Breakeven≤{YES_BREAKEVEN_PRICE}c\n"
        f"SessionScore≥{MIN_SESSION_SCORE}"
    )


def telegram_halt(reason: str, balance: float) -> None:
    tg.send_telegram_message(
        f"⛔ HALTED (PERMANENT)\nReason: {reason}\nBalance: ${balance:.2f}"
    )


def telegram_profit_target(realized: float, target: float, balance: float) -> None:
    """The good halt: the day's profit goal is banked. Deliberately distinct from
    telegram_halt (which reads as an emergency) — this is the plan working."""
    pct = (realized / session_start_balance * 100) if session_start_balance > 0 else 0.0
    tg.send_telegram_message(
        f"🎯 DAILY TARGET HIT — trading stopped for today\n"
        f"Today's profit: ${realized:+.2f} ({pct:.2f}%)\n"
        f"Goal was: ${target:.2f} "
        f"({DAILY_PROFIT_TARGET_PCT*100:.1f}% of ${session_start_balance:.2f})\n"
        f"Balance: ${balance:.2f}\n"
        f"No new trades until the next trading day (UTC midnight). Open "
        f"positions, if any, still settle normally."
    )


# ─────────────────────────────────────────────────────────────────────────────
# TRADE-WINDOW STATS + SCHEDULED REPORT  (twice-daily P&L / win rate briefing)
#
# One source of truth for time-windowed performance: trade_window_stats scans the
# in-memory trade_history (a maxlen=500 deque — best-effort, this-run only) and
# tallies wins/losses/PnL over settled trades since a cutoff. Used by both the
# scheduled 9am/9pm report and the /winrate command's snapshot fields, so the two
# always agree. Works identically in paper and live (both write result + pnl onto
# the trade rec at settlement).
# ─────────────────────────────────────────────────────────────────────────────

def _report_tz():
    """The tz the scheduled report fires in; UTC if REPORT_TIMEZONE can't load."""
    if ZoneInfo is None:
        return timezone.utc
    try:
        return ZoneInfo(REPORT_TIMEZONE)
    except Exception:
        log.warning("REPORT_TIMEZONE '%s' unavailable (no tzdata?) — using UTC.",
                    REPORT_TIMEZONE)
        return timezone.utc


def _report_hours() -> "list[int]":
    """Parsed, sorted, de-duplicated valid hours (0–23) from REPORT_HOURS."""
    out = set()
    for tok in REPORT_HOURS_RAW.split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            h = int(tok)
        except ValueError:
            continue
        if 0 <= h <= 23:
            out.add(h)
    return sorted(out)


def _parse_trade_epoch(rec: dict) -> "float | None":
    """Epoch seconds for a trade rec's entry timestamp, or None if unparseable."""
    ts = rec.get("time")
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def trade_window_stats(since_epoch: "float | None" = None) -> "tuple[int, int, float]":
    """(wins, losses, pnl) over SETTLED trades in trade_history whose entry time is
    at/after since_epoch (None = all in memory). PnL sums the per-trade realized
    pnl the settlement path stamps on each rec. Never raises."""
    wins = losses = 0
    pnl = 0.0
    for t in trade_history:
        if t.get("result") not in ("win", "loss"):
            continue
        if since_epoch is not None:
            te = _parse_trade_epoch(t)
            if te is None or te < since_epoch:
                continue
        if t["result"] == "win":
            wins += 1
        else:
            losses += 1
        try:
            pnl += float(t.get("pnl", 0.0) or 0.0)
        except (TypeError, ValueError):
            pass
    return wins, losses, round(pnl, 2)


def _tz_day_start_epoch(days_ago: int = 0, tz=None) -> float:
    """Epoch seconds for local midnight `days_ago` days back, in the report tz.
    days_ago=0 → the start of today's local calendar day."""
    tz = tz or _report_tz()
    d = (datetime.now(tz) - timedelta(days=days_ago)).date()
    return datetime(d.year, d.month, d.day, tzinfo=tz).timestamp()


def _fmt_winrate(wins: int, losses: int) -> str:
    total = wins + losses
    if not total:
        return "no settled trades yet"
    return f"{wins / total * 100:.0f}% ({wins}W/{losses}L)"


def build_scheduled_report(balance: float) -> str:
    """The twice-daily briefing body: balance, today's P&L + win rate, and the
    persistent all-time figures. Pure — takes the balance, reads shared state."""
    tz = _report_tz()
    now_local = datetime.now(tz)
    d_w, d_l, d_pnl = trade_window_stats(_tz_day_start_epoch(0, tz))
    # All-time comes from the PERSISTENT lifetime tally (survives redeploys),
    # scoped to the current paper/live mode.
    a_w, a_l, a_pnl = lifetime.stats(DEMO_MODE)
    mode   = "PAPER 🟡" if DEMO_MODE else "LIVE 🔴"
    active = ("Recovery" if recovery.active
              else "Probation ramp" if probation.active else "Normal")
    label  = "Morning" if now_local.hour < 12 else "Evening"
    return (
        f"📊 FlipPulse {label} Report — {now_local.strftime('%b %d, %I:%M %p %Z')}\n"
        f"Mode: {mode} · {active}\n"
        f"🏦 Balance: ${balance:,.2f}\n"
        f"— Today —\n"
        f"💵 P&L: ${d_pnl:+,.2f}\n"
        f"🎯 Win rate: {_fmt_winrate(d_w, d_l)}\n"
        f"— All-time —\n"
        f"💵 P&L: ${a_pnl:+,.2f}\n"
        f"🎯 Win rate: {_fmt_winrate(a_w, a_l)}"
    )


class ReportScheduler:
    """Fires build_scheduled_report() at the configured local hours, once per slot.
    Persists the last slot sent so a redeploy can't double-send and a long-down
    slot is skipped rather than delivered stale. Mutated in place, never raises."""

    def __init__(self, path: str, persist: bool) -> None:
        self.last_slot: str = ""
        self._path    = path
        self._persist = persist
        if self._persist:
            self._load()

    def _latest_past_slot(self, now_local: datetime):
        """The most recent scheduled datetime ≤ now_local (today's hours, or
        yesterday's last hour before the first fire of the day). None if none."""
        hours = _report_hours()
        if not hours:
            return None
        tz = now_local.tzinfo
        candidates = []
        for d_off in (0, 1):
            day = (now_local - timedelta(days=d_off)).date()
            for h in hours:
                candidates.append(datetime(day.year, day.month, day.day, h, tzinfo=tz))
        past = [c for c in candidates if c <= now_local]
        return max(past) if past else None

    def maybe_send(self, balance: float) -> bool:
        """Check the clock and send the briefing if a fresh slot has arrived.
        Returns True only when a message was actually sent."""
        if not REPORT_SCHEDULE_ENABLED:
            return False
        try:
            now_local = datetime.now(_report_tz())
            slot_dt   = self._latest_past_slot(now_local)
            if slot_dt is None:
                return False
            slot_key = slot_dt.strftime("%Y-%m-%d %H")
            if slot_key == self.last_slot:
                return False
            # Too far past the scheduled time (slept/down through it) → consume the
            # slot silently so the next slot fires cleanly, but don't send stale.
            if (now_local - slot_dt).total_seconds() > REPORT_MAX_LATE_SECS:
                self.last_slot = slot_key
                self._save()
                return False
            sent = tg.send_telegram_message(build_scheduled_report(balance))
            # Mark consumed regardless of send success so a Telegram outage doesn't
            # make us retry the same slot every cycle for hours.
            self.last_slot = slot_key
            self._save()
            return bool(sent)
        except Exception as e:  # pragma: no cover - observability must not break trading
            log.debug("scheduled report check failed: %s", e)
            return False

    def _save(self) -> None:
        if not self._persist:
            return
        try:
            tmp = f"{self._path}.tmp"
            with open(tmp, "w") as f:
                json.dump({"last_slot": self.last_slot}, f)
            os.replace(tmp, self._path)
        except OSError as e:
            log.warning("Report │ state save failed: %s", e)

    def _load(self) -> None:
        try:
            with open(self._path) as f:
                self.last_slot = str(json.load(f).get("last_slot", "") or "")
        except (OSError, ValueError):
            return


report_scheduler = ReportScheduler(REPORT_STATE_PATH, REPORT_PERSIST)


def write_status_snapshot(balance: float) -> None:
    """Write a small JSON status snapshot for the web dashboard.

    Never raises — observability must not break trading (a local run with no
    /data volume just skips the write).
    """
    if not STATUS_SNAPSHOT_PATH:
        return
    try:
        if DEMO_MODE:
            resolved = [t for t in trade_history if t.get("result") in ("win", "loss")]
            wins   = sum(1 for t in resolved if t["result"] == "win")
            losses = len(resolved) - wins
            session_pnl = paper_daily_pnl
        else:
            wins, losses = live_wins, live_losses
            session_pnl = live_daily_realized
        total = wins + losses
        # wilson_confidence already returns percentages: (rate%, lower%, upper%).
        rate_pct, lo_pct, hi_pct = wilson_confidence(wins, total) if total > 0 else (0.0, 0.0, 0.0)
        active_mode = ("recovery" if recovery.active
                       else "probation" if probation.active else "normal")
        # Time-windowed W/L + PnL (report-tz calendar), for /winrate and /pnl and
        # the dashboard. "week" is a rolling 7 days. Best-effort over in-memory
        # history (same source as the scheduled report), so the two always agree.
        d_w, d_l, d_pnl = trade_window_stats(_tz_day_start_epoch(0))
        w_w, w_l, w_pnl = trade_window_stats(_tz_day_start_epoch(6))
        _wr = lambda w, l: round(w / (w + l) * 100, 1) if (w + l) else 0.0
        # Persistent all-time tally (survives redeploys), scoped to paper/live.
        lt_w, lt_l, lt_pnl = lifetime.stats(DEMO_MODE)
        snapshot = {
            "version": BOT_VERSION,
            "trading_format": TRADING_FORMAT,
            "demo_mode": DEMO_MODE,
            # A requested-but-not-yet-applied paper↔live flip (applies on the next
            # flat cycle via restart). None unless a flip is pending; the dashboard
            # and /status show it so the user knows the switch is armed.
            "pending_demo_mode": (t if (t := _read_mode_override()) is not None
                                  and t != DEMO_MODE else None),
            "balance": round(float(balance), 2),
            "session_pnl": round(float(session_pnl), 2),
            "wins": wins,
            "losses": losses,
            "win_rate": rate_pct,
            "wilson_ci": [lo_pct, hi_pct],
            # Time-windowed figures for /winrate and /pnl (report-tz; week = 7d).
            "wins_today": d_w, "losses_today": d_l,
            "win_rate_today": _wr(d_w, d_l), "pnl_today": d_pnl,
            "wins_week": w_w, "losses_week": w_l,
            "win_rate_week": _wr(w_w, w_l), "pnl_week": w_pnl,
            # Persistent all-time figures (survive redeploys) — the "stop the win
            # rate resetting" fix. Scoped to the current paper/live mode.
            "lifetime_wins": lt_w, "lifetime_losses": lt_l,
            "lifetime_win_rate": _wr(lt_w, lt_l), "lifetime_pnl": lt_pnl,
            "report_timezone": REPORT_TIMEZONE,
            "active_mode": active_mode,
            # Recovery Mode "No Stake Change" toggle — surfaced so /status, the
            # dashboard, and the /recoverynostakechange command can report it.
            "recovery_no_stake_change": recovery_no_stake_change_enabled(),
            # Recovery-scoped win rate + the restore threshold, so /status can show
            # progress toward the win-rate fast-exit while recovery is active.
            "recovery_wins": recovery.wins,
            "recovery_losses": recovery.losses,
            "recovery_win_rate": round(recovery.winrate() * 100, 1),
            "recovery_winrate_restore_pct": round(RECOVERY_WINRATE_RESTORE_PCT * 100, 1),
            # The balance recovery is clawing back to (0 when not in recovery),
            # so /status and the dashboard can show how far there is to go.
            "recovery_target": round(recovery.target_balance, 2),
            "active_trade_pct": round(active_trade_fraction() * 100, 2),
            "active_trade_size": round(active_trade_size(balance), 2),
            # Full-size risk knob + the hard bounds the Telegram /risk command
            # clamps into. normal_trade_pct reflects any live /risk override.
            "normal_trade_pct": round(effective_normal_trade_pct() * 100, 2),
            "risk_min_pct": round(RISK_MIN_TRADE_PCT * 100, 2),
            "risk_max_pct": round(MAX_TRADE_PCT * 100, 2),
            # Customer reserve (set aside) + the balance actually in play, and the
            # live trading format — all surfaced so the dashboard can render them.
            "reserve_dollars": round(effective_reserve(), 2),
            "tradeable_balance": round(tradeable_balance(balance), 2),
            "billing": billing.snapshot(balance),
            "open_positions": len(open_orders),
            "open_tickers": [o.get("ticker", "") for o in open_orders.values()],
            "session_state": session_state.value,
            "halted": _session_halted,
            # Why the day is halted ("" while trading, "profit_target",
            # "session_stop") so /status and the dashboard can say "goal reached"
            # instead of showing a scary generic stop.
            "halt_reason": _halt_reason,
            # Daily profit target: the goal in dollars, today's realized progress,
            # and the percentage knob behind them.
            "daily_target_enabled": DAILY_PROFIT_TARGET_ENABLED
                                    and DAILY_PROFIT_TARGET_PCT > 0,
            "daily_target_pct": round(DAILY_PROFIT_TARGET_PCT * 100, 2),
            "daily_target_dollars": daily_profit_target_dollars(),
            "daily_target_progress": round(today_realized_pnl(), 2),
            "session_start_balance": round(session_start_balance, 2),
            "last_signal": last_signal_desc,
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        tmp = STATUS_SNAPSHOT_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(snapshot, f)
        os.replace(tmp, STATUS_SNAPSHOT_PATH)
    except Exception as e:  # pragma: no cover - observability must never break trading
        log.debug("status snapshot write failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN DECISION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def run_decision(market: dict, balance: float) -> None:
    global last_signal_desc

    ticker  = market["ticker"]
    yes_bid = market.get("yes_bid", 0)
    yes_ask = market.get("yes_ask", 0)
    if yes_bid <= 0 or yes_ask <= 0 or yes_bid >= yes_ask:
        return
    yes_mid = (yes_bid + yes_ask) // 2

    if not expiry_guard(yes_mid):
        return
    if not spread_check(yes_bid, yes_ask):
        return
    if ticker in active_tickers:
        log.info("Position guard │ %s", ticker[-15:])
        return
    if ticker in session_traded_tickers:
        log.info("Session guard │ already traded %s", ticker[-15:])
        last_signal_desc = f"session re-entry ({ticker[-10:]})"
        return
    if not cooldown_check():
        return
    if not session_stop_check(balance):
        return
    # The day's goal: once +DAILY_PROFIT_TARGET_PCT is banked, stop trading.
    # Normally already latched at settlement; this is the belt-and-braces gate so
    # no entry can slip through on a cycle where the target was just reached.
    if not daily_profit_target_check(balance):
        last_signal_desc = "daily profit target hit — stopped for today"
        return
    if not streak_check():
        last_signal_desc = f"streak pause ({consecutive_losses}L)"
        return
    if not performance_guard():
        last_signal_desc = "perf guard (Wilson LB < 50%)"
        return
    if not session_quality_check():
        last_signal_desc = f"session quality UTC{datetime.now(timezone.utc).hour}"
        return
    if len(open_orders) >= MAX_CONCURRENT_POS:
        log.info("Concurrent │ %d open", len(open_orders))
        return

    mins = minutes_to_expiry(market)
    if mins < MIN_MINUTES_TO_EXPIRY:
        log.info("Expiry imminent │ %.1f min", mins)
        last_signal_desc = "expiry imminent"
        return

    if check_vol_circuit():
        last_signal_desc = "vol circuit open"
        return

    regime, r_squared, realized_vol = compute_regime()
    if regime in (Regime.UNKNOWN, Regime.RANGING, Regime.HIGH_VOL):
        log.info("Regime │ %s — no trade", regime.value)
        last_signal_desc = f"regime={regime.value}"
        return

    try:
        ob_raw = get_order_book(ticker)
    except Exception as e:
        log.warning("OB fetch failed: %s", e)
        return

    ob = analyze_order_book(ob_raw, yes_mid)
    if ob is None:
        last_signal_desc = "OB no signal"
        return

    ob_dir = ob["direction"]
    if not check_ob_trend(ticker, ob_dir, ob["imbalance"]):
        last_signal_desc = "OB fading"
        return

    # Direction gate: never bet the order book against the measured trend. Both
    # of 2026-06-19's losing trades did exactly that (NO in TRENDING_UP, YES in
    # TRENDING_DOWN) while the one aligned trade won. Require agreement.
    if not regime_agrees(regime, ob_dir):
        log.info("Regime conflict │ OB=%s vs %s — no trade", ob_dir, regime.value)
        last_signal_desc = f"regime conflict OB={ob_dir} {regime.value}"
        return

    momentum_verdict, momentum_adj = compute_momentum(ob_dir)
    if momentum_verdict == "CONFLICT":
        log.info("Momentum CONFLICT │ OB=%s", ob_dir)
        last_signal_desc = f"CONFLICT OB={ob_dir}"
        return

    # ── DOCTRINE LAYER 7 (restored v9.3.0) ───────────────────────────────────
    # BTC spot momentum must EXPLICITLY AGREE with the order-book direction.
    # NEUTRAL (flat BTC) is not confirmation; trading on the order book alone is
    # the single condition this bot was post-mortemed never to do (v6.0.0;
    # 2026-03-27/28 50% loss). Every trade in the 2026-06-20→22 bleed fired on
    # BTC=NEUTRAL because v9.0.6→v9.2.0 left no NEUTRAL gate here.
    #
    # Applies in EVERY sizing mode, recovery included — recovery's exit is
    # balance-driven (RecoveryState.maybe_exit, checked every cycle), never a
    # reason to trade unconfirmed setups. A calm, all-NEUTRAL session producing
    # zero trades is CORRECT.
    if not momentum_gate_ok(momentum_verdict):
        log.info("Momentum │ require AGREE, got %s (OB=%s) — no trade",
                 momentum_verdict, ob_dir)
        last_signal_desc = f"momentum {momentum_verdict} (need AGREE)"
        return

    # ── v10.1.0 ORDERING CHANGE ───────────────────────────────────────────────
    # The contract price is resolved BEFORE the probability is finalised, because
    # the market anchor needs it: the quoted price is the market's own
    # probability estimate and is the base rate the model adjusts. Pre-10.1.0 the
    # probability was computed first and never saw the price at all, which is how
    # "edge" degenerated into "cheapness" (corr(price, edge) = -0.88 across the
    # 65 audited signals). See market_anchored_win_prob.
    if ob_dir == "YES":
        if yes_mid > YES_BREAKEVEN_PRICE:
            log.info("Price guard │ YES %dc > breakeven", yes_mid)
            return
        direction      = "YES"
        contract_price = yes_mid
    else:
        no_price = 100 - yes_mid
        if no_price > YES_BREAKEVEN_PRICE:
            log.info("Price guard │ NO %dc > breakeven", no_price)
            return
        direction      = "NO"
        contract_price = no_price

    if not (25 <= contract_price <= 75):
        log.info("Bias filter │ %dc outside 25-75", contract_price)
        return

    model_prob, model_base = bayesian_win_prob(ob, momentum_verdict, momentum_adj,
                                               regime, r_squared, realized_vol)
    win_prob = market_anchored_win_prob(model_prob, model_base, contract_price)

    # With the anchor on, this floor means what it says: the trade must be more
    # likely than not to WIN, which puts a hard price floor at roughly
    # (MIN_WIN_PROB - MAX_MODEL_EDGE_PP). That is the intended consequence of the
    # audit — over the 8 settled trades in the audited window, entries below 50c
    # went 1W-4L while entries above 50c went 2W-1L, and the unanchored model was
    # steering almost exclusively into the cheap half.
    if win_prob < MIN_WIN_PROB:
        log.info("WinProb │ %.3f < %.3f (model %.3f @ %dc)",
                 win_prob, MIN_WIN_PROB, model_prob, contract_price)
        last_signal_desc = f"win_prob {win_prob:.2f} < {MIN_WIN_PROB:.2f}"
        return

    session_score = get_session_score()
    conf = compute_confidence(ob, regime, r_squared, momentum_verdict,
                               win_prob, mins, session_score)
    if conf < MIN_CONFIDENCE:
        log.info("Confidence │ %.0f < %d", conf, MIN_CONFIDENCE)
        last_signal_desc = f"conf {conf:.0f} < {MIN_CONFIDENCE}"
        return

    edge = calc_edge(win_prob, contract_price)
    if edge < MIN_EDGE_PCT:
        log.info("Edge │ %.3f < min %.3f", edge, MIN_EDGE_PCT)
        last_signal_desc = f"edge {edge:.3f} < {MIN_EDGE_PCT:.3f}"
        return

    # Secondary, opt-in: expected value per DOLLAR STAKED rather than per
    # contract. MIN_EDGE_PCT is payout-denominated, so the same threshold demands
    # a very different return on the cash at risk at 30c than at 65c.
    ror = edge_return_on_risk(edge, contract_price)
    if MIN_EDGE_ROR > 0 and ror < MIN_EDGE_ROR:
        log.info("Edge RoR │ %.1f%% < min %.1f%%", ror * 100, MIN_EDGE_ROR * 100)
        last_signal_desc = f"edge RoR {ror:.2f} < {MIN_EDGE_ROR:.2f}"
        return

    bet = kelly_bet(win_prob, contract_price, balance)
    # v10.3.0: the old `bet < 0.25` cutoff was the last raw-dollar rule in the
    # entry path — it blocked every account under ~$2.50 regardless of config,
    # which is exactly the "the rules differ at $20 vs $20,000" problem. It was
    # also redundant: size_contracts already rejects an unaffordable stake, and
    # does it against MAX_TRADE_PCT (a percentage), so a dust stake still cannot
    # buy a contract that would breach the ceiling.
    if bet <= 0:
        log.info("Kelly │ no stake (edge gate or zero tradeable balance)")
        return
    if balance < bet:
        log.warning("Insufficient balance")
        return

    if direction == "YES":
        limit_price = max(1, min(yes_bid + 1, yes_ask - 1))
    else:
        no_best     = 100 - yes_ask
        limit_price = max(1, min(no_best + 1, 100 - yes_bid - 1))
    limit_price = max(1, min(99, limit_price))

    if abs(limit_price - contract_price) > 8:
        log.info("Limit drift │ %dc too far", limit_price)
        return

    # ── v10.1.0: size BEFORE announcing ──────────────────────────────────────
    # This check used to live inside place_order, AFTER the edge justification
    # had been logged and pushed to Telegram. Across 2026-07-23→26 it silently
    # discarded 55 of 65 announced signals (84.6%) — every one of which reads in
    # the log like a trade the bot chose to take. Reject here, with the real
    # reason, so a logged signal is always a placed order.
    count, size_reason = size_contracts(bet, limit_price, balance)
    if count < 1:
        log.warning("Sizing │ under-capitalised — %s", size_reason)
        last_signal_desc = f"unsizeable: {size_reason}"
        return
    cost = round(limit_price * count / 100.0, 2)

    # Liquidity gate, expressed relative to THIS order rather than in fixed
    # dollars: the book must be able to absorb the trade several times over. The
    # flat MIN_OB_DEPTH floor above says the market is worth trading at all; this
    # says it is worth trading at OUR size. Same rule at every balance — which is
    # the point, since a $75 floor is 133x cover for a $20 account and 0.0075x
    # cover for a $100,000 one. Checked before the announce, like the sizing.
    if not depth_covers_order(ob["total_depth"], cost):
        need = cost * MIN_DEPTH_STAKE_MULT
        log.info("Liquidity │ book $%.0f < %.1f× order $%.2f (need $%.0f) — "
                 "no trade", ob["total_depth"], MIN_DEPTH_STAKE_MULT, cost, need)
        last_signal_desc = (f"thin book: ${ob['total_depth']:.0f} < "
                            f"{MIN_DEPTH_STAKE_MULT:.1f}× order ${cost:.2f}")
        return

    _pw     = len(_perf_window)
    wlb_str = (f" WLB={wilson_lower_bound(sum(1 for w in _perf_window), _pw)*100:.1f}%"
               if _pw >= 10 else " WLB=n/a")

    log.info(
        "📋 EDGE JUSTIFICATION │ %s %s @ %dc │ regime=%s(R²=%.2f) │ "
        "OB=%.1f%% $%.0f │ BTC=%s │ WinP=%.1f%% (model %.1f%%) Edge=%.1fpp "
        "RoR=%.1f%% Conf=%.0f │ %d @ %dc = $%.2f │ %.1fmin%s",
        direction, ticker[-15:], contract_price,
        regime.value, r_squared,
        ob["imbalance"] * 100, ob["total_depth"],
        momentum_verdict, win_prob * 100, model_prob * 100, edge * 100,
        ror * 100, conf, count, limit_price, cost, mins, wlb_str
    )
    if count == 1 and "rounded up" in size_reason:
        log.info("Sizing │ %s", size_reason)

    last_signal_desc = f"SIGNAL {direction} conf={conf:.0f} p={win_prob:.2f}"
    # balance_before = the realized balance for this cycle (fetched before any
    # order cost is debited) → the exact recovery target if this trade loses.
    place_order(ticker, direction, bet, limit_price, win_prob, edge,
                balance_before=balance, count=count)


# ─────────────────────────────────────────────────────────────────────────────
# DAILY SESSION ROLLOVER
# ─────────────────────────────────────────────────────────────────────────────

def maybe_roll_session_day(current_balance: float) -> bool:
    """Reset the daily risk budget at the UTC day boundary.

    The daily-loss cap is, by name, a *daily* limit — but the old code latched
    `_session_halted` permanently, so once the cap was hit the bot slept "1hr"
    forever and needed a redeploy to trade again (2026-06-19: idle 13:25→next
    day). Here a new UTC day clears the halt, re-baselines the drawdown
    references to the live balance, and wipes the per-session ticker/streak
    state — so a fresh day always starts with a fresh budget and no manual
    intervention. Returns True when a rollover happened.

    v10.2.0: this is also what re-arms the DAILY PROFIT TARGET. session_start_balance
    is re-based to the live balance here, so today's +3% goal is 3% of what today
    opened with (yesterday's profit compounds into the new target), and clearing
    `_session_halted` is what lets a bot that banked its target yesterday trade
    again this morning — no redeploy, no manual reset.
    """
    global _session_day, _session_halted, _halt_reason, session_start_balance
    global session_stop_threshold, daily_pnl, paper_daily_pnl, consecutive_losses
    global session_state, streak_pause_until, live_daily_realized
    global live_wins, live_losses, _live_prior

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today == _session_day:
        return False

    was_halted   = _session_halted
    was_target   = _halt_reason == "profit_target"
    _session_day = today
    _session_halted        = False
    _halt_reason           = ""
    session_start_balance  = current_balance
    session_stop_threshold = current_balance * SESSION_STOP_FRACTION
    daily_pnl              = 0.0
    paper_daily_pnl        = 0.0
    live_daily_realized    = 0.0
    consecutive_losses     = 0
    streak_pause_until     = 0.0
    session_state          = SessionState.ACTIVE
    session_traded_tickers.clear()

    # The session W/L tally is DAILY state: it feeds performance_guard()'s
    # Wilson floor and the "Today's Tally" line in the win/loss alerts. Left
    # uncleared, a sub-50% stretch froze the guard PERMANENTLY for the life of
    # the process — blocked trading produces no new samples, so the lower bound
    # could never heal (the same lock-up class v9.0.8 fixed for boot-seeded
    # history, reachable here with ≥MIN_SAMPLE_TRADES genuinely-settled trades).
    # A fresh day starts a fresh sample, exactly like every other halt above;
    # the persistent all-time record lives in LifetimeStats, not here.
    live_wins   = 0
    live_losses = 0
    _live_prior = OB_BASE_ACCURACY

    # v9.7.0: a fresh trading day re-enters the slow-roll ramp from the floor so
    # the first trade of the day is small and scales up only as the edge re-proves
    # itself, rather than firing full size cold. Recovery is the deeper claw-back
    # tier and takes priority — never override it. start() is a safe no-op when
    # the ramp is disabled (the v10.2.0 DEFAULT — the slow-roll is itself a
    # laddering approach) or there is no sub-full room, in which case sizing stays
    # at the flat normal fraction.
    if not recovery.active:
        probation.start(_probation_rungs(), effective_normal_trade_pct(), reason="Daily slow-roll")

    target = daily_profit_target_dollars()
    goal   = (f" │ today's goal ${target:.2f} (+{DAILY_PROFIT_TARGET_PCT*100:.1f}%)"
              if target > 0 else "")
    log.info("🔄 New trading day %s │ balance $%.2f │ daily budget reset%s%s",
             today, current_balance,
             " (target hit yesterday — trading resumed)" if was_target
             else " (halt cleared)" if was_halted else "", goal)
    # Overwrite yesterday's record straight away, so a restart in the first
    # cycles of the new day restores TODAY's baseline rather than falling back
    # to a fresh boot (or, worse, adopting a record the rollover just voided).
    save_daily_state()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_restart_for_mode_change() -> None:
    """Apply a pending paper↔live flip. If MODE_OVERRIDE_PATH now differs from the
    running DEMO_MODE and the bot is FLAT (no open position), restart into the new
    mode. Restarting only when flat guarantees an in-flight position is never
    abandoned by the switch. The exit is non-zero so Railway's ON_FAILURE restart
    policy boots a fresh process that reads the new mode at startup (DEMO_MODE =
    _boot_demo_mode()). No-op when no flip is pending. Never raises."""
    try:
        target = _read_mode_override()
        if target is None or target == DEMO_MODE or open_orders:
            return
        new_mode = "PAPER 🟡" if target else "LIVE 🔴"
        log.warning("Mode flip requested → %s. Bot is flat; restarting to apply.", new_mode)
        tg.send_status_message(
            f"🔀 Switching to {new_mode}. Restarting now to apply — back in a few "
            f"seconds trading in {'paper' if target else 'LIVE (real money)'} mode.")
    except Exception as e:  # a flip must never crash the loop; retry next cycle
        log.warning("Mode-change check error (will retry): %s", e)
        return
    logging.shutdown()
    os._exit(3)             # non-zero → Railway ON_FAILURE restart → boot reads new mode


def main() -> None:
    # ── CRITICAL GLOBAL DECLARATION RULE ─────────────────────────────────────
    # The following module-level mutable containers must NEVER appear here:
    #   open_orders, active_tickers, trade_history, session_traded_tickers,
    #   _processed_settlement_ids, btc_prices, btc_returns, _prev_ob
    #
    # These are mutated IN-PLACE (dict/set/deque methods). Declaring them in
    # a global statement causes Python to mark every reference inside main()
    # as a local variable. The set comprehension that reads active_tickers
    # then raises UnboundLocalError before any local assignment has occurred.
    # ─────────────────────────────────────────────────────────────────────────
    global session_start_balance, session_stop_threshold, daily_pnl
    global paper_balance, paper_daily_pnl, last_trade_ts
    global consecutive_losses, last_signal_desc, running_pnl
    global live_wins, live_losses, streak_pause_until, live_daily_realized
    global _last_known_balance, _shutdown_requested, _session_start_ts
    global _session_halted, _halt_reason, session_state, _session_day

    init_base_url()

    # Default matches .env.example so a manual deploy that skips the var starts
    # at the same documented paper balance.
    paper_balance         = _env_dollars("PAPER_BALANCE", 1000.0)
    _session_start_ts     = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _session_day          = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    _session_halted       = False
    _halt_reason          = ""
    session_state         = SessionState.ACTIVE

    # In-place resets — no global declaration needed
    session_traded_tickers.clear()
    _processed_settlement_ids.clear()

    log.info("━" * 70)
    log.info("  FLIPPULSE %s │ %s", BOT_VERSION, "PAPER 🟡" if DEMO_MODE else "LIVE 🔴")
    log.info("  Trading Format: %s", TRADING_FORMAT)
    log.info("  Start: %s", _session_start_ts)
    log.info("  Regime R²≥%.2f | VolCap=%.3f%% | Circuit=%.2f%%",
             R2_TREND_THRESHOLD, VOLATILITY_CAP_PCT, VOL_CIRCUIT_BREAKER)
    log.info("  OB depth≥$%.0f imb≥%.0f%% | WinP≥%.0f%% Edge≥%.0f%%",
             MIN_OB_DEPTH, OB_IMBALANCE_THRESH * 100, MIN_WIN_PROB * 100, MIN_EDGE_PCT * 100)
    log.info("  AGREE-gate=%s | MinConf=%d | Breakeven≤%dc | NEUTRALdrag=%.3f",
             "ON" if REQUIRE_AGREE_MOMENTUM else "OFF",
             MIN_CONFIDENCE, YES_BREAKEVEN_PRICE, NEUTRAL_ACCURACY_DRAG)
    log.info("  Momentum lookback=%d intervals | thresh≥%.2f%% or R²≥%.2f",
             MOMENTUM_LOOKBACK, MOMENTUM_THRESH_PCT, MOMENTUM_R2_MIN)
    # "Sizing (% of balance)" is a provisioner green-verify boot marker — keep
    # the prefix in sync with onboarding/provisioner.py LOG_MARKERS.
    log.info("  Sizing (%% of balance): normal=%.1f%% recovery=%.1f%% max=%.1f%%%s",
             NORMAL_TRADE_PCT * 100, RECOVERY_TRADE_PCT * 100, MAX_TRADE_PCT * 100,
             " (RECOVERY active, target $%.2f)" % recovery.target_balance
             if recovery.active else
             " (PROBATION ramp, rung %.1f%%→full %.1f%%)"
             % (probation.current_size() * 100, NORMAL_TRADE_PCT * 100)
             if probation.active else "")
    log.info("  Liquidity: book ≥ %.1f× the order (floor $%.0f depth)",
             MIN_DEPTH_STAKE_MULT, MIN_OB_DEPTH)
    log.info("  Daily profit target: %s",
             ("+%.1f%% of the day's opening balance — trading stops when hit"
              % (DAILY_PROFIT_TARGET_PCT * 100))
             if DAILY_PROFIT_TARGET_ENABLED and DAILY_PROFIT_TARGET_PCT > 0
             else "OFF (trades the full day)")
    log.info("  SessionScore≥%d", MIN_SESSION_SCORE)
    log.info("  TimePrior: %dh buckets fullN=%d | now=%s prior=%.3f n=%d",
             BUCKET_GROUP_HOURS, BUCKET_PRIOR_FULL_N, bucket_stats.key_now(),
             *bucket_stats.prior_for(bucket_stats.key_now()))
    log.info("━" * 70)

    tg.validate_telegram_connection()

    live_wins          = 0
    live_losses        = 0
    streak_pause_until = 0.0

    if DEMO_MODE:
        running_pnl            = 0.0
        session_start_balance  = paper_balance
        session_stop_threshold = paper_balance * SESSION_STOP_FRACTION
        # A restart must not hand the day a fresh +3% budget: adopt today's
        # persisted opening balance, realized P&L and halt when there is one.
        restore_daily_state(paper_balance)
        recovery.reconcile_on_boot(paper_balance)
        probation.reconcile_on_boot()
        billing.reconcile_on_boot(paper_balance)
        log_size_feasibility(paper_balance)
        telegram_boot(paper_balance)
    else:
        # Boot-time balance fetch: retry a transient Kalshi/API blip in-process
        # first, then exit NON-ZERO. railway.toml uses restartPolicyType
        # ON_FAILURE, which only restarts non-zero exits — a plain `return`
        # here (exit 0) left the bot permanently, silently down after a
        # transient outage during deploy. sys.exit(1) hands the outage to
        # Railway's restart policy instead.
        bal         = 0.0
        balance_err: Optional[Exception] = None
        for attempt in range(5):
            if attempt:
                time.sleep(15 * attempt)          # 15s, 30s, 45s, 60s (~2.5 min total)
            try:
                bal = get_live_balance(allow_cached_zero=False)
                balance_err = None
                break
            except Exception as e:
                balance_err = e
                log.warning("Starting balance fetch attempt %d/5 failed: %s",
                            attempt + 1, e)
        if balance_err is not None:
            log.error("Cannot fetch starting balance after 5 attempts — exiting "
                      "for restart: %s", balance_err)
            tg.send_telegram_message(f"🛑 FlipPulse {BOT_VERSION} boot failed: balance error")
            sys.exit(1)
        if bal <= 0.0:
            log.error("Starting balance $0 — exiting for restart")
            tg.send_telegram_message(f"🛑 FlipPulse {BOT_VERSION} boot failed: balance=$0")
            sys.exit(1)
        _last_known_balance    = bal
        session_start_balance  = bal
        session_stop_threshold = bal * SESSION_STOP_FRACTION
        open_orders.clear()
        active_tickers.clear()
        consecutive_losses = 0
        running_pnl        = 0.0
        live_daily_realized = 0.0
        # A restart must not hand the day a fresh +3% budget: adopt today's
        # persisted opening balance, realized P&L and halt when there is one.
        restore_daily_state(bal)
        recovery.reconcile_on_boot(bal)
        probation.reconcile_on_boot()
        billing.reconcile_on_boot(bal)
        log_size_feasibility(bal)
        telegram_boot(bal)

    resolve_cycle = 0

    while not _shutdown_requested:
        try:
            # Apply a pending paper↔live flip as soon as the bot is flat (checked
            # first so it also fires while halted, when there is no open position).
            _maybe_restart_for_mode_change()
            if _session_halted:
                # Halt is paused-for-the-day, not forever: poll often enough to
                # catch the UTC rollover that clears it (maybe_roll_session_day),
                # then resume automatically — no redeploy needed.
                # A halt stops NEW entries, never the bookkeeping on trades
                # already on the book: keep resolving settlements and cancelling
                # stale orders, or a position open when the daily target landed
                # would sit unsettled (and its ticker locked) until tomorrow.
                resolve_open_orders()
                cancel_stale_orders()
                halt_bal = paper_balance if DEMO_MODE else get_live_balance()
                # The scheduled briefing still lands while halted (the day's
                # summary is exactly what a paused customer wants to see).
                report_scheduler.maybe_send(halt_bal)
                write_status_snapshot(halt_bal)
                save_daily_state()
                if not maybe_roll_session_day(halt_bal):
                    log.info("Halted for the day (%s) — paused until UTC rollover.",
                             _halt_reason or "halted")
                    time.sleep(HALT_POLL_INTERVAL_SECS)
                    continue

            # Telegram policy: messages fire on a trade entry, a trade settlement,
            # a triggered guardrail, or the twice-daily scheduled briefing
            # (report_scheduler, below). No other periodic heartbeat — liveness is
            # otherwise pull-based via the /status and /health-log commands.
            ingest_btc_price()

            market = get_active_market()
            if not market:
                log.info("No active market — waiting %ds", POLL_INTERVAL)
                last_signal_desc = "no market"
                time.sleep(POLL_INTERVAL)
                continue

            current_ticker      = market.get("ticker", "")
            tickers_with_orders = {t.get("ticker", "") for t in open_orders.values()}
            expired = {t for t in active_tickers
                       if t != current_ticker and t not in tickers_with_orders}
            if expired:
                active_tickers.difference_update(expired)
                log.info("Expired locks: %s", expired)

            current_balance = paper_balance if DEMO_MODE else get_live_balance()
            maybe_roll_session_day(current_balance)
            # Recovery win-rate restore runs first: a strong recovery win rate
            # while the stake is held below base fast-tracks straight back to the
            # full stake (no balance target, no probation ramp). Otherwise fall
            # through to the normal balance-target exit.
            if not maybe_winrate_restore(current_balance):
                # Recovery EXIT check runs every cycle, independent of trading, so
                # the bot can never wedge in recovery once balance reaches target.
                # On a real exit, begin the graduated probation ramp instead of
                # snapping straight back to full size (no-op if the ramp is disabled
                # or there is no sub-full room, in which case sizing resumes normal).
                # In "No Stake Change" mode the stake never dropped, so there is
                # nothing to ramp back from — skip the ramp entirely.
                if recovery.maybe_exit(current_balance) and not recovery_no_stake_change_enabled():
                    probation.start(_probation_rungs(), effective_normal_trade_pct())
            # Performance-fee billing: close the month + report the fee at the UTC
            # month boundary (observability only; never moves money).
            billing.maybe_month_rollover(current_balance)
            run_decision(market, current_balance)
            write_status_snapshot(current_balance)
            # Today's opening balance, realized P&L and halt state — so a restart
            # resumes the day instead of re-arming a fresh +3% hunt.
            save_daily_state()
            # Twice-daily P&L + win-rate briefing (9am/9pm ET by default). Idempotent
            # per slot, so calling it every cycle only fires once per scheduled time.
            report_scheduler.maybe_send(current_balance)

            resolve_cycle += 1
            if resolve_cycle % 3 == 0:
                resolve_open_orders()
                cancel_stale_orders()

                if DEMO_MODE:
                    resolved = [t for t in trade_history
                                if t.get("result") in ("win", "loss")]
                    wins  = sum(1 for t in resolved if t["result"] == "win")
                    total = len(resolved)
                    wr    = wins / total if total > 0 else 0.0
                    log.info("📋 PAPER │ $%.2f │ PnL=$%+.2f │ WR=%.1f%% │ Prior=%.3f │ %s",
                             paper_balance, paper_daily_pnl, wr * 100,
                             _live_prior, session_state.value)
                else:
                    live_bal  = get_live_balance()
                    # v9.3.1: PnL shown is REALIZED (settled) dollars — the same
                    # value the daily-loss breaker uses. `cash` is the raw
                    # balance−start delta, which dips by an open position's outlay
                    # until it settles and must NOT be read as a loss.
                    cash_delta = live_bal - session_start_balance
                    daily_pnl  = live_daily_realized
                    wlb       = wilson_lower_bound(live_wins, live_wins + live_losses)
                    log.info(
                        "Portfolio │ $%.2f │ PnL=$%+.2f │ cash=$%+.2f │ WR=%d/%d LB=%.1f%% │ Prior=%.3f │ %s",
                        live_bal, daily_pnl, cash_delta,
                        live_wins, live_wins + live_losses,
                        wlb * 100, _live_prior, session_state.value,
                    )

                if recovery.active:
                    log.info(recovery.status_line(current_balance))
                elif probation.active:
                    log.info(probation.status_line())

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.error("Unexpected: %s", e, exc_info=True)
            time.sleep(POLL_INTERVAL)

    final = paper_balance if DEMO_MODE else get_live_balance()
    log.info("Shutdown. Final balance: $%.2f", final)
    tg.send_status_message(f"🛑 FlipPulse {BOT_VERSION} stopped. Final: ${final:.2f}")


if __name__ == "__main__":
    # Single-customer Telegram command listener (/status, /health-log). Runs in a
    # daemon thread and never touches the trading path; a no-op when Telegram env
    # vars are unset. Guarded so observability can never stop the bot booting.
    try:
        import command_bot
        command_bot.start_command_bot()
    except Exception as _cb_err:  # pragma: no cover - must never break trading
        log.warning("Command bot not started: %s", _cb_err)

    # Customer self-service web dashboard (login-protected). Runs in a daemon
    # thread reading/writing the same /data override files as /risk; a no-op when
    # DASHBOARD_PASSWORD is unset. Guarded so it can never stop the bot booting.
    try:
        import dashboard
        dashboard.start_dashboard()
    except Exception as _db_err:  # pragma: no cover - must never break trading
        log.warning("Dashboard not started: %s", _db_err)

    main()
