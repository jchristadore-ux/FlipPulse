"""
FlipPulse — automated Railway provisioning.

Turns a paid onboarding submission into a running customer bot with ZERO manual
Railway work. Everything the administrator runbook did by hand — create the
project, point a service at the FlipPulse repo, attach the /data volume, paste
the variables, redeploy, watch the logs — is executed here through Railway's
public GraphQL API (https://backboard.railway.app/graphql/v2).

Flow (mirrors ADMINISTRATOR_ONBOARDING.md §2–§6, one checkpoint per section):

    create_project      §2  New Project
    create_service      §2  Deploy from GitHub repo (root directory blank →
                            repo-root railway.toml → `python bot.py`)
    attach_volume       §3  Volume mounted at /data
    set_variables       §4  Full variable set incl. the /data *_STATE_PATH vars
    deploy              §6  Trigger redeploy
    verify              §6  Poll deployment → SUCCESS, then scan boot logs for
                            the runbook's "green verify" markers

Design notes
------------
* IDEMPOTENT / RESUMABLE: every step records its Railway ids into the
  submission file under "provisioning" BEFORE moving on. Re-running
  `provision()` skips completed steps, so a retry after a partial failure
  resumes instead of duplicating projects.
* One provisioning attempt per submission at a time, enforced with an O_EXCL
  lockfile next to the submission (safe across processes/gunicorn workers).
* Secrets never touch disk unencrypted and are never logged: they are
  decrypted in memory with ONBOARDING_FERNET_KEY and sent only to Railway's
  variables API over TLS.
* Every customer starts in paper mode (DEMO_MODE=true) exactly like the
  manual runbook. Going live stays a deliberate manual step.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

log = logging.getLogger("flippulse.provisioner")

# ── Config (all via env) ──────────────────────────────────────────────────────
SUBMISSIONS_DIR = Path(os.environ.get("SUBMISSIONS_DIR", Path(__file__).parent / "submissions"))

RAILWAY_API_URL   = os.environ.get("RAILWAY_API_URL", "https://backboard.railway.app/graphql/v2")
RAILWAY_API_TOKEN = os.environ.get("RAILWAY_API_TOKEN", "").strip()
RAILWAY_TEAM_ID   = os.environ.get("RAILWAY_TEAM_ID", "").strip()      # optional (workspace)

# The repo every customer service deploys from — identical code for everyone,
# only the variables differ (runbook §2).
PROVISION_REPO        = os.environ.get("PROVISION_REPO", "jchristadore-ux/FlipPulse").strip()
PROVISION_REPO_BRANCH = os.environ.get("PROVISION_REPO_BRANCH", "main").strip()

# Operator chat id(s) baked into every provisioned bot (runbook §7) so all
# alerts fan out to you. Blank = customer-only alerts.
BOT_OPERATOR_CHAT_ID = os.environ.get("BOT_OPERATOR_CHAT_ID", "").strip()

# Deploy watch knobs.
DEPLOY_TIMEOUT_SECS = int(os.environ.get("PROVISION_DEPLOY_TIMEOUT", "600"))
DEPLOY_POLL_SECS    = float(os.environ.get("PROVISION_DEPLOY_POLL", "10"))

# The runbook's "green verify": these log lines must appear in the boot logs.
# Comma-separated override via PROVISION_LOG_MARKERS.
LOG_MARKERS = [m for m in os.environ.get(
    "PROVISION_LOG_MARKERS",
    "✅ RSA private key loaded.,Sizing (% of balance)").split(",") if m.strip()]

# How many provisioning jobs may run at once (Railway API friendliness).
MAX_CONCURRENCY = int(os.environ.get("PROVISION_MAX_CONCURRENCY", "2"))

# Operator alert bot (same one the onboarding form uses).
TG_BOT_TOKEN = os.environ.get("ONBOARDING_TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT_ID   = os.environ.get("ONBOARDING_TELEGRAM_CHAT_ID", "").strip()

DEPLOY_OK_STATUSES      = {"SUCCESS"}
DEPLOY_PENDING_STATUSES = {"QUEUED", "WAITING", "INITIALIZING", "BUILDING", "DEPLOYING"}
DEPLOY_FAILED_STATUSES  = {"FAILED", "CRASHED", "REMOVED", "SKIPPED"}

STEPS = ("create_project", "create_service", "attach_volume",
         "set_variables", "deploy", "verify")


class ProvisionError(RuntimeError):
    """A provisioning step failed. `step` names the checkpoint that failed."""

    def __init__(self, step: str, message: str):
        super().__init__(message)
        self.step = step


def is_configured() -> bool:
    """True when automated provisioning can run (Railway token present)."""
    return bool(RAILWAY_API_TOKEN)


# ── Railway GraphQL client ────────────────────────────────────────────────────
class RailwayClient:
    """Minimal client for Railway's public GraphQL API.

    Auth is a bearer token (account or workspace token from
    https://railway.app/account/tokens). Retries transient failures
    (429 / 5xx / network) with exponential backoff; GraphQL-level errors are
    raised immediately — they are deterministic, retrying won't help.
    """

    MAX_TRIES = 4
    BACKOFF_BASE = 2.0          # 2s, 4s, 8s

    def __init__(self, token: str = "", url: str = ""):
        self.token = token or RAILWAY_API_TOKEN
        self.url = url or RAILWAY_API_URL
        if not self.token:
            raise ProvisionError("config", "RAILWAY_API_TOKEN is not set — cannot provision.")

    def gql(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query, "variables": variables or {}}
        headers = {"Authorization": f"Bearer {self.token}",
                   "Content-Type": "application/json"}
        last_exc: Exception | None = None
        for attempt in range(self.MAX_TRIES):
            if attempt:
                time.sleep(self.BACKOFF_BASE ** attempt)
            try:
                resp = requests.post(self.url, json=payload, headers=headers, timeout=30)
            except requests.RequestException as exc:
                last_exc = exc
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = RuntimeError(f"Railway API HTTP {resp.status_code}")
                continue
            body = resp.json()
            if body.get("errors"):
                msgs = "; ".join(e.get("message", "?") for e in body["errors"])
                raise ProvisionError("railway_api", f"Railway API error: {msgs}")
            return body.get("data", {})
        raise ProvisionError("railway_api",
                             f"Railway API unreachable after {self.MAX_TRIES} tries: {last_exc}")

    # — mutations / queries used by the provisioning flow —

    def project_create(self, name: str) -> tuple[str, str]:
        """Create a project; returns (project_id, production_environment_id)."""
        q = """
        mutation($input: ProjectCreateInput!) {
          projectCreate(input: $input) {
            id
            environments { edges { node { id name } } }
          }
        }"""
        inp: dict = {"name": name}
        if RAILWAY_TEAM_ID:
            inp["teamId"] = RAILWAY_TEAM_ID
        data = self.gql(q, {"input": inp})["projectCreate"]
        envs = [e["node"] for e in data["environments"]["edges"]]
        if not envs:
            raise ProvisionError("create_project", "Project created but has no environment.")
        # Prefer the default "production" environment; fall back to the first.
        env = next((e for e in envs if e["name"] == "production"), envs[0])
        return data["id"], env["id"]

    def service_create(self, project_id: str, name: str,
                       repo: str, branch: str, variables: dict) -> str:
        """Create a service wired to the GitHub repo (root directory stays blank,
        so Railway reads the repo-root railway.toml → `python bot.py`). Variables
        are passed at creation so the FIRST build already has them — no
        crash-loop window."""
        q = """
        mutation($input: ServiceCreateInput!) {
          serviceCreate(input: $input) { id }
        }"""
        inp = {"projectId": project_id, "name": name, "branch": branch,
               "source": {"repo": repo}, "variables": variables}
        return self.gql(q, {"input": inp})["serviceCreate"]["id"]

    def volume_create(self, project_id: str, environment_id: str,
                      service_id: str, mount_path: str = "/data") -> str:
        q = """
        mutation($input: VolumeCreateInput!) {
          volumeCreate(input: $input) { id }
        }"""
        inp = {"projectId": project_id, "environmentId": environment_id,
               "serviceId": service_id, "mountPath": mount_path}
        return self.gql(q, {"input": inp})["volumeCreate"]["id"]

    def variables_upsert(self, project_id: str, environment_id: str,
                         service_id: str, variables: dict) -> None:
        q = """
        mutation($input: VariableCollectionUpsertInput!) {
          variableCollectionUpsert(input: $input)
        }"""
        inp = {"projectId": project_id, "environmentId": environment_id,
               "serviceId": service_id, "variables": variables}
        self.gql(q, {"input": inp})

    def service_redeploy(self, environment_id: str, service_id: str) -> None:
        q = """
        mutation($environmentId: String!, $serviceId: String!) {
          serviceInstanceRedeploy(environmentId: $environmentId, serviceId: $serviceId)
        }"""
        self.gql(q, {"environmentId": environment_id, "serviceId": service_id})

    def latest_deployment(self, project_id: str, environment_id: str,
                          service_id: str) -> dict | None:
        q = """
        query($input: DeploymentListInput!) {
          deployments(first: 1, input: $input) {
            edges { node { id status } }
          }
        }"""
        inp = {"projectId": project_id, "environmentId": environment_id,
               "serviceId": service_id}
        edges = self.gql(q, {"input": inp})["deployments"]["edges"]
        return edges[0]["node"] if edges else None

    def deployment_logs(self, deployment_id: str, limit: int = 200) -> list[str]:
        q = """
        query($deploymentId: String!, $limit: Int) {
          deploymentLogs(deploymentId: $deploymentId, limit: $limit) { message }
        }"""
        rows = self.gql(q, {"deploymentId": deployment_id, "limit": limit})["deploymentLogs"]
        return [r.get("message", "") for r in rows]

    def project_delete(self, project_id: str) -> None:
        q = "mutation($id: String!) { projectDelete(id: $id) }"
        self.gql(q, {"id": project_id})


# ── Submission persistence ────────────────────────────────────────────────────
def _sub_path(sub_id: str) -> Path:
    return SUBMISSIONS_DIR / f"{sub_id}.json"


def load_submission(sub_id: str) -> dict:
    path = _sub_path(sub_id)
    if not path.exists():
        raise ProvisionError("load", f"No submission {sub_id!r} in {SUBMISSIONS_DIR}")
    return json.loads(path.read_text())


def _save_submission(sub: dict) -> None:
    path = _sub_path(sub["id"])
    path.write_text(json.dumps(sub, indent=2))
    os.chmod(path, 0o600)


def _checkpoint(sub: dict, **updates) -> dict:
    """Merge updates into sub['provisioning'] and persist — the resume record."""
    prov = sub.setdefault("provisioning", {})
    prov.update(updates)
    prov["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save_submission(sub)
    return prov


# ── Variable set (runbook §4, complete — nothing left to add by hand) ─────────
def deploy_variables(sub: dict, secrets: dict) -> dict:
    """The FULL environment for a customer bot: the per-customer values from the
    submission plus the /data state paths from .env.example. The Kalshi key goes
    in as the single-line KALSHI_PRIVATE_KEY_PEM_B64 (can't be mangled)."""
    pem_b64 = base64.b64encode(secrets.get("kalshi_private_key_pem", "").encode()).decode()
    variables = {
        "KALSHI_API_KEY_ID": secrets.get("kalshi_api_key_id", ""),
        "KALSHI_PRIVATE_KEY_PEM_B64": pem_b64,
        "DEMO_MODE": "true",                       # every customer starts in paper
        "PAPER_BALANCE": str(sub.get("starting_balance", "")),
        "TRADING_FORMAT": sub.get("trading_format", "balanced"),
        "TELEGRAM_BOT_TOKEN": secrets.get("telegram_bot_token", ""),
        "TELEGRAM_CHAT_ID": sub.get("telegram_chat_id", ""),
        # State on the /data volume so it survives redeploys (runbook §3–§4).
        "RECOVERY_STATE_PATH": "/data/recovery_state.json",
        "PROBATION_STATE_PATH": "/data/probation_state.json",
        "LADDER_STATE_PATH": "/data/ladder_state.json",
        "BUCKET_STATS_PATH": "/data/bucket_stats.json",
        "BILLING_STATE_PATH": "/data/billing_state.json",
        "STATUS_SNAPSHOT_PATH": "/data/status_snapshot.json",
        "HEALTH_LOG_PATH": "/data/health.log",
        # Performance fee stays a disabled placeholder (runbook §9b).
        "PERF_FEE_PCT": "0.0",
        "BILLING_LOG_PATH": "/data/billing.log",
    }
    if BOT_OPERATOR_CHAT_ID:
        variables["TELEGRAM_OPERATOR_CHAT_ID"] = BOT_OPERATOR_CHAT_ID
    return variables


def _decrypt_secrets(sub: dict) -> dict:
    key = os.environ.get("ONBOARDING_FERNET_KEY", "").strip()
    if not key:
        raise ProvisionError("decrypt", "ONBOARDING_FERNET_KEY is not set — cannot decrypt.")
    from cryptography.fernet import Fernet
    f = Fernet(key.encode())
    return {k: f.decrypt(v.encode()).decode()
            for k, v in sub.get("secrets_encrypted", {}).items()}


# ── Locking (one attempt per submission across processes) ─────────────────────
_LOCK_STALE_SECS = 45 * 60


def _acquire_lock(sub_id: str) -> Path | None:
    lock = SUBMISSIONS_DIR / f"{sub_id}.provisioning.lock"
    try:
        if lock.exists() and time.time() - lock.stat().st_mtime > _LOCK_STALE_SECS:
            lock.unlink()                          # stale — a crashed attempt
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return lock
    except FileExistsError:
        return None


# ── Operator notification ─────────────────────────────────────────────────────
def _notify_operator(text: str) -> None:
    if not (TG_BOT_TOKEN and TG_CHAT_ID):
        log.info("Operator Telegram not configured — skipping alert.")
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:                          # alerting must never break provisioning
        log.warning("Operator alert failed: %s", e)


# ── The provisioning state machine ────────────────────────────────────────────
def provision(sub_id: str, client: RailwayClient | None = None,
              require_paid: bool = True) -> dict:
    """Provision (or resume provisioning) one submission. Returns the final
    provisioning record. Raises ProvisionError on failure — the record keeps
    every id created so far, so calling again resumes where it stopped."""
    sub = load_submission(sub_id)
    prov = sub.setdefault("provisioning", {})

    if prov.get("status") == "provisioned":
        log.info("%s already provisioned — nothing to do.", sub_id)
        return prov
    if require_paid and sub.get("payment_status") != "paid":
        raise ProvisionError("payment", f"Submission {sub_id} is not paid "
                             f"({sub.get('payment_status')!r}); use force to override.")

    lock = _acquire_lock(sub_id)
    if lock is None:
        raise ProvisionError("lock", f"Provisioning already in progress for {sub_id}.")

    client = client or RailwayClient()
    handle = sub.get("handle", "customer")
    try:
        _checkpoint(sub, status="in_progress", error=None,
                    started_at=prov.get("started_at") or datetime.now(timezone.utc).isoformat())

        # §2 create the Railway project (one project per customer).
        if not prov.get("project_id"):
            project_id, environment_id = client.project_create(f"flippulse-{handle}")
            _checkpoint(sub, project_id=project_id, environment_id=environment_id,
                        step="create_project")
            log.info("%s: project %s created.", sub_id, project_id)

        secrets = _decrypt_secrets(sub)
        variables = deploy_variables(sub, secrets)

        # §2 service from the FlipPulse repo, variables injected at creation so
        # the very first build boots with a full config.
        if not prov.get("service_id"):
            service_id = client.service_create(
                prov["project_id"], f"{handle}-bot",
                PROVISION_REPO, PROVISION_REPO_BRANCH, variables)
            _checkpoint(sub, service_id=service_id, step="create_service")
            log.info("%s: service %s created from %s@%s.",
                     sub_id, service_id, PROVISION_REPO, PROVISION_REPO_BRANCH)

        # §3 volume at /data so state survives redeploys.
        if not prov.get("volume_id"):
            volume_id = client.volume_create(
                prov["project_id"], prov["environment_id"], prov["service_id"], "/data")
            _checkpoint(sub, volume_id=volume_id, step="attach_volume")
            log.info("%s: volume %s mounted at /data.", sub_id, volume_id)

        # §4 upsert the full variable set (idempotent — also heals a resumed run
        # where service_create's inline variables never landed).
        client.variables_upsert(prov["project_id"], prov["environment_id"],
                                prov["service_id"], variables)
        _checkpoint(sub, step="set_variables", variables_set=sorted(variables.keys()))

        # §6 deploy with everything in place.
        client.service_redeploy(prov["environment_id"], prov["service_id"])
        _checkpoint(sub, step="deploy")

        # §6 verify: wait for SUCCESS, then require the boot-log markers.
        deployment = _wait_for_deployment(client, prov, sub)
        _verify_boot_logs(client, deployment["id"], sub)

        prov = _checkpoint(sub, status="provisioned", step="verify",
                           deployment_id=deployment["id"],
                           provisioned_at=datetime.now(timezone.utc).isoformat())
        _notify_operator(
            "✅ FlipPulse bot provisioned\n"
            f"Customer: {sub.get('full_name')} ({handle})\n"
            f"Format: {sub.get('trading_format')} · paper balance "
            f"${float(sub.get('starting_balance', 0)):,.2f}\n"
            f"Project: https://railway.app/project/{prov['project_id']}\n"
            f"Mode: PAPER (DEMO_MODE=true) — going live stays manual.\n"
            f"Submission: {sub_id}")
        return prov

    except ProvisionError as e:
        _checkpoint(sub, status="failed", step=e.step, error=str(e))
        _notify_operator(
            "❌ FlipPulse provisioning FAILED\n"
            f"Customer: {sub.get('full_name')} ({handle})\n"
            f"Step: {e.step}\nError: {e}\n"
            f"Submission: {sub_id}\n"
            "Retry: it resumes from the last completed step "
            f"(python admin_cli.py provision {sub_id})")
        raise
    finally:
        try:
            lock.unlink()
        except OSError:
            pass


def _wait_for_deployment(client: RailwayClient, prov: dict, sub: dict) -> dict:
    """Poll the latest deployment until it succeeds, fails, or times out."""
    deadline = time.monotonic() + DEPLOY_TIMEOUT_SECS
    last_status = "UNKNOWN"
    while time.monotonic() < deadline:
        dep = client.latest_deployment(prov["project_id"], prov["environment_id"],
                                       prov["service_id"])
        if dep:
            last_status = dep.get("status", "UNKNOWN")
            if last_status in DEPLOY_OK_STATUSES:
                return dep
            if last_status in DEPLOY_FAILED_STATUSES:
                tail = ""
                try:
                    tail = "\n".join(client.deployment_logs(dep["id"], 20)[-5:])
                except ProvisionError:
                    pass
                raise ProvisionError("deploy",
                                     f"Deployment ended {last_status}. Last log lines:\n{tail}")
        time.sleep(DEPLOY_POLL_SECS)
    raise ProvisionError("deploy",
                         f"Deployment not healthy after {DEPLOY_TIMEOUT_SECS}s "
                         f"(last status: {last_status}).")


def _verify_boot_logs(client: RailwayClient, deployment_id: str, sub: dict) -> None:
    """The runbook's green verify: the boot banner must show a loaded Kalshi key
    and the active sizing percentages."""
    logs = "\n".join(client.deployment_logs(deployment_id, 300))
    missing = [m for m in LOG_MARKERS if m not in logs]
    if missing:
        raise ProvisionError("verify",
                             "Deployment succeeded but boot verification failed — "
                             f"missing log markers: {missing}. Check the service logs.")


def deprovision(sub_id: str, client: RailwayClient | None = None) -> None:
    """Delete the customer's Railway project (explicit operator action only —
    never called automatically, so a failed provision keeps its partial state
    for inspection/resume)."""
    sub = load_submission(sub_id)
    prov = sub.get("provisioning") or {}
    project_id = prov.get("project_id")
    if not project_id:
        raise ProvisionError("deprovision", f"{sub_id} has no provisioned project recorded.")
    (client or RailwayClient()).project_delete(project_id)
    sub["provisioning"] = {"status": "deprovisioned",
                           "deleted_project_id": project_id,
                           "updated_at": datetime.now(timezone.utc).isoformat()}
    _save_submission(sub)
    log.info("%s: project %s deleted.", sub_id, project_id)


# ── Background queue (webhook → async provisioning) ───────────────────────────
_queue: "queue.Queue[tuple[str, bool]]" = queue.Queue()
_workers_started = False
_workers_lock = threading.Lock()


def _worker() -> None:
    while True:
        sub_id, require_paid = _queue.get()
        try:
            provision(sub_id, require_paid=require_paid)
        except ProvisionError as e:
            log.error("Provisioning %s failed at %s: %s", sub_id, e.step, e)
        except Exception:
            log.exception("Unexpected provisioning error for %s", sub_id)
        finally:
            _queue.task_done()


def enqueue(sub_id: str, require_paid: bool = True) -> None:
    """Queue a submission for background provisioning (returns immediately —
    used by the Stripe webhook so the 200 goes back to Stripe fast).
    require_paid=False is the operator override for manually-billed customers."""
    global _workers_started
    with _workers_lock:
        if not _workers_started:
            for i in range(MAX_CONCURRENCY):
                threading.Thread(target=_worker, name=f"provisioner-{i}",
                                 daemon=True).start()
            _workers_started = True
    _queue.put((sub_id, require_paid))
    log.info("Queued %s for provisioning.", sub_id)
