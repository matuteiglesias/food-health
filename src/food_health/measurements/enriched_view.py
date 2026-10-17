"""Private, idempotent estimate projection over an unchanged observed snapshot.

The source SQLite remains the sole persisted authority for observed values.
Derived estimates are a separate, replaceable JSON artifact with fingerprint
consistency checks. No Sheet/API requests occur inside this module.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from .enrichment import MODEL_VERSION, infer_missing, source_fingerprint
from .snapshot import load_snapshot


def enrichment_path(root: str | Path) -> Path:
    return Path(root) / ".local" / "measurements-enriched.json"


def _atomic_json(path: Path, data: dict) -> bool:
    serialized=(json.dumps(
        data,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False,
    )+"\n").encode("utf-8")
    if path.exists() and path.read_bytes()==serialized:
        return False
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(path.parent,0o700)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=".enrichment-",suffix=".json")
    try:
        with os.fdopen(fd,"wb") as out:
            out.write(serialized)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(tmp,0o600)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return True


def refresh_enrichment(db_path: str | Path, *, source_id: str,
                       output_path: str | Path, worksheet: str = "MEDIDAS") -> dict:
    """Build an estimate artifact atomically from a committed canonical snapshot."""
    rows=load_snapshot(db_path,source_id=source_id,worksheet=worksheet)
    fingerprint=source_fingerprint(rows)
    path=Path(output_path)
    if path.exists():
        try:
            with path.open(encoding="utf-8") as handle:
                existing=json.load(handle)
            if (existing.get("source_observation_sha256")==fingerprint
                    and existing.get("model_version")==MODEL_VERSION
                    and existing.get("schema_version")==1):
                return {"changed":False,"input_rows":existing["input_rows"],
                        "estimation_count":existing["estimation_count"],
                        "target_count":len(existing["target_diagnostics"])}
        except (ValueError, KeyError, TypeError, OSError):
            pass  # Repair corrupted/private derived artifacts by re-computing.
    result=infer_missing(rows)
    changed=_atomic_json(path,result)
    return {
        "changed":changed,"input_rows":result["input_rows"],
        "estimation_count":result["estimation_count"],
        "target_count":len(result["target_diagnostics"]),
    }


def load_enriched_view(db_path: str | Path, *, source_id: str,
                       output_path: str | Path, worksheet: str = "MEDIDAS") -> list[dict]:
    """Return observed and separate estimated values, rejecting stale projections.

    For each returned row: `observed` is authoritative, `estimated` is
    uncertainty-aware. `values` is a convenient merged view, but consumers
    must inspect `provenance` and not call it directly measured.
    """
    rows=load_snapshot(db_path,source_id=source_id,worksheet=worksheet)
    path=Path(output_path)
    with path.open(encoding="utf-8") as handle:
        data=json.load(handle)
    if data.get("schema_version")!=1 or data.get("model_version")!=MODEL_VERSION:
        raise ValueError("Enrichment version mismatch: regenerate derived snapshot")
    if data.get("source_observation_sha256")!=source_fingerprint(rows):
        raise ValueError("Stale enrichment: canonical observations changed; rerun enrich")
    estimates={item["source_row"]:item for item in data["rows"]}
    if set(estimates)!={item["source_row"] for item in rows}:
        raise ValueError("Enrichment row identities do not match canonical input")
    result=[]
    for row in rows:
        derived=estimates[row["source_row"]]
        if derived["date"]!=row["date"]:
            raise ValueError("Enrichment dates inconsistent with canonical input")
        observed=dict(row["observed"])
        predicted=dict(derived["estimated"])
        if set(observed)&set(predicted):
            raise ValueError("Enrichment attempted to overwrite direct observations")
        result.append({
            "source_row":row["source_row"],"date":row["date"],
            "observed":observed,"estimated":predicted,
            "values":{**observed,**{k:v["value"] for k,v in predicted.items()}},
            "provenance":{**{k:"observed" for k in observed},
                          **{k:"estimated_not_observed" for k in predicted}},
        })
    return result
