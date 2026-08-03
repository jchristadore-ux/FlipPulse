"""Balance-independence invariants (v10.3.0 owner directive: "validate that
balance is irrelevant — the same rules apply at $20 and $20,000").

The audit that produced these tests found three dollar-denominated mechanics
that made the risk actually taken differ by account size. What is asserted here
is the property, not the implementation:

  * the configured stake percentage is a CEILING at every balance (sizing rounds
    down, never up),
  * no raw-dollar cutoff decides whether a signal is tradeable,
  * the liquidity requirement scales with the order rather than sitting at a
    fixed dollar floor,
  * the percentage rules (daily goal, session stop) are exact at every size,
  * the unavoidable integer-contract granularity converges to zero as the
    balance grows, and is always an UNDER-risk.

Same import shim as test_bot_engine.py.

Run: pytest test_balance_independence.py
"""

import base64
import os

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_PEM = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption()).decode()
os.environ.setdefault("KALSHI_API_KEY_ID", "test-key")
os.environ.setdefault("KALSHI_PRIVATE_KEY_PEM_B64",
                      base64.b64encode(_PEM.encode()).decode())
os.environ.setdefault("DEMO_MODE", "true")
for _persist in ("RECOVERY_PERSIST", "PROBATION_PERSIST", "BUCKET_PERSIST",
                 "BILLING_PERSIST", "REPORT_PERSIST", "LIFETIME_PERSIST"):
    os.environ.setdefault(_persist, "false")

import bot  # noqa: E402  (env must be set first)


# Spans four orders of magnitude — the whole point is that these behave alike.
BALANCES = [5, 10, 20, 50, 100, 250, 1_000, 5_000, 20_000, 100_000]
# expiry_guard only lets mids 15c-85c through, so this brackets the band the
# strategy can ever buy in.
PRICES = [15, 30, 47, 67, 85]


@pytest.fixture(autouse=True)
def _flat_config(monkeypatch):
    """Stock sizing, no customer override files, no reduced tier."""
    monkeypatch.setattr(bot.recovery, "active", False)
    monkeypatch.setattr(bot.probation, "active", False)
    monkeypatch.setattr(bot, "NORMAL_TRADE_PCT", 0.10)
    monkeypatch.setattr(bot, "MAX_TRADE_PCT", 0.15)
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", False)
    monkeypatch.setattr(bot, "MIN_DEPTH_STAKE_MULT", 3.0)
    monkeypatch.setattr(bot, "_risk_override_cache", None)
    monkeypatch.setattr(bot, "_reserve_cache", None)
    monkeypatch.setattr(bot, "RISK_OVERRIDE_PATH", "/nonexistent/risk.json")
    monkeypatch.setattr(bot, "RESERVE_OVERRIDE_PATH", "/nonexistent/reserve.json")


def _win_p(price):
    """A win prob with positive expectancy at this price, so kelly_bet's edge
    gate never fires and the balance-dependent behaviour is isolated."""
    return min(0.97, price / 100.0 + 0.10)


def _risk_taken(balance, price):
    """The risk ACTUALLY taken as a % of balance, or None if the signal is
    skipped. Mirrors run_decision's path: stake -> whole contracts -> cost."""
    bet = bot.kelly_bet(_win_p(price), price, balance)
    if bet <= 0:
        return None
    count, _ = bot.size_contracts(bet, price, balance)
    if count < 1:
        return None
    return (price * count / 100.0) / balance * 100.0


# ── the configured percentage is a ceiling everywhere ────────────────────────

def test_configured_pct_is_never_exceeded_at_any_balance():
    """The headline invariant. Before v10.3.0 a $5 balance took 13.40% on a 67c
    contract against a configured 10%, because the sub-contract stake rounded UP
    and was bounded by MAX_TRADE_PCT rather than by the configured fraction."""
    for balance in BALANCES:
        for price in PRICES:
            pct = _risk_taken(balance, price)
            if pct is None:
                continue
            assert pct <= 10.0 + 1e-9, (
                f"${balance} @ {price}c risked {pct:.2f}% against a 10% config")


def test_the_specific_regression_five_dollars_at_67c():
    """The measured over-risk case, pinned: a $5 balance wanting $0.50 of a 67c
    contract must skip rather than buy $0.67 (13.4%)."""
    assert _risk_taken(5, 67) is None


