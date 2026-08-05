"""Recovery Mode is anchored to realized TRADE P&L, never to the account balance
(v10.3.3, owner directive: "withdrawals must not trigger recovery mode").

Before v10.3.3 recovery stored an absolute target — the balance immediately
before the losing trade — and exited when the live balance climbed back to it.
Cash the customer moved in or out of Kalshi therefore read exactly like trading:
a withdrawal inflated the claw-back (and could latch recovery forever), while a
deposit cleared it without a dollar being earned back.

These tests pin the new contract:
  * what recovery OWES is the losing trade's realized dollars;
  * only settled trades move it (apply_pnl), never a transfer;
  * the balance target is DERIVED from today's balance, so it re-bases when the
    account does;
  * a pre-v10.3.3 state file still migrates and still exits.

Same import shim as test_recovery_nsc.py.

Run: pytest test_recovery_pnl_anchor.py
"""

import base64
import json
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


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    """Reset recovery + probation around every test and mute Telegram."""
    monkeypatch.setattr(bot.tg, "send_telegram_message", lambda *_a, **_k: True)
    monkeypatch.setattr(bot.tg, "send_status_message", lambda *_a, **_k: True)
    monkeypatch.setattr(bot, "_recovery_nsc_cache", None)
    monkeypatch.setattr(bot, "RECOVERY_NSC_OVERRIDE_PATH", "/nonexistent/nsc.json")
    bot.recovery.active  = False
    bot.recovery.deficit = 0.0
    bot.recovery.wins = bot.recovery.losses = 0
    bot.recovery._legacy_target = 0.0
    bot.probation.active = False
    yield
    bot.recovery.active  = False
    bot.recovery.deficit = 0.0
    bot.recovery._legacy_target = 0.0
    bot.probation.active = False


def _loss(cost, balance_before=1000.0, mode="normal"):
    """A settled losing trade record (the bot stamps `pnl` at settlement)."""
    return {"mode_at_entry": mode, "balance_before": balance_before,
            "cost": cost, "pnl": -cost, "result": "loss"}


# ── entry is sized by the loss, not by a balance gap ──────────────────────────
def test_entry_claws_back_exactly_what_the_trade_lost():
    bot.on_trade_settled(False, _loss(3.0), 997.0, pnl=-3.0)
    assert bot.recovery.active is True
    assert bot.recovery.deficit == 3.0
    assert bot.recovery.target_for(997.0) == 1000.0


def test_withdrawal_before_settlement_does_not_inflate_the_clawback():
    """The bug: $400 withdrawn while the trade was open used to be added to the
    claw-back, because the target was the pre-trade balance ($1000) and the
    balance had fallen to $597. Only the $3 the trade lost is owed."""
    bot.on_trade_settled(False, _loss(3.0, balance_before=1000.0), 597.0, pnl=-3.0)
    assert bot.recovery.deficit == 3.0
    # The displayed target re-bases onto the post-withdrawal balance.
    assert bot.recovery.target_for(597.0) == 600.0


def test_a_withdrawal_alone_never_arms_recovery():
    """Cash leaving the account is not a settled trade, so nothing calls the
    hook — and a winning trade around it must not arm recovery either."""
    bot.on_trade_settled(True, {"mode_at_entry": "normal", "pnl": 2.0}, 600.0, pnl=2.0)
    assert bot.recovery.active is False
    assert bot.recovery.deficit == 0.0


def test_zero_pnl_settlement_does_not_arm():
    """An unfilled/expired order lost nothing — there is nothing to claw back."""
    assert bot.recovery.enter(0.0, 1000.0) is False
    bot.on_trade_settled(False, _loss(0.0), 1000.0, pnl=0.0)
    assert bot.recovery.active is False


def test_reduced_size_loss_does_not_arm():
    """Only a full-size (normal-mode) loss arms the deeper tier."""
    bot.on_trade_settled(False, _loss(3.0, mode="probation"), 997.0, pnl=-3.0)
    assert bot.recovery.active is False


def test_entry_falls_back_to_the_pnl_on_the_trade_record():
    """Settlement stamps `pnl` on the record; the explicit argument is optional."""
    bot.on_trade_settled(False, _loss(4.25), 995.75)
    assert bot.recovery.deficit == 4.25


# ── progress moves on settled trades only ─────────────────────────────────────
def test_wins_pay_the_deficit_down_and_losses_deepen_it():
    bot.on_trade_settled(False, _loss(10.0), 990.0, pnl=-10.0)
    assert bot.recovery.deficit == 10.0
    bot.on_trade_settled(True, {"mode_at_entry": "recovery"}, 994.0, pnl=4.0)
    assert bot.recovery.deficit == 6.0
    bot.on_trade_settled(False, {"mode_at_entry": "recovery"}, 992.0, pnl=-2.0)
    assert bot.recovery.deficit == 8.0


def test_a_further_loss_does_not_re_arm_or_reset_the_claw_back():
    bot.on_trade_settled(False, _loss(10.0), 990.0, pnl=-10.0)
    bot.on_trade_settled(False, _loss(5.0, balance_before=990.0), 985.0, pnl=-5.0)
    assert bot.recovery.deficit == 15.0     # deepened, not restarted at $5


def test_deposits_and_withdrawals_do_not_move_the_deficit():
    bot.on_trade_settled(False, _loss(10.0), 990.0, pnl=-10.0)
    # No settlement happens on a transfer, so nothing calls apply_pnl — and the
    # per-cycle exit check sees the same $10 owed at any balance.
    assert bot.recovery.maybe_exit(590.0) is False      # withdrew $400
    assert bot.recovery.maybe_exit(9_990.0) is False    # deposited $9,000
    assert bot.recovery.deficit == 10.0
    assert bot.recovery.active is True


