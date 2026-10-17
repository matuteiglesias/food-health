"""Minimal operational entrypoint. No remote calls or writes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="food-health")
    parser.add_argument("command", choices=["doctor"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest = root / "archive" / "legacy" / "_manifest.json"
    print("food-health: bootstrap status")
    print(f"project_root: {root}")
    print(f"legacy_archive: {'present' if manifest.exists() else 'not found'}")
    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        print(f"legacy_original_files: {len(data.get('files', []))}")
    print("measurements_source: Google Sheets / Personal Measurements (canonical, read-only)")
    print("No network access and no source writes performed")
    return 0
