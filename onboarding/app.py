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

It then tracks the customer's BILLING LIFECYCLE for as long as they are a
customer — renewals, failed payments, cancellations, refunds and disputes all
arrive as Stripe webhooks and are recorded on the submission (see
`_EVENT_HANDLERS`). Without that, a subscription business only ever learns
about the first payment.

Design notes
------------
* Secrets are NEVER logged and NEVER sent to Telegram — only the encrypted
  submission file holds them, and only the holder of ONBOARDING_FERNET_KEY can
  read them back.
* Run behind HTTPS (Railway terminates TLS for you). The form collects a private
  key, so a plain-HTTP deployment is not acceptable.
* This service is standalone — it does not import the trading bot.
* Money events never fail silently: anything Stripe tells us that we cannot
  reconcile to a submission raises an operator Telegram alert rather than a
  quiet 200.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import (Flask, abort, make_response, redirect, render_template,
                   request, send_from_directory, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

try:
    from submission_store import locked, read as read_submission, write as write_submission, write_unlocked
except ImportError:
    from onboarding.submission_store import (locked, read as read_submission,
                                               write as write_submission,
                                               write_unlocked)

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

# Whether to show the "Founders 100 Club" launch banner on the signup form. It's
# on whenever a founding-offer delivery mode is configured (auto-coupon or a
# promo-code box), so the marketing promise ("first 100 join free") matches what
# checkout will actually apply. When the coupon is exhausted the operator unsets
# FOUNDING_COUPON_ID (or sets FOUNDER_OFFER_ACTIVE=false) and the banner drops —
# see 11_COMPLIANCE_KIT.md §7: never advertise a closed offer.
_founder_env = os.environ.get("FOUNDER_OFFER_ACTIVE", "").strip().lower()
if _founder_env in ("1", "true", "yes"):
    FOUNDER_OFFER_ACTIVE = True
elif _founder_env in ("0", "false", "no"):
    FOUNDER_OFFER_ACTIVE = False
else:
    FOUNDER_OFFER_ACTIVE = bool(FOUNDING_COUPON_ID or STRIPE_ALLOW_PROMO_CODES)

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

# Consent checkboxes on the signup form — each must be individually checked so
# the customer's acceptance of the risk disclosure, the software-only/no-advice
# terms, eligibility, and the full agreement is recorded separately rather than
# lumped into one box. Keep in sync with the checkboxes in templates/form.html.
CONSENT_FIELDS = ("ack_risk", "ack_software", "ack_eligibility", "agree")

# Bump when the Risk Disclosure & Agreement text in form.html changes materially,
# so each stored submission is provably tied to the terms version accepted.
TERMS_VERSION = "2026-07-09"


# ── Storage durability guard ──────────────────────────────────────────────────
# Submissions are the ONLY record that a customer paid: payment_status, the
# Stripe customer/subscription ids, the billing lifecycle, and the encrypted
# credentials all live in SUBMISSIONS_DIR. On Railway the container filesystem
# is ephemeral — anything not on an attached volume is destroyed by every
# redeploy. Losing it means paid customers with no bot, no record and no way to
# reconcile against Stripe. Warn loudly rather than discovering it after a deploy.
def _submissions_look_ephemeral() -> bool:
    """True when SUBMISSIONS_DIR sits inside the code checkout (the Railway
    default) rather than on a mounted volume."""
    try:
        here = Path(__file__).resolve().parent
        return SUBMISSIONS_DIR.resolve() == (here / "submissions").resolve() \
            or here in SUBMISSIONS_DIR.resolve().parents
    except OSError:                                 # pragma: no cover - defensive
        return False


def _submissions_writable() -> bool:
    """True when we can actually persist a submission right now."""
    try:
        SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
        return os.access(SUBMISSIONS_DIR, os.W_OK)
    except OSError:
        return False


if STRIPE_SECRET_KEY and _submissions_look_ephemeral():
    log.error(
        "SUBMISSIONS_DIR=%s is inside the code checkout, which Railway wipes on "
        "every redeploy — but Stripe is LIVE. Paid-customer records (payment "
        "status, Stripe ids, encrypted credentials) will be destroyed by the next "
        "deploy. Attach a volume and set SUBMISSIONS_DIR=/data/submissions.",
        SUBMISSIONS_DIR)

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
    """Ready-to-paste Railway variables for a submission.
    Uses provisioner.paste_variables so manual deploys get the same /data state
    paths as automated provisioning (credentials + volume paths). Decrypts the
    stored secrets — callers must be operator-authorized."""
    s = {k: _decrypt(v) for k, v in sub.get("secrets_encrypted", {}).items()}
    return list(provisioner.paste_variables(sub, s).items())


def _load_submission(sub_id: str) -> "dict | None":
    # sub_id is used as a filename — reject anything that isn't a bare id.
    if not re.fullmatch(r"[A-Za-z0-9_\-]+", sub_id or ""):
        return None
    path = SUBMISSIONS_DIR / f"{sub_id}.json"
    if not path.exists():
        return None
    try:
        return read_submission(path)
    except (OSError, ValueError):
        return None


def _admin_session_cookie() -> str:
    """Derived admin session value — never store the raw ADMIN_TOKEN in a cookie
    (query-string logins still accept the raw token once, then set this cookie)."""
    return hmac.new(b"flippulse-admin-v1", ADMIN_TOKEN.encode(),
                    hashlib.sha256).hexdigest()


def _admin_authorized() -> bool:
    """True when the request carries the operator token (cookie, header, or query)."""
    if not ADMIN_TOKEN:
        return False
    cookie = request.cookies.get("fp_admin") or ""
    if cookie and hmac.compare_digest(cookie, _admin_session_cookie()):
        return True
    # Legacy: older cookies stored the raw token — still accept, then rotate.
    if cookie and hmac.compare_digest(cookie, ADMIN_TOKEN):
        return True
    supplied = (request.headers.get("X-Admin-Token")
                or request.args.get("token") or "")
    return bool(supplied) and hmac.compare_digest(supplied, ADMIN_TOKEN)


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


def _stripe_id(value):
    """Normalise a Stripe reference to its bare id string.

    An expanded field comes back as a nested object ({"id": "sub_…", …}) while an
    unexpanded one is already the id string. Storing the object would make later
    lookups by id silently miss."""
    if value is None or isinstance(value, str):
        return value
    return _stripe_get(value, "id")


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
        # Mirror the metadata onto the SUBSCRIPTION itself. Renewal, dunning and
        # cancellation events carry the subscription — not the checkout session —
        # so without this the only link back to a submission is the id lookup in
        # _find_submission_by_stripe, which fails if the file was ever restored
        # from a backup without its stripe ids.
        subscription_data={"metadata": {"submission_id": sub["id"],
                                        "handle": sub["handle"]}},
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
                           perf_pct=PERF_PCT, error=request.args.get("error"),
                           founder_offer=FOUNDER_OFFER_ACTIVE)


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
    # Every consent box is separately required so acceptance of the risk
    # disclosure, the software-only/no-advice terms, eligibility, and the full
    # agreement is individually recorded — not a single lumped "agree".
    if not all(f.get(c) for c in CONSENT_FIELDS):
        return redirect(url_for("form", error=(
            "Please read the Risk Disclosure & Agreement and check each "
            "acknowledgment box to continue.")))
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
        # Proof of consent: which terms version was accepted, when, from where.
        "consent": {
            "accepted": list(CONSENT_FIELDS),
            "terms_version": TERMS_VERSION,
            "accepted_at": now.isoformat(),
            "ip": request.remote_addr or "",
            "user_agent": request.headers.get("User-Agent", "")[:300],
        },
        # secrets — encrypted at rest, decryptable only with ONBOARDING_FERNET_KEY
        "secrets_encrypted": {
            "kalshi_api_key_id": _encrypt(f.get("kalshi_api_key_id").strip()),
            "kalshi_private_key_pem": _encrypt(f.get("kalshi_private_key_pem")),
            "telegram_bot_token": _encrypt(f.get("telegram_bot_token").strip()),
        },
    }

    SUBMISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SUBMISSIONS_DIR / f"{sub_id}.json"
    write_submission(path, submission)
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


