"""Read-only Food & Household Stock adapters for canonical Google Sheets.

The Google account credential is supplied by Application Default Credentials.
Source IDs are supplied at runtime (never embedded in Git). All parsing
is deterministic and never writes source spreadsheets.
"""
from __future__ import annotations

import math
import os
from typing import Any

from food_health.nutrition.composition import NUTRIENTS_PER_100G

READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
FOOD_PLAN_RANGE = "'CURATED_PLAN'!A1:I120"
FOOD_CATALOG_RANGE = "'SOURCE_NUTRIENTS'!A1:K"
STOCK_RANGE = "'STOCK'!A1:E120"


def _client(service: Any = None) -> Any:
    if service is not None:
        return service
    try:
        import google.auth
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError("Install food-health[measurements] for Google Sheets access") from exc
    credentials, _ = google.auth.default(scopes=[READ_ONLY_SCOPE])
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def _read(service: Any, sheet_id: str, area: str) -> list[list]:
    if not isinstance(sheet_id, str) or not sheet_id.strip():
        raise ValueError("Sheet ID must be configured")
    result = (service.spreadsheets().values().get(
        spreadsheetId=sheet_id, range=area, valueRenderOption="UNFORMATTED_VALUE",
        dateTimeRenderOption="FORMATTED_STRING",
    ).execute())
    data = result.get("values")
    if not isinstance(data, list) or not data or not isinstance(data[0], list):
        raise ValueError("Google Sheets response empty or malformed")
    return data


def _field(row: list, index: int) -> object:
    return row[index] if index < len(row) else None


