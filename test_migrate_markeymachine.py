"""Tests for tools/migrate_markeymachine.py.

The migration runs ONCE, against a live-money account, with no paper dry run.
The unit conversions are therefore the whole risk surface: a stake that comes
out 100× too large is a real loss, and nothing downstream would catch it. These
tests pin the conversions, the precedence rules, and the state-file handling.
"""

import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "tools"))

from migrate_markeymachine import (  # noqa: E402
    DROPPED,
    format_env_block,
    migrate_state,
    parse_env,
    Report,
    translate_env,
)


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def test_parse_env_handles_railway_raw_editor_shapes():
    text = (
        "# a comment\n"
        "\n"
        "NORMAL_TRADE_SIZE=5.0\n"
        "export DEMO_MODE=false\n"
        'TRADING_FORMAT="balanced"\n'
        "EMPTY=\n"
        "no_equals_sign\n"
    )
    got = parse_env(text)
    assert got == {
        "NORMAL_TRADE_SIZE": "5.0",
        "DEMO_MODE": "false",
        "TRADING_FORMAT": "balanced",
        "EMPTY": "",
    }


def test_parse_env_keeps_equals_inside_values():
    """Base64 PEMs are padded with '=' — partition on the FIRST '=' only."""
    got = parse_env("KALSHI_PRIVATE_KEY_PEM_B64=YWJjZA==\n")
    assert got["KALSHI_PRIVATE_KEY_PEM_B64"] == "YWJjZA=="


# ─────────────────────────────────────────────────────────────────────────────
# Sizing conversion — the core risk
# ─────────────────────────────────────────────────────────────────────────────

def test_dollar_stakes_become_fractions_of_balance():
    env, _ = translate_env({"NORMAL_TRADE_SIZE": "50", "RECOVERY_TRADE_SIZE": "15"},
                           balance=1000.0)
    assert env["NORMAL_TRADE_PCT"] == "0.05"     # $50 of $1000
    assert env["RECOVERY_TRADE_PCT"] == "0.015"  # $15 of $1000


def test_missing_balance_is_a_hard_error_not_a_silent_passthrough():
    """Copying `50` straight into NORMAL_TRADE_PCT would mean 5000% of balance."""
    with pytest.raises(SystemExit) as exc:
        translate_env({"NORMAL_TRADE_SIZE": "50"}, balance=None)
    assert "NORMAL_TRADE_SIZE" in str(exc.value)


def test_zero_balance_is_rejected_rather_than_dividing_by_zero():
    with pytest.raises(SystemExit):
        translate_env({"NORMAL_TRADE_SIZE": "50"}, balance=0.0)


def test_explicit_normal_trade_size_beats_legacy_alias():
    """MarkeyMachine resolves NORMAL_TRADE_SIZE first, then TRADE_SIZE_DOLLARS."""
    env, rep = translate_env(
        {"NORMAL_TRADE_SIZE": "50", "TRADE_SIZE_DOLLARS": "5"}, balance=1000.0)
    assert env["NORMAL_TRADE_PCT"] == "0.05"
    assert any("TRADE_SIZE_DOLLARS" in d for d in rep.dropped)


def test_legacy_alias_used_when_it_is_the_only_one_set():
    env, _ = translate_env({"TRADE_SIZE_DOLLARS": "25"}, balance=500.0)
    assert env["NORMAL_TRADE_PCT"] == "0.05"


def test_max_bet_fraction_carries_over_unscaled():
    """Both sides are already a fraction of bankroll — dividing would be wrong."""
    env, _ = translate_env({"MAX_BET_FRACTION": "0.04"}, balance=1000.0)
    assert env["MAX_TRADE_PCT"] == "0.04"


def test_max_trade_pct_defaults_when_no_source_ceiling():
    env, rep = translate_env({"MIN_CONFIDENCE": "0.6"}, balance=None)
    assert env["MAX_TRADE_PCT"] == "0.15"
    assert any("MAX_TRADE_PCT" in d for d in rep.defaulted)


