"""Tests for the trading engine's pure money-path functions — the code with the
richest bug history in the changelog (settlement PnL reconstruction, PEM
normalization, percentage sizing, edge math) previously had zero coverage.

bot.py requires Kalshi credentials at import, so a throwaway RSA key is
generated and injected before the import. All persistence is disabled so no
state files are written to the repo.

Run: pytest test_bot_engine.py
"""

import base64
import os
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()).decode()

os.environ.setdefault("KALSHI_API_KEY_ID", "test-key")
os.environ.setdefault("KALSHI_PRIVATE_KEY_PEM_B64",
                      base64.b64encode(_PEM.encode()).decode())
os.environ.setdefault("DEMO_MODE", "true")
for _persist in ("RECOVERY_PERSIST", "PROBATION_PERSIST",
                 "BUCKET_PERSIST", "BILLING_PERSIST", "LIFETIME_PERSIST"):
    os.environ.setdefault(_persist, "false")

import bot  # noqa: E402  (env must be set first)


# ── settlement PnL reconstruction (_extract_realized_dollars) ─────────────────
# v9.0.7's ~100x profit-inflation bug lived here: `revenue` arrives in CENTS,
# the *_dollars cost fields in dollars.

def test_settlement_real_kxbtc15m_schema():
    rec = {"revenue": 16900, "yes_total_cost_dollars": 0.0,
           "no_total_cost_dollars": 99.71, "fee_cost": 0.58,
           "market_result": "no", "ticker": "KXBTC15M-X"}
    assert bot._extract_realized_dollars(rec) == round(169.0 - 99.71 - 0.58, 4)


def test_settlement_unfilled_order_is_zero_not_a_loss():
    rec = {"revenue": 0, "yes_total_cost_dollars": 0.0,
           "no_total_cost_dollars": 0.0, "fee_cost": 0.0}
    assert bot._extract_realized_dollars(rec) == 0.0


def test_settlement_missing_cost_falls_back_to_trade_cost():
    rec = {"revenue": 10000, "fee_cost": 1.0}
    assert bot._extract_realized_dollars(rec, trade_cost=50.0) == round(100.0 - 50.0 - 1.0, 4)


def test_settlement_direct_fields_win_and_cents_convert():
    assert bot._extract_realized_dollars({"realized_pnl_dollars": 12.5}) == 12.5
    assert bot._extract_realized_dollars({"realized_pnl_cents": 1250}) == 12.5


def test_settlement_result_only_record_returns_none():
    # No economics at all → None, so the caller logs instead of miscounting.
    assert bot._extract_realized_dollars({"market_result": "yes"}) is None


# ── PEM normalization (the #1 onboarding paste failure) ───────────────────────

def _loads(pem_text: str) -> bool:
    normalized = bot._normalize_pem(pem_text)
    serialization.load_pem_private_key(normalized.encode(), password=None)
    return True


def test_pem_clean_roundtrip():
    assert _loads(_PEM)


def test_pem_survives_quotes_and_literal_newlines():
    assert _loads('"' + _PEM.replace("\n", "\\n") + '"')


def test_pem_survives_flattened_single_line():
    assert _loads(_PEM.replace("\n", " "))


# ── percentage sizing ─────────────────────────────────────────────────────────

def test_active_trade_size_is_normal_fraction(monkeypatch):
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.15)
    assert bot.active_trade_size(1000.0) == 100.0


def test_active_trade_size_clamped_by_max_pct(monkeypatch):
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.50)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.15)
    assert bot.active_trade_size(1000.0) == 150.0


def test_recovery_mode_uses_recovery_fraction(monkeypatch):
    # The reduced recovery tier only applies with "No Stake Change" OFF; it is ON
    # by default from v10.2.0 (flat risk — see test_flat_risk_no_ladder below).
    monkeypatch.setattr(bot, "RECOVERY_NO_STAKE_CHANGE", False)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", "/nonexistent/nsc.json")
    monkeypatch.setattr(bot.recovery, "active", True)
    monkeypatch.setattr(bot, "RECOVERY_TRADE_PCT", 0.03)
    assert bot.active_trade_fraction() == 0.03


def test_probation_rungs_step_between_recovery_and_normal(monkeypatch):
    monkeypatch.setattr(bot, "RECOVERY_TRADE_PCT", 0.03)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "PROBATION_RUNG_STEP_PCT", 0.035)
    monkeypatch.setattr(bot, "PROBATION_RUNGS_RAW", "")
    assert bot._probation_rungs() == [0.03, 0.065]
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.02)   # no room → no ramp
    assert bot._probation_rungs() == []


