"""
FlipPulse — digital customer onboarding service.

A small Flask app that serves the branded onboarding form and, on submit:
  1. Validates the intake.
  2. ENCRYPTS the customer's secrets (Kalshi PEM + API key id, Telegram bot token)
     at rest with Fernet, and writes a submission file to SUBMISSIONS_DIR — the
     "backend admin file" the operator opens to deploy (see admin_cli.py).
  3. Alerts the operator over Telegram (non-secret summary only).
  4. If Stripe is configured, launches Checkout to collect the one-time SETUP fee
     and start the MONTHLY subscription (card kept on file for future invoices).
     Otherwise it shows a local success page.

Design notes
------------
* Secrets are NEVER logged and NEVER sent to Telegram — only the encrypted
  submission file holds them, and only the holder of ONBOARDING_FERNET_KEY can
  read them back.
* Run behind HTTPS (Railway terminates TLS for you). The form collects a private
  key, so a plain-HTTP deployment is not acceptable.
* This service is standalone — it does not import the trading bot.
"""

from __future__ import annotations

import base64
import hmac
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import (Flask, abort, make_response, redirect, render_template,
                   request, send_from_directory, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    import provisioner                     # gunicorn/app run from onboarding/
except ImportError:                        # imported as the onboarding.* package
    from onboarding import provisioner

log = logging.getLogger("flippulse.onboarding")
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s │ %(levelname)-7s │ %(message)s")

app = Flask(__name__)

# Railway terminates TLS at its proxy, so without this Flask sees plain HTTP:
# request.is_secure is False (the admin cookie loses its Secure flag) and
# request.host_url is http:// (breaking the Stripe redirect fallback when
# PUBLIC_BASE_URL is unset). Trust exactly one proxy hop's forwarding headers.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# The form's largest legitimate field is a ~4 KB PEM; anything near this cap is
# abuse. Oversized bodies get a 413 before any parsing or disk write.
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

# ── Config (all via env) ──────────────────────────────────────────────────────
SUBMISSIONS_DIR = Path(os.environ.get("SUBMISSIONS_DIR", Path(__file__).parent / "submissions"))
FERNET_KEY      = os.environ.get("ONBOARDING_FERNET_KEY", "").strip()

TG_BOT_TOKEN    = os.environ.get("ONBOARDING_TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT_ID      = os.environ.get("ONBOARDING_TELEGRAM_CHAT_ID", "").strip()

ADMIN_TOKEN         = os.environ.get("ADMIN_TOKEN", "").strip()

STRIPE_SECRET_KEY   = os.environ.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_SETUP_PRICE  = os.environ.get("STRIPE_SETUP_PRICE_ID", "").strip()
STRIPE_MONTHLY_PRICE= os.environ.get("STRIPE_MONTHLY_PRICE_ID", "").strip()
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
PUBLIC_BASE_URL     = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")

# Founding-customer offer (e.g. the "Founder 100" $249-off-first-invoice coupon).
# Two mutually-exclusive delivery modes — Stripe rejects a session that uses both:
#   • FOUNDING_COUPON_ID set  → the coupon is auto-applied to every signup (no code
#     to type). If the coupon is exhausted/expired/invalid, checkout retries once
#     WITHOUT it so signups never break — the offer just quietly ends.
#   • else STRIPE_ALLOW_PROMO_CODES truthy → the Checkout page shows an "Add
#     promotion code" box so customers can enter a code (e.g. FOUNDER100).
# Leave both unset for full-price checkout.
FOUNDING_COUPON_ID      = os.environ.get("FOUNDING_COUPON_ID", "").strip()
STRIPE_ALLOW_PROMO_CODES = os.environ.get("STRIPE_ALLOW_PROMO_CODES", "").strip().lower() in ("1", "true", "yes")

# The webhook secret is REQUIRED whenever Stripe is live: without it the
# checkout.session.completed webhook cannot be verified, so paid customers are
# never marked paid and auto-provisioning never fires — silently. Fail loudly
# at boot so the misconfiguration is caught before the first real signup.
if STRIPE_SECRET_KEY and not STRIPE_WEBHOOK_SECRET:
    log.error(
        "STRIPE_SECRET_KEY is set but STRIPE_WEBHOOK_SECRET is not — paid "
        "checkouts will NEVER be marked paid and auto-provisioning will NEVER "
        "fire. Create a webhook endpoint for checkout.session.completed in the "
        "Stripe dashboard and set STRIPE_WEBHOOK_SECRET to its signing secret.")

# Auto-provision a customer's Railway bot as soon as Stripe confirms payment.
# Requires RAILWAY_API_TOKEN (see provisioner.py / AUTOMATED_PROVISIONING.md).
# Set to "false" to fall back to the manual runbook / the /admin button.
AUTO_PROVISION = os.environ.get("AUTO_PROVISION", "true").strip().lower() in ("1", "true", "yes")

# Display-only pricing (kept in sync with the docs / Stripe prices).
PRICE_SETUP   = os.environ.get("ONBOARDING_PRICE_SETUP", "150")
PRICE_MONTHLY = os.environ.get("ONBOARDING_PRICE_MONTHLY", "99")
PERF_PCT      = os.environ.get("ONBOARDING_PERF_PCT", "0")   # placeholder — fee not shown/charged

VALID_FORMATS = ("conservative", "balanced", "aggressive")
SECRET_FIELDS = ("kalshi_api_key_id", "kalshi_private_key_pem", "telegram_bot_token")

# Boot reconciliation: the provisioning queue is in-memory, so a restart between
# Stripe's webhook (already acknowledged with a 200 — Stripe won't retry) and
# the worker finishing would otherwise strand a PAID customer with no bot and no
# alert. Re-enqueue anything paid-but-unfinished; each job resumes from its last
# checkpoint. Best-effort — a sweep failure must never stop the app booting.
if AUTO_PROVISION and provisioner.is_configured():
    try:
        provisioner.reconcile_pending()
    except Exception:                              # pragma: no cover - defensive
        log.exception("Provisioning boot sweep failed — continuing to serve.")


def _fernet():
    """Return a Fernet cipher, or None if no key is configured (secrets then
    cannot be stored and the form refuses submission)."""
    if not FERNET_KEY:
        return None
    from cryptography.fernet import Fernet
    return Fernet(FERNET_KEY.encode())


def _encrypt(value: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("ONBOARDING_FERNET_KEY is not set — cannot store secrets.")
    return f.encrypt((value or "").encode()).decode()


def _decrypt(token: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("ONBOARDING_FERNET_KEY is not set — cannot read secrets.")
    return f.decrypt((token or "").encode()).decode()


def _deploy_env(sub: dict) -> list:
    """Ready-to-paste Railway variables for a submission (matches admin_cli.py).
    The Kalshi private key is emitted as a single-line base64 blob
    (KALSHI_PRIVATE_KEY_PEM_B64) so it can't be mangled by a multi-line paste.
    Decrypts the stored secrets — callers must be operator-authorized."""
    s = {k: _decrypt(v) for k, v in sub.get("secrets_encrypted", {}).items()}
    pem_b64 = base64.b64encode(s.get("kalshi_private_key_pem", "").encode()).decode()
    return [
        ("KALSHI_API_KEY_ID", s.get("kalshi_api_key_id", "")),
        ("KALSHI_PRIVATE_KEY_PEM_B64", pem_b64),
        ("DEMO_MODE", "true"),
        ("PAPER_BALANCE", str(sub.get("starting_balance", ""))),
        ("TRADING_FORMAT", sub.get("trading_format", "balanced")),
        ("TELEGRAM_BOT_TOKEN", s.get("telegram_bot_token", "")),
        ("TELEGRAM_CHAT_ID", sub.get("telegram_chat_id", "")),
    ]


def _load_submission(sub_id: str) -> "dict | None":
    # sub_id is used as a filename — reject anything that isn't a bare id.
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", sub_id or ""):
        return None
    path = SUBMISSIONS_DIR / f"{sub_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _admin_authorized() -> bool:
    """True when the request carries the operator token (cookie, header, or query)."""
    if not ADMIN_TOKEN:
        return False
    supplied = (request.cookies.get("fp_admin")
                or request.headers.get("X-Admin-Token")
                or request.args.get("token") or "")
    return hmac.compare_digest(supplied, ADMIN_TOKEN)


def _pem_looks_valid(pem: str) -> bool:
    """True only if the pasted text is a COMPLETE, loadable RSA private key — so a
    truncated/mangled key is rejected at signup instead of crash-looping a bot later."""
    try:
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        s = (pem or "").strip().strip('"').strip("'").replace("\\n", "\n")
        m = re.search(r"-----BEGIN ([A-Z ]+?)-----(.*?)-----END \1-----", s, re.DOTALL)
        if not m:
            return False
        body = re.sub(r"\s+", "", m.group(2))
        wrapped = "\n".join(body[i:i + 64] for i in range(0, len(body), 64))
        norm = f"-----BEGIN {m.group(1)}-----\n{wrapped}\n-----END {m.group(1)}-----\n"
        load_pem_private_key(norm.encode(), password=None)
        return True
    except Exception:
        return False


def _validate_telegram_setup(token: str, chat_id: str) -> "str | None":
    """Confirm the customer's OWN Telegram bot actually works before we store the
    submission — so a wrong token or an unreachable chat id can never reach a
    deployed bot and silently kill every alert. Returns None if everything checks
    out, otherwise a customer-friendly error string.

    'chat not found' at deploy time is the #1 onboarding failure: the customer
    pastes a chat id from a different bot, mistypes it, or never presses Start on
    their bot. We catch all three here by validating the token (getMe) and then
    doing exactly what the bot will do in production — send a real message — so a
    green signup guarantees a green deploy. Network hiccups are NOT treated as a
    failure (we don't want to block signups on a transient blip); only definitive
    rejections from Telegram are."""
    token = (token or "").strip()
    chat_id = (chat_id or "").strip()
    base = f"https://api.telegram.org/bot{token}"
    try:
        me = requests.get(f"{base}/getMe", timeout=10).json()
    except Exception as exc:
        log.warning("Telegram getMe unreachable during signup (allowing): %s", exc)
        return None  # transient — don't block the customer on our network
    if not me.get("ok"):
        return ("That Telegram bot token was rejected by Telegram. Copy it again "
                "from @BotFather — it looks like 123456789:AA... — and re-submit.")

    bot_name = me.get("result", {}).get("username", "your bot")
    try:
        r = requests.post(f"{base}/sendMessage", timeout=10, json={
            "chat_id": chat_id,
            "text": "✅ FlipPulse connected to your Telegram — this is where your "
                    "trade alerts will arrive.",
        })
        body = r.json()
    except Exception as exc:
        log.warning("Telegram sendMessage unreachable during signup (allowing): %s", exc)
        return None  # transient — don't block the customer on our network
    if body.get("ok"):
        return None
    code = body.get("error_code")
    if code in (400, 403):
        return (f"We couldn't reach that chat ID with your bot @{bot_name}. "
                f"Open Telegram, press Start (or send any message) to @{bot_name}, "
                "then make sure the chat ID matches. Tip: message @userinfobot to "
                "get your numeric chat ID, then re-submit.")
    return (f"Telegram rejected the test message ({body.get('description', code)}). "
            "Please double-check your bot token and chat ID, then re-submit.")


def _slug(text: str) -> str:
    # Lowercase alnum + dashes, capped so it stays a valid Railway project name
    # (used as "flippulse-<handle>" and "<handle>-bot").
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:40].strip("-") or "customer")


def _send_operator_message(text: str) -> None:
    """Best-effort Telegram alert to the operator — never breaks the request."""
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        log.info("Operator Telegram not configured — skipping alert.")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:                      # alerting must not break signup
        log.warning("Operator alert failed: %s", e)


def _notify_operator(sub: dict) -> None:
    """Telegram alert to the operator. Non-secret summary ONLY."""
    _send_operator_message(
        "🔔 New FlipPulse signup\n"
        f"Name: {sub['full_name']}\n"
        f"Email: {sub['email']}\n"
        f"Handle: {sub['handle']}\n"
        f"Format: {sub['trading_format']}\n"
        f"Starting balance: ${sub['starting_balance']:,.2f}\n"
        f"Submission: {sub['id']}\n"
        "Run:  python admin_cli.py show " + sub["id"]
    )


# ── Submit rate limiting ──────────────────────────────────────────────────────
# The form is public and marketing traffic includes bots. Every submission
# writes disk, calls the Telegram API twice (validation), and pings the
# operator — so throttle per client IP. In-memory is fine: the service runs a
# single gunicorn worker, and a restart resetting the window is harmless.
_SUBMIT_WINDOW_SECS = 600
_SUBMIT_MAX_PER_IP  = 5
_submit_hits: "dict[str, list[float]]" = {}


def _submit_rate_limited(ip: str) -> bool:
    """True when this IP has exhausted its submissions for the window."""
    import time
    now  = time.time()
    hits = [t for t in _submit_hits.get(ip, []) if now - t < _SUBMIT_WINDOW_SECS]
    if len(hits) >= _SUBMIT_MAX_PER_IP:
        _submit_hits[ip] = hits
        return True
    hits.append(now)
    _submit_hits[ip] = hits
    if len(_submit_hits) > 10_000:              # bound memory under a flood
        _submit_hits.clear()
    return False


# Stripe ids resolved from a product to its default price are cached so we don't
# re-hit the API on every signup. Keyed by the configured prod_… id.
_price_id_cache: "dict[str, str]" = {}


def _stripe_get(obj, key):
    """Read a field from a Stripe API object *or* a plain dict.

    stripe-python ≥ 8 (we run v15) returns `StripeObject` instances that — unlike
    older releases — no longer subclass `dict`, so `obj.get("…")` raises
    `AttributeError: 'Product' object has no attribute 'get'` (str(e) == "get").
    That crashed real signups even though the unit tests (which mock `retrieve`
    to return a plain dict) stayed green. Attribute access works on a StripeObject
    and the isinstance(dict) branch keeps plain dicts working too."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


def _resolve_price_id(configured: str) -> str:
    """Return a usable Stripe **Price** id for a configured value.

    The Stripe dashboard shows a product's `prod_…` id far more prominently than
    its `price_…` id, so operators routinely paste the product id into
    STRIPE_MONTHLY_PRICE_ID / STRIPE_SETUP_PRICE_ID — which Checkout rejects with
    "No such price: 'prod_…'". Rather than fail the signup, if we're handed a
    product id we look up that product's default price and use it. A real price
    id (or anything else) is returned unchanged."""
    pid = (configured or "").strip()
    if not pid.startswith("prod_"):
        return pid                               # already a price id (or empty)
    if pid in _price_id_cache:
        return _price_id_cache[pid]
    import stripe
    product = stripe.Product.retrieve(pid)
    default_price = _stripe_get(product, "default_price")
    price_id = default_price if isinstance(default_price, str) else _stripe_get(default_price, "id")
    if not price_id:
        raise RuntimeError(
            f"Stripe product {pid} has no default price — set a default price on "
            f"the product, or configure a price id (price_…) instead of the "
            f"product id.")
    _price_id_cache[pid] = price_id
    log.info("Resolved Stripe product %s → default price %s.", pid, price_id)
    return price_id


def _start_stripe_checkout(sub: dict):
    """Create a Stripe Checkout session (setup fee + monthly subscription, card on
    file). Returns the redirect URL, or None if Stripe is not configured."""
    if not (STRIPE_SECRET_KEY and STRIPE_MONTHLY_PRICE):
        return None
    import stripe
    stripe.api_key = STRIPE_SECRET_KEY
    line_items = [{"price": _resolve_price_id(STRIPE_MONTHLY_PRICE), "quantity": 1}]
    if STRIPE_SETUP_PRICE:                      # one-time setup fee on the first invoice
        line_items.append({"price": _resolve_price_id(STRIPE_SETUP_PRICE), "quantity": 1})
    base = PUBLIC_BASE_URL or request.host_url.rstrip("/")
    params = dict(
        mode="subscription",
        line_items=line_items,
        customer_email=sub["email"],
        client_reference_id=sub["id"],
        metadata={"submission_id": sub["id"], "handle": sub["handle"],
                  "trading_format": sub["trading_format"]},
        payment_method_collection="always",     # keep the card on file for future invoices
        success_url=f"{base}{url_for('success')}?sid={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base}{url_for('cancelled')}?submission={sub['id']}",
    )
    # Founding offer: auto-apply the coupon, OR (mutually exclusive) let the
    # customer type a promotion code. Never both — Stripe rejects that combo.
    if FOUNDING_COUPON_ID:
        params["discounts"] = [{"coupon": FOUNDING_COUPON_ID}]
    elif STRIPE_ALLOW_PROMO_CODES:
        params["allow_promotion_codes"] = True

    try:
        session = stripe.checkout.Session.create(**params)
    except stripe.error.StripeError as e:
        # The founding coupon is exhausted/expired/invalid — don't break signup.
        # Retry once at full price so the customer can still check out; the
        # limited-time offer has simply run its course.
        if FOUNDING_COUPON_ID and params.pop("discounts", None) is not None:
            log.warning("Founding coupon %s rejected (%s) — retrying checkout at "
                        "full price", FOUNDING_COUPON_ID, e)
            session = stripe.checkout.Session.create(**params)
        else:
            raise
    return session.url


@app.get("/")
def form():
    return render_template("form.html", formats=VALID_FORMATS,
                           price_setup=PRICE_SETUP, price_monthly=PRICE_MONTHLY,
                           perf_pct=PERF_PCT, error=request.args.get("error"))


@app.post("/submit")
def submit():
    # ProxyFix has already resolved remote_addr to the real client IP.
    if _submit_rate_limited(request.remote_addr or "?"):
        return redirect(url_for("form", error=(
            "Too many sign-up attempts from your connection — please wait a few "
            "minutes and try again.")))
    f = request.form
    required = ["full_name", "email", "starting_balance", "trading_format",
                "kalshi_api_key_id", "kalshi_private_key_pem",
                "telegram_bot_token", "telegram_chat_id"]
    missing = [k for k in required if not (f.get(k) or "").strip()]
    if missing:
        return redirect(url_for("form", error="Please complete: " + ", ".join(missing)))
    if f.get("trading_format") not in VALID_FORMATS:
        return redirect(url_for("form", error="Pick a trading format."))
    if not f.get("agree"):
        return redirect(url_for("form", error="Please accept the terms to continue."))
    try:
        balance = float(str(f.get("starting_balance")).replace(",", "").replace("$", ""))
        if balance <= 0:
            raise ValueError
    except ValueError:
        return redirect(url_for("form", error="Enter a valid starting balance."))
    # Reject an incomplete/mangled Kalshi key at signup so it can never reach (and
    # crash-loop) a deployed bot.
    if not _pem_looks_valid(f.get("kalshi_private_key_pem")):
        return redirect(url_for("form", error=(
            "That Kalshi private key looks incomplete — please paste the ENTIRE key file, "
            "every line from '-----BEGIN' through '-----END-----', with nothing cut off.")))

    # Validate the customer's Telegram bot end-to-end (token + reachable chat) so a
    # broken config is caught here at signup instead of silently killing alerts on
    # the deployed bot. A green signup sends the customer a real confirmation msg.
    tg_error = _validate_telegram_setup(f.get("telegram_bot_token"), f.get("telegram_chat_id"))
    if tg_error:
        return redirect(url_for("form", error=tg_error))

    if _fernet() is None:
        log.error("ONBOARDING_FERNET_KEY not set — refusing to store secrets.")
        return redirect(url_for("form",
            error="Onboarding is temporarily unavailable — please contact us."))

    now = datetime.now(timezone.utc)
    # The customer may choose their own handle (names their bot + dashboard as
    # "flippulse-<handle>"); it's slugified for safety and falls back to their
    # name when left blank.
    handle = _slug(f.get("handle")) if (f.get("handle") or "").strip() else _slug(f.get("full_name"))
    sub_id = f"{now.strftime('%Y%m%d-%H%M%S')}_{handle}_{uuid.uuid4().hex[:6]}"
    submission = {
        "id": sub_id,
        "created_at": now.isoformat(),
        "full_name": f.get("full_name").strip(),
        "email": f.get("email").strip(),
        "handle": handle,
        "trading_format": f.get("trading_format"),
        "starting_balance": round(balance, 2),
        "telegram_chat_id": f.get("telegram_chat_id").strip(),
        "payment_status": "pending",
        # secrets — encrypted at rest, decryptable only with ONBOARDING_FERNET_KEY
        "secrets_encrypted": {
            "kalshi_api_key_id": _encrypt(f.get("kalshi_api_key_id").strip()),
            "kalshi_private_key_pem": _encrypt(f.get("kalshi_private_key_pem")),
            "telegram_bot_token": _encrypt(f.get("telegram_bot_token").strip()),
        },
    }

    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SUBMISSIONS_DIR / f"{sub_id}.json"
    path.write_text(json.dumps(submission, indent=2))
    os.chmod(path, 0o600)                        # least-privilege on the secret file
    log.info("Stored submission %s (secrets encrypted).", sub_id)

    _notify_operator(submission)

    try:
        checkout_url = _start_stripe_checkout(submission)
    except Exception as e:
        # Stripe is configured but Checkout could not start (outage, bad price
        # id). The customer must NOT see the normal success page — it claims
        # payment was received. Show the payment-pending variant and alert the
        # operator to send a payment link; the submission is already saved.
        log.warning("Stripe checkout failed (submission still saved): %s", e)
        _send_operator_message(
            "⚠️ Stripe Checkout FAILED at signup\n"
            f"Customer: {submission['full_name']} <{submission['email']}>\n"
            f"Submission: {sub_id} (saved, payment_status=pending)\n"
            f"Error: {type(e).__name__}: {e}\n"
            "Action: send them a payment link / invoice manually.\n"
            "To provision the bot now anyway (skips the paid gate):\n"
            f"  python admin_cli.py provision {sub_id}")
        return redirect(url_for("success", pay="pending"))
    if checkout_url:
        return redirect(checkout_url, code=303)
    return redirect(url_for("success"))


@app.get("/success")
def success():
    return render_template("success.html", price_monthly=PRICE_MONTHLY, perf_pct=PERF_PCT,
                           payment_pending=request.args.get("pay") == "pending")


@app.get("/cancelled")
def cancelled():
    return render_template("cancelled.html")


@app.post("/stripe/webhook")
def stripe_webhook():
    """Mark a submission paid once Checkout completes (and auto-provision).
    Requires STRIPE_WEBHOOK_SECRET to verify the event signature."""
    if not STRIPE_WEBHOOK_SECRET:
        if STRIPE_SECRET_KEY:
            # Stripe is live but we can't verify events. Returning non-200 makes
            # Stripe retry and flag the endpoint as failing (dashboard + email),
            # instead of silently swallowing a real payment.
            log.error("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not "
                      "set — cannot verify it. This payment will NOT be marked "
                      "paid or provisioned until the secret is configured.")
            return ("webhook secret not configured", 500)
        return ("", 200)                # Stripe not in use — harmless no-op
    import stripe
    try:
        event = stripe.Webhook.construct_event(
            request.get_data(), request.headers.get("Stripe-Signature", ""),
            STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        log.warning("Bad Stripe webhook: %s", e)
        return ("", 400)
    if event["type"] == "checkout.session.completed":
        # event["data"]["object"] is a StripeObject, not a dict — .get() raises
        # AttributeError on stripe ≥ 8 (see _stripe_get), which 500'd every real
        # completed checkout and left paid customers stuck on payment_status=pending.
        session = event["data"]["object"]
        sid = _stripe_get(session, "client_reference_id")
        p = SUBMISSIONS_DIR / f"{sid}.json"
        if sid and p.exists():
            d = json.loads(p.read_text())
            d["payment_status"] = "paid"
            d["stripe_customer"] = _stripe_get(session, "customer")
            d["stripe_subscription"] = _stripe_get(session, "subscription")
            p.write_text(json.dumps(d, indent=2))
            log.info("Submission %s marked paid.", sid)
            # Payment confirmed → provision the customer's Railway bot with no
            # operator action. Queued in the background so Stripe gets its 200
            # immediately; the provisioning result lands on operator Telegram.
            if AUTO_PROVISION and provisioner.is_configured():
                already = (d.get("provisioning") or {}).get("status")
                if already not in ("in_progress", "provisioned"):
                    provisioner.enqueue(sid)
            elif AUTO_PROVISION:
                log.warning("AUTO_PROVISION is on but RAILWAY_API_TOKEN is not set — "
                            "submission %s needs manual deployment.", sid)
    return ("", 200)


@app.get("/admin")
def admin_list():
    """Operator dashboard — lists submissions. Disabled unless ADMIN_TOKEN is set."""
    if not ADMIN_TOKEN:
        abort(404)
    # A valid ?token= establishes an httponly cookie so it isn't in every URL after.
    q = request.args.get("token")
    if q and hmac.compare_digest(q, ADMIN_TOKEN):
        resp = make_response(redirect(url_for("admin_list")))
        resp.set_cookie("fp_admin", ADMIN_TOKEN, httponly=True,
                        samesite="Lax", secure=request.is_secure)
        return resp
    if not _admin_authorized():
        abort(404)
    subs = []
    for p in sorted(SUBMISSIONS_DIR.glob("*.json"), reverse=True):
        try:
            subs.append(json.loads(p.read_text()))
        except (OSError, ValueError):
            continue
    return render_template("admin_list.html", subs=subs)


@app.get("/admin/<sub_id>")
def admin_detail(sub_id: str):
    if not _admin_authorized():
        abort(404)
    sub = _load_submission(sub_id)
    if sub is None:
        abort(404)
    try:
        env_pairs = _deploy_env(sub)
    except Exception as e:                       # bad key / corrupt secret
        log.warning("admin detail decrypt failed for %s: %s", sub_id, e)
        env_pairs = None
    # Every value (incl. the base64 key) is a single line — paste the whole block as-is.
    env_text = "\n".join(f"{k}={v}" for k, v in (env_pairs or []))
    return render_template("admin_detail.html", sub=sub, env_text=env_text,
                           has_env=env_pairs is not None,
                           prov=sub.get("provisioning") or {},
                           railway_ready=provisioner.is_configured())


@app.post("/admin/<sub_id>/provision")
def admin_provision(sub_id: str):
    """Operator button: provision (or retry) this customer's Railway bot now.
    Skips the paid gate — clicking it IS the operator's authorization (covers
    manually-billed customers and Stripe-less installs)."""
    if not _admin_authorized():
        abort(404)
    sub = _load_submission(sub_id)
    if sub is None:
        abort(404)
    if not provisioner.is_configured():
        return redirect(url_for("admin_detail", sub_id=sub_id))
    if (sub.get("provisioning") or {}).get("status") != "in_progress":
        # Mark it in_progress on disk before enqueuing so the redirect below
        # immediately shows "⏳ deploying" instead of racing the worker's first
        # checkpoint and looking like the button did nothing.
        provisioner.mark_queued(sub_id)
        provisioner.enqueue(sub_id, require_paid=False)
    return redirect(url_for("admin_detail", sub_id=sub_id))


# ── Pre-onboarding guide (static landing page + step-by-step guide) ───────────
# The zero-experience setup experience lives in ./guide as self-contained static
# files (see guide/README.md). Served under /welcome/ so a customer can read the
# landing page, follow the guide, print the checklist, and then click through to
# the form at "/". All internal links are relative, so this whole directory is
# also usable as standalone files or rendered to PDF offline.
GUIDE_DIR = (Path(__file__).parent / "guide").resolve()


@app.get("/welcome")
def welcome_redirect():
    return redirect("/welcome/")


@app.get("/welcome/")
def welcome_index():
    return send_from_directory(GUIDE_DIR, "index.html")


@app.get("/welcome/<path:filename>")
def welcome_file(filename: str):
    # send_from_directory safely rejects path traversal outside GUIDE_DIR.
    return send_from_directory(GUIDE_DIR, filename)


@app.get("/healthz")
def healthz():
    # ok is False when Stripe is live without a webhook secret — that combination
    # silently strands paid customers (never marked paid, never provisioned).
    stripe_ok = bool(STRIPE_WEBHOOK_SECRET) or not STRIPE_SECRET_KEY
    return {"ok": stripe_ok, "stripe": bool(STRIPE_SECRET_KEY),
            "stripe_webhook": bool(STRIPE_WEBHOOK_SECRET),
            "encryption": bool(FERNET_KEY), "admin_dashboard": bool(ADMIN_TOKEN),
            "railway": provisioner.is_configured(), "auto_provision": AUTO_PROVISION}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