def test_stake_above_ceiling_is_warned_about():
    env, rep = translate_env(
        {"NORMAL_TRADE_SIZE": "100", "MAX_BET_FRACTION": "0.04"}, balance=1000.0)
    assert env["NORMAL_TRADE_PCT"] == "0.1"
    assert env["MAX_TRADE_PCT"] == "0.04"
    assert any("exceeds MAX_TRADE_PCT" in w for w in rep.warnings)


def test_stake_rounding_to_zero_is_warned_about():
    """$1 against a $100k balance rounds to 0.0 — the bot would never trade."""
    _, rep = translate_env({"NORMAL_TRADE_SIZE": "1"}, balance=1_000_000.0)
    assert any("rounded to 0" in w for w in rep.warnings)


def test_balance_typo_producing_over_100pct_is_warned_about():
    _, rep = translate_env({"NORMAL_TRADE_SIZE": "500"}, balance=100.0)
    assert any("over 100% of balance" in w for w in rep.warnings)


def test_probation_rungs_list_is_rescaled_elementwise():
    env, _ = translate_env({"PROBATION_RUNGS": "30,65"}, balance=1000.0)
    assert env["PROBATION_RUNGS"] == "0.03,0.065"


def test_unparseable_probation_rungs_left_unset_with_a_warning():
    env, rep = translate_env({"PROBATION_RUNGS": "small,big"}, balance=1000.0)
    assert "PROBATION_RUNGS" not in env
    assert any("unparseable" in w for w in rep.warnings)


# ─────────────────────────────────────────────────────────────────────────────
# Guardrail rehoming and dropped behaviour
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_loss_caps_are_rehomed_to_the_ladder_that_still_reads_them():
    """FlipPulse deleted the bot-level caps; left unrenamed they'd do nothing."""
    env, _ = translate_env(
        {"MAX_DAILY_LOSS_DOLLARS": "40", "MAX_DAILY_LOSS_PCT": "0.06"}, balance=1000.0)
    assert env["LADDER_MAX_DAILY_LOSS_DOLLARS"] == "40"
    assert env["LADDER_MAX_DAILY_LOSS_PCT"] == "0.06"
    assert "MAX_DAILY_LOSS_DOLLARS" not in env


def test_markeymachine_only_features_are_reported_with_a_reason():
    _, rep = translate_env(
        {"PROFIT_LOCK_ENABLED": "true", "TRADE_WINDOW": "04:00-07:30",
         "KELLY_FRACTION": "0.30"}, balance=None)
    text = " ".join(rep.dropped)
    assert "PROFIT_LOCK_ENABLED" in text and "TRADE_WINDOW" in text and "KELLY_FRACTION" in text
    # Every dropped var explains itself — the report is the go-live checklist.
    assert all(" — " in d for d in rep.dropped)


def test_every_dropped_key_has_a_nonempty_reason():
    assert all(reason.strip() for reason in DROPPED.values())


def test_unrecognised_vars_are_surfaced_not_swallowed():
    _, rep = translate_env({"WHAT_IS_THIS": "7"}, balance=None)
    assert any("WHAT_IS_THIS" in u for u in rep.unrecognised)


def test_platform_injected_vars_are_ignored():
    _, rep = translate_env({"RAILWAY_PROJECT_ID": "abc", "PORT": "8080"}, balance=None)
    assert not rep.unrecognised


# ─────────────────────────────────────────────────────────────────────────────
# The emitted environment
# ─────────────────────────────────────────────────────────────────────────────

def test_state_paths_are_forced_onto_the_data_volume():
    """A relative path inherited from the source would land on ephemeral disk
    and be wiped by the next redeploy."""
    env, _ = translate_env({"RECOVERY_STATE_PATH": "recovery_state.json"}, balance=None)
    assert env["RECOVERY_STATE_PATH"] == "/data/recovery_state.json"
    assert env["DAILY_STATE_PATH"] == "/data/daily_state.json"


PEM = "-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----"