def test_kelly_bet_gates_out_negative_expectancy(monkeypatch):
    # p=0.5 at 50c is exactly break-even → full_kelly 0 → no bet.
    assert bot.kelly_bet(0.50, 50, 1000.0) == 0.0
    # Positive expectancy → the active-mode fraction of balance.
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.15)
    assert bot.kelly_bet(0.70, 50, 1000.0) == 100.0


# ── edge & statistics ─────────────────────────────────────────────────────────

def test_calc_edge():
    assert round(bot.calc_edge(0.70, 50), 6) == round(0.7 * 0.5 - 0.3 * 0.5, 6)
    assert bot.calc_edge(0.70, 0) == 0.0
    assert bot.calc_edge(0.70, 100) == 0.0


def test_edge_return_on_risk_is_per_dollar_staked():
    # 8pp of edge is a 26.7% return on a 30c stake but only 12.3% on a 65c one —
    # the distinction MIN_EDGE_PCT (payout-denominated) cannot express.
    assert round(bot.edge_return_on_risk(0.08, 30), 4) == round(0.08 / 0.30, 4)
    assert round(bot.edge_return_on_risk(0.08, 65), 4) == round(0.08 / 0.65, 4)
    assert bot.edge_return_on_risk(0.08, 0) == 0.0


# ── v10.1.0 market anchor ─────────────────────────────────────────────────────
# The audited failure: win_prob was a near-constant ~0.70 that ignored the
# quoted price, so calc_edge turned "cheap" into "edgy" — corr(price, edge) was
# -0.88 over 65 signals and the model's 72.5% mean claim realized 37.5%.

def test_anchor_reduces_the_model_to_its_incremental_signal(monkeypatch):
    monkeypatch.setattr(bot, "MARKET_ANCHOR_ENABLED", True)
    monkeypatch.setattr(bot, "MAX_MODEL_EDGE_PP", 0.08)
    # Model claimed 0.729 from a 0.638 base: a 9.1pp lift, clamped to 8pp and
    # applied to the market's 30c → 38%, not the 72.9% the old model reported.
    assert round(bot.market_anchored_win_prob(0.729, 0.638, 30), 4) == 0.38
    # Same signal on a 65c contract lands at 73% — the lift is what carries over,
    # not the level.
    assert round(bot.market_anchored_win_prob(0.729, 0.638, 65), 4) == 0.73


def test_anchor_makes_edge_price_neutral(monkeypatch):
    """calc_edge(price/100 + lift, price) == lift at EVERY price.

    This identity is the whole point: it turns MIN_EDGE_PCT into a bar on
    percentage points of claimed advantage that reads the same at 30c and 65c.
    Pre-anchor, a 5% edge gate passed a 30c contract at p >= 0.36 but demanded
    p >= 0.71 at 65c — that asymmetry WAS the cheapness tilt.
    """
    monkeypatch.setattr(bot, "MARKET_ANCHOR_ENABLED", True)
    monkeypatch.setattr(bot, "MAX_MODEL_EDGE_PP", 0.08)
    for price in (30, 40, 50, 65, 70):
        p = bot.market_anchored_win_prob(0.90, 0.60, price)   # lift clamps to +8pp
        assert round(bot.calc_edge(p, price), 6) == 0.08


def test_anchor_clamps_both_directions_and_can_be_disabled(monkeypatch):
    monkeypatch.setattr(bot, "MAX_MODEL_EDGE_PP", 0.08)
    monkeypatch.setattr(bot, "MARKET_ANCHOR_ENABLED", True)
    assert round(bot.market_anchored_win_prob(0.20, 0.60, 50), 4) == 0.42   # -8pp floor
    assert round(bot.market_anchored_win_prob(0.62, 0.60, 50), 4) == 0.52   # small lift passes through
    monkeypatch.setattr(bot, "MARKET_ANCHOR_ENABLED", False)
    assert bot.market_anchored_win_prob(0.90, 0.60, 50) == 0.90


# ── v10.1.0 sizing floor ──────────────────────────────────────────────────────
# `int(bet * 100 / price)` floored 55 of 65 audited signals to zero contracts —
# 84.6% — after the edge justification had already been logged and sent.

def test_size_contracts_normal_case():
    assert bot.size_contracts(2.14, 40, 100.0)[0] == 5      # 5.35 -> 5
    assert bot.size_contracts(1.00, 25, 100.0)[0] == 4