def _id(value: object) -> str | None:
    """Normalize numeric IDs from Sheets to stable strings; never round."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError("Invalid boolean food ID")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError("Nonintegral food ID")
        return str(int(value))
    if isinstance(value, int):
        return str(value)
    raw = str(value).strip()
    return raw if raw.isdecimal() else None


def _nonnegative(value: object, name: str, *, allow_missing: bool = False) -> float | None:
    if value is None or str(value).strip().upper() in {"", "NULL", "NA", "N/A", "NAN"}:
        if allow_missing:
            return None
        raise ValueError(f"Missing {name}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid {name}: expected finite nonnegative number")
    return number


def _header(values: list[list], required: set[str]) -> dict[str, int]:
    names = [str(x).strip() for x in values[0]]
    absent = required - set(names)
    if absent:
        raise ValueError("Missing worksheet headers: " + ", ".join(sorted(absent)))
    for item in required:
        if names.count(item) != 1:
            raise ValueError("Ambiguous worksheet column: " + item)
    return {name: names.index(name) for name in required}


def parse_curated_plan(values: list[list]) -> dict:
    """Read only explicit 3-day quantities and source IDs, not derived macros.

    Footer/label rows without numeric 3-day quantities are ignored. A nonzero
    quantity without a usable ID aborts the import.
    """
    if not values:
        raise ValueError("Empty curated plan")
    cols = _header(values, {"ID", "cant 3d"})
    items = []
    for row_idx, row in enumerate(values[1:], start=2):
        raw = _field(row, cols["cant 3d"])
        if raw is None or raw == "":
            continue
        if isinstance(raw, bool):
            raise ValueError(f"Boolean grams on worksheet row {row_idx}")
        try:
            grams = float(raw)
        except (ValueError, TypeError):
            # Summary/footer rows contain text, not a food quantity.
            continue
        if not math.isfinite(grams) or grams < 0:
            raise ValueError(f"Invalid quantity on worksheet row {row_idx}")
        if grams == 0:
            continue
        food_id = _id(_field(row, cols["ID"]))
        if not food_id:
            raise ValueError(f"Active plan row {row_idx} has no food ID")
        items.append({"food_id": food_id, "grams": grams, "source_row": row_idx})
    if not items:
        raise ValueError("Curated plan has no active foods")
    return {"period_days": 3, "items": items, "source_tab": "CURATED_PLAN"}


def parse_catalog(values: list[list]) -> dict[str, dict]:
    """Read reference nutrients per 100g from Food!SOURCE_NUTRIENTS A:K.

    Missing measurements in the catalog remain None, NOT zero.
    """
    if not values:
        raise ValueError("Empty nutrient catalog")
    cols = _header(values, {"ID", "name", "Food Group", *NUTRIENTS_PER_100G})
    out = {}
    for row_idx, row in enumerate(values[1:], start=2):
        food_id = _id(_field(row, cols["ID"]))
        if food_id is None:
            if any(value not in (None, "") for value in row):
                raise ValueError(f"Unidentified nutrient source row {row_idx}")
            continue
        if food_id in out:
            raise ValueError(f"Duplicate food ID at source row {row_idx}")
        out[food_id] = {
            "name": str(_field(row, cols["name"]) or ""),
            "group": str(_field(row, cols["Food Group"]) or ""),
            "per_100g": {
                field: _nonnegative(_field(row, cols[field]), field, allow_missing=True)
                for field in NUTRIENTS_PER_100G
            },
            "source_row": row_idx,
        }
    if not out:
        raise ValueError("Nutrient catalog has no entries")
    return out


def parse_stock(values: list[list]) -> dict:
    """Preserve stock quantity heading as provenance, NOT as today's count."""
    if not values:
        raise ValueError("Empty stock sheet")
    names = [str(x).strip() for x in values[0]]
    fixed = _header(values, {"item", "storage", "urgency", "notes"})
    quantity_columns = [name for name in names if name.startswith("qty_g ")]
    if len(quantity_columns) != 1 or names.count(quantity_columns[0]) != 1:
        raise ValueError("Expected exactly one dated qty_g column")
    qty_name = quantity_columns[0]
    qty_idx = names.index(qty_name)
    items = []
    for row_idx, row in enumerate(values[1:], start=2):
        name = str(_field(row, fixed["item"]) or "").strip()
        if not name:
            continue
        raw = _field(row, qty_idx)
        quantity = None
        if raw not in (None, ""):
            try:
                quantity = _nonnegative(raw, "stock quantity")
            except ValueError:
                # A source note/unknown marker is not a quantity of zero.
                quantity = None
        items.append({
            "item": name, "storage": str(_field(row, fixed["storage"]) or ""),
            "urgency": str(_field(row, fixed["urgency"]) or ""),
            "notes": str(_field(row, fixed["notes"]) or ""),
            "quantity_g": quantity,
            "quantity_raw": raw if quantity is None else None,
            "source_row": row_idx,
        })
    if not items:
        raise ValueError("Stock sheet has no rows")
    return {
        "source_tab": "STOCK",
        "quantity_heading": qty_name,
        "snapshot_date_unresolved": True,
        "items": items,
    }


def fetch_food_and_stock(
    *, food_sheet_id: str | None = None, stock_sheet_id: str | None = None,
    service: Any = None
) -> dict:
    """Read-only cohesive snapshot. Raises on any failed source read/validation."""
    food_id = food_sheet_id or os.environ.get("FOOD_HEALTH_FOOD_SHEET_ID")
    stock_id = stock_sheet_id or os.environ.get("FOOD_HEALTH_STOCK_SHEET_ID")
    if not food_id or not stock_id:
        raise ValueError("Set FOOD_HEALTH_FOOD_SHEET_ID and FOOD_HEALTH_STOCK_SHEET_ID")
    client = _client(service)
    plan = parse_curated_plan(_read(client, food_id, FOOD_PLAN_RANGE))
    catalog = parse_catalog(_read(client, food_id, FOOD_CATALOG_RANGE))
    stock = parse_stock(_read(client, stock_id, STOCK_RANGE))
    missing = {r["food_id"] for r in plan["items"]} - set(catalog)
    if missing:
        raise ValueError(f"{len(missing)} active curated food IDs absent from catalog")
    return {"schema_version": 1, "plan": plan, "catalog": catalog, "stock": stock}
