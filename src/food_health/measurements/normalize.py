"""Pure normalization of Google Sheets MEDIDAS values; source untouched.

Use only recorded anthropometric values. Rows without numeric measurements
produce no observation. Date plausibility is not validated in this layer;
future-dated nonblank values require separate upstream data-quality checks.
Columns with duplicated names receive stable suffixes.
"""
from __future__ import annotations

from datetime import datetime
from collections import Counter

ANTHROPOMETRIC = {
    "Neck", "Shoulder", "Chest", "Flexed", "Arm", "Forearm", "Waist",
    "Belly", "Hips", "Butt", "Thigh", "Calf", "Weight", "Body Fat", "Muscle"
}


def normalize_measurements(values: list[list], header_row: int = 3) -> list[dict]:
    """Read a sheet grid and return measured values with physical row provenance.

    header_row is 1-based. Dates are mm/dd/YYYY in the current canonical sheet.
    Does not invent values, interpolate, or convert unverified fields.
    """
    if len(values) < header_row:
        raise ValueError("header row absent")
    headers = values[header_row - 1]
    counts: Counter = Counter()
    normalized_headers = []
    for value in headers:
        name = str(value).strip() if value is not None else ""
        counts[name] += 1
        normalized_headers.append(name if counts[name] == 1 else f"{name}#{counts[name]}")
    records = []
    for row_number, row in enumerate(values[header_row:], start=header_row + 1):
        if not row or not row[0]:
            continue
        try:
            date = datetime.strptime(str(row[0]).strip(), "%m/%d/%Y").date()
        except ValueError:
            continue
        observations = {}
        for name, value in zip(normalized_headers[1:], row[1:]):
            if name.split("#")[0] not in ANTHROPOMETRIC or value in (None, ""):
                continue
            try:
                observations[name] = float(str(value).replace(",", "."))
            except ValueError:
                continue
        if observations:
            records.append({"date": date.isoformat(), "source_row": row_number,
                            "observed": observations})
    return records
