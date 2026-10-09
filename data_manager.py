import csv
import os

# Folder and file where inventory records will be stored
DATA_FOLDER = "data"
RECORDS_FILE = os.path.join(DATA_FOLDER, "records.csv")

# define column names in the CSV file
FIELDNAMES = [
    "owner_name",
    "business_nature",
    "business_type",
    "date",
    "day_of_week",
    "food_item",
    "quantity_prepared",
    "quantity_sold",
    "additional_information"
]


def save_inventory_record(record):
    """Save one food inventory record to the CSV file."""

    # Create the data folder if it does not exist
    os.makedirs(DATA_FOLDER, exist_ok=True)

    # Check whether the CSV file needs its column headings
    needs_header = (
        not os.path.exists(RECORDS_FILE)           # Does records.csv not exist yet?
        or os.path.getsize(RECORDS_FILE) == 0      # Does it exist but contain nothing?
    )

    # Open the file in append mode to add a new row
    with open(
        RECORDS_FILE, "a", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(file, fieldnames=FIELDNAMES)

        # Write column headings for a new or empty file
        if needs_header:
            writer.writeheader()

        # Save the record info as one row
        writer.writerow({
            field: record.get(field, "")
            for field in FIELDNAMES
        })


def load_inventory_records():                     # retrieve record
    """Load all saved inventory records."""

    if not os.path.exists(RECORDS_FILE):
        return []

    with open(
        RECORDS_FILE, "r", newline="", encoding="utf-8"
    ) as file:

        reader = csv.DictReader(file)
        return list(reader)
    