"""command_bot.py — single-customer Telegram command listener for FlipPulse.

The customer's own bot already *sends* alerts (telegram_utils.py). This module
lets that same bot *answer* commands so the customer (and the operator) can check
on it — and retune their own risk — from Telegram without any dashboard:

  /status      — current mode (paper/live), balance, PnL, open positions /
                 ladder state, session state, and the last tick time.
  /health-log  — tail of the recent health/activity log.
  /risk        — show the current full-size risk %, or `/risk <percent>` to set it
                 (e.g. `/risk 8`); `/risk reset` restores the configured default.
  /help        — list the commands.

Design (single-customer long-poll listener):
  * Long-polls Telegram getUpdates in a background daemon thread — no inbound
    webhook, no extra service. railway.toml still just runs `python bot.py`.
  * Only messages from authorized chat ids (TELEGRAM_CHAT_ID plus any
    TELEGRAM_OPERATOR_CHAT_ID) are answered; everything else is ignored.
  * The read commands (/status, /health-log) only report state the bot writes to
    disk. The single write command, /risk, cannot place a trade or flip DEMO_MODE
    — it only tunes the ONE full-size stake knob, and does so by dropping a
    clamped value into RISK_OVERRIDE_PATH for the engine to pick up. bot.py
    re-clamps it into [RISK_MIN_TRADE_PCT, MAX_TRADE_PCT] and keeps every
    downside guardrail, so this module stays fully decoupled from the trading loop.
  * `/status` reads the JSON snapshot bot.py writes to STATUS_SNAPSHOT_PATH each
    decision cycle; `/health-log` tails HEALTH_LOG_PATH, which this module wires
    up as a rotating file copy of the bot's log output.
  * Never raises into the trading loop — observability must not break trading.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import List, Optional

import requests

log = logging.getLogger("FlipPulse.command_bot")

# Where bot.py persists its state on the Railway volume. Defaults match
# .env.example so a properly-configured deploy needs no extra wiring.
STATUS_SNAPSHOT_PATH = os.environ.get("STATUS_SNAPSHOT_PATH", "").strip() or "/data/status_snapshot.json"
HEALTH_LOG_PATH      = os.environ.get("HEALTH_LOG_PATH", "").strip() or "/data/health.log"
# Where /risk writes the customer's chosen full-size fraction for the engine to
# read. Must match bot.py's RISK_OVERRIDE_PATH (same default, same /data volume).
RISK_OVERRIDE_PATH   = os.environ.get("RISK_OVERRIDE_PATH", "").strip() or "/data/risk_override.json"
# Where /live and /paper write the desired mode for the engine to restart into.
# Must match bot.py's MODE_OVERRIDE_PATH.
MODE_OVERRIDE_PATH   = os.environ.get("MODE_OVERRIDE_PATH", "").strip() or "/data/mode_override.json"
# Where /recoverynostakechange writes the toggle for the engine to read back.
# Must match bot.py's RECOVERY_NSC_OVERRIDE_PATH (same default, same /data volume).
RECOVERY_NSC_OVERRIDE_PATH = os.environ.get("RECOVERY_NSC_OVERRIDE_PATH", "").strip() \
    or "/data/recovery_nsc_override.json"


def _env_pct(name: str, default_frac: float) -> float:
    """A fraction env var (e.g. MAX_TRADE_PCT=0.15) read as a PERCENT (15.0).
    Used only as a fallback bound before the first status snapshot exists."""
    try:
        return float((os.environ.get(name, "") or "").strip() or default_frac) * 100.0
    except ValueError:
        return default_frac * 100.0


# Fallback clamp bounds (in percent) used only until bot.py has written a snapshot
# carrying the live risk_min_pct / risk_max_pct. Kept in lock-step with bot.py.
RISK_MIN_PCT_FALLBACK = _env_pct("RISK_MIN_TRADE_PCT", 0.01)
RISK_MAX_PCT_FALLBACK = _env_pct("MAX_TRADE_PCT", 0.15)

HELP = (
    "📖 FlipPulse commands\n"
    "\n"
    "📊 Check performance\n"
    "/status — mode, balance, P&L, win rate, positions, recovery state\n"
    "/winrate [day|week] — win rate today, this week, or all-time (default: all three)\n"
    "/pnl [day|week] — profit/loss today, this week, or all-time (default: all three)\n"
    "/balance — current balance + P&L at a glance\n"
    "/health-log [n] — last n lines of the activity log (default 20)\n"
    "\n"
    "🎚 Tune your bot\n"
    "/risk [percent] — show or set your full-size stake %, e.g. /risk 8; /risk reset for the default\n"
    "/recoverynostakechange on|off — keep the stake unchanged during recovery mode "
    "(on = don't shrink the stake while clawing back); no arg shows the current setting\n"
    "\n"
    "🔴 Live / paper\n"
    "/mode — show paper/live mode; /live confirm to go LIVE (real money), /paper to go back\n"
    "\n"
    "/help — this message"
)


# ── health log wiring ─────────────────────────────────────────────────────────
def attach_health_log(path: str = HEALTH_LOG_PATH) -> bool:
    """Mirror the bot's log output into a rotating file so /health-log has
    something to tail. Attaches to the same logger bot.py uses. Best-effort:
    if the volume isn't mounted (e.g. a local run), it's skipped silently."""
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=512_000, backupCount=1)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s │ %(levelname)-8s │ %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
        bot_logger = logging.getLogger("MarkeyMachine")
        # Avoid double-attaching if start_command_bot is called more than once.
        if not any(isinstance(h, RotatingFileHandler)
                   and getattr(h, "baseFilename", "") == handler.baseFilename
                   for h in bot_logger.handlers):
            bot_logger.addHandler(handler)
        return True
    except Exception as exc:  # pragma: no cover - env-dependent
        log.warning("Health log file unavailable (%s) — /health-log limited.", exc)
        return False


# ── command handling (pure of network; testable) ──────────────────────────────
class CommandHandler:
    def __init__(self, authorized_chats: set,
                 snapshot_path: str = STATUS_SNAPSHOT_PATH,
                 health_log_path: str = HEALTH_LOG_PATH,
                 risk_override_path: str = RISK_OVERRIDE_PATH,
                 mode_override_path: str = MODE_OVERRIDE_PATH,
                 nsc_override_path: str = RECOVERY_NSC_OVERRIDE_PATH) -> None:
        self.authorized = {str(c) for c in authorized_chats}
        self.snapshot_path = snapshot_path
        self.health_log_path = health_log_path
        self.risk_override_path = risk_override_path
        self.mode_override_path = mode_override_path
        self.nsc_override_path = nsc_override_path

    def handle(self, chat_id, text: str) -> Optional[str]:
        chat_id = str(chat_id)
        if chat_id not in self.authorized:
            return None  # ignore strangers
        text = (text or "").strip()
        if not text.startswith("/"):
            return None
        parts = text.split()
        # tolerate "/status@mybot", "/health-log"/"/health_log", and a stray
        # trailing "%" (so "/winrate%" — as the customer guide writes it — works).
        cmd = parts[0].lower().lstrip("/").split("@")[0].replace("_", "-").rstrip("%")
        # a separator-insensitive form so "/RecoveryModeNoStakeChange",
        # "/recovery-no-stake-change" and "/rnsc" all route the same way.
        compact = cmd.replace("-", "")
        args = parts[1:]

        if cmd in ("help", "start", "commands"):
            return HELP
        if cmd == "status":
            return self._do_status()
        if cmd == "health-log":
            return self._do_health_log(args)
        if cmd == "risk":
            return self._do_risk(args, chat_id)
        if compact in ("winrate", "wr"):
            return self._do_winrate(args)
        if compact in ("pnl", "pandl", "profit", "pl"):
            return self._do_pnl(args)
        if compact in ("balance", "bal"):
            return self._do_pnl([])   # balance headline + P&L at a glance
        if compact in ("recoverynostakechange", "recoverymodenostakechange",
                       "rnsc", "nostakechange"):
            return self._do_recovery_nsc(args, chat_id)
        if cmd in ("mode", "live", "paper"):
            return self._do_mode(cmd, args, chat_id)
        return f"Unknown command.\n{HELP}"

    # ── /status ────────────────────────────────────────────────────────────────
    def _do_status(self) -> str:
        snap = self._read_snapshot()
        if snap is None:
            return ("No status snapshot yet. The bot writes one each cycle to "
                    f"{self.snapshot_path} once it's booted and STATUS_SNAPSHOT_PATH "
                    "is set — give it a minute after deploy.")
        mode = "LIVE 🔴" if snap.get("demo_mode") is False else "PAPER 🟡"
        if snap.get("pending_demo_mode") is not None:
            mode += f" → {'PAPER' if snap.get('pending_demo_mode') else 'LIVE'} (once flat)"
        bal = snap.get("balance")
        pnl = snap.get("session_pnl")
        wins = snap.get("wins", 0) or 0
        losses = snap.get("losses", 0) or 0
        total = wins + losses
        open_n = snap.get("open_positions", 0) or 0
        tickers = snap.get("open_tickers") or []
        active_mode = snap.get("active_mode", "normal")
        size = snap.get("active_trade_size")
        pct = snap.get("active_trade_pct")
        lines = [
            f"📊 FlipPulse status — {mode}",
            f"Format: {snap.get('trading_format', '?')}",
            f"Balance: ${bal:,.2f}  │  PnL: ${pnl:+,.2f}"
            if isinstance(bal, (int, float)) and isinstance(pnl, (int, float))
            else f"Balance: {bal}  │  PnL: {pnl}",
        ]
        # Prefer the PERSISTENT all-time record (survives redeploys); fall back to
        # the session tally only before any lifetime data exists.
        lt_w = snap.get("lifetime_wins", 0) or 0
        lt_l = snap.get("lifetime_losses", 0) or 0
        if lt_w + lt_l:
            lwr = snap.get("lifetime_win_rate", 0) or 0
            lines.append(f"Record (all-time): {lt_w}W/{lt_l}L ({lwr:.0f}%)")
        elif total:
            wr = snap.get("win_rate", 0)
            lines.append(f"Record: {wins}W/{losses}L ({wr:.0f}%)")
        size_str = ""
        if isinstance(pct, (int, float)):
            size_str = f" · size {pct:.1f}%"
            if isinstance(size, (int, float)):
                size_str += f" (~${size:,.2f})"
        elif isinstance(size, (int, float)):
            size_str = f" · size ${size:,.2f}"
        lines.append(f"Ladder/mode: {active_mode}{size_str}")
        # Recovery Mode "No Stake Change" toggle + recovery-scoped win rate.
        if snap.get("recovery_no_stake_change"):
            lines.append("Recovery: No-Stake-Change ON (stake held while clawing back)")
        if active_mode == "recovery":
            tgt = snap.get("recovery_target")
            if isinstance(tgt, (int, float)) and tgt > 0:
                lines.append(f"Recovery target: ${tgt:,.2f} (balance to claw back to)")
            rw = snap.get("recovery_wins", 0) or 0
            rl = snap.get("recovery_losses", 0) or 0
            if rw + rl:
                rr  = snap.get("recovery_win_rate", 0)
                thr = snap.get("recovery_winrate_restore_pct", 70)
                lines.append(f"Recovery WR: {rr:.0f}% ({rw}W/{rl}L) — "
                             f"auto-restore full stake at {thr:.0f}%")
        norm = snap.get("normal_trade_pct")
        if isinstance(norm, (int, float)):
            lines.append(f"Risk (full-size): {norm:.1f}% — change with /risk")
        open_str = f"{open_n}"
        if tickers:
            open_str += " [" + ", ".join(t[-15:] for t in tickers if t) + "]"
        lines.append(f"Open positions: {open_str}")
        sess = snap.get("session_state", "?")
        if snap.get("halted"):
            sess += " · HALTED ⛔"
        lines.append(f"Session: {sess}")
        lines.append(f"Last signal: {snap.get('last_signal', '—')}")
        lines.append(f"Last tick: {self._fmt_age(snap.get('updated_at'))}")
        return "\n".join(lines)

    def _read_snapshot(self) -> Optional[dict]:
        try:
            with open(self.snapshot_path) as f:
                return json.load(f)
        except (FileNotFoundError, ValueError, OSError):
            return None

    def _no_snapshot_msg(self) -> str:
        return ("No data yet — the bot writes a status snapshot each cycle once "
                "it's booted. Give it a minute after deploy, then try again.")

    @staticmethod
    def _wl(snap: dict, suffix: str) -> tuple:
        """(wins, losses) for a window suffix ('_today'/'_week'/'') from the snapshot."""
        w = snap.get(f"wins{suffix}", 0) or 0
        l = snap.get(f"losses{suffix}", 0) or 0
        return int(w), int(l)

    @staticmethod
    def _lifetime_wl(snap: dict) -> tuple:
        """(wins, losses) from the PERSISTENT all-time tally (survives redeploys)."""
        return (int(snap.get("lifetime_wins", 0) or 0),
                int(snap.get("lifetime_losses", 0) or 0))

    # ── /winrate [day|week] ──────────────────────────────────────────────────────
    def _do_winrate(self, args) -> str:
        snap = self._read_snapshot()
        if snap is None:
            return self._no_snapshot_msg()
        window = (args[0].strip().lower() if args else "")

        def line(label: str, suffix: str, rate_key: str) -> str:
            w, l = self._wl(snap, suffix)
            n = w + l
            if not n:
                return f"{label}: no settled trades yet"
            rate = snap.get(rate_key, 0) or 0
            return f"{label}: {rate:.0f}% ({w}W/{l}L)"

        def all_time() -> str:
            w, l = self._lifetime_wl(snap)
            if not (w + l):
                return "All-time: no settled trades yet"
            rate = snap.get("lifetime_win_rate", 0) or 0
            return f"All-time: {rate:.0f}% ({w}W/{l}L)"

        if window in ("day", "today", "d"):
            return "🎯 Win rate — " + line("Today", "_today", "win_rate_today")
        if window in ("week", "w", "7d"):
            return "🎯 Win rate — " + line("This week", "_week", "win_rate_week")
        if window in ("all", "session", "total", "alltime", "all-time", "lifetime"):
            return "🎯 Win rate — " + all_time()
        # No/unknown arg → show all three.
        return (
            "🎯 Win rate\n"
            + line("Today", "_today", "win_rate_today") + "\n"
            + line("This week", "_week", "win_rate_week") + "\n"
            + all_time()
            + "\n(Use /winrate day or /winrate week for one window.)"
        )

    # ── /pnl [day|week] ──────────────────────────────────────────────────────────
    def _do_pnl(self, args) -> str:
        snap = self._read_snapshot()
        if snap is None:
            return self._no_snapshot_msg()
        window = (args[0].strip().lower() if args else "")

        def line(label: str, pnl_key: str, suffix: str) -> str:
            val = snap.get(pnl_key)
            w, l = self._wl(snap, suffix)
            if not isinstance(val, (int, float)):
                return f"{label}: —"
            return f"{label}: ${val:+,.2f} ({w}W/{l}L)"

        def all_time() -> str:
            val = snap.get("lifetime_pnl")
            w, l = self._lifetime_wl(snap)
            if not isinstance(val, (int, float)):
                return "All-time: —"
            return f"All-time: ${val:+,.2f} ({w}W/{l}L)"

        if window in ("day", "today", "d"):
            return "💵 P&L — " + line("Today", "pnl_today", "_today")
        if window in ("week", "w", "7d"):
            return "💵 P&L — " + line("This week", "pnl_week", "_week")
        if window in ("all", "session", "total", "alltime", "all-time", "lifetime"):
            return "💵 P&L — " + all_time()
        bal = snap.get("balance")
        head = f"🏦 Balance: ${bal:,.2f}\n" if isinstance(bal, (int, float)) else ""
        return (
            "💵 P&L\n" + head
            + line("Today", "pnl_today", "_today") + "\n"
            + line("This week", "pnl_week", "_week") + "\n"
            + all_time()
            + "\n(Use /pnl day or /pnl week for one window.)"
        )

    # ── /recoverynostakechange on|off ────────────────────────────────────────────
    def _do_recovery_nsc(self, args, chat_id: str) -> str:
        snap = self._read_snapshot() or {}
        cur = snap.get("recovery_no_stake_change")
        arg = (args[0].strip().lower() if args else "")
        if not arg:
            state = ("ON" if cur else "OFF") if isinstance(cur, bool) else "unknown (bot still booting)"
            return (
                f"🛟 Recovery Mode — No Stake Change: {state}\n"
                "When ON, recovery still triggers and tracks the claw-back, but keeps "
                "your stake at the full size and keeps laddering — no stake reduction, "
                "no jump-back on exit.\n"
                "Turn it on with `/recoverynostakechange on`, off with "
                "`/recoverynostakechange off`."
            )
        if arg in ("on", "true", "yes", "1", "enable", "enabled"):
            enabled = True
        elif arg in ("off", "false", "no", "0", "disable", "disabled"):
            enabled = False
        else:
            return ("Say `/recoverynostakechange on` or `/recoverynostakechange off`.")
        if not self._write_nsc_override(enabled, chat_id):
            return ("Couldn't save the setting (storage unavailable). No change was "
                    "made — please try again.")
        if enabled:
            return ("✅ Recovery Mode → No Stake Change is now ON.\n"
                    "During recovery the bot keeps your full stake and keeps "
                    "laddering — takes effect immediately, even mid-recovery.")
        return ("✅ Recovery Mode → No Stake Change is now OFF.\n"
                "Recovery will use the standard reduced stake while clawing back. "
                "Takes effect immediately.")

    def _write_nsc_override(self, enabled: bool, chat_id: str) -> bool:
        """Atomically persist the toggle for the engine to read back (mirror of the
        /risk and /mode override writes)."""
        payload = {"enabled": bool(enabled), "set_by": str(chat_id),
                   "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            parent = os.path.dirname(self.nsc_override_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self.nsc_override_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(payload, f)
            os.replace(tmp, self.nsc_override_path)
            return True
        except OSError as exc:
            log.warning("Failed to write NSC override (%s).", exc)
            return False

    # ── /risk ────────────────────────────────────────────────────────────────────
    def _risk_bounds(self, snap: Optional[dict]) -> tuple:
        """(min_pct, max_pct) clamp band. Prefer the live bounds the engine writes
        into the snapshot; fall back to the env-derived defaults before the first
        snapshot exists."""
        lo = hi = None
        if snap is not None:
            lo = snap.get("risk_min_pct")
            hi = snap.get("risk_max_pct")
        lo = float(lo) if isinstance(lo, (int, float)) else RISK_MIN_PCT_FALLBACK
        hi = float(hi) if isinstance(hi, (int, float)) else RISK_MAX_PCT_FALLBACK
        if hi < lo:                       # defensive: never invert the band
            lo, hi = hi, lo
        return lo, hi

    def _current_risk_pct(self, snap: Optional[dict]) -> Optional[float]:
        """The full-size risk % currently in force (reflects any live override)."""
        if snap is None:
            return None
        val = snap.get("normal_trade_pct")
        return float(val) if isinstance(val, (int, float)) else None

    def _do_risk(self, args, chat_id: str) -> str:
        snap = self._read_snapshot()
        lo, hi = self._risk_bounds(snap)
        # No argument → report current setting and the allowed range.
        if not args:
            cur = self._current_risk_pct(snap)
            cur_str = f"{cur:.1f}%" if cur is not None else "unknown (bot still booting)"
            return (
                f"🎯 Risk (full-size stake): {cur_str} of balance per trade.\n"
                f"Change it with e.g. `/risk 8` (allowed {lo:.0f}–{hi:.0f}%). "
                f"`/risk reset` restores the configured default.\n"
                f"Recovery mode and all safety guardrails still apply on top."
            )
        arg = args[0].strip().lower()
        if arg in ("reset", "default", "off", "clear"):
            return self._clear_risk_override()
        # Parse a percentage. Accept "8", "8%", or a fraction like "0.08".
        raw = arg.rstrip("%")
        try:
            val = float(raw)
        except ValueError:
            return (f"Couldn't read '{args[0]}' as a number. Try `/risk 8` for 8%, "
                    f"or `/risk reset` for the default.")
        if val != val or val <= 0:        # NaN or non-positive
            return "Risk must be a positive percentage, e.g. `/risk 8`."
        # A bare value ≤ 1 (and no % sign) is read as a fraction (0.08 → 8%);
        # anything larger is read as a percent (8 → 8%).
        pct = val * 100.0 if (val <= 1 and not arg.endswith("%")) else val
        clamped = max(lo, min(pct, hi))
        note = ""
        if abs(clamped - pct) > 1e-9:
            note = f"\n(‘{pct:.1f}%’ was outside {lo:.0f}–{hi:.0f}% — clamped to {clamped:.1f}%.)"
        ok = self._write_risk_override(clamped, chat_id)
        if not ok:
            return ("Couldn't save the new risk setting (storage unavailable). "
                    "No change was made — please try again.")
        return (f"✅ Risk set to {clamped:.1f}% of balance per trade.{note}\n"
                f"Takes effect on the next trade. `/risk reset` restores the default.")

    def _write_risk_override(self, pct: float, chat_id: str) -> bool:
        """Atomically persist the chosen full-size fraction for the engine to read.
        Stores the FRACTION (0.08) the engine expects, plus context for auditing."""
        payload = {
            "normal_trade_pct": round(pct / 100.0, 6),
            "pct": round(pct, 4),
            "set_by": str(chat_id),
            "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        try:
            parent = os.path.dirname(self.risk_override_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self.risk_override_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(payload, f)
            os.replace(tmp, self.risk_override_path)
            return True
        except OSError as exc:
            log.warning("Failed to write risk override (%s).", exc)
            return False

    def _clear_risk_override(self) -> str:
        try:
            os.remove(self.risk_override_path)
        except FileNotFoundError:
            return "Risk was already at the configured default — nothing to reset."
        except OSError as exc:
            log.warning("Failed to clear risk override (%s).", exc)
            return ("Couldn't clear the override (storage unavailable). "
                    "The previous setting is still in effect.")
        return ("✅ Risk override cleared — back to the configured default. "
                "Takes effect on the next trade.")

    # ── /mode · /live · /paper ────────────────────────────────────────────────────
    def _current_mode(self) -> Optional[bool]:
        """Running demo_mode from the snapshot (True=paper, False=live), or None."""
        snap = self._read_snapshot()
        if snap is None:
            return None
        val = snap.get("demo_mode")
        return val if isinstance(val, bool) else None

    def _do_mode(self, cmd: str, args, chat_id: str) -> str:
        demo = self._current_mode()
        cur = "unknown (bot still booting)" if demo is None else ("PAPER 🟡" if demo else "LIVE 🔴")
        if cmd == "mode":
            snap = self._read_snapshot() or {}
            pend = snap.get("pending_demo_mode")
            extra = ""
            if pend is not None:
                extra = f"\n⏳ Switching to {'PAPER' if pend else 'LIVE'} once the bot is flat."
            return (f"Trading mode: {cur}.{extra}\n"
                    f"Go live with /live confirm (real money); /paper to go back.")
        if cmd == "paper":
            if demo is True:
                return "Already in PAPER mode 🟡."
            if not self._write_mode(True, chat_id):
                return "Couldn't save the mode change (storage unavailable)."
            return ("↩️ Switching to PAPER — the bot will restart into paper mode once "
                    "it's flat (no open position).")
        # cmd == "live"
        if demo is False:
            return "Already in LIVE mode 🔴 (real money)."
        if (args[0].strip().lower() if args else "") != "confirm":
            return ("⚠️ LIVE trading uses REAL money from your Kalshi account.\n"
                    "To proceed, reply:  /live confirm\n"
                    "(You can switch back anytime with /paper.)")
        if not self._write_mode(False, chat_id):
            return "Couldn't save the mode change (storage unavailable)."
        return ("🔴 Going LIVE — the bot will restart into live trading with REAL money "
                "once it's flat (no open position). Use /paper to switch back.")

    def _write_mode(self, demo_mode: bool, chat_id: str) -> bool:
        payload = {"demo_mode": bool(demo_mode), "set_by": str(chat_id),
                   "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            parent = os.path.dirname(self.mode_override_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = self.mode_override_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(payload, f)
            os.replace(tmp, self.mode_override_path)
            return True
        except OSError as exc:
            log.warning("Failed to write mode override (%s).", exc)
            return False

    @staticmethod
    def _fmt_age(updated_at: Optional[str]) -> str:
        if not updated_at:
            return "unknown"
        try:
            ts = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age = int((datetime.now(timezone.utc) - ts).total_seconds())
            return f"{updated_at} ({age}s ago)"
        except ValueError:
            return updated_at

    # ── /health-log ─────────────────────────────────────────────────────────────
    def _do_health_log(self, args) -> str:
        n = next((int(x) for x in args if x.isdigit()), 20)
        n = min(40, max(5, n))
        lines = self._tail(self.health_log_path, n)
        if lines is None:
            return ("Health log not available yet — it's written to "
                    f"{self.health_log_path} on the /data volume once the bot is "
                    "running. Railway's deploy logs have the full output.")
        body = "\n".join(lines) or "(log is empty so far)"
        # Telegram hard-caps messages at 4096 chars.
        if len(body) > 3500:
            body = body[-3500:]
        return f"🩺 health log — last {len(lines)} line(s):\n{body}"

    @staticmethod
    def _tail(path: str, n: int) -> Optional[List[str]]:
        try:
            with open(path, "r", errors="replace") as f:
                return [ln.rstrip("\n") for ln in f.readlines()[-n:]]
        except (FileNotFoundError, OSError):
            return None


# ── long-poll listener thread ─────────────────────────────────────────────────
class TelegramListener:
    def __init__(self, handler: CommandHandler, token: str) -> None:
        self.handler = handler
        self.token = token
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._offset = 0

    def _api(self, method: str, params: dict) -> Optional[dict]:
        try:
            r = requests.get(f"https://api.telegram.org/bot{self.token}/{method}",
                             params=params, timeout=60)
            return r.json() if r.status_code == 200 else None
        except Exception as exc:  # pragma: no cover - network
            log.debug("telegram %s error: %s", method, exc)
            return None

    def _send(self, chat_id, text: str) -> None:
        self._api("sendMessage", {"chat_id": chat_id, "text": text})

    def poll_once(self) -> bool:
        """One getUpdates long-poll cycle. Returns False when the call itself
        failed (network error or a non-ok response) so the caller can back off."""
        data = self._api("getUpdates", {"offset": self._offset, "timeout": 50})
        if not data or not data.get("ok"):
            return False
        for upd in data.get("result", []):
            self._offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("edited_message") or {}
            chat = (msg.get("chat") or {}).get("id")
            text = msg.get("text", "")
            if chat is None or not text:
                continue
            try:
                reply = self.handler.handle(chat, text)
            except Exception as exc:  # pragma: no cover
                reply = f"Error: {exc}"
            if reply:
                self._send(chat, reply)
        return True

    def _run(self) -> None:
        log.info("Telegram command listener started (/status, /health-log).")
        while not self._stop.is_set():
            try:
                if not self.poll_once():
                    # getUpdates failed — a network blip, or HTTP 409 while a
                    # second instance holds the long poll during a redeploy
                    # overlap. Without this pause the thread busy-loops and
                    # hammers Telegram; _stop.wait keeps stop() responsive.
                    self._stop.wait(5)
            except Exception as exc:  # pragma: no cover
                log.debug("listener cycle error: %s", exc)
                self._stop.wait(5)

    def start(self) -> "TelegramListener":
        if self._thread and self._thread.is_alive():
            return self
        self._thread = threading.Thread(target=self._run, name="tg-commands", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()


_listener: Optional[TelegramListener] = None


def start_command_bot() -> Optional[TelegramListener]:
    """Idempotent singleton. Enabled only when the customer's Telegram bot is
    configured (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID). No-op otherwise, so a
    bot with Telegram disabled — or a local run — just skips it."""
    global _listener
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chats = {c.strip() for c in os.environ.get("TELEGRAM_CHAT_ID", "").split(",") if c.strip()}
    chats |= {c.strip() for c in os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", "").split(",") if c.strip()}
    if not token or not chats:
        log.info("Command bot disabled — TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set.")
        return None
    attach_health_log()
    if _listener is None:
        _listener = TelegramListener(CommandHandler(chats), token).start()
    return _listener
