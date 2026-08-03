"""Small, process-safe persistence helpers for onboarding submission files."""
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def locked(path: Path):
    """Lock a submission's sidecar lock for the duration of a read/modify/write."""
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def read(path: Path) -> dict:
    with locked(path):
        return json.loads(path.read_text())


def write_unlocked(path: Path, data: dict) -> None:
    """Atomically replace a submission; caller holds locked(path)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp",
                                    dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as tmp:
            json.dump(data, tmp, indent=2)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
        os.chmod(path, 0o600)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def write(path: Path, data: dict) -> None:
    with locked(path):
        write_unlocked(path, data)
