"""JSON persistence for historical Hawker AI sales records."""

import csv
from datetime import date
from pathlib import Path


# Historical sales records
DATA_FOLDER = Path(__file__).resolve().parent / "data"
RECORDS_FILE = DATA_FOLDER / "sales_records.csv"

FIELDNAMES = [
    "user_name",
    "business_type",
    "record_date",
    "food_item",
    "portions_prepared",
    "portions_sold",
    "past_context",
]


# start - for storing historical sales records
def add_record(storage_path: Path, record: dict) -> None:
    """Append one sales record to the CSV file."""
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    needs_header = (
        not storage_path.exists()
        or storage_path.stat().st_size == 0
    )

    row = {
        field: record.get(field, "")
        for field in FIELDNAMES
    }

    if isinstance(row["record_date"], date):
        row["record_date"] = row["record_date"].isoformat()

    with storage_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)

        if needs_header:
            writer.writeheader()

        writer.writerow(row)

def load_records(storage_path: Path) -> list[dict]:
    """Load saved CSV records and change saved dates back into Python dates."""
    if not storage_path.exists():
        return []

    records = []

    with storage_path.open("r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if not row:
                continue

            records.append({
                "user_name": row["user_name"],
                "business_type": row["business_type"],
                "record_date": date.fromisoformat(row["record_date"]),
                "food_item": row["food_item"],
                "portions_prepared": int(row["portions_prepared"]),
                "portions_sold": int(row["portions_sold"]),
                "past_context": row.get("past_context", "") or "",
            })
    return records


def save_records(storage_path: Path, records: list[dict]) -> None:
    """Write all sales records to CSV."""
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    with storage_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)
        writer.writeheader()

        for record in records:
            row = {
                field: record.get(field, "")
                for field in FIELDNAMES
            }

            if isinstance(row["record_date"], date):
                row["record_date"] = row["record_date"].isoformat()

            writer.writerow(row)




# def save_inventory_record(record):
#     """Save one food record to the CSV file."""

#     os.makedirs(DATA_FOLDER, exist_ok=True)

#     # Check if the CSV file needs column headings
#     needs_header = (
#         not os.path.exists(RECORDS_FILE)
#         or os.path.getsize(RECORDS_FILE) == 0
#     )

#     with open(
#         RECORDS_FILE, "a", newline="", encoding="utf-8"
#     ) as file:

#         writer = csv.DictWriter(file, fieldnames=FIELDNAMES)

#         if needs_header:
#             writer.writeheader()

#         # Save only the standardised fields
#         writer.writerow({
#             field: record.get(field, "")
#             for field in FIELDNAMES
#         })


# def load_inventory_records():
#     """Load all saved food records."""

#     if not os.path.exists(RECORDS_FILE):
#         return []

#     with open(
#         RECORDS_FILE, "r", newline="", encoding="utf-8"
#     ) as file:

#         reader = csv.DictReader(file)
#         return list(reader)


# def get_food_history(user_name, food_item):
#     """Retrieve records for a specific user and food item."""

#     records = load_inventory_records()

#     food_history = [
#         record for record in records
#         if record["user_name"].strip().lower() == user_name.strip().lower()
#         and record["food_item"].strip().lower() == food_item.strip().lower()
#     ]

#     # Sort records from earliest to latest
#     food_history.sort(key=lambda record: record["record_date"])

#     return food_history