# ── Stripe webhook ────────────────────────────────────────────────────────────
# A checkout session only *completes* as paid for these payment_status values.
# "unpaid" happens with delayed/async payment methods (the customer left Checkout
# before the funds cleared); "no_payment_required" is a 100%-discounted first
# invoice, i.e. the Founder-100 coupon — a real, provisionable customer.
PAID_SESSION_STATUSES = ("paid", "no_payment_required")

# Stripe subscription statuses that mean this customer's bot should NOT be
# (re-)deployed. "past_due" is deliberately absent: Stripe is still retrying the
# card, and killing a live trading bot over one failed retry is worse than
# carrying a customer for a few days.
BILLING_TERMINAL = ("canceled", "unpaid", "refunded", "disputed")

# Processed-event ledger. Stripe retries any delivery it doesn't see a 2xx for
# and can legitimately deliver the same event twice; without a ledger a retried
# checkout.session.completed re-runs the whole paid path (and can double-enqueue
# provisioning). One O_EXCL marker file per event id is atomic across gunicorn
# workers and survives a restart, unlike an in-memory set.
_EVENT_DIR_NAME = ".stripe_events"
_EVENT_LEDGER_MAX = 5000


def _event_dir() -> Path:
    return SUBMISSIONS_DIR / _EVENT_DIR_NAME


