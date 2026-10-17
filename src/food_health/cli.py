"""CLI for private read-only source syncs and offline summaries."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def _sheet_id(explicit_id: str | None) -> str:
    value = explicit_id or os.environ.get("FOOD_HEALTH_MEASUREMENTS_SHEET_ID")
    if not value:
        raise ValueError("Set FOOD_HEALTH_MEASUREMENTS_SHEET_ID in the private environment")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="food-health")
    parser.add_argument("command", choices=["doctor", "measurements-sync", "measurements-summary", "measurements-report"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--db", type=Path, help="Private local SQLite snapshot path")
    parser.add_argument("--sheet-id", help="Canonical spreadsheet ID (prefer private environment)")
    parser.add_argument("--height-m", type=float, help="Optional height in meters for BMI")
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.command == "doctor":
        manifest = root / "archive" / "legacy" / "_manifest.json"
        print("food-health: bootstrap status")
        print(f"project_root: {root}")
        print(f"legacy_archive: {'present' if manifest.exists() else 'not found'}")
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            print(f"legacy_original_files: {len(data.get('files', []))}")
        print("measurements_source: Google Sheets / Personal Measurements (canonical, read-only)")
        print("Doctor does no network access and no source writes")
        return 0

    source_id = _sheet_id(args.sheet_id)
    db_path = args.db if args.db is not None else root / ".local" / "measurements.sqlite3"

    if args.command == "measurements-sync":
        from .measurements.google_sheets import fetch_observed_measurements
        from .measurements.snapshot import sync_snapshot

        observations = fetch_observed_measurements(source_id)
        # Never wipe the private snapshot following an unexpectedly empty API response.
        if not observations:
            raise RuntimeError("Upstream read contained no measurements; local snapshot untouched")
        result = sync_snapshot(db_path, observations, source_id=source_id)
        print(
            f"rows={result.rows} inserted={result.inserted} updated={result.updated} "
            f"deleted={result.deleted} unchanged={result.unchanged} "
            f"duplicate_dates={result.duplicate_dates}"
        )
        print("Canonical Google Sheet not modified; private local state updated")
        return 0

    if args.command == "measurements-report":
        from .measurements.snapshot import load_snapshot
        from .measurements.report import build_measurement_report, save_private_report

        records = load_snapshot(db_path, source_id=source_id)
        report = build_measurement_report(records, height_m=args.height_m)
        target = root / ".local" / "reports" / "measurements.json"
        save_private_report(target, report)
        print(f"Private report generated: {target} ({len(records)} observed rows)")
        return 0

    from .measurements.snapshot import snapshot_summary

    summary = snapshot_summary(db_path, source_id=source_id)
    print(
        f"rows={summary['rows']} first_date={summary['first_date']} "
        f"last_date={summary['last_date']} duplicate_dates={summary['duplicate_dates']}"
    )
    return 0