def test_exit_fires_once_the_loss_is_earned_back_at_any_balance():
    """A withdrawal used to make the target unreachable and latch recovery for
    good. Earning the $10 back now clears it even from a smaller account."""
    bot.on_trade_settled(False, _loss(10.0), 990.0, pnl=-10.0)
    bot.on_trade_settled(True, {"mode_at_entry": "recovery"}, 600.0, pnl=10.0)
    assert bot.recovery.deficit == 0.0
    assert bot.recovery.maybe_exit(600.0) is True       # never reached $1000
    assert bot.recovery.active is False


def test_apply_pnl_is_a_no_op_when_not_recovering():
    bot.recovery.apply_pnl(-50.0)
    assert bot.recovery.active is False
    assert bot.recovery.deficit == 0.0


def test_sub_cent_residue_does_not_hold_recovery_open():
    bot.recovery.active  = True
    bot.recovery.deficit = 0.004
    assert bot.recovery.maybe_exit(100.0) is True


# ── the derived target ────────────────────────────────────────────────────────
def test_target_tracks_the_account_not_a_frozen_number():
    bot.on_trade_settled(False, _loss(10.0), 990.0, pnl=-10.0)
    assert bot.recovery.target_for(990.0) == 1000.0
    # Win $4: balance up 4, owed down 4 → the goal has not moved.
    bot.on_trade_settled(True, {"mode_at_entry": "recovery"}, 994.0, pnl=4.0)
    assert bot.recovery.target_for(994.0) == 1000.0
    # Withdraw $400: the goal comes down with the account, it is not $400 further.
    assert bot.recovery.target_for(594.0) == 600.0


def test_target_is_zero_when_not_recovering():
    assert bot.recovery.target_for(1000.0) == 0.0


# ── persistence + legacy migration ────────────────────────────────────────────
def _state(tmp_path, payload):
    path = str(tmp_path / "recovery_state.json")
    with open(path, "w") as f:
        json.dump(payload, f)
    return path


def test_deficit_round_trips_through_the_state_file(tmp_path):
    path = str(tmp_path / "recovery_state.json")
    a = bot.RecoveryState(path, persist=True)
    assert a.enter(-7.5, 992.5) is True
    a.apply_pnl(2.5)
    b = bot.RecoveryState(path, persist=True)
    assert (b.active, b.deficit) == (True, 5.0)


def test_legacy_state_migrates_to_a_deficit_at_boot(tmp_path):
    """Schema 1 stored only "climb back to $1000"; at $960 that is $40 owed."""
    path = _state(tmp_path, {"schema": 1, "active": True,
                             "target_balance": 1000.0, "wins": 2, "losses": 1})
    r = bot.RecoveryState(path, persist=True)
    r.reconcile_on_boot(960.0)
    assert r.active is True
    assert r.deficit == 40.0
    # ...and from here it is pure trade P&L: the migration runs once.
    r.apply_pnl(40.0)
    assert r.maybe_exit(400.0) is True


def test_legacy_state_already_whole_exits_on_boot(tmp_path):
    path = _state(tmp_path, {"schema": 1, "active": True,
                             "target_balance": 1000.0})
    r = bot.RecoveryState(path, persist=True)
    r.reconcile_on_boot(1200.0)
    assert r.active is False


def test_boot_clears_a_state_with_nothing_left_to_claw_back(tmp_path):
    path = _state(tmp_path, {"schema": 2, "active": True, "deficit": 0.0})
    r = bot.RecoveryState(path, persist=True)
    r.reconcile_on_boot(500.0)
    assert r.active is False


def test_paper_settlement_arms_recovery_with_the_trade_loss(monkeypatch):
    """End-to-end through resolve_open_orders: the settlement path hands the
    realized P&L to the recovery hook (a withdrawal that moved `paper_balance`
    away from `balance_before` cannot change what is owed)."""
    monkeypatch.setattr(bot, "fetch_btc_price", lambda: 99_000.0)
    monkeypatch.setattr(bot, "daily_profit_target_check", lambda *_a, **_k: False)
    monkeypatch.setattr(bot, "paper_balance", 597.0)
    trade = {
        "time": "2026-08-05T00:00:00+00:00", "ticker": "KXBTC15M-TEST",
        "side": "YES", "price": 50, "count": 6, "cost": 3.0,
        "order_id": "oid-1", "result": "pending",
        "placed_at": 0.0,                       # long past the 900s paper hold
        "btc_entry_price": 100_000.0,           # BTC fell → a YES loss
        "mode_at_entry": "normal", "balance_before": 1000.0,
        "entry_bucket": "am",
    }
    bot.open_orders.clear()
    bot.trade_history.append(trade)
    bot.open_orders["oid-1"] = trade
    try:
        bot.resolve_open_orders()
    finally:
        bot.open_orders.clear()
        bot.trade_history.remove(trade)
    assert trade["result"] == "loss"
    assert bot.recovery.active is True
    assert bot.recovery.deficit == 3.0          # the loss, not the $403 gap


def test_boot_resumes_an_outstanding_claw_back_unchanged(tmp_path):
    """A redeploy after a withdrawal must resume the SAME $12 — the balance it
    boots at is irrelevant to what is owed."""
    path = _state(tmp_path, {"schema": 2, "active": True, "deficit": 12.0})
    r = bot.RecoveryState(path, persist=True)
    r.reconcile_on_boot(300.0)
    assert (r.active, r.deficit) == (True, 12.0)