def _claim_event(event_id: str) -> bool:
    """Atomically claim an event id for processing.

    Returns True if this process won the claim (process it), False if the event
    was already handled (a Stripe retry — acknowledge and do nothing). The claim
    is released by _release_event if processing raises, so Stripe's retry can
    pick it up again rather than the event being lost behind a stale marker."""
    if not event_id:
        return True                                # nothing to dedupe on
    d = _event_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
        fd = os.open(d / event_id, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(int(time.time())).encode())
        os.close(fd)
    except FileExistsError:
        log.info("Stripe event %s already processed — ignoring the retry.", event_id)
        return False
    except OSError as e:                           # can't dedupe → still process
        log.warning("Could not write the Stripe event ledger (%s) — processing "
                    "without replay protection.", e)
        return True
    _prune_event_ledger(d)
    return True


def _release_event(event_id: str) -> None:
    """Drop a claim so a failed event is reprocessed on Stripe's retry."""
    if not event_id:
        return
    try:
        (_event_dir() / event_id).unlink()
    except OSError:
        pass


def _prune_event_ledger(d: Path) -> None:
    """Keep the ledger bounded — oldest markers first."""
    try:
        markers = list(d.iterdir())
        if len(markers) <= _EVENT_LEDGER_MAX:
            return
        for p in sorted(markers, key=lambda p: p.stat().st_mtime)[:len(markers) - _EVENT_LEDGER_MAX]:
            p.unlink(missing_ok=True)
    except OSError:                                # pragma: no cover - defensive
        pass


def _iter_submissions():
    """Yield (path, submission) for every stored submission, newest first."""
    try:
        paths = sorted(SUBMISSIONS_DIR.glob("*.json"), reverse=True)
    except OSError:                                # pragma: no cover - defensive
        return
    for p in paths:
        try:
            yield p, read_submission(p)
        except (OSError, ValueError):
            continue


def _find_submission_by_stripe(customer=None, subscription=None,
                               submission_id=None) -> "tuple[Path, dict] | tuple[None, None]":
    """Locate the submission a post-checkout Stripe event belongs to.

    Renewals, dunning, cancellations and refunds carry a customer/subscription id
    but NO client_reference_id — that only exists on the checkout session — so the
    ids recorded at checkout time are the link back. `submission_id` (from the
    subscription metadata we set in _start_stripe_checkout) is tried first because
    it survives a submission file being restored without its stripe ids."""
    if submission_id:
        path = SUBMISSIONS_DIR / f"{submission_id}.json"
        sub = _load_submission(submission_id)
        if sub is not None:
            return path, sub
    subscription = _stripe_id(subscription)
    customer = _stripe_id(customer)
    if not (subscription or customer):
        return None, None
    fallback = (None, None)
    for path, sub in _iter_submissions():
        if subscription and sub.get("stripe_subscription") == subscription:
            return path, sub                        # exact — a customer may have several
        if customer and sub.get("stripe_customer") == customer and fallback == (None, None):
            fallback = (path, sub)
    return fallback


