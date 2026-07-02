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
                 "BUCKET_PERSIST", "BILLING_PERSIST"):
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
    monkeypatch.setattr(bot, "stake_ladder", None)
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
