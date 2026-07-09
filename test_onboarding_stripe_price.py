"""Tests for Stripe price-id resolution: an operator who pastes a PRODUCT id
(prod_…) — the id the Stripe dashboard shows most prominently — where a PRICE id
(price_…) is required must get a working checkout, not the
"No such price: 'prod_…'" failure that stranded the first real signup.

Run: pytest test_onboarding_stripe_price.py
"""

import pytest
import stripe

import onboarding.app as app_mod


@pytest.fixture(autouse=True)
def fresh_price_cache():
    app_mod._price_id_cache.clear()
    yield
    app_mod._price_id_cache.clear()


class _StripeObj:
    """Stand-in for a stripe-python StripeObject: attribute + item access, but
    deliberately NO .get() method. Real StripeObjects (stripe ≥ 8) don't subclass
    dict, so product.get("default_price") raises AttributeError: get — the bug
    that broke live signups. Returning a plain dict here (as this test used to)
    hid it, because dicts DO have .get()."""

    def __init__(self, data):
        object.__setattr__(self, "_data", data)

    def __getattr__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(key)

    def __getitem__(self, key):
        return self._data[key]


def _fake_product(monkeypatch, mapping):
    """Patch stripe.Product.retrieve to return default_price per the mapping.
    Records how many times it was called so caching can be asserted. An expanded
    (object) default_price is itself wrapped in a StripeObject stand-in, mirroring
    what the real API returns."""
    calls = {"n": 0}

    def _wrap(value):
        return _StripeObj(value) if isinstance(value, dict) else value

    class FakeProduct:
        @staticmethod
        def retrieve(pid):
            calls["n"] += 1
            return _StripeObj({"default_price": _wrap(mapping[pid])})

    monkeypatch.setattr(stripe, "Product", FakeProduct)
    return calls


def test_price_id_passthrough_makes_no_api_call(monkeypatch):
    """A real price id is returned unchanged and never touches the Stripe API."""
    def explode(pid):
        raise AssertionError("must not call Stripe for a price id")
    monkeypatch.setattr(stripe, "Product", type("P", (), {"retrieve": staticmethod(explode)}))
    assert app_mod._resolve_price_id("price_123") == "price_123"
    assert app_mod._resolve_price_id("") == ""


def test_product_id_resolves_to_default_price(monkeypatch):
    _fake_product(monkeypatch, {"prod_ABC": "price_XYZ"})
    assert app_mod._resolve_price_id("prod_ABC") == "price_XYZ"


def test_expanded_default_price_object_resolves(monkeypatch):
    """default_price can come back as an expanded object rather than a bare id."""
    _fake_product(monkeypatch, {"prod_ABC": {"id": "price_OBJ"}})
    assert app_mod._resolve_price_id("prod_ABC") == "price_OBJ"


def test_product_without_default_price_raises(monkeypatch):
    _fake_product(monkeypatch, {"prod_NONE": None})
    with pytest.raises(RuntimeError) as exc:
        app_mod._resolve_price_id("prod_NONE")
    assert "default price" in str(exc.value)


def test_resolution_is_cached(monkeypatch):
    calls = _fake_product(monkeypatch, {"prod_ABC": "price_XYZ"})
    assert app_mod._resolve_price_id("prod_ABC") == "price_XYZ"
    assert app_mod._resolve_price_id("prod_ABC") == "price_XYZ"
    assert calls["n"] == 1                      # second call served from cache