def _update_submission(path: Path, **fields) -> dict:
    """Merge fields into a submission under its lock. `billing` merges key-wise so
    two events in flight don't erase each other's fields."""
    with locked(path):
        try:
            d = json.loads(path.read_text())
        except (OSError, ValueError):
            raise
        billing = fields.pop("billing", None)
        d.update(fields)
        if billing is not None:
            merged = dict(d.get("billing") or {})
            merged.update(billing)
            merged["updated_at"] = datetime.now(timezone.utc).isoformat()
            d["billing"] = merged
        write_unlocked(path, d)
        return d


def _set_billing(path: Path, sub: dict, status: str, event_type: str,
                 **extra) -> dict:
    """Record a billing-lifecycle transition on a submission."""
    billing = {"status": status, "last_event": event_type}
    billing.update(extra)
    updated = _update_submission(path, billing=billing)
    log.info("Submission %s billing → %s (%s).", sub.get("id"), status, event_type)
    return updated


def _who(sub: dict) -> str:
    return f"{sub.get('full_name', '?')} <{sub.get('email', '?')}> ({sub.get('handle', '?')})"


def _money(amount_cents, currency="usd") -> str:
    """Stripe amounts are minor units."""
    try:
        return f"{(int(amount_cents) / 100):,.2f} {str(currency or 'usd').upper()}"
    except (TypeError, ValueError):
        return "?"


def _invoice_subscription(invoice):
    """The subscription an invoice belongs to, across API versions.

    Stripe moved `invoice.subscription` under
    `invoice.parent.subscription_details.subscription` in the 2025 API versions;
    the account's version decides which one an event carries, so read both."""
    direct = _stripe_id(_stripe_get(invoice, "subscription"))
    if direct:
        return direct
    parent = _stripe_get(invoice, "parent")
    details = _stripe_get(parent, "subscription_details")
    return _stripe_id(_stripe_get(details, "subscription"))


def _metadata_submission_id(obj):
    """The submission id we stamped onto the object's metadata, if present."""
    meta = _stripe_get(obj, "metadata")
    sid = _stripe_get(meta, "submission_id")
    return sid if isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9_\-]+", sid) else None


# ── Individual event handlers ─────────────────────────────────────────────────
def _handle_checkout_completed(session, event_type: str) -> None:
    """Mark a submission paid and start provisioning — the money-in path."""
    sid = _stripe_get(session, "client_reference_id") or _metadata_submission_id(session)
    pay_status = _stripe_get(session, "payment_status")
    customer = _stripe_id(_stripe_get(session, "customer"))
    subscription = _stripe_id(_stripe_get(session, "subscription"))
    email = (_stripe_get(session, "customer_email")
             or _stripe_get(_stripe_get(session, "customer_details"), "email") or "?")

    sub = _load_submission(sid) if sid else None
    if sub is None:
        # Money may have moved and we cannot tie it to anyone. Never a silent 200:
        # this is the one failure mode that leaves a real customer charged with no
        # bot, no record, and nobody looking.
        log.error("Stripe %s for unknown submission %r (customer=%s, "
                  "subscription=%s) — cannot reconcile.", event_type, sid, customer, subscription)
        _send_operator_message(
            "🚨 Stripe checkout completed but NO matching submission\n"
            f"Email: {email}\n"
            f"client_reference_id: {sid or '(none)'}\n"
            f"Stripe customer: {customer or '?'}\n"
            f"Stripe subscription: {subscription or '?'}\n"
            f"Payment status: {pay_status or '?'}\n"
            "The customer may have been charged. Reconcile in the Stripe "
            "dashboard and either refund them or provision by hand.")
        return

    path = SUBMISSIONS_DIR / f"{sid}.json"
    # Stripe explicitly telling us the session is NOT paid must not provision a
    # bot: with a delayed payment method the funds have not cleared yet, and
    # checkout.session.async_payment_succeeded arrives later (or never). A missing
    # payment_status is treated as paid — every real Checkout session carries the
    # field, and refusing on its absence would break Stripe-less/manual flows.
    if pay_status is not None and pay_status not in PAID_SESSION_STATUSES:
        _update_submission(path, payment_status="awaiting_payment",
                           stripe_customer=customer, stripe_subscription=subscription,
                           billing={"status": "awaiting_payment", "last_event": event_type})
        log.warning("Submission %s checkout completed with payment_status=%r — "
                    "NOT provisioning until payment clears.", sid, pay_status)
        _send_operator_message(
            "⏳ FlipPulse checkout completed but payment has NOT cleared\n"
            f"Customer: {_who(sub)}\n"
            f"Stripe payment_status: {pay_status}\n"
            f"Submission: {sid}\n"
            "No bot deployed. It provisions automatically when Stripe confirms "
            "the payment (checkout.session.async_payment_succeeded).")
        return

    _mark_paid_and_provision(path, sid, customer, subscription, event_type)


