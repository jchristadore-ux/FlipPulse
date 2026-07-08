"""Tests for the automated Railway provisioner — the state machine that turns a
paid submission into a running customer bot with no manual Railway work.

Run: pytest test_provisioner.py
"""

import json

import pytest
from cryptography.fernet import Fernet

import onboarding.provisioner as prov_mod


FERNET_KEY = Fernet.generate_key().decode()
PEM = "-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----\n"

BOOT_LOGS = ["🚀 boot", "✅ RSA private key loaded.",
             "Sizing (% of balance): normal=10.0% recovery=3.0% max=15.0%"]


class FakeRailway:
    """Duck-typed RailwayClient that records every call and can be told to fail."""

    def __init__(self, deploy_status="SUCCESS", logs=None, fail_on=None):
        self.calls = []
        self.deploy_status = deploy_status
        self.logs = BOOT_LOGS if logs is None else logs
        self.fail_on = fail_on
        self.variables = {}

    def _maybe_fail(self, step):
        if self.fail_on == step:
            raise prov_mod.ProvisionError(step, f"simulated {step} failure")

    def project_create(self, name):
        self.calls.append("project_create")
        self._maybe_fail("project_create")
        return "proj-1", "env-1"

    def service_create(self, project_id, name, repo, branch, variables):
        self.calls.append("service_create")
        self._maybe_fail("service_create")
        self.variables = dict(variables)
        return "svc-1"

    def volume_create(self, project_id, environment_id, service_id, mount_path="/data"):
        self.calls.append("volume_create")
        self._maybe_fail("volume_create")
        assert mount_path == "/data"
        return "vol-1"

    def service_domain_create(self, environment_id, service_id, target_port):
        self.calls.append("service_domain_create")
        self._maybe_fail("create_domain")
        self.domain_target_port = target_port
        return "jane-doe-bot-production.up.railway.app"

    def variables_upsert(self, project_id, environment_id, service_id, variables):
        self.calls.append("variables_upsert")
        self.variables = dict(variables)

    def service_redeploy(self, environment_id, service_id):
        self.calls.append("service_redeploy")

    def latest_deployment(self, project_id, environment_id, service_id):
        self.calls.append("latest_deployment")
        return {"id": "dep-1", "status": self.deploy_status}

    def deployment_logs(self, deployment_id, limit=200):
        self.calls.append("deployment_logs")
        return list(self.logs)

    def project_delete(self, project_id):
        self.calls.append(("project_delete", project_id))


@pytest.fixture
def submission(tmp_path, monkeypatch):
    """A paid submission on disk, with the provisioner pointed at tmp storage."""
    monkeypatch.setenv("ONBOARDING_FERNET_KEY", FERNET_KEY)
    monkeypatch.setattr(prov_mod, "SUBMISSIONS_DIR", tmp_path)
    monkeypatch.setattr(prov_mod, "DEPLOY_POLL_SECS", 0.01)
    monkeypatch.setattr(prov_mod, "DEPLOY_TIMEOUT_SECS", 1)
    f = Fernet(FERNET_KEY.encode())
    sub = {
        "id": "20260701-120000_jane_ab12cd",
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "handle": "jane-doe",
        "trading_format": "balanced",
        "starting_balance": 1000.0,
        "telegram_chat_id": "555",
        "payment_status": "paid",
        "secrets_encrypted": {
            "kalshi_api_key_id": f.encrypt(b"key-id").decode(),
            "kalshi_private_key_pem": f.encrypt(PEM.encode()).decode(),
            "telegram_bot_token": f.encrypt(b"123:abc").decode(),
        },
    }
    (tmp_path / f"{sub['id']}.json").write_text(json.dumps(sub))
    return sub


def _stored(tmp_path, sub_id):
    return json.loads((tmp_path / f"{sub_id}.json").read_text())


def test_happy_path_provisions_and_records_ids(submission, tmp_path):
    client = FakeRailway()
    prov = prov_mod.provision(submission["id"], client=client)

    assert prov["status"] == "provisioned"
    assert prov["project_id"] == "proj-1"
    assert prov["service_id"] == "svc-1"
    assert prov["volume_id"] == "vol-1"
    assert prov["deployment_id"] == "dep-1"
    # Persisted to disk, not just in memory.
    assert _stored(tmp_path, submission["id"])["provisioning"]["status"] == "provisioned"


