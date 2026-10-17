"""Historical activity-day diagnostics from legacy volume.csv (2022–2023).

Archive is NOT evidence of present-day workout completion. Presence of a
nonempty '1' means a recorded day; blanks mean unrecorded/unknown rather
than proven inactivity.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

CHANNELS = ("Resistance", "Cardio", "Calistenia")


def load_legacy_activity(file: str | Path):
    """Parse the archived activity-day CSV without modifying it."""
    import pandas as pd

    rows = []
    with open(file, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(CHANNELS).issubset(reader.fieldnames):
            raise ValueError("Legacy activity CSV is missing expected channels")
        date_col = reader.fieldnames[0]
        for row in reader:
            day = date.fromisoformat(row[date_col])
            event = {"date": pd.Timestamp(day)}
            for key in CHANNELS:
                marker = (row.get(key) or "").strip()
                if marker not in ("", "0", "1"):
                    raise ValueError("Unknown historical activity marker")
                event[key] = 1 if marker == "1" else 0
            rows.append(event)
    if not rows:
        raise ValueError("No historical activity rows")
    frame = pd.DataFrame(rows).set_index("date").sort_index()
    if not frame.index.is_unique:
        raise ValueError("Duplicate activity dates")
    return frame
