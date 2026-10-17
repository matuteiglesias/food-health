"""Read-only adapter for the canonical Personal Measurements Google Sheet.

No credentials or source identifiers are stored in this repository.
Requires optional [measurements] dependencies for live Google API access.
"""
from __future__ import annotations

import os
from typing import Any

from .normalize import normalize_measurements

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
MEDIDAS_RANGE = "'MEDIDAS'!A:AJ"


def fetch_measurements_grid(
    spreadsheet_id: str | None = None, *, service: Any = None
) -> list[list]:
    """Read all populated MEDIDAS cells without writing to the source.

    If `service` is provided, treat it as an injected Google Sheets v4 client,
    allowing tests and offline clients without Google packages installed.
    """
    spreadsheet_id = spreadsheet_id or os.environ.get("FOOD_HEALTH_MEASUREMENTS_SHEET_ID")
    if not spreadsheet_id:
        raise ValueError("FOOD_HEALTH_MEASUREMENTS_SHEET_ID is required")

    if service is None:
        try:
            import google.auth
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Google Sheets support is optional; install 'food-health[measurements]'"
            ) from exc
        credentials, _ = google.auth.default(scopes=[READ_ONLY_SCOPE])
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=MEDIDAS_RANGE,
            valueRenderOption="UNFORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING",
        )
        .execute()
    )
    values = result.get("values", [])
    if not isinstance(values, list):
        raise ValueError("Invalid Google Sheets values response")
    return values


def fetch_observed_measurements(
    spreadsheet_id: str | None = None, *, service: Any = None
) -> list[dict]:
    """Normalize observed body measurements; preserve original source-row indexes."""
    return normalize_measurements(
        fetch_measurements_grid(spreadsheet_id=spreadsheet_id, service=service)
    )
