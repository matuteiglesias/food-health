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
    parser.add_argument("command", choices=["doctor", "measurements-sync", "measurements-summary", "measurements-report", "measurements-dashboard", "food-sync", "food-summary"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--db", type=Path, help="Private local SQLite snapshot path")
    parser.add_argument("--sheet-id", help="Canonical spreadsheet ID (prefer private environment)")
    parser.add_argument("--height-m", type=float, help="Optional height in meters for BMI")
    parser.add_argument("--output-dir", type=Path, help="Private destination directory for dashboard")
    parser.add_argument("--no-legacy-activity", action="store_true", help="Skip archived 2022–2023 activity plot")
    parser.add_argument("--legacy-goals-file", type=Path, help="Explicit opt-in: compare against archived goal CSV (not current goals)")
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

    if args.command in ("food-sync", "food-summary"):
        from .nutrition.private_snapshot import (
            private_summary, read_private_snapshot, write_private_snapshot,
        )

        path = root / ".local" / "food-stock.json"
        if args.command == "food-sync":
            from .nutrition.google_sheets import fetch_food_and_stock
            from .nutrition.composition import composition

            snapshot = fetch_food_and_stock()
            plan = snapshot["plan"]
            # Validate the full intended nutrient calculation before replacing
            # the prior private snapshot. Do not interpret plans as consumption.
            composition(snapshot["catalog"], plan["items"], period_days=plan["period_days"])
            changed = write_private_snapshot(path, snapshot)
            result = private_summary(snapshot)
            print(
                f"plan_active_rows={result['plan_active_rows']} "
                f"reference_foods={result['reference_foods']} "
                f"stock_rows={result['stock_rows']} "
                f"changed={str(changed).lower()}"
            )
            print("Source Sheets unchanged; stock snapshot currentness is unverified")
            return 0

        result = private_summary(read_private_snapshot(path))
        print(
            f"plan_active_rows={result['plan_active_rows']} "
            f"reference_foods={result['reference_foods']} "
            f"stock_rows={result['stock_rows']} "
            f"stock_heading={result['stock_heading']} "
            "stock_currentness=unverified"
        )
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

    if args.command == "measurements-dashboard":
        from .measurements.snapshot import load_snapshot
        from .measurements.dashboard import generate_dashboard

        records = load_snapshot(db_path, source_id=source_id)
        out = args.output_dir or (root / ".local" / "reports" / "measurement-atlas")
        # This repository is public. Never write personal report content to a
        # user-supplied path outside the ignored .local hierarchy.
        if not out.resolve().is_relative_to((root / ".local").resolve()):
            raise ValueError("Private dashboard output must be inside <root>/.local/")
        archive_activity = root / "archive" / "legacy" / "legacy_23" / "volume.csv"
        activity_file = None if args.no_legacy_activity else archive_activity
        receipt = generate_dashboard(records, output_dir=out, height_m=args.height_m, activity_file=activity_file, goals_file=args.legacy_goals_file)
        print(f"PRIVATE dashboard: {receipt['index']}")
        print(f"observed_source_rows={receipt['source_rows']} figures={receipt['figures']} archived_activity_days={receipt['activity_rows']}")
        print("No Google Sheets access/write; no missing-date imputation")
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
