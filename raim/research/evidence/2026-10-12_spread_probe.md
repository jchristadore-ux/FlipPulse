# Spread probe — 2026-10-12 ~03:10 UTC

**What this is:** a single ~3-minute sample of public REST top-of-book data. It is preliminary Gate 0 evidence about spreads and nothing more.

**What this is not:** it does not measure adverse selection, fill probability, queue position or markouts. It also covers one Sunday-night (US) window, so it is not representative of other sessions.

Reproduce with `python3 raim/research/spread_probe.py 60`. That takes 60 samples at a 3-second interval. Coinbase was sampled separately (40 × 3 s) because the first pass had no User-Agent header and the requests were rejected.

`med_depth10bp_usd` is the mean of bid-side and ask-side USD notional within ±10 bps of mid.

| venue | pair | n | median spread (bps) | p90 spread (bps) | median depth ±10 bp (USD/side) |
|---|---|---|---|---|---|
| coinbase | BTC-USD | 40 | 0.001 | 0.001 | 2,611,800 |
| coinbase | ETH-USD | 40 | 0.059 | 0.275 | 942,252 |
| coinbase | SOL-USD | 40 | 0.896 | 1.792 | 303,706 |
| coinbase | DOGE-USD | 40 | 3.455 | 3.458 | 50,456 |
| coinbase | LINK-USD | 40 | 1.499 | 2.248 | 57,922 |
| coinbase | AVAX-USD | 40 | 2.764 | 2.765 | 24,086 |
| kraken | XBTUSD | 60 | 0.012 | 0.012 | 1,246,259 |
| kraken | ETHUSD | 60 | 0.039 | 0.039 | 518,798 |
| kraken | SOLUSD | 60 | 0.896 | 0.896 | 936,524 |
| kraken | XDGUSD | 60 | 0.012 | 0.208 | 43,624 |
| kraken | LINKUSD | 60 | 1.497 | 3.506 | 49,793 |
| kraken | AVAXUSD | 60 | 0.921 | 1.843 | 78,907 |
| binanceus | BTCUSDT | 60 | 0.044 | 0.044 | 291,477 |
| binanceus | ETHUSDT | 60 | 0.236 | 0.393 | 84,556 |
| binanceus | SOLUSDT | 60 | 0.895 | 0.895 | 31,922 |
| binanceus | DOGEUSDT | 60 | 4.605 | 5.756 | 9,866 |
| binanceus | LINKUSDT | 60 | 4.500 | 5.999 | 35,683 |
| binanceus | AVAXUSDT | 60 | 6.443 | 7.358 | 2,266 |
| binanceus | BTCUSD | 60 | 1.359 | 1.705 | 131,310 |
| binanceus | ETHUSD | 60 | 0.275 | 0.669 | 90,415 |
| binanceus | SOLUSD | 60 | 1.792 | 2.689 | 18,757 |

## Observations

1. **Most major pairs are tick-constrained.** Their spread is one price increment. On those books the maker edge comes from queue priority, not from spread width.
2. **The widest spreads are on Binance.US alt/USDT pairs.** DOGE, LINK and AVAX show 4.5–6.4 bps. That is still at most about 3.2 bps of half-spread.
3. **Coinbase and Kraken fail Gate 0 at retail fee tiers.** No pair sampled has a half-spread above about 1.75 bps (Coinbase DOGE-USD). Coinbase's retail maker fee is reported at about 40 bps by secondary sources (unverified). Kraken's tier-1 maker fee is 40 bps per its fee page. Even Kraken's lowest tier with a non-zero maker fee, 2 bps at $5M+ volume, is above the half-spread of almost every pair sampled. A 0% maker fee needs $10M+ in 30-day volume. Gate 0 fails before any adverse selection is counted.
4. **Binance.US is the only candidate where Gate 0 can pass.** Its published maker fee is 0%. Passing then depends entirely on measured E[adverse selection] being below about 2.2–3.2 bps on those alt/USDT pairs. Binance.US is a thin venue whose prices likely follow Coinbase and Binance global, so adverse selection may well exceed that. **Unknown — must be measured** with trade-tape markouts (FR-G0).
