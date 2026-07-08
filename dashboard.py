"""dashboard.py — single-customer self-service web dashboard for FlipPulse.

Each customer runs their own bot; this module lets that bot serve the customer a
small, login-protected web page to fine-tune their own setup WITHOUT a redeploy:

  • Risk %          — full-size stake fraction (same knob as the /risk command).
  • Trading Format  — Conservative / Balanced / Aggressive (applies on next restart).
  • Telegram alerts — mute or unmute trade-entry / win / loss notifications.
  • Set aside ($)   — ring-fence a dollar reserve the bot will never stake.

Design (mirrors command_bot.py — self-contained, threaded, never breaks trading):
  * Stdlib only (http.server) so the minimal customer-bot image gains no new
    dependency; runs in a background daemon thread off the trading path.
  * Fully DECOUPLED from the engine: it never imports bot.py. It reads the live
    state bot.py already writes to the status snapshot, and it writes the SAME
    /data override files bot.py reads back at its sizing chokepoint (risk, reserve)
    or at boot (format) — the mirror image of the status snapshot. Every write is
    re-validated and re-clamped on the engine side, so the dashboard can only ever
    request a change within the safe band, never force an unsafe one.
  * Enabled only when DASHBOARD_PASSWORD is set (like ADMIN_TOKEN gates the
    operator dashboard); a no-op otherwise, so a bot without it just skips serving.
  * Auth is a password + a signed, expiring session cookie (HMAC over a server
    secret). No database, no external service.
  * Never raises into the trading loop.

SECURITY: serve behind HTTPS (Railway's generated domain terminates TLS). The
password is the only gate; keep DASHBOARD_PASSWORD strong and per-customer.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import logging
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Tuple
from urllib.parse import parse_qs

try:
    from formats import FORMATS            # dependency-free; safe to import here
except Exception:                          # pragma: no cover - formats always present
    FORMATS = {}

log = logging.getLogger("FlipPulse.dashboard")

# Same /data paths bot.py uses — the dashboard and the engine meet on these files.
STATUS_SNAPSHOT_PATH  = os.environ.get("STATUS_SNAPSHOT_PATH", "").strip() or "/data/status_snapshot.json"
RISK_OVERRIDE_PATH    = os.environ.get("RISK_OVERRIDE_PATH", "").strip() or "/data/risk_override.json"
RESERVE_OVERRIDE_PATH = os.environ.get("RESERVE_OVERRIDE_PATH", "").strip() or "/data/reserve_override.json"
FORMAT_OVERRIDE_PATH  = os.environ.get("FORMAT_OVERRIDE_PATH", "").strip() or "/data/format_override.json"
TELEGRAM_PREFS_PATH   = os.environ.get("TELEGRAM_PREFS_PATH", "").strip() or "/data/telegram_prefs.json"
# Where the signing secret is persisted so sessions survive a restart (falls back
# to an ephemeral per-boot secret if the volume isn't writable).
SECRET_PATH           = os.environ.get("DASHBOARD_SECRET_PATH", "").strip() or "/data/dashboard_secret"

SESSION_TTL_SECONDS   = 12 * 60 * 60       # a login lasts 12h
COOKIE                = "fp_session"
# Fallback clamp bounds (percent) used until the engine has written a snapshot.
_RISK_MIN_FALLBACK    = 1.0
_RISK_MAX_FALLBACK    = 15.0
# Telegram alert categories the customer may mute (safety/halt alerts stay ON).
TELEGRAM_CATEGORIES   = ("trade_entry", "wins", "losses")


# ── settings I/O (pure, testable; no network) ──────────────────────────────────
class Settings:
    """Reads current state from the status snapshot + override files and writes
    validated override files. All writes are atomic; all reads are best-effort."""

    def __init__(self,
                 snapshot_path: str = STATUS_SNAPSHOT_PATH,
                 risk_path: str = RISK_OVERRIDE_PATH,
                 reserve_path: str = RESERVE_OVERRIDE_PATH,
                 format_path: str = FORMAT_OVERRIDE_PATH,
                 telegram_path: str = TELEGRAM_PREFS_PATH) -> None:
        self.snapshot_path = snapshot_path
        self.risk_path = risk_path
        self.reserve_path = reserve_path
        self.format_path = format_path
        self.telegram_path = telegram_path

    # -- reads -------------------------------------------------------------------
    def _read_json(self, path: str) -> Optional[dict]:
        try:
            with open(path) as f:
                return json.load(f)
        except (FileNotFoundError, ValueError, OSError):
            return None

    def snapshot(self) -> Optional[dict]:
        return self._read_json(self.snapshot_path)

    def risk_bounds(self, snap: Optional[dict]) -> Tuple[float, float]:
        lo = hi = None
        if snap is not None:
            lo, hi = snap.get("risk_min_pct"), snap.get("risk_max_pct")
        lo = float(lo) if isinstance(lo, (int, float)) else _RISK_MIN_FALLBACK
        hi = float(hi) if isinstance(hi, (int, float)) else _RISK_MAX_FALLBACK
        return (lo, hi) if hi >= lo else (hi, lo)

    def state(self) -> dict:
        """The full current-settings view the UI renders and the API returns."""
        snap = self.snapshot()
        lo, hi = self.risk_bounds(snap)
        # Current values: prefer live snapshot (reflects overrides the engine has
        # already picked up); fall back to the override files themselves.
        risk = snap.get("normal_trade_pct") if snap else None
        reserve = snap.get("reserve_dollars") if snap else None
        fmt = snap.get("trading_format") if snap else None
        if reserve is None:
            r = self._read_json(self.reserve_path) or {}
            reserve = r.get("reserve_dollars", 0.0)
        fmt_override = (self._read_json(self.format_path) or {}).get("trading_format")
        prefs = self.telegram_prefs()
        return {
            "connected": snap is not None,
            "mode": ("live" if snap and snap.get("demo_mode") is False else "paper"),
            "balance": (snap or {}).get("balance"),
            "tradeable_balance": (snap or {}).get("tradeable_balance"),
            "session_pnl": (snap or {}).get("session_pnl"),
            "risk_pct": risk,
            "risk_min_pct": lo,
            "risk_max_pct": hi,
            "reserve_dollars": float(reserve or 0.0),
            "trading_format": fmt,
            "format_override": fmt_override,
            "formats": [{"key": k, "name": v.get("display_name", k),
                         "blurb": v.get("blurb", "")} for k, v in FORMATS.items()],
            "telegram": prefs,
            "updated_at": (snap or {}).get("updated_at"),
        }

    def telegram_prefs(self) -> dict:
        prefs = self._read_json(self.telegram_path) or {}
        return {c: bool(prefs.get(c, True)) for c in TELEGRAM_CATEGORIES}

    # -- writes (atomic) ---------------------------------------------------------
    def _write_json(self, path: str, payload: dict) -> bool:
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(payload, f)
            os.replace(tmp, path)
            return True
        except OSError as exc:
            log.warning("Dashboard write to %s failed: %s", path, exc)
            return False

    def _stamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def set_risk(self, pct: float) -> Tuple[bool, str]:
        snap = self.snapshot()
        lo, hi = self.risk_bounds(snap)
        clamped = max(lo, min(pct, hi))
        ok = self._write_json(self.risk_path, {
            "normal_trade_pct": round(clamped / 100.0, 6),
            "pct": round(clamped, 4), "set_by": "dashboard", "updated_at": self._stamp()})
        note = "" if abs(clamped - pct) < 1e-9 else f" (clamped to {clamped:.1f}%)"
        return ok, f"Risk set to {clamped:.1f}%{note}."

    def set_reserve(self, dollars: float) -> Tuple[bool, str]:
        snap = self.snapshot()
        bal = (snap or {}).get("balance")
        amt = max(0.0, dollars)
        note = ""
        if isinstance(bal, (int, float)) and amt > bal:
            amt = float(bal)
            note = f" (capped at your balance ${bal:,.2f})"
        ok = self._write_json(self.reserve_path, {
            "reserve_dollars": round(amt, 2), "set_by": "dashboard",
            "updated_at": self._stamp()})
        return ok, f"Set aside ${amt:,.2f}{note}."

    def set_format(self, fmt: str) -> Tuple[bool, str]:
        key = (fmt or "").strip().lower().replace("-", "_").replace(" ", "_")
        if FORMATS and key not in FORMATS:
            return False, f"Unknown format '{fmt}'."
        ok = self._write_json(self.format_path, {
            "trading_format": key, "set_by": "dashboard", "updated_at": self._stamp()})
        return ok, (f"Trading format set to {key}. This one takes effect on the "
                    f"bot's next restart.")

    def set_telegram(self, prefs: dict) -> Tuple[bool, str]:
        cur = self.telegram_prefs()
        for c in TELEGRAM_CATEGORIES:
            if c in prefs:
                cur[c] = bool(prefs[c])
        ok = self._write_json(self.telegram_path, {**cur, "updated_at": self._stamp()})
        on = [c for c in TELEGRAM_CATEGORIES if cur[c]]
        return ok, f"Telegram alerts updated ({', '.join(on) or 'all muted'})."

    def apply(self, body: dict) -> Tuple[bool, list]:
        """Apply any subset of settings from a parsed JSON body. Returns
        (all_ok, messages)."""
        msgs, ok_all = [], True
        if "risk_pct" in body:
            ok, m = self.set_risk(_to_float(body["risk_pct"]))
            ok_all &= ok; msgs.append(m)
        if "reserve_dollars" in body:
            ok, m = self.set_reserve(_to_float(body["reserve_dollars"]))
            ok_all &= ok; msgs.append(m)
        if "trading_format" in body:
            ok, m = self.set_format(body["trading_format"])
            ok_all &= ok; msgs.append(m)
        if "telegram" in body and isinstance(body["telegram"], dict):
            ok, m = self.set_telegram(body["telegram"])
            ok_all &= ok; msgs.append(m)
        if not msgs:
            return False, ["No recognized settings in request."]
        return ok_all, msgs


def _to_float(v) -> float:
    try:
        return float(str(v).strip().rstrip("%"))
    except (TypeError, ValueError):
        return float("nan")


# ── session tokens (signed, expiring) ──────────────────────────────────────────
def _load_secret() -> bytes:
    env = os.environ.get("DASHBOARD_SECRET", "").strip()
    if env:
        return env.encode()
    try:
        with open(SECRET_PATH, "rb") as f:
            data = f.read().strip()
            if data:
                return data
    except OSError:
        pass
    token = secrets.token_hex(32).encode()
    try:
        parent = os.path.dirname(SECRET_PATH)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(SECRET_PATH, "wb") as f:
            f.write(token)
        os.chmod(SECRET_PATH, 0o600)
    except OSError:                         # ephemeral secret — sessions drop on restart
        log.info("Dashboard secret not persisted (volume unavailable); sessions reset on restart.")
    return token


def make_session(secret: bytes, ttl: int = SESSION_TTL_SECONDS) -> str:
    exp = str(int(time.time()) + ttl)
    sig = hmac.new(secret, exp.encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def valid_session(secret: bytes, cookie: Optional[str]) -> bool:
    if not cookie or "." not in cookie:
        return False
    exp, _, sig = cookie.partition(".")
    expected = hmac.new(secret, exp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        return int(exp) > int(time.time())
    except ValueError:
        return False


# ── HTTP handler ───────────────────────────────────────────────────────────────
class _Handler(BaseHTTPRequestHandler):
    server_version = "FlipPulseDashboard/1.0"

    # server-injected attributes
    settings: Settings
    password: str
    secret: bytes

    def log_message(self, *args) -> None:      # silence default stderr logging
        return

    # -- helpers -----------------------------------------------------------------
    def _cookie(self) -> Optional[str]:
        raw = self.headers.get("Cookie", "")
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == COOKIE:
                return v
        return None

    def _authed(self) -> bool:
        return valid_session(self.secret, self._cookie())

    def _send(self, code: int, body: bytes, ctype: str, extra=None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or []):
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _html(self, code: int, markup: str, extra=None) -> None:
        self._send(code, markup.encode("utf-8"), "text/html; charset=utf-8", extra)

    def _json(self, code: int, obj: dict, extra=None) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"), "application/json", extra)

    def _read_body(self) -> bytes:
        try:
            n = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            return b""
        return self.rfile.read(n) if n > 0 else b""

    # -- routing -----------------------------------------------------------------
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            if self._authed():
                self._html(200, _dashboard_page(self.settings.state()))
            else:
                self._html(200, _login_page())
            return
        if path == "/api/state":
            if not self._authed():
                self._json(401, {"error": "unauthorized"})
                return
            self._json(200, self.settings.state())
            return
        if path == "/healthz":
            self._json(200, {"ok": True})
            return
        self._html(404, "<h1>404</h1>")

    do_HEAD = do_GET

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/login":
            self._handle_login()
            return
        if path == "/logout":
            self._html(303, "", extra=[("Location", "/"),
                       ("Set-Cookie", f"{COOKIE}=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict")])
            return
        if path == "/api/settings":
            self._handle_settings()
            return
        self._html(404, "<h1>404</h1>")

    def _handle_login(self) -> None:
        form = parse_qs(self._read_body().decode("utf-8", "replace"))
        supplied = (form.get("password") or [""])[0]
        if self.password and hmac.compare_digest(supplied, self.password):
            cookie = make_session(self.secret)
            self._html(303, "", extra=[
                ("Location", "/"),
                ("Set-Cookie",
                 f"{COOKIE}={cookie}; Path=/; Max-Age={SESSION_TTL_SECONDS}; "
                 f"HttpOnly; SameSite=Strict")])
        else:
            self._html(401, _login_page(error="Incorrect password."))

    def _handle_settings(self) -> None:
        if not self._authed():
            self._json(401, {"error": "unauthorized"})
            return
        try:
            body = json.loads(self._read_body().decode("utf-8", "replace") or "{}")
            if not isinstance(body, dict):
                raise ValueError("body must be an object")
        except ValueError:
            self._json(400, {"error": "invalid JSON"})
            return
        ok, msgs = self.settings.apply(body)
        self._json(200 if ok else 500, {"ok": ok, "messages": msgs,
                                        "state": self.settings.state()})


# ── HTML rendering ─────────────────────────────────────────────────────────────
_STYLE = """
:root{color-scheme:light dark}
*{box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
 margin:0;background:#0f1216;color:#e6e9ef;line-height:1.5}
.wrap{max-width:640px;margin:0 auto;padding:24px 18px 64px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:#8b93a7;font-size:13px;margin:0 0 20px}
.card{background:#171b22;border:1px solid #232936;border-radius:12px;padding:18px;margin:0 0 16px}
.card h2{font-size:15px;margin:0 0 4px}
.card p.hint{color:#8b93a7;font-size:12.5px;margin:2px 0 12px}
label{display:block;font-size:13px;margin:0 0 6px;color:#c3c9d6}
input[type=number],select{width:100%;padding:10px;border-radius:8px;border:1px solid #2c3444;
 background:#0f1216;color:#e6e9ef;font-size:15px}
.row{display:flex;gap:10px;align-items:center}
.toggle{display:flex;align-items:center;justify-content:space-between;padding:8px 0;
 border-bottom:1px solid #232936}
.toggle:last-child{border-bottom:0}
button{background:#3b82f6;color:#fff;border:0;border-radius:8px;padding:11px 16px;
 font-size:15px;font-weight:600;cursor:pointer}
button.ghost{background:#232936;color:#c3c9d6}
button:disabled{opacity:.5;cursor:default}
.stat{display:flex;justify-content:space-between;font-size:14px;padding:4px 0}
.stat b{font-variant-numeric:tabular-nums}
.pill{display:inline-block;font-size:11px;padding:2px 8px;border-radius:999px;
 background:#233045;color:#7fb0ff;margin-left:6px}
.msg{margin:0 0 16px;padding:10px 12px;border-radius:8px;font-size:13.5px;display:none}
.msg.ok{background:#12281a;color:#7fe0a0;display:block}
.msg.err{background:#2a1616;color:#ff9a9a;display:block}
.foot{color:#6b7280;font-size:12px;text-align:center;margin-top:24px}
.login{max-width:360px;margin:12vh auto 0}
"""


def _login_page(error: str = "") -> str:
    err = f'<div class="msg err" style="display:block">{html.escape(error)}</div>' if error else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlipPulse — Sign in</title><style>{_STYLE}</style></head><body>
<div class="wrap login"><h1>FlipPulse</h1><p class="sub">Sign in to tune your bot.</p>
{err}
<form method="post" action="/login" class="card">
<label for="pw">Password</label>
<input id="pw" name="password" type="password" autofocus autocomplete="current-password"
 style="width:100%;padding:10px;border-radius:8px;border:1px solid #2c3444;background:#0f1216;color:#e6e9ef">
<div style="height:12px"></div><button type="submit" style="width:100%">Sign in</button>
</form><p class="foot">Your funds stay on Kalshi. This page only changes bot settings.</p>
</div></body></html>"""


def _fmt_money(v) -> str:
    return f"${v:,.2f}" if isinstance(v, (int, float)) else "—"


def _dashboard_page(st: dict) -> str:
    fmt_opts = "".join(
        f'<option value="{html.escape(f["key"])}"'
        f'{" selected" if (st.get("format_override") or st.get("trading_format")) == f["key"] else ""}>'
        f'{html.escape(f["name"])}</option>'
        for f in st.get("formats", []))
    tg = st.get("telegram", {})

    def toggle(cat, label):
        checked = "checked" if tg.get(cat, True) else ""
        return (f'<div class="toggle"><span>{label}</span>'
                f'<input type="checkbox" data-tg="{cat}" {checked}></div>')

    risk = st.get("risk_pct")
    risk_val = f"{risk:.1f}" if isinstance(risk, (int, float)) else ""
    lo, hi = st.get("risk_min_pct", 1), st.get("risk_max_pct", 15)
    reserve = st.get("reserve_dollars", 0.0)
    mode_pill = f'<span class="pill">{html.escape(st.get("mode","?").upper())}</span>'
    conn = ("" if st.get("connected") else
            '<div class="msg err" style="display:block">Bot is still booting — '
            'values will populate shortly. You can still save changes.</div>')

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlipPulse — Dashboard</title><style>{_STYLE}</style></head><body>
<div class="wrap">
  <h1>Your FlipPulse bot {mode_pill}</h1>
  <p class="sub">Fine-tune your setup. Changes save instantly (format applies on next restart).</p>
  {conn}
  <div id="msg" class="msg"></div>

  <div class="card">
    <div class="stat"><span>Balance</span><b>{_fmt_money(st.get("balance"))}</b></div>
    <div class="stat"><span>In play (after set-aside)</span><b>{_fmt_money(st.get("tradeable_balance"))}</b></div>
    <div class="stat"><span>Session PnL</span><b>{_fmt_money(st.get("session_pnl"))}</b></div>
  </div>

  <div class="card">
    <h2>Risk per trade</h2>
    <p class="hint">Full-size stake as a % of balance. Allowed {lo:.0f}–{hi:.0f}%.</p>
    <div class="row">
      <input id="risk" type="number" step="0.5" min="{lo}" max="{hi}" value="{risk_val}" placeholder="e.g. 8">
      <button data-save="risk">Save</button>
    </div>
  </div>

  <div class="card">
    <h2>Set aside</h2>
    <p class="hint">Dollars to ring-fence — the bot never stakes this. It trades only the balance above it.</p>
    <div class="row">
      <input id="reserve" type="number" step="10" min="0" value="{reserve:.2f}" placeholder="0">
      <button data-save="reserve">Save</button>
    </div>
  </div>

  <div class="card">
    <h2>Trading format</h2>
    <p class="hint">Your overall risk posture. Takes effect on the bot's next restart.</p>
    <div class="row">
      <select id="format">{fmt_opts}</select>
      <button data-save="format">Save</button>
    </div>
  </div>

  <div class="card">
    <h2>Telegram alerts</h2>
    <p class="hint">Mute routine trade alerts. Safety, halt and recovery alerts always stay on.</p>
    {toggle("trade_entry","Trade entered")}
    {toggle("wins","Wins")}
    {toggle("losses","Losses")}
    <div style="height:12px"></div>
    <button data-save="telegram">Save alert settings</button>
  </div>

  <form method="post" action="/logout"><button class="ghost" type="submit">Sign out</button></form>
  <p class="foot">Your funds stay on Kalshi. This page only changes bot settings.</p>
</div>
<script>
const msg = document.getElementById('msg');
function show(ok, text){{ msg.textContent = text; msg.className = 'msg ' + (ok?'ok':'err'); }}
async function save(payload){{
  try{{
    const r = await fetch('/api/settings', {{method:'POST',headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify(payload)}});
    const d = await r.json();
    show(d.ok, (d.messages||['Saved.']).join(' '));
  }}catch(e){{ show(false, 'Network error — not saved.'); }}
}}
document.querySelectorAll('[data-save]').forEach(b => b.addEventListener('click', () => {{
  const k = b.getAttribute('data-save');
  if(k==='risk')    return save({{risk_pct: parseFloat(document.getElementById('risk').value)}});
  if(k==='reserve') return save({{reserve_dollars: parseFloat(document.getElementById('reserve').value)}});
  if(k==='format')  return save({{trading_format: document.getElementById('format').value}});
  if(k==='telegram'){{
    const tg = {{}};
    document.querySelectorAll('[data-tg]').forEach(c => tg[c.getAttribute('data-tg')] = c.checked);
    return save({{telegram: tg}});
  }}
}}));
</script>
</body></html>"""


# ── server lifecycle ────────────────────────────────────────────────────────────
_server: Optional[ThreadingHTTPServer] = None


def start_dashboard() -> Optional[ThreadingHTTPServer]:
    """Idempotent singleton. Enabled only when DASHBOARD_PASSWORD is set; a no-op
    otherwise (a local run or a bot that hasn't opted in just skips it). Binds
    0.0.0.0:$DASHBOARD_PORT (default $PORT or 8080) in a daemon thread."""
    global _server
    if _server is not None:
        return _server
    password = os.environ.get("DASHBOARD_PASSWORD", "").strip()
    if not password:
        log.info("Dashboard disabled — DASHBOARD_PASSWORD not set.")
        return None
    port = int(os.environ.get("DASHBOARD_PORT", "").strip()
               or os.environ.get("PORT", "").strip() or "8080")
    secret = _load_secret()
    settings = Settings()

    handler = type("_BoundHandler", (_Handler,),
                   {"settings": settings, "password": password, "secret": secret})
    _server = ThreadingHTTPServer(("0.0.0.0", port), handler)
    t = threading.Thread(target=_server.serve_forever, name="fp-dashboard", daemon=True)
    t.start()
    log.info("Customer dashboard listening on 0.0.0.0:%d", port)
    return _server