def _mark_paid_and_provision(path: Path, sid: str, customer, subscription,
                             event_type: str) -> None:
    """Flip a submission to paid and queue its bot. Shared by the immediate and
    the delayed (async_payment_succeeded) payment paths."""
    d = _update_submission(path, payment_status="paid",
                           stripe_customer=customer,
                           stripe_subscription=subscription,
                           billing={"status": "active", "last_event": event_type,
                                    "paid_at": datetime.now(timezone.utc).isoformat()})
    log.info("Submission %s marked paid.", sid)
    # Payment confirmed → provision the customer's Railway bot with no operator
    # action. Queued in the background so Stripe gets its 200 immediately; the
    # provisioning result lands on operator Telegram.
    if AUTO_PROVISION and provisioner.is_configured():
        already = (d.get("provisioning") or {}).get("status")
        if already not in ("in_progress", "provisioned"):
            provisioner.enqueue(sid)
    elif AUTO_PROVISION:
        log.warning("AUTO_PROVISION is on but RAILWAY_API_TOKEN is not set — "
                    "submission %s needs manual deployment.", sid)


def _handle_async_payment_succeeded(session, event_type: str) -> None:
    """A delayed payment method finally cleared — now the customer is really paid."""
    sid = _stripe_get(session, "client_reference_id") or _metadata_submission_id(session)
    sub = _load_submission(sid) if sid else None
    if sub is None:
        _handle_checkout_completed(session, event_type)     # reuses the alert path
        return
    _mark_paid_and_provision(SUBMISSIONS_DIR / f"{sid}.json", sid,
                             _stripe_id(_stripe_get(session, "customer")),
                             _stripe_id(_stripe_get(session, "subscription")),
                             event_type)


def _handle_async_payment_failed(session, event_type: str) -> None:
    """A delayed payment method was declined. No bot; tell the operator."""
    sid = _stripe_get(session, "client_reference_id") or _metadata_submission_id(session)
    sub = _load_submission(sid) if sid else None
    if sub is None:
        return
    _set_billing(SUBMISSIONS_DIR / f"{sid}.json", sub, "payment_failed", event_type)
    _update_submission(SUBMISSIONS_DIR / f"{sid}.json", payment_status="pending")
    _send_operator_message(
        "❌ FlipPulse checkout payment FAILED (delayed payment method)\n"
        f"Customer: {_who(sub)}\n"
        f"Submission: {sid}\n"
        "No bot deployed. Follow up with a fresh payment link.")


