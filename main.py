"""Application coordinator for the Hawker AI command-line program.

This module connects the six managers without duplicating their work:

* ``Input_output_manager`` collects and displays information.
* ``logic_manager`` validates data and applies business rules.
* ``data_manager`` reads and writes CSV files.
* ``forecast_adapter`` creates a safe, user-facing forecast.
* ``ai_manager`` is called by the adapter when an AI estimate is needed.
* ``activity_logger`` is called by the adapter to keep an audit trail.
"""

import Input_output_manager as io_manager
import data_manager
import forecast_adapter
import logic_manager


def add_sales_record() -> None:
    """Collect, validate, and save one confirmed historical sales record."""
    record = io_manager.collect_sales_record()
    logic_manager.validate_sales_record(record)
    data_manager.add_record(data_manager.RECORDS_FILE, record)

    # Retain the business type in the IO manager's temporary lookup cache only
    # after the record has been accepted and saved successfully.
    normalised_name = " ".join(record["user_name"].split()).casefold()
    io_manager.registered_business[normalised_name] = record["business_type"]
    print("Historical sales record saved successfully!")


def generate_forecast() -> None:
    """Collect a forecast request, generate it, display it, and save its summary."""
    request = io_manager.collect_forecast_infomation()
    all_records = data_manager.load_records(data_manager.RECORDS_FILE)
    response = forecast_adapter.generate_logged_forecast(request, all_records)

    io_manager.show_forecast(response)
    data_manager.save_ai_recommendation(
        data_manager.AI_RECOMMENDATIONS_FILE,
        request["user_name"],
        request["food_item"],
        request["target_date"],
        response["suggested_portions"],
        response["reasoning"],
    )


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
                print("Exiting the programme...")
                print("Thank you for using Hawker AI! Have a pleasant day ahead!")
                return
            else:
                print("Please choose an option from 1 to 5.")
        except (KeyError, TypeError, ValueError) as error:
            print(f"\nUnable to continue: {error}\n")
        except RuntimeError as error:
            print(f"\nUnable to generate forecast: {error}\n")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return


if __name__ == "__main__":
    run()
