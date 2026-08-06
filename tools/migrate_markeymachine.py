#!/usr/bin/env python3
"""Translate a MarkeyMachine bot deployment into a FlipPulse one.

WHY THIS EXISTS
───────────────
MarkeyMachine and FlipPulse are the same trading engine forked apart. Moving
MarkeyMachine into the FlipPulse Railway project means running it on
FlipPulse's `bot.py`, and the two do NOT share a config surface. Three things
have to be reconciled, and all three are easy to get silently wrong by hand:

  1. SIZING UNITS. MarkeyMachine stakes in DOLLARS (NORMAL_TRADE_SIZE,
     RECOVERY_TRADE_SIZE, PROBATION_RUNG_STEP). FlipPulse stakes in a FRACTION
     OF LIVE BALANCE (NORMAL_TRADE_PCT, RECOVERY_TRADE_PCT,
     PROBATION_RUNG_STEP_PCT). Copying `5.0` from one to the other does not
     mean "$5" — it means "500% of balance", which the ceiling then clamps to
     MAX_TRADE_PCT. Every dollar knob must be divided by the balance it was
     sized against.

  2. DELETED GUARDRAILS. FlipPulse deleted MAX_DAILY_LOSS_PCT,
     MAX_DAILY_LOSS_DOLLARS and MIN_BALANCE_FLOOR as dead config (bot.py
     v9.4.0). Left as-is, MarkeyMachine's daily loss caps would be read by
     nothing and the account would trade uncapped. The two that still have a
     live consumer are re-pointed at ladder.py's equivalents.

  3. STATE SCHEMAS. bucket_stats.json is byte-identical between the forks;
     recovery_state.json is schema 1 there and schema 2 here (FlipPulse's
     loader already back-converts it); probation_state.json shares a schema
     number but stores DOLLARS there and FRACTIONS here — the one file that
     looks compatible and is not.

USAGE
─────
    python tools/migrate_markeymachine.py \
        --env-in    markeymachine.env \
        --balance   1234.56 \
        --state-in  ./mm-data \
        --env-out   flippulse.env \
        --state-out ./fp-data

`--env-in` is the raw `KEY=VALUE` block copied out of the MarkeyMachine
service's Railway variables (Raw Editor). `--balance` is the account balance
those dollar stakes were sized against — required whenever a dollar knob is
present, because it is the divisor for every unit conversion. `--state-in` is
a copy of the MarkeyMachine `/data` volume; omit both state flags to translate
config only.

Nothing is read from or written to Railway: this is a pure offline translator,
so its output can be reviewed before anything touches a live account.
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# THE MAPPING TABLES
#
# Every MarkeyMachine variable is in exactly one of these four tables. A var in
# none of them is unknown to both forks and is reported as "unrecognised" so a
# typo in the source config can never be silently dropped.
# ─────────────────────────────────────────────────────────────────────────────

# Same name, same units, same meaning in both forks — copied through verbatim.
CARRY_THROUGH = {
    "KALSHI_API_KEY_ID", "KALSHI_PRIVATE_KEY_PEM", "DEMO_MODE", "PAPER_BALANCE",
    "TRADING_FORMAT", "POLL_INTERVAL_SECS",
    # Decision-engine gates. Identical implementations on both sides.
    "MIN_CONFIDENCE", "MIN_EDGE_PCT", "MIN_WIN_PROB", "MIN_SAMPLE_TRADES",
    "MIN_SESSION_SCORE", "MIN_MINUTES_TO_EXPIRY", "MIN_OB_DEPTH_DOLLARS",
    "MIN_PRICES_FOR_REGIME", "OB_BASE_ACCURACY", "OB_IMBALANCE_THRESH",
    "MOMENTUM_LOOKBACK", "MOMENTUM_THRESH_PCT", "MOMENTUM_R2_MIN",
    "MOMENTUM_ACCURACY_LIFT", "NEUTRAL_ACCURACY_DRAG", "REQUIRE_AGREE_MOMENTUM",
    "TREND_LOOKBACK", "R2_TREND_THRESHOLD", "YES_BREAKEVEN_PRICE",
    "VOLATILITY_CAP_PCT", "VOL_CIRCUIT_BREAKER",
    # Risk holds that survived the fork unchanged.
    "MAX_CONCURRENT_POS", "MAX_CONSEC_LOSSES", "STREAK_PAUSE_SECS",
    "STALE_ORDER_TIMEOUT", "SESSION_STOP_FRACTION",
    # Probation ramp (the non-dollar knobs).
    "PROBATION_RAMP_ENABLED", "PROBATION_PERSIST", "PROBATION_WIN_STREAK",
    "PROBATION_WIN_RATE_MIN", "PROBATION_WINRATE_MIN_TRADES",
    # Bucket stats — identical class, identical on-disk schema.
    "BUCKET_PERSIST", "BUCKET_GROUP_HOURS", "BUCKET_PRIOR_FULL_N",
    "RECOVERY_PERSIST",
    # ladder.py is effectively shared; these names are read by both copies.
    "LADDER_ENABLED", "LADDER_WINDOW", "LADDER_MIN_TRADES", "LADDER_MAX_MULT",
    "LADDER_COOLDOWN_SECS", "LADDER_COOLDOWN_CYCLES", "LADDER_STREAK_DEMOTE_AT",
    "LADDER_VOL_CAP_AT_BASE", "LADDER_DRAWDOWN_ACTION", "LADDER_PERSIST",
}

# Renamed, but the VALUE carries over unchanged (already a fraction, or a
# straight rehoming to the consumer FlipPulse actually kept).
RENAMED: Dict[str, str] = {
    # Both are "hard ceiling as a fraction of bankroll" — same units, new name.
    "MAX_BET_FRACTION": "MAX_TRADE_PCT",
    # FlipPulse deleted the bot-level daily caps; ladder.py still honours these.
    "MAX_DAILY_LOSS_DOLLARS": "LADDER_MAX_DAILY_LOSS_DOLLARS",
    "MAX_DAILY_LOSS_PCT": "LADDER_MAX_DAILY_LOSS_PCT",
}

# Renamed AND rescaled: dollars ÷ balance → fraction of balance.
DOLLARS_TO_FRACTION: Dict[str, str] = {
    "NORMAL_TRADE_SIZE": "NORMAL_TRADE_PCT",
    "TRADE_SIZE_DOLLARS": "NORMAL_TRADE_PCT",   # legacy alias for the above
    "RECOVERY_TRADE_SIZE": "RECOVERY_TRADE_PCT",
    "PROBATION_RUNG_STEP": "PROBATION_RUNG_STEP_PCT",
}

# No FlipPulse consumer. Dropping these CHANGES TRADING BEHAVIOUR, so each one
# carries the reason it is being dropped and that reason is printed in the
# report — this is the list to read before going live, not after.
DROPPED: Dict[str, str] = {
    "KELLY_FRACTION":
        "FlipPulse sizes from NORMAL_TRADE_PCT, not a Kelly fraction.",
    "KELLY_RECOVERY_MULT":
        "No Kelly sizing in FlipPulse; recovery uses RECOVERY_TRADE_PCT.",
    "MIN_BALANCE_FLOOR":
        "Deleted in FlipPulse v9.4.0. Nearest survivor: SESSION_STOP_FRACTION.",
    "PROFIT_LOCK_ENABLED":
        "Profit lock is MarkeyMachine-only. Nearest: DAILY_PROFIT_TARGET_PCT.",
    "PROFIT_LOCK_ARM_PCT": "Profit lock is MarkeyMachine-only.",
    "PROFIT_LOCK_TARGET_PCT": "Profit lock is MarkeyMachine-only.",
    "PROFIT_LOCK_GIVEBACK_PCT": "Profit lock is MarkeyMachine-only.",
    "PROFIT_LOCK_PERSIST": "Profit lock is MarkeyMachine-only.",
    "PROFIT_LOCK_STATE_PATH": "Profit lock is MarkeyMachine-only.",
    "TRADE_WINDOW":
        "No trading-hours window in FlipPulse — the bot trades all day.",
    "TRADE_WINDOW_TZ": "No trading-hours window in FlipPulse.",
    "WINDOW_EXTEND_UNTIL_GOAL": "No trading-hours window in FlipPulse.",
    "DAILY_TARGET_LADDER_ENABLED":
        "MarkeyMachine's ladder daily goal has no FlipPulse equivalent.",
    "DAILY_MIN_TARGET_PCT": "MarkeyMachine ladder daily goal — not in FlipPulse.",
    "DAILY_TARGET_DECAY_HOURS": "MarkeyMachine ladder daily goal — not in FlipPulse.",
    "TEMP_OVERRIDE_ENABLED":
        "Temp stake override is MarkeyMachine-only. Nearest: RISK_OVERRIDE_PATH.",
    "TEMP_OVERRIDE_BASE": "Temp stake override is MarkeyMachine-only.",
    "TEMP_OVERRIDE_STEP": "Temp stake override is MarkeyMachine-only.",
    "TEMP_OVERRIDE_WIN_STREAK": "Temp stake override is MarkeyMachine-only.",
    "TEMP_OVERRIDE_EXIT_BALANCE": "Temp stake override is MarkeyMachine-only.",
    "TEMP_OVERRIDE_PERSIST": "Temp stake override is MarkeyMachine-only.",
    "TEMP_OVERRIDE_STATE_PATH": "Temp stake override is MarkeyMachine-only.",
    "HIGH_STAKE_GATE_SIZE":
        "High-stake gate is MarkeyMachine-only; MAX_TRADE_PCT is the ceiling here.",
    "HIGH_STAKE_MIN_BALANCE": "High-stake gate is MarkeyMachine-only.",
    "PERF_GUARD_DERATE":
        "FlipPulse's performance guard PAUSES (PERF_GUARD_PAUSE_SECS) instead of derating.",
    "PERF_GUARD_FLOOR": "FlipPulse's performance guard pauses instead of derating.",
    "RECOVERY_KEEP_NORMAL_STAKE":
        "Superseded by RECOVERY_NO_STAKE_CHANGE (default true in FlipPulse).",
    "RECOVERY_WINRATE_STEPUP":
        "Superseded by RECOVERY_WINRATE_RESTORE_ENABLED.",
    "RECOVERY_STEPUP_WINRATE":
        "Superseded by RECOVERY_WINRATE_RESTORE_PCT.",
    "RECOVERY_STEPUP_MIN_TRADES":
        "Superseded by RECOVERY_WINRATE_MIN_TRADES.",
    "RECOVERY_TRIGGER_PCT":
        "FlipPulse arms recovery off a full-size loss, not a drawdown threshold.",
    "RECOVERY_EXIT_TRADES": "FlipPulse exits recovery when the deficit is repaid.",
    "RECOVERY_WIN_RATE_MIN": "FlipPulse exits recovery when the deficit is repaid.",
    "RECOVERY_MAX_SECS": "FlipPulse exits recovery when the deficit is repaid.",
    "RECOVERY_LADDER_PAUSE_TRADES":
        "Ladder pause on recovery exit is not configurable in FlipPulse.",
    "LADDER_STATE_PATH":
        "Re-emitted as a /data path in the FlipPulse state-path block.",
}

# State paths are always re-emitted onto the /data volume, whatever the source
# config said, so a stale relative path can never send state to ephemeral disk.
STATE_PATHS: Dict[str, str] = {
    "RECOVERY_STATE_PATH": "/data/recovery_state.json",
    "PROBATION_STATE_PATH": "/data/probation_state.json",
    "BUCKET_STATS_PATH": "/data/bucket_stats.json",
    "BILLING_STATE_PATH": "/data/billing_state.json",
    "DAILY_STATE_PATH": "/data/daily_state.json",
    "LIFETIME_STATS_PATH": "/data/lifetime_stats.json",
    "REPORT_STATE_PATH": "/data/report_state.json",
    "STATUS_SNAPSHOT_PATH": "/data/status_snapshot.json",
    "HEALTH_LOG_PATH": "/data/health.log",
    "RISK_OVERRIDE_PATH": "/data/risk_override.json",
    "RESERVE_OVERRIDE_PATH": "/data/reserve_override.json",
    "FORMAT_OVERRIDE_PATH": "/data/format_override.json",
    "TELEGRAM_PREFS_PATH": "/data/telegram_prefs.json",
    "MODE_OVERRIDE_PATH": "/data/mode_override.json",
    "RECOVERY_NSC_OVERRIDE_PATH": "/data/recovery_nsc_override.json",
    "DASHBOARD_SECRET_PATH": "/data/dashboard_secret",
    "BILLING_LOG_PATH": "/data/billing.log",
    "LADDER_STATE_PATH": "/data/ladder_state.json",
}

# FlipPulse-only settings with no MarkeyMachine source. Emitted at their
# bot.py defaults so the generated block is the COMPLETE environment — a
# reviewer sees every value the bot will run on, not just the migrated subset.
FLIPPULSE_DEFAULTS: Dict[str, str] = {
    "MARKET_ANCHOR_ENABLED": "true",
    "MAX_MODEL_EDGE_PP": "25",
    "MIN_EDGE_ROR": "0.15",
    "OB_IMBALANCE_MAX": "0.85",
    "MIN_DEPTH_STAKE_MULT": "1.5",
    "MIN_ORDER_ROUNDUP": "false",
    "MAX_MINUTES_TO_EXPIRY": "60",
    "BTC_STALE_MAX_SECS": "120",
    "RISK_MIN_TRADE_PCT": "0.01",
    "PERF_GUARD_WINDOW": "10",
    "PERF_GUARD_PAUSE_SECS": "3600",
    "RECOVERY_NO_STAKE_CHANGE": "true",
    "RECOVERY_WINRATE_RESTORE_ENABLED": "true",
    "RECOVERY_WINRATE_RESTORE_PCT": "0.70",
    "RECOVERY_WINRATE_MIN_TRADES": "5",
    "DAILY_PROFIT_TARGET_ENABLED": "true",
    "DAILY_PROFIT_TARGET_PCT": "0.03",
    "REPORT_SCHEDULE_ENABLED": "true",
    "REPORT_HOURS": "9,21",
    "REPORT_TIMEZONE": "America/New_York",
    # MarkeyMachine is your own account, not a billed customer.
    "PERF_FEE_PCT": "0.0",
}

# Secrets and per-deployment values the translator cannot know. Emitted as
# empty placeholders so a missing one fails loudly in review, not at boot.
REQUIRED_MANUAL: List[Tuple[str, str]] = [
    ("KALSHI_PRIVATE_KEY_PEM_B64", "base64 of the Kalshi PEM — single line, unmanglable"),
    ("TELEGRAM_BOT_TOKEN", "MarkeyMachine's existing BotFather token"),
    ("TELEGRAM_CHAT_ID", "MarkeyMachine's existing Telegram chat id"),
    ("TELEGRAM_OPERATOR_CHAT_ID", "your operator chat id (oversight alerts)"),
    ("DASHBOARD_PASSWORD", "a strong password for this bot's web dashboard"),
]


# ─────────────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_env(text: str) -> Dict[str, str]:
    """Parse a Railway Raw-Editor / dotenv block into a dict.

    Tolerates `export ` prefixes, `#` comments and blank lines. Handles values
    wrapped in single or double quotes INCLUDING multi-line ones: Railway quotes
    any value containing a newline, which is exactly how KALSHI_PRIVATE_KEY_PEM
    arrives. Reading only the first line of a PEM would silently truncate the
    key, so an unterminated quote consumes lines until its closing quote."""
    out: Dict[str, str] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        if not key:
            continue
        if val and val[0] in ("'", '"'):
            quote = val[0]
            # Closed on the same line? Otherwise absorb lines until it closes.
            if len(val) >= 2 and val.endswith(quote):
                val = val[1:-1]
            else:
                parts = [val[1:]]
                while i < len(lines):
                    nxt = lines[i]
                    i += 1
                    if nxt.rstrip().endswith(quote):
                        parts.append(nxt.rstrip()[:-1])
                        break
                    parts.append(nxt)
                val = "\n".join(parts)
        out[key] = val
    return out


def _as_float(val: str) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────

class Report:
    """Everything the translation did, for printing. Kept separate from the
    emitted env so the report can be read without diffing two files."""

    def __init__(self) -> None:
        self.carried: List[str] = []
        self.renamed: List[str] = []
        self.rescaled: List[str] = []
        self.dropped: List[str] = []
        self.defaulted: List[str] = []
        self.unrecognised: List[str] = []
        self.warnings: List[str] = []


def translate_env(src: Dict[str, str], balance: float | None) -> Tuple[Dict[str, str], Report]:
    """MarkeyMachine env → the COMPLETE FlipPulse env, plus a change report."""
    rep = Report()
    out: Dict[str, str] = {}

    # Dollar knobs first: they decide whether --balance was required.
    needs_balance = [k for k in DOLLARS_TO_FRACTION if k in src and _as_float(src[k])]
    if needs_balance and (balance is None or balance <= 0):
        raise SystemExit(
            "error: --balance is required (and must be > 0) because these dollar "
            "stakes need converting to fractions of balance: "
            + ", ".join(sorted(needs_balance))
        )

    for key, val in src.items():
        if key in DOLLARS_TO_FRACTION:
            dollars = _as_float(val)
            if dollars is None:
                rep.warnings.append(f"{key}={val!r} is not a number — skipped.")
                continue
            new_key = DOLLARS_TO_FRACTION[key]
            # TRADE_SIZE_DOLLARS is the legacy alias for NORMAL_TRADE_SIZE; if
            # both are present the explicit one must win, exactly as
            # MarkeyMachine's own _env_float fallback chain resolves it.
            if key == "TRADE_SIZE_DOLLARS" and "NORMAL_TRADE_SIZE" in src:
                rep.dropped.append(
                    f"{key} — NORMAL_TRADE_SIZE is also set and takes precedence.")
                continue
            frac = round(dollars / balance, 4)  # type: ignore[operator]
            out[new_key] = f"{frac}"
            rep.rescaled.append(
                f"{key}=${dollars:g} → {new_key}={frac} "
                f"({frac * 100:.2f}% of ${balance:,.2f})")
            if frac <= 0:
                rep.warnings.append(
                    f"{new_key} rounded to 0 — ${dollars:g} is below 0.01% of the "
                    f"balance. The bot would never size a trade. Set it by hand.")
            elif frac > 1:
                rep.warnings.append(
                    f"{new_key}={frac} is over 100% of balance — MAX_TRADE_PCT "
                    f"will clamp every trade. Check --balance is correct.")
        elif key in RENAMED:
            out[RENAMED[key]] = val
            rep.renamed.append(f"{key} → {RENAMED[key]} (={val})")
        elif key in DROPPED:
            rep.dropped.append(f"{key} — {DROPPED[key]}")
        elif key in STATE_PATHS:
            continue  # re-emitted from STATE_PATHS below, never copied
        elif key == "PROBATION_RUNGS":
            continue  # a list, not a scalar — rescaled in its own block below
        elif key in CARRY_THROUGH:
            out[key] = val
            rep.carried.append(f"{key}={val}")
        elif key.startswith(("RAILWAY_", "NIXPACKS_", "PORT")):
            continue  # platform-injected, not ours to carry
        else:
            rep.unrecognised.append(f"{key}={val}")

    # PROBATION_RUNGS is a comma-separated LIST of stakes: dollars there,
    # fractions here. Handled apart from the scalar table.
    if src.get("PROBATION_RUNGS", "").strip():
        raw = src["PROBATION_RUNGS"]
        vals = [_as_float(p.strip()) for p in raw.split(",") if p.strip()]
        if all(v is not None for v in vals) and vals:
            if balance and balance > 0:
                fracs = [round(v / balance, 4) for v in vals]  # type: ignore[operator]
                out["PROBATION_RUNGS"] = ",".join(str(f) for f in fracs)
                rep.rescaled.append(
                    f"PROBATION_RUNGS={raw} (dollars) → {out['PROBATION_RUNGS']} (fractions)")
            else:
                rep.warnings.append(
                    "PROBATION_RUNGS present but --balance missing — left unset so "
                    "FlipPulse auto-builds the ramp from RECOVERY_TRADE_PCT.")
        else:
            rep.warnings.append(f"PROBATION_RUNGS={raw!r} unparseable — left unset.")

    # A percentage sizing model needs a sane ceiling. MarkeyMachine's
    # MAX_BET_FRACTION default (0.04) is far tighter than FlipPulse's (0.15);
    # if neither was set explicitly, take FlipPulse's default and say so.
    if "MAX_TRADE_PCT" not in out:
        out["MAX_TRADE_PCT"] = "0.15"
        rep.defaulted.append("MAX_TRADE_PCT=0.15 (FlipPulse default; MAX_BET_FRACTION was unset)")

    # The ceiling must not sit below the normal stake, or every trade clamps.
    n_pct, m_pct = _as_float(out.get("NORMAL_TRADE_PCT", "")), _as_float(out.get("MAX_TRADE_PCT", ""))
    if n_pct and m_pct and n_pct > m_pct:
        rep.warnings.append(
            f"NORMAL_TRADE_PCT={n_pct} exceeds MAX_TRADE_PCT={m_pct} — every trade "
            f"will be clamped to the ceiling. Raise MAX_TRADE_PCT or lower the stake.")

    for key, path in STATE_PATHS.items():
        out[key] = path
    for key, val in FLIPPULSE_DEFAULTS.items():
        if key not in out:
            out[key] = val
            rep.defaulted.append(f"{key}={val}")

    # The PEM is migrated as base64 ONLY. Carrying the raw multi-line form into
    # Railway is what KALSHI_PRIVATE_KEY_PEM_B64 exists to avoid: a newline
    # mangled in a web form yields a key that fails to load at boot. When the
    # source config carried the real PEM we can derive the base64 here, which
    # removes the single most error-prone manual step of the whole migration.
    raw_pem = src.get("KALSHI_PRIVATE_KEY_PEM", "")
    out.pop("KALSHI_PRIVATE_KEY_PEM", None)
    rep.carried = [c for c in rep.carried if not c.startswith("KALSHI_PRIVATE_KEY_PEM=")]
    if "BEGIN" in raw_pem and "END" in raw_pem:
        pem = raw_pem.replace("\\n", "\n").strip() + "\n"
        out["KALSHI_PRIVATE_KEY_PEM_B64"] = base64.b64encode(pem.encode()).decode()
        rep.renamed.append(
            "KALSHI_PRIVATE_KEY_PEM → KALSHI_PRIVATE_KEY_PEM_B64 "
            "(base64-encoded here; single-line, cannot be mangled)")
    elif raw_pem:
        rep.warnings.append(
            "KALSHI_PRIVATE_KEY_PEM was set but does not look like a PEM "
            "(no BEGIN/END markers) — encode it by hand into "
            "KALSHI_PRIVATE_KEY_PEM_B64.")

    for key, why in REQUIRED_MANUAL:
        if not out.get(key):
            out[key] = ""
            rep.warnings.append(f"{key} must be filled in by hand — {why}.")
    return out, rep


# ─────────────────────────────────────────────────────────────────────────────
# STATE MIGRATION
# ─────────────────────────────────────────────────────────────────────────────

def _read_json(path: Path) -> dict | None:
    try:
        with path.open() as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def migrate_state(src_dir: Path, dst_dir: Path, balance: float | None,
                  rep: Report) -> List[str]:
    """Convert a MarkeyMachine /data volume into a FlipPulse one.

    Only three files cross over. Everything else is either MarkeyMachine-only
    (no consumer here) or FlipPulse-only (the bot creates it on first boot,
    and a hand-made one would be worse than absent)."""
    notes: List[str] = []
    dst_dir.mkdir(parents=True, exist_ok=True)

    # ── bucket_stats.json — identical class, identical schema. Straight copy.
    src_bucket = src_dir / "bucket_stats.json"
    if src_bucket.is_file():
        data = _read_json(src_bucket)
        if data is None:
            notes.append("bucket_stats.json — unreadable/not an object, SKIPPED.")
        elif int(data.get("schema", 1)) != 1:
            notes.append(f"bucket_stats.json — schema {data.get('schema')} != 1, SKIPPED.")
        else:
            shutil.copyfile(src_bucket, dst_dir / "bucket_stats.json")
            n = len(data.get("buckets") or {})
            notes.append(f"bucket_stats.json — copied verbatim ({n} buckets, hourly priors kept).")
    else:
        notes.append("bucket_stats.json — not present in source.")

    # ── recovery_state.json — MarkeyMachine schema 1, FlipPulse schema 2.
    # FlipPulse's loader ALREADY back-converts `target_balance` (it holds it as
    # _legacy_target and turns it into a deficit at reconcile_on_boot, which is
    # the first point a live balance exists). So the file is left at schema 1
    # on purpose — converting it here would have to invent the balance that
    # boot reconciliation reads for real. The only fix needed is the win/loss
    # key rename, which would otherwise reset the recovery-scoped tallies to 0.
    src_rec = src_dir / "recovery_state.json"
    if src_rec.is_file():
        data = _read_json(src_rec)
        if data is None:
            notes.append("recovery_state.json — unreadable/not an object, SKIPPED.")
        else:
            out = {
                "schema": 1,                      # FlipPulse reads v1 natively
                "active": bool(data.get("active", False)),
                "target_balance": float(data.get("target_balance", 0.0) or 0.0),
                "wins": int(data.get("period_wins", 0) or 0),
                "losses": int(data.get("period_losses", 0) or 0),
            }
            (dst_dir / "recovery_state.json").write_text(json.dumps(out))
            if out["active"]:
                notes.append(
                    f"recovery_state.json — ACTIVE, target ${out['target_balance']:,.2f} "
                    f"kept at schema 1; FlipPulse converts it to a deficit on first boot. "
                    f"period_wins/losses → wins/losses ({out['wins']}W/{out['losses']}L).")
            else:
                notes.append("recovery_state.json — inactive, carried across (no claw-back pending).")
    else:
        notes.append("recovery_state.json — not present in source.")

    # ── probation_state.json — SAME schema number, DIFFERENT units. This is the
    # file that looks safe to copy and is not: rungs/full_size are dollars in
    # MarkeyMachine and fractions of balance in FlipPulse.
    src_prob = src_dir / "probation_state.json"
    if src_prob.is_file():
        data = _read_json(src_prob)
        if data is None:
            notes.append("probation_state.json — unreadable/not an object, SKIPPED.")
        elif not data.get("active"):
            notes.append("probation_state.json — ramp inactive, SKIPPED (nothing to preserve).")
        elif not balance or balance <= 0:
            notes.append(
                "probation_state.json — ACTIVE but --balance missing, so dollar rungs "
                "cannot be converted to fractions. SKIPPED: the bot rebuilds the ramp "
                "from RECOVERY_TRADE_PCT on the next recovery exit.")
        else:
            rungs = [round(float(r) / balance, 4) for r in (data.get("rungs") or [])]
            full = round(float(data.get("full_size", 0.0) or 0.0) / balance, 4)
            out = {
                "schema": 1,
                "active": True,
                "rungs": rungs,
                "level": int(data.get("level", 0) or 0),
                "full_size": full,
                "streak": int(data.get("streak", 0) or 0),
                "wins": int(data.get("wins", 0) or 0),
                "losses": int(data.get("losses", 0) or 0),
                "day": data.get("day") or "",
            }
            (dst_dir / "probation_state.json").write_text(json.dumps(out))
            notes.append(
                f"probation_state.json — ACTIVE ramp converted dollars→fractions "
                f"(rungs {rungs}, graduating at {full}); resumes at level {out['level']}.")
    else:
        notes.append("probation_state.json — not present in source.")

    # ── MarkeyMachine-only state. No consumer in FlipPulse; carrying it would
    # leave dead files on the volume implying behaviour that will not happen.
    for name, why in (
        ("profit_lock_state.json", "profit lock does not exist in FlipPulse"),
        ("temp_override_state.json", "temp stake override does not exist in FlipPulse"),
    ):
        if (src_dir / name).is_file():
            notes.append(f"{name} — NOT migrated ({why}).")
            rep.warnings.append(
                f"{name} exists in the source volume: that feature stops at cutover.")

    # ── FlipPulse-only state, deliberately absent. daily_state.json in
    # particular must NOT be hand-made: a wrong session_start_balance would
    # mis-arm the +3% daily halt on the very first day.
    notes.append(
        "daily_state.json / lifetime_stats.json / billing_state.json / report_state.json "
        "— not created; the bot writes them on first boot (correct by construction).")
    return notes


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────────────────────

def format_env_block(env: Dict[str, str]) -> str:
    """Railway Raw-Editor format: plain KEY=VALUE, sorted for reviewable diffs."""
    return "\n".join(f"{k}={env[k]}" for k in sorted(env)) + "\n"


def _section(title: str, items: List[str], bullet: str = "  • ") -> None:
    if not items:
        return
    print(f"\n{title} ({len(items)})")
    for item in items:
        print(f"{bullet}{item}")


def print_report(rep: Report, state_notes: List[str]) -> None:
    print("=" * 78)
    print("MarkeyMachine → FlipPulse migration report")
    print("=" * 78)
    _section("RESCALED (dollars → fraction of balance)", rep.rescaled)
    _section("RENAMED", rep.renamed)
    _section("CARRIED THROUGH unchanged", rep.carried)
    _section("FILLED IN at FlipPulse defaults", rep.defaulted)
    _section("DROPPED — no FlipPulse consumer", rep.dropped)
    _section("UNRECOGNISED — in neither fork, review by hand", rep.unrecognised)
    if state_notes:
        _section("STATE FILES", state_notes)
    if rep.warnings:
        print(f"\n⚠️  ACTION REQUIRED ({len(rep.warnings)})")
        for w in rep.warnings:
            print(f"  ! {w}")
    print()


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Translate a MarkeyMachine deployment into a FlipPulse one.")
    ap.add_argument("--env-in", required=True, type=Path,
                    help="MarkeyMachine env file (Railway Raw Editor block)")
    ap.add_argument("--env-out", type=Path,
                    help="write the FlipPulse env block here (default: stdout)")
    ap.add_argument("--balance", type=float,
                    help="account balance the dollar stakes were sized against; "
                         "required when any dollar knob is set")
    ap.add_argument("--state-in", type=Path, help="copy of MarkeyMachine's /data volume")
    ap.add_argument("--state-out", type=Path, help="directory to write migrated state into")
    args = ap.parse_args(argv)

    if not args.env_in.is_file():
        print(f"error: {args.env_in} not found", file=sys.stderr)
        return 2
    if bool(args.state_in) != bool(args.state_out):
        print("error: --state-in and --state-out must be given together", file=sys.stderr)
        return 2

    src = parse_env(args.env_in.read_text())
    env, rep = translate_env(src, args.balance)

    state_notes: List[str] = []
    if args.state_in:
        if not args.state_in.is_dir():
            print(f"error: {args.state_in} is not a directory", file=sys.stderr)
            return 2
        state_notes = migrate_state(args.state_in, args.state_out, args.balance, rep)

    block = format_env_block(env)
    if args.env_out:
        args.env_out.write_text(block)
        print(f"Wrote {len(env)} variables → {args.env_out}")
    else:
        print(block)
    print_report(rep, state_notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