def _handle_checkout_expired(session, event_type: str) -> None:
    """Abandoned cart: the Checkout session timed out unpaid. Recorded so the
    operator dashboard stops showing an eternally 'pending' signup — a later
    successful checkout still flips it to paid."""
    sid = _stripe_get(session, "client_reference_id") or _metadata_submission_id(session)
    sub = _load_submission(sid) if sid else None
    if sub is None or sub.get("payment_status") != "pending":
        return
    path = SUBMISSIONS_DIR / f"{sid}.json"
    _update_submission(path, payment_status="abandoned",
                       billing={"status": "abandoned", "last_event": event_type})
    log.info("Submission %s: checkout expired unpaid (abandoned).", sid)


def _handle_invoice_paid(invoice, event_type: str) -> None:
    """A renewal cleared. Clears any dunning state so a customer who fixed their
    card is no longer flagged past_due."""
    path, sub = _find_submission_by_stripe(
        customer=_stripe_get(invoice, "customer"),
        subscription=_invoice_subscription(invoice),
        submission_id=_metadata_submission_id(invoice))
    if sub is None:
        log.info("Stripe %s not matched to a submission (customer=%s).",
                 event_type, _stripe_id(_stripe_get(invoice, "customer")))
        return
    _set_billing(path, sub, "active", event_type,
                 last_invoice_paid_at=datetime.now(timezone.utc).isoformat(),
                 last_invoice_amount=_stripe_get(invoice, "amount_paid"),
                 failed_attempts=0)


def _handle_invoice_payment_failed(invoice, event_type: str) -> None:
    """Dunning: a renewal charge was declined. The bot keeps running — Stripe is
    still retrying the card — but the operator needs to know now, because after
    the retries are exhausted the subscription goes unpaid/canceled."""
    path, sub = _find_submission_by_stripe(
        customer=_stripe_get(invoice, "customer"),
        subscription=_invoice_subscription(invoice),
        submission_id=_metadata_submission_id(invoice))
    attempts = _stripe_get(invoice, "attempt_count")
    amount = _money(_stripe_get(invoice, "amount_due"), _stripe_get(invoice, "currency"))
    if sub is None:
        log.warning("Stripe %s not matched to a submission (customer=%s).",
                    event_type, _stripe_id(_stripe_get(invoice, "customer")))
        _send_operator_message(
            "⚠️ Stripe invoice payment FAILED for an unmatched customer\n"
            f"Stripe customer: {_stripe_id(_stripe_get(invoice, 'customer')) or '?'}\n"
            f"Amount due: {amount}\n"
            "Reconcile in the Stripe dashboard.")
        return
    _set_billing(path, sub, "past_due", event_type, failed_attempts=attempts,
                 amount_due=_stripe_get(invoice, "amount_due"))
    _send_operator_message(
        "⚠️ FlipPulse renewal payment FAILED\n"
        f"Customer: {_who(sub)}\n"
        f"Amount due: {amount} · attempt {attempts or '?'}\n"
        f"Submission: {sub.get('id')}\n"
        "Their bot is still running — Stripe is retrying the card. If the "
        "retries are exhausted the subscription cancels and you'll get a second "
        "alert; deprovision then:\n"
        f"  python admin_cli.py deprovision {sub.get('id')}")


def _handle_subscription_updated(subscription, event_type: str) -> None:
    """Track the subscription's own status (active / past_due / unpaid / paused)
    and a pending end-of-period cancellation."""
    path, sub = _find_submission_by_stripe(
        customer=_stripe_get(subscription, "customer"),
        subscription=_stripe_get(subscription, "id"),
        submission_id=_metadata_submission_id(subscription))
    if sub is None:
        return
    status = _stripe_get(subscription, "status") or "unknown"
    cancel_at_period_end = bool(_stripe_get(subscription, "cancel_at_period_end"))
    previous = (sub.get("billing") or {}).get("status")
    _set_billing(path, sub, status, event_type,
                 cancel_at_period_end=cancel_at_period_end)
    if cancel_at_period_end and not (sub.get("billing") or {}).get("cancel_at_period_end"):
        _send_operator_message(
            "🔻 FlipPulse subscription set to CANCEL at period end\n"
            f"Customer: {_who(sub)}\n"
            f"Submission: {sub.get('id')}\n"
            "Their bot keeps running until the period ends; you'll get the "
            "cancellation alert then.")
    elif status in BILLING_TERMINAL and previous not in BILLING_TERMINAL:
        _send_operator_message(
            f"🔻 FlipPulse subscription is now {status.upper()}\n"
            f"Customer: {_who(sub)}\n"
            f"Submission: {sub.get('id')}\n"
            "Their bot is STILL RUNNING — deprovision when you're ready:\n"
            f"  python admin_cli.py deprovision {sub.get('id')}")