def test_size_contracts_never_costs_more_than_the_stake():
    """Round-down invariant, stated directly on the sizing function."""
    for balance in BALANCES:
        for price in PRICES:
            bet = bot.kelly_bet(_win_p(price), price, balance)
            count, _ = bot.size_contracts(bet, price, balance)
            assert price * count / 100.0 <= bet + 1e-9


def test_round_up_is_off_by_default():
    assert bot.MIN_ORDER_ROUNDUP is False


def test_round_up_when_re_enabled_can_exceed_the_configured_pct(monkeypatch):
    """Control: the opt-in escape hatch still behaves as documented, so the
    default is a deliberate choice rather than an accident."""
    monkeypatch.setattr(bot, "MIN_ORDER_ROUNDUP", True)
    count, reason = bot.size_contracts(0.50, 67, 5.0)   # $5 balance, 10% = $0.50
    assert count == 1 and "rounded up" in reason
    assert 0.67 / 5.0 * 100 > 10.0                       # 13.4% — over the config


# ── no raw-dollar cutoff decides tradeability ────────────────────────────────

def test_a_sub_quarter_stake_still_trades_when_it_affords_a_contract():
    """The old `if bet < 0.25: return` blocked this outright — a dollar constant
    that made a small account play by different rules. What matters now is only
    whether the stake affords a whole contract inside MAX_TRADE_PCT."""
    bet = 0.20                                  # under the retired $0.25 floor
    count, _ = bot.size_contracts(bet, 15, 20.0)
    assert count == 1


def test_tradeability_is_decided_by_percentage_not_dollars():
    """One contract is affordable iff it fits the MAX_TRADE_PCT ceiling — the
    same relative test at every balance."""
    # 15c contract vs a 15% ceiling: needs a balance of at least $1.00.
    assert bot.size_contracts(0.05, 15, 0.90)[0] == 0     # ceiling $0.135 < 15c
    assert bot.size_contracts(0.15, 15, 1.50)[0] == 1     # ceiling $0.225 > 15c


# ── liquidity scales with the order ──────────────────────────────────────────

def test_depth_requirement_is_a_multiple_of_the_order():
    assert bot.depth_covers_order(300.0, 100.0) is True    # exactly 3x
    assert bot.depth_covers_order(299.0, 100.0) is False


def test_same_liquidity_rule_at_every_account_size():
    """A $20 account and a $20,000 account face the identical requirement,
    stated relative to their own order. The old flat $75 floor gave the first
    37x cover and the second 0.04x."""
    for balance in BALANCES:
        order = bot.active_trade_size(balance)
        assert bot.depth_covers_order(order * 3.0, order) is True
        assert bot.depth_covers_order(order * 2.99, order) is False


def test_big_account_order_that_used_to_pass_the_flat_floor_now_fails():
    """A $2,000 order against a book showing $75 — 26.7x oversized — passed the
    old gate untouched."""
    assert bot.depth_covers_order(75.0, 2_000.0) is False


def test_multiplier_zero_disables_the_gate(monkeypatch):
    monkeypatch.setattr(bot, "MIN_DEPTH_STAKE_MULT", 0.0)
    assert bot.depth_covers_order(1.0, 10_000.0) is True


# ── the percentage rules are exact at every size ─────────────────────────────

def test_daily_goal_is_exactly_the_configured_pct_at_every_balance(monkeypatch):
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_ENABLED", True)
    monkeypatch.setattr(bot, "DAILY_PROFIT_TARGET_PCT", 0.03)
    for balance in BALANCES:
        monkeypatch.setattr(bot, "session_start_balance", float(balance))
        assert bot.daily_profit_target_dollars() == round(balance * 0.03, 2)


def test_stake_fraction_is_exactly_the_configured_pct_at_every_balance():
    for balance in BALANCES:
        assert bot.active_trade_size(balance) == round(balance * 0.10, 2)


# ── the unavoidable part: integer granularity, and how it behaves ────────────

def test_granularity_error_converges_as_the_balance_grows():
    """Contracts are integral, so a small balance cannot land exactly on its
    percentage. That is the market, not a rule — assert it shrinks with size and
    is always an under-risk."""
    worst = {}
    for balance in BALANCES:
        deviations = [10.0 - pct for price in PRICES
                      if (pct := _risk_taken(balance, price)) is not None]
        worst[balance] = max(deviations)
        assert min(deviations) >= -1e-9        # never an OVER-risk
    assert worst[20] > worst[1_000] > worst[20_000]
    assert worst[20_000] < 0.01                # exact, to the cent, when large
    assert worst[5_000] < 0.05
