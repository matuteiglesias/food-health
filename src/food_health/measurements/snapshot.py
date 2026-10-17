"""Private, atomic snapshot of observations from the canonical spreadsheet.

No external API calls here. Changes to existing rows and deleted rows are
handled by full-snapshot reconciliation. Duplicate dates remain distinct
because physical worksheet row numbers are the stable ingest key.

NOTE: worksheet row is an operational locator, not an immutable event ID.
Inserted/deleted sheet rows may therefore register as changes, intentionally.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from typing import Iterable

CREATE = """
CREATE TABLE IF NOT EXISTS measured_observations (
    source_id TEXT NOT NULL,
    worksheet TEXT NOT NULL,
    source_row INTEGER NOT NULL,
    observation_date TEXT NOT NULL,
    observed_json TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    PRIMARY KEY (source_id, worksheet, source_row)
);
CREATE INDEX IF NOT EXISTS idx_measurement_date
    ON measured_observations(source_id, worksheet, observation_date);
"""


@dataclass(frozen=True)
class SyncResult:
    rows: int
    inserted: int
    updated: int
    deleted: int
    unchanged: int
    duplicate_dates: int


def _canonical_record(row: dict) -> tuple[int, str, str, str]:
    """Validate, serialize and hash one observed record, without side effects."""
    row_no = row.get("source_row")
    raw_date = row.get("date")
    fields = row.get("observed")
    if type(row_no) is not int or row_no < 4:
        raise ValueError("invalid worksheet row index")
    try:
        parsed_date = date.fromisoformat(raw_date)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid observation date") from exc
    if not isinstance(fields, dict) or not fields:
        raise ValueError("observed fields must be nonempty")
    normalized: dict[str, float] = {}
    for name, value in fields.items():
        if not isinstance(name, str) or not name:
            raise ValueError("invalid field label")
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("observed value must be numeric")
        if not math.isfinite(float(value)):
            raise ValueError("observed value must be finite")
        normalized[name] = float(value)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256((parsed_date.isoformat()+"|"+payload).encode("utf8")).hexdigest()
    return row_no, parsed_date.isoformat(), payload, digest


def _open_private_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(db_path.parent, 0o700)
    conn = sqlite3.connect(db_path)
    os.chmod(db_path, 0o600)
    conn.executescript(CREATE)
    return conn


def sync_snapshot(
    db_path: str | Path,
    observations: Iterable[dict],
    *,
    source_id: str,
    worksheet: str = "MEDIDAS",
) -> SyncResult:
    """Atomically reflect an authoritative full read into a private SQLite db.

    An empty input represents an empty authoritative snapshot and deletes
    prior observations. Callers MUST validate successful, nonempty upstream
    source reads before invoking this function.
    """
    if not source_id or not worksheet:
        raise ValueError("source and worksheet required")
    rows = [_canonical_record(r) for r in observations]
    indexed = {r[0]: r for r in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate physical source row")
    counts = Counter(r[1] for r in rows)
    duplicates = sum(v - 1 for v in counts.values() if v > 1)
    db = _open_private_db(Path(db_path))
    try:
        db.execute("BEGIN IMMEDIATE")
        existing = {
            int(row): digest
            for row, digest in db.execute(
                """SELECT source_row, content_sha256 FROM measured_observations
                   WHERE source_id=? AND worksheet=?""",
                (source_id, worksheet),
            )
        }
        inserted = updated = unchanged = 0
        for row_no, day, payload, digest in rows:
            old_hash = existing.get(row_no)
            if old_hash == digest:
                unchanged += 1
            elif old_hash is None:
                db.execute(
                    """INSERT INTO measured_observations
                       (source_id,worksheet,source_row,observation_date,observed_json,content_sha256)
                       VALUES (?,?,?,?,?,?)""",
                    (source_id, worksheet, row_no, day, payload, digest),
                )
                inserted += 1
            else:
                db.execute(
                    """UPDATE measured_observations
                       SET observation_date=?,observed_json=?,content_sha256=?
                       WHERE source_id=? AND worksheet=? AND source_row=?""",
                    (day, payload, digest, source_id, worksheet, row_no),
                )
                updated += 1
        removed_rows = existing.keys() - indexed.keys()
        # Fail closed on unexpectedly truncated reads: never erase most of an
        # established history because an upstream response was incomplete.
        # Small fixture/sheet edits below 20 rows can be freely reconciled.
        if len(existing) >= 20 and len(removed_rows) > max(5, len(existing) // 10):
            raise ValueError(
                "Snapshot would remove over 10% of historical rows; "
                "check Google Sheets read completeness before retrying"
            )
        for row_no in removed_rows:
            db.execute(
                """DELETE FROM measured_observations
                   WHERE source_id=? AND worksheet=? AND source_row=?""",
                (source_id, worksheet, row_no),
            )
        db.commit()
        return SyncResult(
            rows=len(rows), inserted=inserted, updated=updated,
            deleted=len(removed_rows), unchanged=unchanged, duplicate_dates=duplicates,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def snapshot_summary(
    db_path: str | Path, *, source_id: str, worksheet: str = "MEDIDAS"
) -> dict:
    """Return aggregate coverage only, without disclosing measured values."""
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"private local snapshot not found: {path}")
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = db.execute(
            """SELECT COUNT(*), MIN(observation_date), MAX(observation_date),
                      COUNT(DISTINCT observation_date)
               FROM measured_observations
               WHERE source_id=? AND worksheet=?""",
            (source_id, worksheet),
        ).fetchone()
        return {
            "rows": row[0], "first_date": row[1], "last_date": row[2],
            "duplicate_dates": row[0]-row[3],
        }
    finally:
        db.close()
