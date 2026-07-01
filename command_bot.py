"""command_bot.py — single-customer Telegram command listener for FlipPulse.

The customer's own bot already *sends* alerts (telegram_utils.py). This module
lets that same bot *answer* two read-only commands so the customer (and the
operator) can check on it from Telegram without any dashboard:

  /status      — current mode (paper/live), balance, PnL, open positions /
                 ladder state, session state, and the last tick time.
  /health-log  — tail of the recent health/activity log.
  /help        — list the commands.

Design (mirrors the long-poll listener markeymachine already uses in
dashboard/telegram_bot.py, trimmed to one customer):
  * Long-polls Telegram getUpdates in a background daemon thread — no inbound
    webhook, no extra service. railway.toml still just runs `python bot.py`.
  * Only messages from authorized chat ids (TELEGRAM_CHAT_ID plus any
    TELEGRAM_OPERATOR_CHAT_ID) are answered; everything else is ignored.
  * Commands are READ-ONLY. Nothing here can place a trade, change a parameter,
    or flip DEMO_MODE — it only reports state the bot already writes to disk.
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
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import List, Optional

import requests

log = logging.getLogger("FlipPulse.command_bot")

# Where bot.py persists its state on the Railway volume. Defaults match
# .env.example so a properly-configured deploy needs no extra wiring.
STATUS_SNAPSHOT_PATH = os.environ.get("STATUS_SNAPSHOT_PATH", "").strip() or "/data/status_snapshot.json"
HEALTH_LOG_PATH      = os.environ.get("HEALTH_LOG_PATH", "").strip() or "/data/health.log"

HELP = (
    "FlipPulse commands:\n"
    "/status — mode, balance, PnL, open positions / ladder state, last tick\n"
    "/health-log [n] — last n lines of the health/activity log (default 20)\n"
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
                 health_log_path: str = HEALTH_LOG_PATH) -> None:
        self.authorized = {str(c) for c in authorized_chats}
        self.snapshot_path = snapshot_path
        self.health_log_path = health_log_path

    def handle(self, chat_id, text: str) -> Optional[str]:
        chat_id = str(chat_id)
        if chat_id not in self.authorized:
            return None  # ignore strangers
        text = (text or "").strip()
        if not text.startswith("/"):
            return None
        parts = text.split()
        # tolerate "/status@mybot" and "/health-log"/"/health_log"
        cmd = parts[0].lower().lstrip("/").split("@")[0].replace("_", "-")
        args = parts[1:]

        if cmd in ("help", "start"):
            return HELP
        if cmd == "status":
            return self._do_status()
        if cmd == "health-log":
            return self._do_health_log(args)
        return f"Unknown command.\n{HELP}"

    # ── /status ────────────────────────────────────────────────────────────────
    def _do_status(self) -> str:
        snap = self._read_snapshot()
        if snap is None:
            return ("No status snapshot yet. The bot writes one each cycle to "
                    f"{self.snapshot_path} once it's booted and STATUS_SNAPSHOT_PATH "
                    "is set — give it a minute after deploy.")
        mode = "LIVE 🔴" if snap.get("demo_mode") is False else "PAPER 🟡"
        bal = snap.get("balance")
        pnl = snap.get("session_pnl")
        wins = snap.get("wins", 0) or 0
        losses = snap.get("losses", 0) or 0
        total = wins + losses
        open_n = snap.get("open_positions", 0) or 0
        tickers = snap.get("open_tickers") or []
        active_mode = snap.get("active_mode", "normal")
        size = snap.get("active_trade_size")
        lines = [
            f"📊 FlipPulse status — {mode}",
            f"Format: {snap.get('trading_format', '?')}",
            f"Balance: ${bal:,.2f}  │  PnL: ${pnl:+,.2f}"
            if isinstance(bal, (int, float)) and isinstance(pnl, (int, float))
            else f"Balance: {bal}  │  PnL: {pnl}",
        ]
        if total:
            wr = snap.get("win_rate", 0)
            lines.append(f"Record: {wins}W/{losses}L ({wr:.0f}%)")
        lines.append(
            f"Ladder/mode: {active_mode}"
            + (f" · size ${size:,.2f}" if isinstance(size, (int, float)) else ""))
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

    def poll_once(self) -> None:
        data = self._api("getUpdates", {"offset": self._offset, "timeout": 50})
        if not data or not data.get("ok"):
            return
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

    def _run(self) -> None:
        log.info("Telegram command listener started (/status, /health-log).")
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception as exc:  # pragma: no cover
                log.debug("listener cycle error: %s", exc)
                time.sleep(5)

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