def test_checkout_uses_resolved_price_ids(monkeypatch):
    """End-to-end: a product id configured for both prices yields line items that
    carry the resolved price ids, so Checkout.Session.create gets valid input."""
    monkeypatch.setattr(app_mod, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(app_mod, "STRIPE_MONTHLY_PRICE", "prod_MONTH")
    monkeypatch.setattr(app_mod, "STRIPE_SETUP_PRICE", "prod_SETUP")
    _fake_product(monkeypatch, {"prod_MONTH": "price_month", "prod_SETUP": "price_setup"})

    captured = {}

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            return type("S", (), {"url": "https://checkout.stripe/x"})

    monkeypatch.setattr(stripe, "checkout", type("C", (), {"Session": FakeSession}))

    sub = {"id": "sub1", "email": "a@b.c", "handle": "h", "trading_format": "balanced"}
    with app_mod.app.test_request_context("/submit"):
        url = app_mod._start_stripe_checkout(sub)

    assert url == "https://checkout.stripe/x"
    prices = [li["price"] for li in captured["line_items"]]
    assert prices == ["price_month", "price_setup"]


def _checkout_env(monkeypatch):
    """Minimal Stripe config so _start_stripe_checkout runs, with pass-through prices."""
    monkeypatch.setattr(app_mod, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(app_mod, "STRIPE_MONTHLY_PRICE", "price_month")
    monkeypatch.setattr(app_mod, "STRIPE_SETUP_PRICE", "price_setup")


def _capture_session(monkeypatch, fail_first=False):
    """Patch stripe.checkout.Session.create, recording every call's kwargs. When
    fail_first is set the first call raises a StripeError (simulating an exhausted
    coupon) and the second succeeds."""
    calls = []

    class FakeSession:
        @staticmethod
        def create(**kwargs):
            calls.append(kwargs)
            if fail_first and len(calls) == 1:
                raise stripe.error.StripeError("coupon exhausted")
            return type("S", (), {"url": "https://checkout.stripe/x"})

    monkeypatch.setattr(stripe, "checkout", type("C", (), {"Session": FakeSession}))
    return calls


def _run_checkout(monkeypatch):
    sub = {"id": "sub1", "email": "a@b.c", "handle": "h", "trading_format": "balanced"}
    with app_mod.app.test_request_context("/submit"):
        return app_mod._start_stripe_checkout(sub)


def test_founding_coupon_auto_applied(monkeypatch):
    """FOUNDING_COUPON_ID set → the coupon rides on the session as a discount and
    no promotion-code box is offered."""
    _checkout_env(monkeypatch)
    monkeypatch.setattr(app_mod, "FOUNDING_COUPON_ID", "10xGeLZu")
    monkeypatch.setattr(app_mod, "STRIPE_ALLOW_PROMO_CODES", True)  # ignored when coupon set
    calls = _capture_session(monkeypatch)

    assert _run_checkout(monkeypatch) == "https://checkout.stripe/x"
    assert calls[0]["discounts"] == [{"coupon": "10xGeLZu"}]
    assert "allow_promotion_codes" not in calls[0]   # mutually exclusive — never both


def test_allow_promotion_codes_when_no_coupon(monkeypatch):
    """No coupon but STRIPE_ALLOW_PROMO_CODES → customer can type a code."""
    _checkout_env(monkeypatch)
    monkeypatch.setattr(app_mod, "FOUNDING_COUPON_ID", "")
    monkeypatch.setattr(app_mod, "STRIPE_ALLOW_PROMO_CODES", True)
    calls = _capture_session(monkeypatch)

    assert _run_checkout(monkeypatch) == "https://checkout.stripe/x"
    assert calls[0]["allow_promotion_codes"] is True
    assert "discounts" not in calls[0]


def test_exhausted_coupon_falls_back_to_full_price(monkeypatch):
    """An invalid/exhausted founding coupon must not break signup: checkout retries
    once WITHOUT the discount."""
    _checkout_env(monkeypatch)
    monkeypatch.setattr(app_mod, "FOUNDING_COUPON_ID", "10xGeLZu")
    monkeypatch.setattr(app_mod, "STRIPE_ALLOW_PROMO_CODES", False)
    calls = _capture_session(monkeypatch, fail_first=True)

    assert _run_checkout(monkeypatch) == "https://checkout.stripe/x"
    assert len(calls) == 2                          # first (with discount) failed, retried
    assert "discounts" in calls[0]
    assert "discounts" not in calls[1]              # retry dropped the coupon
