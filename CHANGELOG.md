# FlipPulse changelog

> Extracted from the historical `bot.py` header (v9.0.7 → current). Kept here so the entrypoint stays readable.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  FLIPPULSE (MarkeyMachine core)  v10.3.3  —  Production Build                ║
║  "No disassemble."                                                           ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.3.3 — WITHDRAWALS NO LONGER FEED RECOVERY MODE (owner directive).       ║
║                                                                              ║
║  Recovery is meant to answer one question: has the bot earned back what it   ║
║  lost trading? It was answering a different one. Entry recorded the balance  ║
║  immediately before the losing trade and exit waited for the live balance to ║
║  climb back to that number — an absolute cash target that cannot tell a      ║
║  trading loss from money the customer moved off Kalshi. Three consequences,  ║
║  all of them the withdrawal's fault and none of them the bot's:              ║
║    • Withdraw between entry and settlement → the target still contained the  ║
║      withdrawn cash, so a $3 loss armed a claw-back of $3 + the withdrawal.  ║
║    • Withdraw mid-recovery → the target went permanently out of reach and    ║
║      recovery latched; reconcile_on_boot dutifully resumed it forever.       ║
║    • Deposit mid-recovery → the target was met by the transfer alone and     ║
║      recovery cleared without a dollar being earned back.                    ║
║                                                                              ║
║  FIX: RecoveryState now stores `deficit` — the realized trade dollars still  ║
║  owed — instead of a balance. It is seeded with the size of the losing trade ║
║  and moves ONLY when a trade settles (a win pays it down, a further loss     ║
║  deepens it, via on_trade_settled → apply_pnl). Exit is "deficit paid",      ║
║  still checked every cycle and on boot. Deposits and withdrawals touch       ║
║  nothing. The balance to climb back to is now DERIVED for display            ║
║  (target_for = current balance + what is owed), so it re-bases with the      ║
║  account: withdraw $400 and the shown target drops $400, it does not become  ║
║  $400 of extra hole. Persisted state is schema 2; a schema-1 file is         ║
║  migrated once at boot (deficit = old target − balance) and is pure trade    ║
║  P&L from then on. /status and the dashboard gain `recovery_deficit`.        ║
║                                                                              ║
║  Unchanged: what ARMS recovery (a settled full-size loss), the No-Stake-     ║
║  Change default, the win-rate restore, the probation ramp, every guard.      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  v10.3.2 — THE DAILY HALT NO LONGER DEPENDS ON A FILE SURVIVING.             ║
║                                                                              ║
║  v10.3.1 persisted the day's state, which fixes the restart — but only when  ║
║  the record is there to read. Three ways it is not: the deploy that FIRST    ║
║  shipped the persistence (no file existed yet — this is what cleared the     ║
║  2026-08-04 halt when its own PR merged and Railway redeployed), a volume    ║
║  that is not mounted where DAILY_STATE_PATH points (every write failed       ║
║  silently), and a wiped/re-created volume. Two layers now:                   ║
║                                                                              ║
║  1. THE PATH IS PROVEN AT BOOT. verify_daily_state_path() write-probes the   ║
║     directory, falls back to RAILWAY_VOLUME_MOUNT_PATH, and logs an ERROR    ║
║     when nothing is durable — instead of discovering it on the redeploy      ║
║     that needed it.                                                          ║
║  2. THE EXCHANGE IS THE BACKSTOP. With no usable local record, a LIVE boot   ║
║     rebuilds today from Kalshi's own settlements since 00:00 UTC             ║
║     (reconcile_today_from_exchange): today's realized P&L, the day's opening ║
║     balance inferred as balance − realized (errs LOW, so it stops earlier,   ║
║     never later), the session-stop floor, and the halt itself if the goal    ║
║     was already banked. Kalshi remembers the day whatever happens to this    ║
║     container, so the +3% goal holds for the whole UTC day across any number ║
║     of restarts, redeploys and merged PRs.                                   ║
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
```
