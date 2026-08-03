"""Tests for the signup consent gate.

The Risk Disclosure & Agreement on the form is enforced as four separate
required checkboxes (ack_risk, ack_software, ack_eligibility, agree). A signup
must check every box, and the accepted terms version + timestamp are recorded on
the stored submission as proof of consent.

Run: pytest test_onboarding_consent.py
"""

import json

import pytest
from cryptography.fernet import Fernet

import onboarding.app as app_mod


BASE_FORM = {
    "full_name": "Jane Doe", "email": "jane@example.com",
    "starting_balance": "1000", "trading_format": "balanced",
    "kalshi_api_key_id": "key-id", "kalshi_private_key_pem": "PEM",
    "telegram_bot_token": "123:abc", "telegram_chat_id": "555",
    "ack_risk": "on", "ack_software": "on", "ack_eligibility": "on", "agree": "on",
}


@pytest.fixture(autouse=True)
def fresh_rate_window():
    app_mod._submit_hits.clear()
    yield
    app_mod._submit_hits.clear()


@pytest.fixture
def submit(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "SUBMISSIONS_DIR", tmp_path)
    monkeypatch.setattr(app_mod, "FERNET_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(app_mod, "_pem_looks_valid", lambda pem: True)
    monkeypatch.setattr(app_mod, "_validate_telegram_setup", lambda t, c: None)
    monkeypatch.setattr(app_mod, "_notify_operator", lambda sub: None)
    monkeypatch.setattr(app_mod, "_start_stripe_checkout", lambda sub: None)

    def _do(**overrides):
        data = dict(BASE_FORM, **overrides)
        # Drop keys explicitly set to None so we can simulate an unchecked box.
        data = {k: v for k, v in data.items() if v is not None}
        r = app_mod.app.test_client().post("/submit", data=data)
        files = list(tmp_path.glob("*.json"))
        sub = json.loads(files[0].read_text()) if files else None
        for f in files:
            f.unlink()
        return r, sub

    return _do


@pytest.mark.parametrize("missing", ["ack_risk", "ack_software", "ack_eligibility", "agree"])
def test_each_consent_box_is_required(submit, missing):
    r, sub = submit(**{missing: None})
    assert sub is None                      # nothing saved
    assert r.status_code == 302
    assert "acknowledgment" in r.headers["Location"].lower() or \
           "acknowledgment" in r.headers["Location"].replace("+", " ").lower()


def test_all_boxes_checked_records_consent(submit):
    r, sub = submit()
    assert sub is not None
    consent = sub["consent"]
    assert set(consent["accepted"]) == set(app_mod.CONSENT_FIELDS)
    assert consent["terms_version"] == app_mod.TERMS_VERSION
    assert consent["accepted_at"]           # timestamp present
