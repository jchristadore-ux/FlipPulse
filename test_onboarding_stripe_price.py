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


def _fake_product(monkeypatch, mapping):
    """Patch stripe.Product.retrieve to return default_price per the mapping.
    Records how many times it was called so caching can be asserted."""
    calls = {"n": 0}

    class FakeProduct:
        @staticmethod
        def retrieve(pid):
            calls["n"] += 1
            return {"default_price": mapping[pid]}

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
