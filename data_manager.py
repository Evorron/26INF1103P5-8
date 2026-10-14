"""csv persistence for historical sales records and AI recommendations."""

import csv
from datetime import date, datetime
from pathlib import Path


# Historical sales records
DATA_FOLDER = Path(__file__).resolve().parent / "data"
RECORDS_FILE = DATA_FOLDER / "sales_records.csv"

RECORD_FIELDS = [
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
    """Save a sales record, rejecting duplicate food items on the same date for the same user."""

    # Load existing records before saving
    existing_records = load_records(storage_path)

    # Normalise values so capitalisation and extra spaces do not bypass the check
    user_name = record["user_name"].strip().casefold()
    food_item = record["food_item"].strip().casefold()
    record_date = record["record_date"]

    if isinstance(record_date, str):
        record_date = date.fromisoformat(record_date)

    # Reject a record if the same user already recorded this item on this date
    for existing in existing_records:
        same_user = (
            existing["user_name"].strip().casefold() == user_name
        )
        same_item = (
            existing["food_item"].strip().casefold() == food_item
        )
        same_date = existing["record_date"] == record_date

        if same_user and same_item and same_date:
            raise ValueError(
                f"You have already recorded '{record['food_item']}' "
                f"on {record_date.isoformat()}. "
                "Each food item can only have one record per day."
            )

    # Save the record if no duplicate was found
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    needs_header = (
        not storage_path.exists()
        or storage_path.stat().st_size == 0
    )

    row = {
        field: record.get(field, "")
        for field in RECORD_FIELDS
    }

    row["record_date"] = record_date.isoformat()

    with storage_path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)

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
        writer = csv.DictWriter(file, fieldnames=RECORD_FIELDS)
        writer.writeheader()

        for record in records:
            row = {
                field: record.get(field, "")
                for field in RECORD_FIELDS
            }

            if isinstance(row["record_date"], date):
                row["record_date"] = row["record_date"].isoformat()

            writer.writerow(row)

# find user's history for a food item
def records_for_item(
    storage_path: Path,
    user_name: str,
    food_item: str
) -> list[dict]:
    """Return records for one user and food item, earliest first."""
    normalized_name = user_name.casefold().strip()
    normalized_item = food_item.casefold().strip()

    matches = [
        record
        for record in load_records(storage_path)
        if record["user_name"].casefold().strip() == normalized_name
        and record["food_item"].casefold().strip() == normalized_item
    ]

    return sorted(matches, key=lambda record: record["record_date"])


# lists the user's recorded food items
def item_names_for_user(
    storage_path: Path,
    user_name: str
) -> list[str]:
    """Return the unique food items recorded by one user."""
    normalized_name = user_name.casefold().strip()

    names = {
        record["food_item"].strip()
        for record in load_records(storage_path)
        if record["user_name"].casefold().strip() == normalized_name
    }

    return sorted(names, key=str.casefold)


# filters records by date
def records_in_date_range(
    storage_path: Path,
    user_name: str,
    food_item: str,
    start_date: date,
    end_date: date
) -> list[dict]:
    """Return matching records within an inclusive date range."""
    item_records = records_for_item(
        storage_path, user_name, food_item
    )

    return [
        record
        for record in item_records
        if start_date <= record["record_date"] <= end_date
    ]

# end - for storing historical sales records


AI_RECOMMENDATIONS_FILE = (
    Path(__file__).resolve().parent
    / "data"
    / "ai_recommendations.csv"
)

AI_RECOMMENDATION_FIELDS = [
    "user_name",
    "food_item",
    "forecast_date",
    "recommended_portions",
    "reason",
    "verified_evidence",
    "suggested_next_step",
    "forecast_method",
    "confidence",
    "generated_at",
    "warning",
]


def save_ai_recommendation(
    storage_path: Path,
    user_name: str,
    food_item: str,
    forecast_date: date,
    recommended_portions: int,
    reason: str,
    verified_evidence: str,
    suggested_next_step: str,
    forecast_method: str,
    confidence: str,
    generated_at: datetime,
    warning: str,
) -> None:
    """Save the final food preparation recommendation to CSV."""
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    needs_header = (
        not storage_path.exists()
        or storage_path.stat().st_size == 0
    )

    row = {
        "user_name": user_name,
        "food_item": food_item,
        "forecast_date": forecast_date.isoformat(),
        "recommended_portions": recommended_portions,
        "reason": reason,
        "verified_evidence": verified_evidence,
        "suggested_next_step": suggested_next_step,
        "forecast_method": forecast_method,
        "confidence": confidence,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "warning": warning,
    }

    with storage_path.open(
        "a", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=AI_RECOMMENDATION_FIELDS,
        )

        if needs_header:
            writer.writeheader()

        writer.writerow(row)


def replace_ai_recommendation(
    storage_path: Path,
    user_name: str,
    food_item: str,
    forecast_date: date,
    recommended_portions: int,
    reason: str,
    verified_evidence: str,
    suggested_next_step: str,
    forecast_method: str,
    confidence: str,
    generated_at: datetime,
    warning: str,
) -> None:
    """Replace an existing forecast for the same user, item, and date."""

    recommendations = load_ai_recommendations(storage_path)

    target_date = forecast_date.isoformat()

    # Remove the existing forecast with the same identifying details
    recommendations = [
        record for record in recommendations
        if not (
            record["user_name"].strip().lower() == user_name.strip().lower()
            and record["food_item"].strip().lower() == food_item.strip().lower()
            and record["forecast_date"] == target_date
        )
    ]

    # Add the new forecast
    recommendations.append({
        "user_name": user_name,
        "food_item": food_item,
        "forecast_date": target_date,
        "recommended_portions": recommended_portions,
        "reason": reason,
        "verified_evidence": verified_evidence,
        "suggested_next_step": suggested_next_step,
        "forecast_method": forecast_method,
        "confidence": confidence,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "warning": warning,
    })

    # Rewrite the CSV with the updated records
    with storage_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=AI_RECOMMENDATION_FIELDS,
        )
        writer.writeheader()
        writer.writerows(recommendations)


def load_ai_recommendations(storage_path: Path) -> list[dict]:
    """Load saved AI forecast recommendations from CSV."""
    if not storage_path.exists():
        return []

    with storage_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader)