def test_size_contracts_rounds_up_to_one_inside_the_hard_ceiling(monkeypatch):
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", True)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.30)
    # The exact 2026-07-26 dead case: a $0.37 stake against a 45c contract.
    count, reason = bot.size_contracts(0.37, 45, 14.83)
    assert count == 1                                       # was 0 for three days
    assert "rounded up" in reason


def test_size_contracts_never_breaches_the_max_trade_ceiling(monkeypatch):
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", True)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.02)         # 2% of $10 = $0.20
    count, reason = bot.size_contracts(0.15, 45, 10.0)      # one contract = $0.45
    assert count == 0
    assert "ceiling" in reason


def test_size_contracts_respects_the_customer_reserve(monkeypatch):
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", True)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 1.0)
    # The round-up is sized against tradeable_balance, not the raw balance, so a
    # ring-fenced reserve can never be spent to reach the one-contract minimum.
    monkeypatch.setattr(bot, "effective_reserve", lambda: 9.80)
    assert bot.size_contracts(0.37, 45, 10.0)[0] == 0       # $0.20 tradeable
    monkeypatch.setattr(bot, "effective_reserve", lambda: 0.0)
    assert bot.size_contracts(0.37, 45, 10.0)[0] == 1       # same balance, no reserve


def test_size_contracts_roundup_can_be_turned_off(monkeypatch):
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", False)
    count, reason = bot.size_contracts(0.37, 45, 14.83)
    assert count == 0
    assert "roundup off" in reason


# ── v10.1.0 order-book imbalance ceiling ──────────────────────────────────────

def _book(yes_dollars, no_dollars, yes_mid=50):
    """A synthetic two-level book with the requested dollar depth per side."""
    return {"orderbook_fp": {
        "yes_dollars": [[(yes_mid - 1) / 100.0, yes_dollars / 2.0],
                        [(yes_mid + 1) / 100.0, yes_dollars / 2.0]],
        "no_dollars":  [[(100 - yes_mid - 1) / 100.0, no_dollars / 2.0],
                        [(100 - yes_mid + 1) / 100.0, no_dollars / 2.0]],
    }}


def test_ob_rejects_a_one_sided_book(monkeypatch):
    # 2026-07-23 22:16: OB=99.8% scored Conf=95, drew the window's biggest stake
    # and lost all of it. One stale level on the far side is a liquidity
    # condition, not conviction.
    monkeypatch.setattr(bot, "OB_IMBALANCE_MAX", 0.95)
    monkeypatch.setattr(bot, "MIN_OB_DEPTH", 50.0)
    assert bot.analyze_order_book(_book(9990.0, 10.0), 50) is None


def test_ob_still_accepts_a_strong_but_two_sided_book(monkeypatch):
    monkeypatch.setattr(bot, "OB_IMBALANCE_MAX", 0.95)
    monkeypatch.setattr(bot, "MIN_OB_DEPTH", 50.0)
    monkeypatch.setattr(bot, "OB_IMBALANCE_THRESH", 0.65)
    ob = bot.analyze_order_book(_book(800.0, 200.0), 50)
    assert ob is not None and ob["direction"] == "YES"
    assert round(ob["imbalance"], 2) == 0.80


def test_wilson_lower_bound_needs_sample_and_is_conservative():
    assert bot.wilson_lower_bound(5, 5) == 0.0            # < 10 trades → no verdict
    wlb = bot.wilson_lower_bound(50, 100)
    assert 0.40 < wlb < 0.50                              # below the empirical 50%
    assert bot.wilson_lower_bound(60, 100) > wlb          # monotonic in wins


# ── env parsing & market helpers ──────────────────────────────────────────────

def test_env_dollars_tolerates_human_formatting(monkeypatch):
    monkeypatch.setenv("X_DOLLARS", "$1,000")
    assert bot._env_dollars("X_DOLLARS", 25.0) == 1000.0
    monkeypatch.setenv("X_DOLLARS", "junk")
    assert bot._env_dollars("X_DOLLARS", 25.0) == 25.0
    monkeypatch.delenv("X_DOLLARS")
    assert bot._env_dollars("X_DOLLARS", 25.0) == 25.0


def test_to_cents():
    assert bot._to_cents("0.59") == 59
    assert bot._to_cents(None) == 0