def test_full_variable_set_injected(submission):
    """Runbook §4 in full: per-customer values AND the /data paths — nothing is
    left for a human to add afterwards."""
    client = FakeRailway()
    prov_mod.provision(submission["id"], client=client)
    v = client.variables
    assert v["DEMO_MODE"] == "true"                    # paper mode, always
    assert v["TRADING_FORMAT"] == "balanced"
    assert v["PAPER_BALANCE"] == "1000.0"
    assert v["TELEGRAM_CHAT_ID"] == "555"
    assert v["KALSHI_API_KEY_ID"] == "key-id"
    import base64
    assert base64.b64decode(v["KALSHI_PRIVATE_KEY_PEM_B64"]).decode() == PEM
    for key in ("RECOVERY_STATE_PATH", "PROBATION_STATE_PATH", "LADDER_STATE_PATH",
                "BUCKET_STATS_PATH", "BILLING_STATE_PATH", "STATUS_SNAPSHOT_PATH",
                "HEALTH_LOG_PATH", "BILLING_LOG_PATH"):
        assert v[key].startswith("/data/"), key
    assert v["PERF_FEE_PCT"] == "0.0"                  # fee stays disabled


def test_dashboard_domain_and_password_provisioned(submission, tmp_path, monkeypatch):
    """The dashboard is reachable end-to-end from provisioning: a public domain is
    generated (targeting DASHBOARD_PORT), the password is injected, and both are
    surfaced to the operator."""
    alerts = []
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: alerts.append(text))
    client = FakeRailway()
    prov = prov_mod.provision(submission["id"], client=client)

    assert prov["dashboard_domain"] == "jane-doe-bot-production.up.railway.app"
    assert client.domain_target_port == int(prov_mod.DASHBOARD_PORT)
    v = client.variables
    assert v["DASHBOARD_PORT"] == prov_mod.DASHBOARD_PORT
    assert v["DASHBOARD_PASSWORD"] and len(v["DASHBOARD_PASSWORD"]) >= 16
    # Success alert carries the URL + password for the operator to relay.
    success = alerts[-1]
    assert "https://jane-doe-bot-production.up.railway.app" in success
    assert v["DASHBOARD_PASSWORD"] in success


def test_dashboard_password_is_stable_across_resume(submission, tmp_path):
    """A resumed run must reuse the SAME dashboard password — variables_upsert
    re-applies the full set every run, so a fresh password would silently rotate
    the customer's login on every reconcile/redeploy."""
    first = FakeRailway(fail_on="volume_create")
    with pytest.raises(prov_mod.ProvisionError):
        prov_mod.provision(submission["id"], client=first)
    pw1 = first.variables["DASHBOARD_PASSWORD"]           # captured at service_create

    resume = FakeRailway()
    prov_mod.provision(submission["id"], client=resume)
    pw2 = resume.variables["DASHBOARD_PASSWORD"]          # re-applied via variables_upsert
    assert pw1 == pw2


def test_dashboard_domain_failure_is_non_fatal(submission, tmp_path, monkeypatch):
    """If Railway won't mint a domain, the bot still provisions (it can trade);
    the operator is told to add the domain by hand."""
    alerts = []
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: alerts.append(text))
    client = FakeRailway(fail_on="create_domain")
    prov = prov_mod.provision(submission["id"], client=client)
    assert prov["status"] == "provisioned"               # not blocked
    assert "dashboard_domain" not in prov
    assert "dashboard_domain_error" in prov
    assert "Generate Domain" in alerts[-1]               # operator guidance


def test_unpaid_submission_is_gated(submission, tmp_path):
    stored = _stored(tmp_path, submission["id"])
    stored["payment_status"] = "pending"
    (tmp_path / f"{submission['id']}.json").write_text(json.dumps(stored))

    with pytest.raises(prov_mod.ProvisionError) as e:
        prov_mod.provision(submission["id"], client=FakeRailway())
    assert e.value.step == "payment"
    # Operator override (admin button / CLI) still works.
    prov = prov_mod.provision(submission["id"], client=FakeRailway(), require_paid=False)
    assert prov["status"] == "provisioned"


def test_failure_is_recorded_and_resume_skips_completed_steps(submission, tmp_path):
    # First attempt dies attaching the volume — after project+service exist.
    failing = FakeRailway(fail_on="volume_create")
    with pytest.raises(prov_mod.ProvisionError):
        prov_mod.provision(submission["id"], client=failing)
    rec = _stored(tmp_path, submission["id"])["provisioning"]
    assert rec["status"] == "failed"
    assert rec["step"] == "volume_create"
    assert rec["project_id"] == "proj-1"               # partial state kept

    # Retry resumes: no second project/service is created.
    retry = FakeRailway()
    prov = prov_mod.provision(submission["id"], client=retry)
    assert prov["status"] == "provisioned"
    assert "project_create" not in retry.calls
    assert "service_create" not in retry.calls
    assert "volume_create" in retry.calls


