"""
telegram_utils.py — Telegram notification module for MarkeyMachine

Responsibilities:
  - Validate credentials at startup
  - Send messages with up to 2 retries
  - Fire WIN trade alerts, heartbeat, entry, halt, daily summary

Design rules:
  - Never raises — all errors logged and swallowed
  - All credentials from env vars, nothing hardcoded
  - _telegram_enabled flag gates everything after validation
"""

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

import requests

log = logging.getLogger("MarkeyMachine.telegram")

# ── Module state ──────────────────────────────────────────────────────────────
_telegram_enabled: bool = False
_bot_token: str = ""
_chat_id:   str = ""          # primary (customer) chat — kept for compatibility
_recipients: list = []        # ordered fan-out list: customer chat + operator(s)

# Diagnostics for the most recent failed send, so boot-time failures are
# actionable in the deploy logs instead of an opaque "all attempts failed".
_last_error: str = ""
_last_error_transient: bool = True   # True → network/5xx/429 (retryable); False → config error

# Background self-heal thread: if Telegram is unreachable at boot (a slow deploy
# network is the common cause), keep retrying off the trading path so alerts
# turn themselves on once connectivity returns — no redeploy needed.
_self_heal_thread: Optional[threading.Thread] = None
_self_heal_lock = threading.Lock()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "").strip() or default)
    except (TypeError, ValueError):
        return default


def _parse_recipients(chat: str, operator: str) -> list:
    """Build the ordered, de-duplicated fan-out list: the customer chat id(s)
    first, then any operator chat id(s). Both fields may be comma-separated so a
    single-customer deploy can also copy the operator (you) on every alert
    without a shared group — see TELEGRAM_OPERATOR_CHAT_ID in .env.example."""
    out: list = []
    for raw in (chat or "", operator or ""):
        for cid in raw.split(","):
            cid = cid.strip()
            if cid and cid not in out:
                out.append(cid)
    return out


# ── Public API ─────────────────────────────────────────────────────────────────