def test_raw_pem_is_replaced_by_a_derived_base64_value():
    """Removes the most error-prone manual step: a newline mangled in the
    Railway form produces a key that fails to load at boot."""
    env, _ = translate_env({"KALSHI_PRIVATE_KEY_PEM": PEM}, balance=None)
    assert "KALSHI_PRIVATE_KEY_PEM" not in env
    decoded = base64.b64decode(env["KALSHI_PRIVATE_KEY_PEM_B64"]).decode()
    assert decoded.startswith("-----BEGIN RSA PRIVATE KEY-----")
    assert decoded.rstrip("\n").endswith("-----END RSA PRIVATE KEY-----")


def test_derived_pem_is_single_line_so_railway_cannot_mangle_it():
    env, _ = translate_env({"KALSHI_PRIVATE_KEY_PEM": PEM}, balance=None)
    assert "\n" not in env["KALSHI_PRIVATE_KEY_PEM_B64"]


def test_escaped_newlines_in_pem_are_normalised_before_encoding():
    """Some exports render the PEM with literal backslash-n."""
    escaped = PEM.replace("\n", "\\n")
    env, _ = translate_env({"KALSHI_PRIVATE_KEY_PEM": escaped}, balance=None)
    assert "\\n" not in base64.b64decode(env["KALSHI_PRIVATE_KEY_PEM_B64"]).decode()


def test_pem_derivation_clears_the_manual_warning():
    _, rep = translate_env({"KALSHI_PRIVATE_KEY_PEM": PEM}, balance=None)
    assert not any("KALSHI_PRIVATE_KEY_PEM_B64 must be filled in" in w for w in rep.warnings)


def test_malformed_pem_is_not_silently_encoded():
    env, rep = translate_env({"KALSHI_PRIVATE_KEY_PEM": "oops-truncated"}, balance=None)
    assert env["KALSHI_PRIVATE_KEY_PEM_B64"] == ""
    assert any("does not look like a PEM" in w for w in rep.warnings)


def test_secrets_are_emitted_empty_and_flagged():
    env, rep = translate_env({}, balance=None)
    for key in ("TELEGRAM_BOT_TOKEN", "DASHBOARD_PASSWORD", "KALSHI_PRIVATE_KEY_PEM_B64"):
        assert env[key] == ""
        assert any(key in w for w in rep.warnings)


def test_each_missing_secret_warns_exactly_once():
    _, rep = translate_env({}, balance=None)
    assert sum("TELEGRAM_BOT_TOKEN must be filled in" in w for w in rep.warnings) == 1


def test_probation_rungs_is_not_also_reported_unrecognised():
    """It is handled in its own block; the scalar loop must not double-report it."""
    _, rep = translate_env({"PROBATION_RUNGS": "30,65"}, balance=1000.0)
    assert not any("PROBATION_RUNGS" in u for u in rep.unrecognised)


def test_perf_fee_is_zero_for_an_owned_account():
    env, _ = translate_env({}, balance=None)
    assert env["PERF_FEE_PCT"] == "0.0"


def test_carried_values_are_not_overwritten_by_defaults():
    env, _ = translate_env({"MAX_CONSEC_LOSSES": "5"}, balance=None)
    assert env["MAX_CONSEC_LOSSES"] == "5"


def test_env_block_is_sorted_and_railway_pasteable():
    block = format_env_block({"B_KEY": "2", "A_KEY": "1"})
    assert block == "A_KEY=1\nB_KEY=2\n"


# ─────────────────────────────────────────────────────────────────────────────
# State migration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def dirs(tmp_path):
    src, dst = tmp_path / "mm", tmp_path / "fp"
    src.mkdir()
    return src, dst


def test_bucket_stats_copied_verbatim(dirs):
    src, dst = dirs
    payload = {"schema": 1, "buckets": {"9": {"wins": 3, "losses": 1}}}
    (src / "bucket_stats.json").write_text(json.dumps(payload))
    migrate_state(src, dst, 1000.0, Report())
    assert json.loads((dst / "bucket_stats.json").read_text()) == payload


def test_bucket_stats_with_unknown_schema_is_skipped(dirs):
    src, dst = dirs
    (src / "bucket_stats.json").write_text(json.dumps({"schema": 99, "buckets": {}}))
    notes = migrate_state(src, dst, 1000.0, Report())
    assert not (dst / "bucket_stats.json").exists()
    assert any("SKIPPED" in n for n in notes)


