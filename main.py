"""Command-line entry point that connects the Hawker AI managers.

Run with ``python main.py`` after installing the dependencies required by
``ai_manager.py``.  This module intentionally coordinates the existing
managers instead of changing their responsibilities.
"""

import input_output_manager as io_manager
import forecast_adapter
import logic_manager


def collect_forecast_request() -> dict:
    """Delegate forecast collection to the repaired IO module."""
    return io_manager.collect_forecast_request()


def add_sales_record() -> None:
    """Collect, validate, and then save one historical sales record."""
    record = io_manager.collect_sales_record()
    try:
        logic_manager.validate_sales_record(record)
    except Exception:
        raise
    io_manager.save_record_to_csv(record)
    io_manager.registered_business[" ".join(record["user_name"].split()).lower()] = record["business_type"]
    print("Historical sales record saved and validated successfully!")


def generate_forecast() -> None:
    """Create a forecast from the current CSV records and display it."""
    request = collect_forecast_request()
    response = forecast_adapter.generate_logged_forecast(
        request, io_manager.load_records_from_csv()
    )
    io_manager.show_forecast(response)


def list_food_items() -> None:
    """Display all distinct items recorded for one user."""
    user_name = io_manager.read_name("Your name: ")
    items = logic_manager.food_items_for_user(
        user_name, io_manager.load_records_from_csv()
    )
    io_manager.show_items(items)


def view_records() -> None:
    """Display historical records matching the user's filters."""
    search_filters = io_manager.collect_record_search()
    records = logic_manager.records_for_search(
        search_filters, io_manager.load_records_from_csv()
    )
    io_manager.show_records(records)


def run() -> None:
    """Run the complete Hawker AI command-line menu."""
    io_manager.show_welcome()
    actions = {
        "1": add_sales_record,
        "2": generate_forecast,
        "3": list_food_items,
        "4": view_records,
    }

    while True:
        try:
            action = io_manager.choose_action()
            if action == "5":
                print("bye-bye")
                return
            if action not in actions:
                print("Please choose an option from 1 to 5.")
                continue
            actions[action]()
        except ValueError as error:
            print(f"\nUnable to continue: {error}\n")
        except RuntimeError as error:
            print(f"\nUnable to generate forecast: {error}\n")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            return


if __name__ == "__main__":
    run()