def _handle_subscription_deleted(subscription, event_type: str) -> None:
    """The customer churned. The bot is deliberately NOT auto-deleted: it may hold
    open positions with the customer's own money, and tearing it down from a
    webhook could strand them. The operator gets an explicit, actionable alert."""
    path, sub = _find_submission_by_stripe(
        customer=_stripe_get(subscription, "customer"),
        subscription=_stripe_get(subscription, "id"),
        submission_id=_metadata_submission_id(subscription))
    if sub is None:
        log.warning("Stripe %s not matched to a submission (subscription=%s).",
                    event_type, _stripe_id(_stripe_get(subscription, "id")))
        _send_operator_message(
            "🔻 A Stripe subscription was cancelled but matched no submission\n"
            f"Stripe subscription: {_stripe_id(_stripe_get(subscription, 'id')) or '?'}\n"
            f"Stripe customer: {_stripe_id(_stripe_get(subscription, 'customer')) or '?'}\n"
            "Reconcile in the Stripe dashboard — a bot may still be running.")
        return
    _set_billing(path, sub, "canceled", event_type,
                 canceled_at=datetime.now(timezone.utc).isoformat())
    prov_status = (sub.get("provisioning") or {}).get("status")
    _send_operator_message(
        "🔻 FlipPulse subscription CANCELLED\n"
        f"Customer: {_who(sub)}\n"
        f"Submission: {sub.get('id')}\n"
        f"Bot: {prov_status or 'not provisioned'}\n"
        "Their bot is NOT stopped automatically (it may hold open positions). "
        "Tell them to flatten, then:\n"
        f"  python admin_cli.py deprovision {sub.get('id')}")


def _handle_charge_refunded(charge, event_type: str) -> None:
    path, sub = _find_submission_by_stripe(
        customer=_stripe_get(charge, "customer"),
        submission_id=_metadata_submission_id(charge))
    amount = _money(_stripe_get(charge, "amount_refunded"), _stripe_get(charge, "currency"))
    if sub is None:
        log.info("Stripe %s not matched to a submission.", event_type)
        return
    _set_billing(path, sub, "refunded", event_type, refunded_amount=amount)
    _send_operator_message(
        "💸 FlipPulse charge REFUNDED\n"
        f"Customer: {_who(sub)}\n"
        f"Refunded: {amount}\n"
        f"Submission: {sub.get('id')}\n"
        f"  python admin_cli.py deprovision {sub.get('id')}")


def _handle_dispute_created(dispute, event_type: str) -> None:
    """A chargeback. Always alerted, even unmatched — a dispute has a response
    deadline and losing it by default costs the disputed amount plus a fee."""
    path, sub = _find_submission_by_stripe(customer=_stripe_get(dispute, "customer"))
    amount = _money(_stripe_get(dispute, "amount"), _stripe_get(dispute, "currency"))
    reason = _stripe_get(dispute, "reason") or "?"
    who = _who(sub) if sub else "(unmatched — see Stripe dashboard)"
    if sub is not None:
        _set_billing(path, sub, "disputed", event_type, dispute_reason=reason)
    _send_operator_message(
        "🚨 FlipPulse charge DISPUTED (chargeback)\n"
        f"Customer: {who}\n"
        f"Amount: {amount} · reason: {reason}\n"
        f"Charge: {_stripe_id(_stripe_get(dispute, 'charge')) or '?'}\n"
        "Respond in the Stripe dashboard BEFORE the evidence deadline — an "
        "unanswered dispute is lost by default. Signup consent (terms version, "
        "timestamp, IP) is stored on the submission as evidence."
        + (f"\nSubmission: {sub.get('id')}" if sub else ""))


