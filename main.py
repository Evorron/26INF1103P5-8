"""Application coordinator for the Hawker AI command-line program.

This module connects the six managers without duplicating their work:

* ``Input_output_manager`` collects and displays information.
* ``logic_manager`` validates data and applies business rules.
* ``data_manager`` reads and writes CSV files.
* ``forecast_adapter`` creates a safe, user-facing forecast.
* ``ai_manager`` is called by the adapter when an AI estimate is needed.
* ``activity_logger`` is called by the adapter to keep an audit trail.
"""

import input_output_manager as io_manager
import data_manager
import forecast_adapter
import logic_manager
from datetime import datetime


def add_sales_record() -> None:
    """Collect, validate, and save one confirmed historical sales record."""
    record = io_manager.collect_sales_record()
    logic_manager.validate_sales_record(record)
    data_manager.add_record(data_manager.RECORDS_FILE, record)

    # Retain the business type in the IO manager's temporary lookup cache only
    # after the record has been accepted and saved successfully.
    normalised_name = " ".join(record["user_name"].split()).casefold()
    io_manager.registered_business[normalised_name] = record["business_type"]
    print("Historical sales record saved successfully!\n")


def generate_forecast() -> None:
    """Collect a forecast request, generate it, display it, and save its summary."""
    request = io_manager.collect_forecast_infomation()
    
    # Load previously saved forecasts
    existing_recommendations = data_manager.load_ai_recommendations(
        data_manager.AI_RECOMMENDATIONS_FILE
    )

    # Convert the requested date to the same format used in the CSV
    target_date = request["target_date"]
    if hasattr(target_date, "isoformat"):
        target_date = target_date.isoformat()
    else:
        target_date = str(target_date)

    # Check for an existing forecast for this user, item, and date
    existing_forecast = next(
        (
            record for record in existing_recommendations
            if record["user_name"].strip().lower()
            == request["user_name"].strip().lower()
            and record["food_item"].strip().lower()
            == request["food_item"].strip().lower()
            and record["forecast_date"] == target_date
        ),
        None,
    )

    replace_existing = False

    # If a forecast already exists, display it and stop
    if existing_forecast is not None:
        print(
            f"\nA forecast already exists for "
            f"{request['food_item']} on {target_date}."
        )

        action = io_manager.ask_duplicate_forecast_action()

        if action == "view":
            io_manager.show_past_forecasts([existing_forecast])
            return
        elif action == "cancel":
            print("\nForecast cancelled. Returning to the main menu.")
            return
        elif action == "replace":
            replace_existing = True

    # Generate the forecast only after the duplicate check
    all_records = data_manager.load_records(data_manager.RECORDS_FILE)
    response = forecast_adapter.generate_logged_forecast(request, all_records)

    io_manager.show_forecast(response)
    save_function = (
        data_manager.replace_ai_recommendation
        if replace_existing
        else data_manager.save_ai_recommendation
    )

    save_function(
        data_manager.AI_RECOMMENDATIONS_FILE,
        request["user_name"],
        request["food_item"],
        request["target_date"],
        response["suggested_portions"],
        response["reasoning"],
        "; ".join(
            item["claim"] for item in response.get("evidence", [])
        ),
        response.get("business_advice") or "",
        response["forecast_method"],
        response["confidence"],
        datetime.now(),
        response.get("warning") or "",
    )

    if replace_existing:
        print("\nYour previous forecast has been replaced.")
    else:
        print("\nYour forecast has been saved.")


def list_food_items() -> None:
    """Display the distinct food items saved for one named user."""
    user_name = input("Your name: ").strip()
    all_records = data_manager.load_records(data_manager.RECORDS_FILE)
    items = logic_manager.food_items_for_user(user_name, all_records)
    io_manager.show_items(items)


def view_records() -> None:
    """Display a user's saved records for a selected item and date range."""
    search_filters = io_manager.collect_record_search()
    all_records = data_manager.load_records(data_manager.RECORDS_FILE)
    records = logic_manager.records_for_search(search_filters, all_records)
    io_manager.show_records(records)



def view_past_forecasts() -> None:
    """Display a past forecast selected by the user."""

    user_name = input("Enter your name: ").strip()
    food_item = input("Enter the food item: ").strip()
    forecast_date = input("Enter the forecast date (YYYY-MM-DD): ").strip()

    recommendations = data_manager.load_ai_recommendations(
        data_manager.AI_RECOMMENDATIONS_FILE
    )

    matching_forecasts = [
        record for record in recommendations
        if record["user_name"].strip().lower() == user_name.lower()
        and record["food_item"].strip().lower() == food_item.lower()
        and record["forecast_date"] == forecast_date
    ]

    io_manager.show_past_forecasts(matching_forecasts)


def run() -> None:
    """Run the menu flow supplied by the IO manager until the user exits."""
    io_manager.display_welcome()

    while True:
        try:
            action = io_manager.display_all()

            if action == "1":
                add_sales_record()
            elif action == "2":
                generate_forecast()
            elif action == "3":
                list_food_items()
            elif action == "4":
                view_records()
            elif action == "5":
                view_past_forecasts()
            elif action == "6":
                print("\nExiting the programme...")
                print("Thank you for using Hawker AI! Have a pleasant day ahead!\n")
                return
            else:
                print("Please choose an option from 1 to 6.")
        except (KeyError, TypeError, ValueError) as error:
            print(f"\nUnable to continue: {error}\n")
        except RuntimeError as error:
            print(f"\nUnable to generate forecast: {error}\n")
        except KeyboardInterrupt:
            print("\nExiting the programme...")
            return


if __name__ == "__main__":
    run()