def test_minutes_to_expiry_sentinel_on_missing_close_time():
    assert bot.minutes_to_expiry({}) == 999.0
    from datetime import datetime, timedelta, timezone
    close = (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert 9.5 < bot.minutes_to_expiry({"close_time": close}) <= 10.0


# ── time-of-day bucket prior ──────────────────────────────────────────────────

def test_bucket_key_grouping():
    assert bot.BucketStats.key_for_hour(19) == "18-20"    # default 3h groups
    assert bot.BucketStats.key_for_hour(0) == "00-02"


def test_bucket_prior_shrinks_toward_base_when_thin():
    stats = bot.BucketStats(path="unused.json", persist=False)
    prior, n = stats.prior_for("18-20")
    assert (prior, n) == (bot.OB_BASE_ACCURACY, 0)        # empty → base prior
    stats._data["18-20"] = {"wins": 1, "losses": 2}       # 33% on n=3 (thin)
    prior, n = stats.prior_for("18-20")
    assert n == 3
    assert 1 / 3 < prior < bot.OB_BASE_ACCURACY           # blended, not raw


# ── momentum gate & staleness ─────────────────────────────────────────────────

def test_momentum_gate_requires_agree(monkeypatch):
    monkeypatch.setattr(bot, "REQUIRE_AGREE_MOMENTUM", True)
    assert bot.momentum_gate_ok("AGREE") is True
    assert bot.momentum_gate_ok("NEUTRAL") is False
    assert bot.momentum_gate_ok("CONFLICT") is False
    monkeypatch.setattr(bot, "REQUIRE_AGREE_MOMENTUM", False)
    assert bot.momentum_gate_ok("NEUTRAL") is True


def test_stale_btc_feed_forces_unknown_regime(monkeypatch):
    bot.btc_prices.clear()
    bot.btc_returns.clear()
    try:
        for i in range(bot.MIN_PRICES_FOR_REGIME + 2):
            bot.btc_prices.append(100_000.0 + i * 50)     # a clean uptrend
        monkeypatch.setattr(bot, "_btc_last_ingest_ts", time.time())
        regime, _, _ = bot.compute_regime()
        assert regime != bot.Regime.UNKNOWN               # fresh feed → readable
        monkeypatch.setattr(bot, "_btc_last_ingest_ts",
                            time.time() - bot.BTC_STALE_MAX_SECS - 1)
        regime, _, _ = bot.compute_regime()
        assert regime == bot.Regime.UNKNOWN               # stale feed → no trade
    finally:
        bot.btc_prices.clear()
        bot.btc_returns.clear()


# ── performance guard can never wedge across days ─────────────────────────────
# A sub-50% Wilson lower bound over ≥ MIN_SAMPLE_TRADES blocks all entries, and
# blocked trading produces no new samples — so a guard that latches freezes the
# bot PERMANENTLY (the v9.0.8 lock-up class). v10.0.0 avoided that by resetting
# the tally at the UTC rollover, but at ~2 trades/day the sample never reached
# MIN_SAMPLE_TRADES and the guard was never evaluated once across 2026-07-23→26.
# v10.1.0 scores a rolling window that survives day boundaries and breaks the
# latch with a timed cool-off instead.

def _reset_perf_guard():
    bot._perf_window.clear()
    bot._perf_guard_until = 0.0


def test_perf_guard_ignores_the_daily_tally_and_uses_its_own_window():
    saved = (bot.live_wins, bot.live_losses)
    try:
        _reset_perf_guard()
        # A losing DAY must not trip the guard on its own — the daily counters
        # are display/alert state and reset at midnight.
        bot.live_wins, bot.live_losses = 5, 15
        assert bot.performance_guard() is True
    finally:
        (bot.live_wins, bot.live_losses) = saved
        _reset_perf_guard()


def test_perf_guard_window_survives_the_day_rollover():
    saved = (bot._session_day, bot._session_halted, bot.session_start_balance,
             bot.session_stop_threshold, bot.live_wins, bot.live_losses,
             bot._live_prior)
    try:
        _reset_perf_guard()
        for _ in range(12):
            bot.perf_guard_record(True)
        bot._session_day = "2000-01-01"
        assert bot.maybe_roll_session_day(1000.0) is True
        assert (bot.live_wins, bot.live_losses) == (0, 0)   # daily tally cleared
        assert len(bot._perf_window) == 12                  # guard sample kept
    finally:
        bot.probation.cancel()                              # rollover arms the ramp
        (bot._session_day, bot._session_halted, bot.session_start_balance,
         bot.session_stop_threshold, bot.live_wins, bot.live_losses,
         bot._live_prior) = saved
        _reset_perf_guard()


def test_perf_guard_trips_on_a_bad_window_then_cools_off_instead_of_latching():
    try:
        _reset_perf_guard()
        for i in range(20):                       # 5W/15L — Wilson LB well under 50%
            bot.perf_guard_record(i < 5)
        assert bot.performance_guard() is False   # trips
        assert bot._perf_guard_until > 0.0
        assert bot.performance_guard() is False   # still inside the cool-off

        bot._perf_guard_until = time.time() - 1   # cool-off elapsed
        assert bot.performance_guard() is True    # re-opens...
        assert len(bot._perf_window) == 0         # ...on a cleared sample, so the
        assert bot.performance_guard() is True    # bad window can never re-latch
    finally:
        _reset_perf_guard()


def test_perf_guard_stays_open_on_a_healthy_window():
    try:
        _reset_perf_guard()
        for i in range(20):                       # 15W/5L
            bot.perf_guard_record(i < 15)
        assert bot.performance_guard() is True
        assert bot._perf_guard_until == 0.0
    finally:
        _reset_perf_guard()


def test_day_rollover_clears_session_halt():
    saved = (bot._session_day, bot._session_halted, bot.session_start_balance,
             bot.session_stop_threshold, bot.live_wins, bot.live_losses)
    try:
        bot._session_halted = True
        bot._session_day = "2000-01-01"
        assert bot.maybe_roll_session_day(500.0) is True
        assert bot._session_halted is False
        assert bot.session_stop_threshold == 500.0 * bot.SESSION_STOP_FRACTION
    finally:
        bot.probation.cancel()
        (bot._session_day, bot._session_halted, bot.session_start_balance,
         bot.session_stop_threshold, bot.live_wins, bot.live_losses) = saved


# ── v10.1.0 stale-order cancellation ──────────────────────────────────────────
# Two distinct defects lived in one except-block. A 404 (order not resting —
# almost always already filled) was retried every cycle until the 1200s purge,
# producing 22 identical warnings in the audited window and holding a phantom
# slot against MAX_CONCURRENT_POS. And a cancel that SUCCEEDED left the market in
# session_traded_tickers, so an unfilled order locked the bot out of its own
# live signal with no position to show for it (07-23 20:16, 07-25 13:00).

class _FakeHTTPError(Exception):
    def __init__(self, status):
        super().__init__(f"{status} Client Error")
        self.response = type("R", (), {"status_code": status})()


def _stage_stale_order(monkeypatch, ticker="KXBTC15M-T", oid="oid-1"):
    rec = {"ticker": ticker, "cost": 0.40, "count": 1,
           "placed_at": time.time() - (bot.STALE_ORDER_TIMEOUT + 60)}
    monkeypatch.setitem(bot.open_orders, oid, rec)
    bot.active_tickers.add(ticker)
    bot.session_traded_tickers.add(ticker)
    monkeypatch.setattr(bot, "DEMO_MODE", False)
    return rec


def test_stale_cancel_404_is_terminal_and_keeps_the_record_for_settlement(monkeypatch):
    try:
        rec = _stage_stale_order(monkeypatch)
        calls = []

        def _boom(path):
            calls.append(path)
            raise _FakeHTTPError(404)

        monkeypatch.setattr(bot, "_delete", _boom)
        bot.cancel_stale_orders()
        assert rec.get("cancel_unresolved") is True
        assert "oid-1" in bot.open_orders          # settlement must still match it
        bot.cancel_stale_orders()                  # ...but never asks again
        assert len(calls) == 1
    finally:
        bot.open_orders.pop("oid-1", None)
        bot.active_tickers.discard("KXBTC15M-T")
        bot.session_traded_tickers.discard("KXBTC15M-T")


def test_stale_cancel_success_releases_the_market_for_a_requote(monkeypatch):
    try:
        _stage_stale_order(monkeypatch)
        monkeypatch.setattr(bot, "_delete", lambda path: {})
        bot.cancel_stale_orders()
        assert "oid-1" not in bot.open_orders
        assert "KXBTC15M-T" not in bot.active_tickers
        # The order never filled, so the session guard must not keep the bot out.
        assert "KXBTC15M-T" not in bot.session_traded_tickers
    finally:
        bot.open_orders.pop("oid-1", None)
        bot.active_tickers.discard("KXBTC15M-T")
        bot.session_traded_tickers.discard("KXBTC15M-T")


def test_stale_cancel_retries_a_transient_error(monkeypatch):
    try:
        rec = _stage_stale_order(monkeypatch)

        def _boom(path):
            raise _FakeHTTPError(503)

        monkeypatch.setattr(bot, "_delete", _boom)
        bot.cancel_stale_orders()
        assert rec.get("cancel_unresolved") is None   # 503 is not terminal
        assert "oid-1" in bot.open_orders
    finally:
        bot.open_orders.pop("oid-1", None)
        bot.active_tickers.discard("KXBTC15M-T")
        bot.session_traded_tickers.discard("KXBTC15M-T")
