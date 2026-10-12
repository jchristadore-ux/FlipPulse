"""One-off top-of-book spread probe (public REST). Preliminary Gate 0 evidence only."""
import json, statistics, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

PAIRS = {
    "coinbase": {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD", "DOGE": "DOGE-USD", "LINK": "LINK-USD", "AVAX": "AVAX-USD"},
    "kraken": {"BTC": "XBTUSD", "ETH": "ETHUSD", "SOL": "SOLUSD", "DOGE": "XDGUSD", "LINK": "LINKUSD", "AVAX": "AVAXUSD"},
    "binanceus": {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "DOGE": "DOGEUSDT", "LINK": "LINKUSDT", "AVAX": "AVAXUSDT",
                  "BTC/USD": "BTCUSD", "ETH/USD": "ETHUSD", "SOL/USD": "SOLUSD"},
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "raim-probe/0.1"}), timeout=10) as r:
        return json.load(r)


def tob(venue, sym):
    if venue == "coinbase":
        d = get(f"https://api.exchange.coinbase.com/products/{sym}/book?level=2")
        b, a = d["bids"], d["asks"]
    elif venue == "kraken":
        d = get(f"https://api.kraken.com/0/public/Depth?pair={sym}&count=25")
        k = next(iter(d["result"]))
        b, a = d["result"][k]["bids"], d["result"][k]["asks"]
    else:
        d = get(f"https://api.binance.us/api/v3/depth?symbol={sym}&limit=50")
        b, a = d["bids"], d["asks"]
    bid, ask = float(b[0][0]), float(a[0][0])
    mid = (bid + ask) / 2
    spread_bps = (ask - bid) / mid * 1e4
    # USD notional within 10 bps of mid, each side
    depth = sum(float(p) * float(q) for p, q, *_ in b if float(p) >= mid * (1 - 1e-3)) + \
            sum(float(p) * float(q) for p, q, *_ in a if float(p) <= mid * (1 + 1e-3))
    return spread_bps, depth / 2


def main(n=int(sys.argv[1]) if len(sys.argv) > 1 else 40, dt=3.0):
    res = {(v, k): ([], []) for v, m in PAIRS.items() for k in m}
    jobs = [(v, k, s) for v, m in PAIRS.items() for k, s in m.items()]
    with ThreadPoolExecutor(8) as ex:
        for _ in range(n):
            t0 = time.time()
            for (v, k, _s), out in zip(jobs, ex.map(lambda j: _safe(j[0], j[2]), jobs)):
                if out:
                    res[(v, k)][0].append(out[0]); res[(v, k)][1].append(out[1])
            time.sleep(max(0, dt - (time.time() - t0)))
    print(f"{'venue':10} {'pair':8} {'n':>3} {'med_spr_bps':>11} {'p90_spr_bps':>11} {'med_depth10bp_usd':>18}")
    for (v, k), (s, d) in res.items():
        if not s:
            print(f"{v:10} {k:8} {0:>3} {'n/a':>11}"); continue
        s2 = sorted(s)
        print(f"{v:10} {k:8} {len(s):>3} {statistics.median(s):>11.3f} {s2[int(0.9*(len(s2)-1))]:>11.3f} {statistics.median(d):>18,.0f}")


def _safe(v, s):
    try:
        return tob(v, s)
    except Exception as e:  # noqa
        return None


if __name__ == "__main__":
    main()
