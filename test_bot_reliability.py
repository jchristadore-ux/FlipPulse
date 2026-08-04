"""Regression tests for bounded long-running bot state."""
import bot


def test_prev_order_book_state_is_bounded():
    bot._prev_ob.clear()
    for i in range(bot.PREV_OB_MAX + 25):
        bot._remember_prev_ob(f"ticker-{i}", ("YES", 0.5, float(i)), float(i))
    assert len(bot._prev_ob) == bot.PREV_OB_MAX
    assert "ticker-0" not in bot._prev_ob
    bot._prev_ob.clear()


def test_processed_settlement_ids_are_bounded():
    bot._processed_settlement_ids.clear()
    for i in range(bot.PROCESSED_SETTLEMENT_IDS_MAX + 25):
        bot._remember_settlement_id(f"settlement-{i}")
    assert len(bot._processed_settlement_ids) == bot.PROCESSED_SETTLEMENT_IDS_MAX
    assert "settlement-0" not in bot._processed_settlement_ids
    bot._processed_settlement_ids.clear()
