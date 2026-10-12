# RAIM Parameter Registry

The status of each parameter is one of:
- `PRIOR`: a cautious starting value, not validated
- `MEASURED`: estimated on our data, in-sample
- `VALIDATED`: holds out of sample under FR-V5
- `INVALIDATED`

**No parameter is VALIDATED yet. No system run has happened.**

| Param | Value | Source | Status | Evidence that would invalidate it |
|---|---|---|---|---|
| `gate0.markout_horizon_s` | 5 | Design choice | PRIOR | Edge sign flips between 5 s and 30/60 s markouts |
| `gate0.min_capture_days` | 7 | Design choice | PRIOR | Regime coverage insufficient: no high-vol day captured |
| `venue.binanceus.maker_fee_bps` | 0.0 | Binance.US blog 2026-04-22 | PRIOR (unverified for this account) | Authenticated fee endpoint or a fill shows > 0 |
| `venue.binanceus.taker_fee_bps` | 2.0 | Binance.US blog 2026-04-22 | PRIOR | Same |
| `feed.stale_ms` | 1500 | Design choice | PRIOR | Normal inter-update gaps exceed it, causing false cancels, or toxic moves happen inside it |
| `feed.clock_skew_alarm_ms` | 250 | Design choice | PRIOR | Measured skew distribution |
| `regime.r4_pull_p` | 0.70 | Brief | PRIOR | Walk-forward shows a better OOS loss-avoidance/uptime trade-off |
| `regime.r4_release_p` | 0.40 | Brief | PRIOR | Same |
| `regime.r4_pull_N` | 5 | Design choice | PRIOR | Flapping rate or latency-to-pull analysis |
| `risk.qmax.z` | 2.33 | 99% one-sided normal | PRIOR | Fat tails: realized unwind losses exceed B more than 1% of the time |
| `risk.qmax.depth_frac_c` | 0.10 | Design choice | PRIOR | Measured market impact of unwinds |
| `quote.gamma` | — | Avellaneda–Stoikov 2008 (illustrative values in paper, not crypto-calibrated) | PRIOR (unset) | Calibrated per instrument/regime |
| `quote.k` | — | To be estimated from fill intensity vs distance from mid | UNSET | — |
| `sim.latency_ms` | — | Unknown; measure in PAPER | UNSET | — |
| `sim.queue_model` | pro-rata cancels (pessimistic/optimistic brackets) | Design choice | PRIOR | PAPER fill-rate divergence |
| `slow.poll_max_rps` | 1.0 | Brief | PRIOR | tradingview-mcp throttling errors |
| `slow.decay_tau_s` | 900 | Design choice | PRIOR | Slow-state usefulness vs age analysis |
| `slow.mcp_version` | 0.8.1 | PyPI latest as of 2026-10-12 | PRIOR | Contract test fails |
| `rate_limit.headroom` | 0.5 | Design choice | PRIOR | Rejects or bans observed |
