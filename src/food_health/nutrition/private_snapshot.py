"""Atomic private snapshots for read-only data integrations.

All source data stays in ignored .local/ files, never in public GitHub.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile


def _encode(snapshot: dict) -> bytes:
    return (json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def write_private_snapshot(path: str | Path, snapshot: dict) -> bool:
    """Atomic write if content changed. Return True only on a changed snapshot.

    Fail closed on large apparent truncations of established plan, catalog
    or stock histories; smaller updates are permitted.
    """
    p = Path(path)
    encoded = _encode(snapshot)
    if p.exists():
        old = read_private_snapshot(p)
        for part, key in (("plan", "items"), ("catalog", None), ("stock", "items")):
            before = len(old[part] if key is None else old[part][key])
            after = len(snapshot[part] if key is None else snapshot[part][key])
            if before >= 20 and after < before * 0.9:
                raise ValueError(f"Suspicious truncation of {part}: private snapshot untouched")
        if hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256(encoded).digest():
            return False
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(p.parent, 0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".food-stock-", suffix=".json", dir=p.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, p)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return True


def read_private_snapshot(path: str | Path) -> dict:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        result = json.load(f)
    if result.get("schema_version") != 1:
        raise ValueError("Unsupported food-stock snapshot schema version")
    for part in ("plan", "catalog", "stock"):
        if part not in result:
            raise ValueError(f"Private snapshot missing {part}")
    return result


def private_summary(snapshot: dict) -> dict:
    """Metadata-only: never echo ingredients, quantities or nutrient values."""
    return {
        "plan_active_rows": len(snapshot["plan"]["items"]),
        "reference_foods": len(snapshot["catalog"]),
        "stock_rows": len(snapshot["stock"]["items"]),
        "stock_heading": snapshot["stock"]["quantity_heading"],
        "stock_is_current": False,
    }
