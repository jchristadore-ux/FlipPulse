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
"""

from __future__ import annotations

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
    secrets = _decrypt_secrets(sub)
    return [
        ("KALSHI_API_KEY_ID", secrets.get("kalshi_api_key_id", "")),
        ("KALSHI_PRIVATE_KEY_PEM", secrets.get("kalshi_private_key_pem", "")),
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
    print(f"# Paste these into the Railway service Variables (plus the /data *_STATE_PATH vars):\n")
    for k, v in _env_pairs(sub):
        if k == "KALSHI_PRIVATE_KEY_PEM":
            print(f"{k} = <<multi-line PEM below>>")
        else:
            print(f"{k} = {v}")
    print("\n# --- KALSHI_PRIVATE_KEY_PEM (paste as one multi-line variable) ---")
    print(dict(_env_pairs(sub))["KALSHI_PRIVATE_KEY_PEM"])


def cmd_env(sub_id: str) -> None:
    """Emit .env-style KEY=VALUE lines (PEM collapsed with \\n)."""
    sub = _load(sub_id)
    for k, v in _env_pairs(sub):
        v = v.replace("\n", "\\n") if k == "KALSHI_PRIVATE_KEY_PEM" else v
        print(f'{k}={v}')


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
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