def test_crashed_deployment_fails_with_log_tail(submission):
    client = FakeRailway(deploy_status="CRASHED")
    with pytest.raises(prov_mod.ProvisionError) as e:
        prov_mod.provision(submission["id"], client=client)
    assert e.value.step == "deploy"
    assert "CRASHED" in str(e.value)


def test_missing_boot_markers_fail_verification(submission):
    client = FakeRailway(logs=["🚀 boot", "something unrelated"])
    with pytest.raises(prov_mod.ProvisionError) as e:
        prov_mod.provision(submission["id"], client=client)
    assert e.value.step == "verify"


def test_already_provisioned_is_a_noop(submission):
    client = FakeRailway()
    prov_mod.provision(submission["id"], client=client)
    again = FakeRailway()
    prov = prov_mod.provision(submission["id"], client=again)
    assert prov["status"] == "provisioned"
    assert again.calls == []                           # nothing touched Railway


def test_deprovision_deletes_the_recorded_project(submission, tmp_path):
    prov_mod.provision(submission["id"], client=FakeRailway())
    client = FakeRailway()
    prov_mod.deprovision(submission["id"], client=client)
    assert ("project_delete", "proj-1") in client.calls
    assert _stored(tmp_path, submission["id"])["provisioning"]["status"] == "deprovisioned"

# ── boot reconciliation sweep ─────────────────────────────────────────────────
# The queue is in-memory and Stripe never retries an acknowledged webhook, so a
# restart must re-enqueue every paid submission whose provisioning never
# finished — and must never resurrect a deliberately deprovisioned customer.

def _write_sub(tmp_path, sub, sub_id, payment="paid", provisioning=None):
    d = dict(sub, id=sub_id)
    d["payment_status"] = payment
    if provisioning is not None:
        d["provisioning"] = provisioning
    else:
        d.pop("provisioning", None)
    (tmp_path / f"{sub_id}.json").write_text(json.dumps(d))


@pytest.fixture
def enqueue_recorder(monkeypatch):
    """Capture re-enqueued ids instead of spinning worker threads."""
    queued = []
    monkeypatch.setattr(prov_mod, "enqueue", lambda sub_id, require_paid=True: queued.append(sub_id))
    monkeypatch.setattr(prov_mod, "RAILWAY_API_TOKEN", "tok")   # is_configured() → True
    monkeypatch.setattr(prov_mod, "_notify_operator", lambda text: None)
    return queued


def test_sweep_requeues_paid_unfinished(submission, tmp_path, enqueue_recorder):
    from datetime import datetime, timedelta, timezone
    stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    fresh = datetime.now(timezone.utc).isoformat()
    (tmp_path / f"{submission['id']}.json").unlink()   # only the explicit cases below
    _write_sub(tmp_path, submission, "s-never")                                    # paid, never attempted
    _write_sub(tmp_path, submission, "s-failed",
               provisioning={"status": "failed", "step": "deploy"})                # paid, failed mid-run
    _write_sub(tmp_path, submission, "s-stale",
               provisioning={"status": "in_progress", "updated_at": stale})        # worker died
    _write_sub(tmp_path, submission, "s-live",
               provisioning={"status": "in_progress", "updated_at": fresh})        # live worker owns it
    _write_sub(tmp_path, submission, "s-done", provisioning={"status": "provisioned"})
    _write_sub(tmp_path, submission, "s-deleted", provisioning={"status": "deprovisioned"})
    _write_sub(tmp_path, submission, "s-unpaid", payment="pending")

    requeued = prov_mod.reconcile_pending()
    assert sorted(requeued) == ["s-failed", "s-never", "s-stale"]
    assert sorted(enqueue_recorder) == ["s-failed", "s-never", "s-stale"]


def test_sweep_noop_without_railway_token(submission, tmp_path, enqueue_recorder, monkeypatch):
    monkeypatch.setattr(prov_mod, "RAILWAY_API_TOKEN", "")
    _write_sub(tmp_path, submission, "s-never")
    assert prov_mod.reconcile_pending() == []
    assert enqueue_recorder == []
