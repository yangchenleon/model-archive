"""Import the four human-editable CSV files in a directory."""
from __future__ import annotations
import csv
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from app.scripts.import_seed import import_data
FILES = {
    "items": "catalog_items.csv",
    "assets": "assets.csv",
    "collection_targets": "collection_targets.csv",
    "events": "asset_events.csv",
}
INT_FIELDS = {"quantity", "priority"}
DECIMAL_FIELDS = {"purchase_price"}
DATE_FIELDS = {"acquired_on"}
DATETIME_FIELDS = {"occurred_at"}
JSON_FIELDS = {"metadata_json"}
def parse_row(row: dict[str | None, str | None], path: Path, row_number: int) -> dict:
    if None in row:
        raise ValueError(f"{path}:{row_number}: too many columns; quote text containing commas")
    parsed: dict = {}
    for field, value in row.items():
        value = (value or "").strip()
        if not value:
            continue
        if field in INT_FIELDS:
            parsed[field] = int(value)
        elif field in DECIMAL_FIELDS:
            parsed[field] = Decimal(value)
        elif field in DATE_FIELDS:
            parsed[field] = date.fromisoformat(value)
        elif field in DATETIME_FIELDS:
            parsed[field] = datetime.fromisoformat(value)
        elif field in JSON_FIELDS:
            parsed[field] = json.loads(value)
        else:
            parsed[field] = value
    return parsed
def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = []
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            if any((value or "").strip() for value in row.values()):
                rows.append(parse_row(row, path, row_number))
        return rows
def main(directory: str) -> None:
    root = Path(directory)
    seed = {name: read_csv(root / filename) for name, filename in FILES.items()}
    created = import_data(seed)
    print("import complete: " + ", ".join(f"{name}={count}" for name, count in created.items()))
if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m app.scripts.import_csv /app/data/drafts/current_snapshot")
    main(sys.argv[1])
