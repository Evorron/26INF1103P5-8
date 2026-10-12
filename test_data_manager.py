
from datetime import datetime
from data_manager import (
    save_inventory_record,
    load_inventory_records,
    get_food_history

)

# Example input — simulates information from the I/O Manager
record = {
    "owner_name": "Tammy",
    "business_nature": "Food and Beverage",
    "business_type": "Hawker Stall",
    "date": "2026-10-07",
    "food_item": "Chicken Rice",
    "quantity_prepared": 100,
    "quantity_sold": 82,
    "additional_information": "Heavy rain during lunch"
}

# Python calculates the day of the week from the date
date_object = datetime.strptime(record["date"], "%Y-%m-%d")
record["day_of_week"] = date_object.strftime("%A")

# Save the record
save_inventory_record(record)

# Load and display saved records for testing
records = load_inventory_records()
print(records)

print("Test completed!")