# Every Stripe event we act on. Anything not listed is acknowledged and ignored,
# so enabling extra events in the Stripe dashboard can never 500 the endpoint.
_EVENT_HANDLERS = {
    "checkout.session.completed":              _handle_checkout_completed,
    "checkout.session.async_payment_succeeded": _handle_async_payment_succeeded,
    "checkout.session.async_payment_failed":   _handle_async_payment_failed,
    "checkout.session.expired":                _handle_checkout_expired,
    "invoice.paid":                            _handle_invoice_paid,
    "invoice.payment_succeeded":               _handle_invoice_paid,
    "invoice.payment_failed":                  _handle_invoice_payment_failed,
    "customer.subscription.updated":           _handle_subscription_updated,
    "customer.subscription.deleted":           _handle_subscription_deleted,
    "charge.refunded":                         _handle_charge_refunded,
    "charge.dispute.created":                  _handle_dispute_created,
}


@app.post("/stripe/webhook")
def stripe_webhook():
    """The billing lifecycle in one endpoint: mark a submission paid once Checkout
    completes (and auto-provision), then track renewals, failed payments,
    cancellations, refunds and disputes for the life of the customer.
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

    event_type = event["type"]
    handler = _EVENT_HANDLERS.get(event_type)
    if handler is None:
        return ("", 200)                # not ours to act on — acknowledge quietly

    event_id = _stripe_get(event, "id")
    if not _claim_event(event_id):
        return ("", 200)                # a Stripe retry of an event we handled

    # event["data"]["object"] is a StripeObject, not a dict — .get() raises
    # AttributeError on stripe ≥ 8 (see _stripe_get), which 500'd every real
    # completed checkout and left paid customers stuck on payment_status=pending.
    try:
        handler(event["data"]["object"], event_type)
    except Exception:
        # Release the claim so Stripe's retry gets a real second attempt, and
        # return 500 so Stripe knows to retry at all. Losing a money event to a
        # transient disk/permission error is not acceptable.
        _release_event(event_id)
        log.exception("Stripe %s (%s) failed — released for retry.", event_type, event_id)
        return ("", 500)
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
        # Store a derived session cookie, not the raw token (proxy/access logs
        # may retain the one-time ?token= URL; the cookie itself must not).
        resp.set_cookie("fp_admin", _admin_session_cookie(), httponly=True,
                        samesite="Lax", secure=request.is_secure, max_age=86400 * 14)
        return resp
    if not _admin_authorized():
        abort(404)
    subs = []
    for p in sorted(SUBMISSIONS_DIR.glob("*.json"), reverse=True):
        try:
            subs.append(read_submission(p))
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
                           billing=sub.get("billing") or {},
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
    """Readiness for taking real customer money.

    ok is False for any condition that silently breaks the paid path:
      • Stripe live without a webhook secret — payments are never marked paid
        and auto-provisioning never fires.
      • No ONBOARDING_FERNET_KEY — every signup is refused at the last step,
        after the customer has already pasted their Kalshi key.
      • SUBMISSIONS_DIR not writable — a submission cannot be persisted at all.

    `submissions_durable` is reported but deliberately kept OUT of ok: it is a
    heuristic (does the path sit inside the code checkout?), and an operator who
    mounts a volume there would get a permanently red health check. The boot-time
    ERROR log is the loud signal for that one.
    """
    stripe_ok = bool(STRIPE_WEBHOOK_SECRET) or not STRIPE_SECRET_KEY
    writable = _submissions_writable()
    durable = not (STRIPE_SECRET_KEY and _submissions_look_ephemeral())
    return {"ok": stripe_ok and bool(FERNET_KEY) and writable,
            "stripe": bool(STRIPE_SECRET_KEY),
            "stripe_webhook": bool(STRIPE_WEBHOOK_SECRET),
            "encryption": bool(FERNET_KEY), "admin_dashboard": bool(ADMIN_TOKEN),
            "submissions_writable": writable, "submissions_durable": durable,
            "railway": provisioner.is_configured(), "auto_provision": AUTO_PROVISION}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
