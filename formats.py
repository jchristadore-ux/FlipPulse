"""
formats.py — Trading Formats (named presets) for FlipPulse.

WHY
---
Every customer funds a different bankroll, so sizing can never be shipped as a
fixed dollar figure. FlipPulse sizes every trade as a **percentage of the current
balance** (see bot.py `active_trade_size`), and a "Trading Format" is a named
bundle of those percentage knobs plus the entry-gate thresholds — the whole risk
posture switched with one variable:

    TRADING_FORMAT=conservative python bot.py

The three customer-facing formats map 1:1 to the branded strategy modes the
onboarding PDF asks the customer to choose from:

    Conservative  •  Balanced  •  Aggressive

DESIGN
------
`apply_format()` seeds each preset value into the environment with
`os.environ.setdefault()` — it only fills a key that is *not already set*. So:

  • Selecting a format gives you its whole posture in one switch.
  • Any explicit env var (Railway config, a one-off override, the dashboard)
    still wins over the preset — formats set defaults, they never clobber.

It must run BEFORE `bot.py` reads its config block (the module-level `_env_*()`
calls), so `bot.py` imports and calls this right after defining its env helpers
and before the first `_require()`.

SIZING IS PERCENTAGES
---------------------
`NORMAL_TRADE_PCT` / `RECOVERY_TRADE_PCT` / `MAX_TRADE_PCT` are fractions of the
current balance (0.10 = 10%). Because they are percentages, one format fits every
customer regardless of their starting balance, and the stake compounds up as the
account grows and de-risks as it shrinks. There are no dollar sizes here.

This module is intentionally dependency-free and does NOT import `bot.py`, so it
can be listed (`python formats.py`) and unit-tested without Kalshi credentials.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Dict, List

log = logging.getLogger("FlipPulse.formats")

DEFAULT_FORMAT = "balanced"

# ── The three branded strategy modes ──────────────────────────────────────────
# Each preset FULLY defines a posture: the percentage sizing knobs (fractions of
# the current balance) plus the entry-gate thresholds. Selecting a format seeds
# all of them; an explicit env var always overrides.
#
# Per-trade sizing (fractions of the CURRENT balance):
#   NORMAL_TRADE_PCT    full stake in normal operation
#   RECOVERY_TRADE_PCT  reduced stake while clawing back a full-size loss
#   MAX_TRADE_PCT       hard ceiling on any single trade (the ladder can't pass it)

FORMATS: Dict[str, dict] = {
    "conservative": {
        "display_name": "Conservative — Capital Preservation",
        "blurb": "Fewer, higher-conviction trades at a small % of balance. Strict "
                 "gates, recovery + probation on, ladder off. Built to protect the "
                 "bankroll.",
        "description": (
            "Tightens every entry gate (order-book imbalance, regime R², "
            "confidence, edge, win-prob), requires BTC momentum AGREE, runs one "
            "position at a time, and keeps the graduated Recovery/Probation "
            "sizing on with the Ladder overlay off. Smallest per-trade percentage "
            "and an earlier session-stop. Lowest trade frequency, lowest variance."
        ),
        "settings": {
            "DEMO_MODE": "true",
            "NORMAL_TRADE_PCT": 0.05,
            "RECOVERY_TRADE_PCT": 0.02,
            "MAX_TRADE_PCT": 0.08,
            "LADDER_ENABLED": "false",
            "PROBATION_RAMP_ENABLED": "true",
            "REQUIRE_AGREE_MOMENTUM": "true",
            "OB_IMBALANCE_THRESH": 0.75,
            "MIN_OB_DEPTH_DOLLARS": 100.0,
            "R2_TREND_THRESHOLD": 0.70,
            "MIN_CONFIDENCE": 70,
            "MIN_EDGE_PCT": 0.08,
            "MIN_WIN_PROB": 0.62,
            "MAX_CONCURRENT_POS": 1,
            "MAX_CONSEC_LOSSES": 2,
            "SESSION_STOP_FRACTION": 0.60,
            "YES_BREAKEVEN_PRICE": 65,
        },
    },
    "balanced": {
        "display_name": "Balanced — Standard (default)",
        "blurb": "The default posture. Moderate per-trade %, two-tier Recovery + "
                 "Probation sizing, ladder off, doctrine-default gates.",
        "description": (
            "The shipped default. Stakes 10% of balance normally, drops to 3% "
            "while clawing back a loss, and never exceeds 15% on any single trade. "
            "The Probation ramp is on, the Ladder overlay is off, momentum-AGREE "
            "is required, and the doctrine entry thresholds apply (OB imbalance "
            "0.70, R² 0.65, confidence 65, edge 6%, win-prob 60%). A sensible "
            "middle ground of frequency and variance for most customers."
        ),
        "settings": {
            "DEMO_MODE": "true",
            "NORMAL_TRADE_PCT": 0.10,
            "RECOVERY_TRADE_PCT": 0.03,
            "MAX_TRADE_PCT": 0.15,
            "LADDER_ENABLED": "false",
            "PROBATION_RAMP_ENABLED": "true",
            "REQUIRE_AGREE_MOMENTUM": "true",
            "OB_IMBALANCE_THRESH": 0.70,
            "MIN_OB_DEPTH_DOLLARS": 75.0,
            "R2_TREND_THRESHOLD": 0.65,
            "MIN_CONFIDENCE": 65,
            "MIN_EDGE_PCT": 0.06,
            "MIN_WIN_PROB": 0.60,
            "MAX_CONCURRENT_POS": 1,
            "MAX_CONSEC_LOSSES": 2,
            "SESSION_STOP_FRACTION": 0.40,
            "YES_BREAKEVEN_PRICE": 67,
        },
    },
    "aggressive": {
        "display_name": "Aggressive — Edge Hunter",
        "blurb": "More trades, larger % of balance, Ladder overlay on (up to 2×). "
                 "Higher throughput and higher variance.",
        "description": (
            "Relaxes the entry gates (lower OB imbalance, R², confidence, edge and "
            "win-prob floors), allows two concurrent positions, raises the "
            "loss-streak pause threshold, and turns the performance-driven Ladder "
            "overlay ON so a hot win rate scales the stake up toward the max. "
            "Stakes 20% of balance normally with a 30% hard ceiling. Highest trade "
            "frequency and variance — only the always-on guardrails (streak pause, "
            "session stop, ladder drawdown caps, MAX_TRADE_PCT) remain."
        ),
        "settings": {
            "DEMO_MODE": "true",
            "NORMAL_TRADE_PCT": 0.20,
            "RECOVERY_TRADE_PCT": 0.05,
            "MAX_TRADE_PCT": 0.30,
            "LADDER_ENABLED": "true",
            "PROBATION_RAMP_ENABLED": "true",
            "REQUIRE_AGREE_MOMENTUM": "true",
            "OB_IMBALANCE_THRESH": 0.65,
            "MIN_OB_DEPTH_DOLLARS": 50.0,
            "R2_TREND_THRESHOLD": 0.60,
            "MIN_CONFIDENCE": 60,
            "MIN_EDGE_PCT": 0.05,
            "MIN_WIN_PROB": 0.58,
            "MAX_CONCURRENT_POS": 2,
            "MAX_CONSEC_LOSSES": 3,
            "SESSION_STOP_FRACTION": 0.35,
            "YES_BREAKEVEN_PRICE": 70,
        },
    },
}


def _resolve(name: str) -> str:
    """Normalize a requested format name to a known key, or DEFAULT_FORMAT."""
    key = (name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key in FORMATS:
        return key
    if key:
        log.warning("Unknown TRADING_FORMAT %r — falling back to %r. Known: %s",
                    name, DEFAULT_FORMAT, ", ".join(FORMATS))
    return DEFAULT_FORMAT


def apply_format(name: str) -> str:
    """Seed the selected format's settings into os.environ as DEFAULTS.

    Uses os.environ.setdefault, so a value already present in the environment
    (Railway config, an explicit override, the dashboard) is never clobbered —
    formats define the posture, explicit env vars win. Returns the resolved
    format name actually applied.
    """
    resolved = _resolve(name)
    for key, value in FORMATS[resolved]["settings"].items():
        os.environ.setdefault(key, str(value))
    log.info("Trading format: %s (%s)", resolved, FORMATS[resolved]["display_name"])
    return resolved


def list_formats() -> List[dict]:
    """Format metadata for the dashboard / CLI (no side effects)."""
    return [
        {
            "name": name,
            "display_name": spec["display_name"],
            "blurb": spec["blurb"],
            "description": spec["description"],
            "settings": dict(spec["settings"]),
            "is_default": name == DEFAULT_FORMAT,
        }
        for name, spec in FORMATS.items()
    ]


def print_formats() -> None:
    """Human-readable listing for `python formats.py` / `bot.py --list-formats`."""
    print("FlipPulse — Trading Formats (all sizing is % of current balance)\n")
    for spec in list_formats():
        star = "  (default)" if spec["is_default"] else ""
        s = spec["settings"]
        print(f"  {spec['name']}{star}")
        print(f"      {spec['display_name']}")
        print(f"      {spec['blurb']}")
        print(f"      normal={s['NORMAL_TRADE_PCT']*100:.0f}% "
              f"recovery={s['RECOVERY_TRADE_PCT']*100:.0f}% "
              f"max={s['MAX_TRADE_PCT']*100:.0f}% "
              f"ladder={s['LADDER_ENABLED']} "
              f"OB≥{s['OB_IMBALANCE_THRESH']} R²≥{s['R2_TREND_THRESHOLD']}\n")
    print("Select with:  TRADING_FORMAT=<name> python bot.py")
    print("Explicit env vars always override a format's defaults.")


if __name__ == "__main__":
    if "--json" in sys.argv:
        import json
        print(json.dumps(list_formats(), indent=2))
    else:
        print_formats()
