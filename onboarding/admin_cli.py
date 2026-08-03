#!/usr/bin/env python3
"""
FlipPulse onboarding — admin CLI.

Reads the backend submission files written by the onboarding form and turns a
selected one into the exact environment variables to paste into the customer's
Railway service (see ADMINISTRATOR_ONBOARDING.md). Decryption requires the same
ONBOARDING_FERNET_KEY the form used.

Usage:
    ONBOARDING_FERNET_KEY=... python admin_cli.py list
    ONBOARDING_FERNET_KEY=... python admin_cli.py show <submission_id>
    ONBOARDING_FERNET_KEY=... python admin_cli.py env  <submission_id>   # .env format

Automated provisioning (also needs RAILWAY_API_TOKEN; see AUTOMATED_PROVISIONING.md):
    ... python admin_cli.py provision   <submission_id>   # create/resume the Railway bot
    ... python admin_cli.py status      <submission_id>   # show provisioning state
    ... python admin_cli.py deprovision <submission_id>   # DELETE the customer's Railway service (bot)
"""

from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

SUBMISSIONS_DIR = Path(os.environ.get("SUBMISSIONS_DIR", Path(__file__).parent / "submissions"))


def _fernet():
    key = os.environ.get("ONBOARDING_FERNET_KEY", "").strip()
    if not key:
        sys.exit("ONBOARDING_FERNET_KEY is not set — cannot decrypt submissions.")
    from cryptography.fernet import Fernet
    return Fernet(key.encode())


def _load(sub_id: str) -> dict:
    path = SUBMISSIONS_DIR / f"{sub_id}.json"
    if not path.exists():
        sys.exit(f"No submission {sub_id!r} in {SUBMISSIONS_DIR}")
    return json.loads(path.read_text())


def _decrypt_secrets(sub: dict) -> dict:
    f = _fernet()
    return {k: f.decrypt(v.encode()).decode()
            for k, v in sub.get("secrets_encrypted", {}).items()}


def cmd_list() -> None:
    subs = sorted(SUBMISSIONS_DIR.glob("*.json"))
    if not subs:
        print(f"(no submissions in {SUBMISSIONS_DIR})")
        return
    print(f"{'ID':<40} {'NAME':<18} {'FORMAT':<12} {'BALANCE':>10}  PAID")
    print("-" * 92)
    for p in subs:
        d = json.loads(p.read_text())
        print(f"{d['id']:<40} {d.get('full_name','')[:17]:<18} "
              f"{d.get('trading_format',''):<12} "
              f"${d.get('starting_balance',0):>9,.0f}  {d.get('payment_status','?')}")


def _env_pairs(sub: dict) -> list[tuple[str, str]]:
    """Ready-to-paste Railway variables. The Kalshi key is a single-line base64 blob
    (KALSHI_PRIVATE_KEY_PEM_B64) so it can't be mangled by a multi-line paste."""
    secrets = _decrypt_secrets(sub)
    pem_b64 = base64.b64encode(secrets.get("kalshi_private_key_pem", "").encode()).decode()
    return [
        ("KALSHI_API_KEY_ID", secrets.get("kalshi_api_key_id", "")),
        ("KALSHI_PRIVATE_KEY_PEM_B64", pem_b64),
        ("DEMO_MODE", "true"),
        ("PAPER_BALANCE", str(sub.get("starting_balance", ""))),
        ("TRADING_FORMAT", sub.get("trading_format", "balanced")),
        ("TELEGRAM_BOT_TOKEN", secrets.get("telegram_bot_token", "")),
        ("TELEGRAM_CHAT_ID", sub.get("telegram_chat_id", "")),
    ]


def cmd_show(sub_id: str) -> None:
    sub = _load(sub_id)
    print(f"# Submission {sub['id']}  ({sub.get('full_name')} <{sub.get('email')}>)")
    print(f"# Created {sub.get('created_at')}  ·  Payment: {sub.get('payment_status')}")
    print("# Paste these into the Railway service Variables (plus the /data *_STATE_PATH")
    print("# vars from .env.example). Every value is a single line — nothing to reformat.\n")
    for k, v in _env_pairs(sub):
        print(f"{k}={v}")


def cmd_env(sub_id: str) -> None:
    """Emit .env-style KEY=VALUE lines (all single-line)."""
    sub = _load(sub_id)
    for k, v in _env_pairs(sub):
        print(f'{k}={v}')


def cmd_provision(sub_id: str) -> None:
    """Run (or resume) automated provisioning synchronously, printing progress.
    The paid gate is skipped — running this command IS the operator decision."""
    import provisioner
    try:
        prov = provisioner.provision(sub_id, require_paid=False)
    except provisioner.ProvisionError as e:
        sys.exit(f"❌ Provisioning failed at step {e.step!r}: {e}\n"
                 f"   Re-run to resume from the last completed step.")
    print(f"✅ Provisioned. Railway project: https://railway.app/project/{prov['project_id']}")
    print("   Bot is in PAPER mode (DEMO_MODE=true). Going live stays a manual step.")


def cmd_status(sub_id: str) -> None:
    sub = _load(sub_id)
    prov = sub.get("provisioning") or {}
    if not prov:
        print(f"{sub_id}: not provisioned.")
        return
    for k in ("status", "step", "error", "project_id", "environment_id",
              "service_id", "volume_id", "deployment_id", "provisioned_at", "updated_at"):
        if prov.get(k):
            print(f"{k:16} {prov[k]}")
    if prov.get("project_id"):
        print(f"{'railway':16} https://railway.app/project/{prov['project_id']}")


def cmd_deprovision(sub_id: str) -> None:
    import provisioner
    sub = _load(sub_id)
    service_id = (sub.get("provisioning") or {}).get("service_id")
    answer = input(f"DELETE Railway service {service_id} for {sub.get('full_name')!r}? "
                   "This stops their bot (the shared project and other bots are "
                   "untouched). Type the customer handle to confirm: ")
    if answer.strip() != sub.get("handle"):
        sys.exit("Aborted — handle did not match.")
    provisioner.deprovision(sub_id)
    print("🗑 Service deleted; submission marked deprovisioned.")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "list":
        cmd_list()
    elif cmd == "show" and len(sys.argv) == 3:
        cmd_show(sys.argv[2])
    elif cmd == "env" and len(sys.argv) == 3:
        cmd_env(sys.argv[2])
    elif cmd == "provision" and len(sys.argv) == 3:
        cmd_provision(sys.argv[2])
    elif cmd == "status" and len(sys.argv) == 3:
        cmd_status(sys.argv[2])
    elif cmd == "deprovision" and len(sys.argv) == 3:
        cmd_deprovision(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