def test_active_recovery_keeps_schema_1_and_renames_win_tallies(dirs):
    """FlipPulse's loader back-converts target_balance itself at boot, using a
    real balance. Only the period_* key names need fixing."""
    src, dst = dirs
    (src / "recovery_state.json").write_text(json.dumps({
        "schema": 1, "active": True, "target_balance": 1200.0,
        "period_wins": 3, "period_losses": 2,
    }))
    migrate_state(src, dst, 1000.0, Report())
    got = json.loads((dst / "recovery_state.json").read_text())
    assert got["schema"] == 1
    assert got["target_balance"] == 1200.0
    assert got["wins"] == 3 and got["losses"] == 2
    assert "period_wins" not in got


def test_inactive_recovery_carries_across_clean(dirs):
    src, dst = dirs
    (src / "recovery_state.json").write_text(json.dumps({"schema": 1, "active": False}))
    migrate_state(src, dst, 1000.0, Report())
    assert json.loads((dst / "recovery_state.json").read_text())["active"] is False


def test_active_probation_rungs_converted_dollars_to_fractions(dirs):
    src, dst = dirs
    (src / "probation_state.json").write_text(json.dumps({
        "schema": 1, "active": True, "rungs": [30.0, 65.0], "level": 1,
        "full_size": 100.0, "streak": 2, "wins": 4, "losses": 1, "day": "2026-08-06",
    }))
    migrate_state(src, dst, 1000.0, Report())
    got = json.loads((dst / "probation_state.json").read_text())
    assert got["rungs"] == [0.03, 0.065]
    assert got["full_size"] == 0.1
    assert got["level"] == 1 and got["day"] == "2026-08-06"


def test_inactive_probation_is_skipped(dirs):
    src, dst = dirs
    (src / "probation_state.json").write_text(json.dumps({"schema": 1, "active": False}))
    migrate_state(src, dst, 1000.0, Report())
    assert not (dst / "probation_state.json").exists()


def test_active_probation_skipped_rather_than_miswritten_without_balance(dirs):
    """Writing dollar rungs into a fraction field would ramp at 3000% of balance."""
    src, dst = dirs
    (src / "probation_state.json").write_text(json.dumps({
        "schema": 1, "active": True, "rungs": [30.0], "full_size": 100.0,
    }))
    notes = migrate_state(src, dst, None, Report())
    assert not (dst / "probation_state.json").exists()
    assert any("SKIPPED" in n and "probation" in n for n in notes)


def test_markeymachine_only_state_is_not_migrated_and_warns(dirs):
    src, dst = dirs
    (src / "profit_lock_state.json").write_text(json.dumps({"armed": True}))
    (src / "temp_override_state.json").write_text(json.dumps({"size": 10.0}))
    rep = Report()
    migrate_state(src, dst, 1000.0, rep)
    assert not (dst / "profit_lock_state.json").exists()
    assert not (dst / "temp_override_state.json").exists()
    assert sum("stops at cutover" in w for w in rep.warnings) == 2


def test_flippulse_only_state_is_left_for_the_bot_to_create(dirs):
    """A hand-made daily_state.json would mis-arm the +3% halt on day one."""
    src, dst = dirs
    (src / "bucket_stats.json").write_text(json.dumps({"schema": 1, "buckets": {}}))
    migrate_state(src, dst, 1000.0, Report())
    for name in ("daily_state.json", "lifetime_stats.json", "billing_state.json"):
        assert not (dst / name).exists()


def test_corrupt_state_file_is_skipped_not_crashed(dirs):
    src, dst = dirs
    (src / "recovery_state.json").write_text("{ not json")
    notes = migrate_state(src, dst, 1000.0, Report())
    assert not (dst / "recovery_state.json").exists()
    assert any("unreadable" in n for n in notes)


def test_empty_source_volume_is_handled(dirs):
    src, dst = dirs
    notes = migrate_state(src, dst, 1000.0, Report())
    assert dst.is_dir()
    assert any("not present in source" in n for n in notes)