def validate_telegram_connection() -> bool:
    """Validate credentials and send a connectivity test. Call once at boot."""
    global _telegram_enabled, _bot_token, _chat_id, _recipients

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat  = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()

    if not token or not chat:
        log.warning("Telegram disabled — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set.")
        _telegram_enabled = False
        return False

    _bot_token  = token
    _chat_id    = chat
    _recipients = _parse_recipients(chat, os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", ""))
    if len(_recipients) > 1:
        log.info("Telegram fan-out to %d recipients (customer + operator).", len(_recipients))

    if _send_raw("🤖 FlipPulse connected to Telegram.\nCredentials validated ✅ — alerts active."):
        log.info("✅ Telegram validated — notifications enabled.")
        _telegram_enabled = True
        return True

    # Validation failed. Distinguish a transient outage (deploy network not up
    # yet — the usual culprit) from a hard config error, because they need very
    # different handling when we're deploying for many customers at scale.
    _telegram_enabled = False
    if _last_error_transient:
        log.warning(
            "⚠️  Telegram unreachable at boot (%s) — retrying in the background; "
            "alerts self-enable once connectivity returns.", _last_error)
        _start_self_heal()
    else:
        log.error(
            "⚠️  Telegram DISABLED — configuration error: %s. Fix the env var and "
            "redeploy; alerts stay off until then.", _last_error)
        _log_config_diagnostic(token)
    return False


def send_telegram_message(text: str) -> bool:
    """Send an arbitrary message. No-op if Telegram is disabled."""
    if not _telegram_enabled:
        return False
    return _send_raw(text)


def send_heartbeat(balance: float, session_pnl: float, open_count: int,
                   trades_today: int, last_signal: str) -> None:
    """
    15-minute heartbeat. Confirms bot is alive and scanning.
    Sent regardless of whether trades are firing.
    """
    if not _telegram_enabled:
        return
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    pnl_sign = "+" if session_pnl >= 0 else ""
    msg = (
        f"💓 Heartbeat — {now}\n"
        f"💵 Balance:     ${balance:,.2f}\n"
        f"📊 Session PnL: {pnl_sign}${session_pnl:.2f}\n"
        f"📂 Open orders: {open_count}\n"
        f"🔁 Trades today:{trades_today}\n"
        f"🔍 Last signal: {last_signal}"
    )
    send_telegram_message(msg)


def send_trade_entry_notification(ticker: str, direction: str, cost: float,
                                   price_cents: int, balance: float,
                                   ob_pct: float = 0.0, edge_pct: float = 0.0,
                                   timestamp: Optional[datetime] = None) -> None:
    """Send a trade entry alert. Fires on every order placed."""
    if not _telegram_enabled:
        return
    ts  = (timestamp or datetime.now(timezone.utc)).strftime("%H:%M UTC")
    pos = "🟢 YES" if direction.upper() == "YES" else "🔴 NO"
    msg = (
        f"📈 TRADE ENTERED — {ts}\n"
        f"📍 {pos}  │  {ticker[-15:]}\n"
        f"💵 Cost: ${cost:.2f}  │  Price: {price_cents}¢\n"
        f"🎯 OB: {ob_pct:.0f}%  │  Edge: {edge_pct:.1f}%\n"
        f"🏦 Balance: ${balance:,.2f}"
    )
    send_telegram_message(msg)


def send_win_notification(profit: float, balance: float, daily_pnl: float,
                           ticker: str, direction: str,
                           wins: int = 0, losses: int = 0,
                           timestamp: Optional[datetime] = None) -> None:
    """Send a WIN alert on every settled winning trade."""
    if not _telegram_enabled:
        return
    if profit <= 0:
        log.debug("send_win_notification called with profit=%.4f — suppressed.", profit)
        return
    ts       = (timestamp or datetime.now(timezone.utc)).strftime("%H:%M UTC")
    pos      = "YES" if direction.upper() == "YES" else "NO"
    pnl_sign = "+" if daily_pnl >= 0 else ""
    tally    = f"{wins}W / {losses}L" if (wins + losses) > 0 else "—"
    msg = (
        f"✅ TRADE SETTLED — WIN  {ts}\n"
        f"📍 {pos}  │  {ticker[-15:]}\n"
        f"💰 Profit: +${profit:.2f}\n"
        f"📊 Today's Tally: {tally}  │  PnL: {pnl_sign}${daily_pnl:.2f}\n"
        f"🏦 Balance: ${balance:,.2f}"
    )
    send_telegram_message(msg)


def send_loss_notification(loss: float, balance: float, daily_pnl: float,
                            ticker: str, direction: str, streak: int,
                            wins: int = 0, losses: int = 0) -> None:
    """Send a LOSS alert on every settled losing trade."""
    if not _telegram_enabled:
        return
    ts         = datetime.now(timezone.utc).strftime("%H:%M UTC")
    pos        = "YES" if direction.upper() == "YES" else "NO"
    pnl_sign   = "+" if daily_pnl >= 0 else ""
    streak_str = f"  │  Streak: {streak}" if streak > 1 else ""
    tally      = f"{wins}W / {losses}L" if (wins + losses) > 0 else "—"
    msg = (
        f"❌ TRADE SETTLED — LOSS  {ts}\n"
        f"📍 {pos}  │  {ticker[-15:]}{streak_str}\n"
        f"💸 Loss: -${loss:.2f}\n"
        f"📊 Today's Tally: {tally}  │  PnL: {pnl_sign}${daily_pnl:.2f}\n"
        f"🏦 Balance: ${balance:,.2f}"
    )
    send_telegram_message(msg)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _describe_http(status: int, body: str) -> Tuple[str, bool]:
    """Turn a non-200 Telegram response into a human-readable reason and a
    transient/permanent flag. Permanent reasons (bad token, bad chat) will never
    fix themselves, so we surface them loudly and do not keep retrying."""
    body = (body or "").strip().replace("\n", " ")[:160]
    if status == 401:
        return (f"HTTP 401 — bot token rejected (check TELEGRAM_BOT_TOKEN). {body}", False)
    if status in (400, 403):
        return (f"HTTP {status} — chat rejected: wrong TELEGRAM_CHAT_ID, or the "
                f"recipient never pressed Start on the bot. {body}", False)
    if status == 404:
        return (f"HTTP 404 — Telegram API not found (malformed bot token?). {body}", False)
    if status == 429:
        return (f"HTTP 429 — rate limited by Telegram (transient). {body}", True)
    if status >= 500:
        return (f"HTTP {status} — Telegram server error (transient). {body}", True)
    return (f"HTTP {status} — {body}", True)


def _log_config_diagnostic(token: str) -> None:
    """On a hard config failure (bad token / 'chat not found'), tell the operator
    exactly how to fix it instead of leaving them to guess. Calls getMe (confirms
    the token and which @bot it belongs to) and getUpdates (lists the chat ids
    that have actually messaged this bot — the valid values for TELEGRAM_CHAT_ID).

    'chat not found' almost always means the configured chat id belongs to a
    *different* bot, or the recipient never pressed Start on this one. Best-effort
    and never raises — diagnostics must not break boot."""
    base = f"https://api.telegram.org/bot{token}"
    try:
        me = requests.get(f"{base}/getMe", timeout=8).json()
        if me.get("ok"):
            bot = me["result"]
            log.error("Telegram token is valid and belongs to @%s (%s). The "
                      "configured chat id was rejected by THIS bot.",
                      bot.get("username", "?"), bot.get("first_name", "?"))
        else:
            log.error("Telegram getMe failed (%s) — the TELEGRAM_BOT_TOKEN itself "
                      "looks wrong.", me.get("description", me))
            return
    except Exception as exc:  # pragma: no cover - network
        log.debug("getMe diagnostic error: %s", exc)
        return

    try:
        upd = requests.get(f"{base}/getUpdates", params={"timeout": 0}, timeout=8).json()
        chats = {}
        for u in upd.get("result", []) if upd.get("ok") else []:
            msg = u.get("message") or u.get("edited_message") or {}
            c = msg.get("chat") or {}
            if c.get("id") is not None:
                who = c.get("username") or c.get("title") or c.get("first_name") or "?"
                chats[str(c["id"])] = who
        if chats:
            listing = ", ".join(f"{cid} ({who})" for cid, who in chats.items())
            log.error("Chats that have messaged @%s: %s. Set TELEGRAM_CHAT_ID to "
                      "the correct id from this list and redeploy.",
                      me["result"].get("username", "this bot"), listing)
        else:
            log.error("No chats have messaged this bot yet — open Telegram, find "
                      "@%s, press Start (or send it any message), then redeploy so "
                      "it can reach you.", me["result"].get("username", "the bot"))
    except Exception as exc:  # pragma: no cover - network
        log.debug("getUpdates diagnostic error: %s", exc)


def _send_raw(text: str) -> bool:
    """Low-level send with up to 2 retries (3 total attempts) per recipient.

    Fans out to every configured recipient (customer chat + any operator chat
    ids). Returns True if the message reached at least one of them. On total
    failure it records a human-readable reason in ``_last_error`` (logged at
    WARNING) plus whether the failure was transient, so a boot-time outage is
    both diagnosable and recoverable."""
    global _last_error, _last_error_transient
    token = _bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    recipients = _recipients or _parse_recipients(
        _chat_id or os.environ.get("TELEGRAM_CHAT_ID", ""),
        os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", ""),
    )

    if not token or not recipients:
        _last_error = "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"
        _last_error_transient = False
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    any_ok = False
    last_reason = ""
    last_transient = True
    for chat in recipients:
        for attempt in range(3):
            try:
                r = requests.post(url, json={"chat_id": chat, "text": text}, timeout=8)
                if r.status_code == 200:
                    any_ok = True
                    break
                reason, transient = _describe_http(r.status_code, r.text)
                last_reason, last_transient = f"chat {chat}: {reason}", transient
                log.debug("Telegram send failed (attempt %d, chat %s): %s",
                          attempt + 1, chat, reason)
            except requests.exceptions.RequestException as exc:
                last_reason = f"chat {chat}: network error ({type(exc).__name__}: {exc})"
                last_transient = True
                log.debug("Telegram send error (attempt %d, chat %s): %s",
                          attempt + 1, chat, exc)
            except Exception as exc:  # never raise into the trading path
                last_reason = f"chat {chat}: unexpected error ({type(exc).__name__}: {exc})"
                last_transient = True
                log.debug("Telegram send error (attempt %d, chat %s): %s",
                          attempt + 1, chat, exc)
            if attempt < 2:
                time.sleep(2)

    if not any_ok:
        _last_error = last_reason or "unknown error"
        _last_error_transient = last_transient
        log.warning("Telegram: all send attempts failed for %d recipient(s) — %s",
                    len(recipients), _last_error)
    return any_ok


# ── Self-heal ───────────────────────────────────────────────────────────────────

def _start_self_heal() -> None:
    """Spin up (once) a daemon thread that keeps retrying the connectivity test
    after a transient boot-time failure, and flips notifications on the moment a
    send succeeds. Idempotent; never touches the trading path."""
    global _self_heal_thread
    with _self_heal_lock:
        if _self_heal_thread is not None and _self_heal_thread.is_alive():
            return
        _self_heal_thread = threading.Thread(
            target=_self_heal_loop, name="tg-selfheal", daemon=True)
        _self_heal_thread.start()


def _self_heal_loop() -> None:
    global _telegram_enabled
    interval = _float_env("TELEGRAM_SELFHEAL_INTERVAL", 15.0)
    max_minutes = _float_env("TELEGRAM_SELFHEAL_MAX_MINUTES", 60.0)
    deadline = time.time() + max_minutes * 60
    while time.time() < deadline:
        time.sleep(max(1.0, interval))
        if _telegram_enabled:      # something else already enabled it
            return
        if _send_raw("🤖 FlipPulse reconnected to Telegram.\nAlerts are now active ✅."):
            _telegram_enabled = True
            log.info("✅ Telegram self-healed — notifications enabled after a "
                     "boot-time connectivity gap.")
            return
        if not _last_error_transient:
            log.error("Telegram self-heal stopped — configuration error: %s. "
                      "Fix the env var and redeploy.", _last_error)
            return
    log.warning("Telegram self-heal gave up after %.0f min (last error: %s); "
                "alerts remain disabled for this run.", max_minutes, _last_error)


def notify(token: str, chat_id: str, text: str) -> bool:
    """Stateless one-shot Telegram send to an explicit token/chat — used by the
    dashboard watchdog for OPERATOR alerts, independent of the bot's module-level
    credentials. Never raises; returns True on a 200 from Telegram."""
    token = (token or "").strip()
    chat_id = (chat_id or "").strip()
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=8)
        return r.status_code == 200
    except Exception as exc:  # pragma: no cover - network failure path
        log.debug("Telegram notify error: %s", exc)
        return False
