"""Command-line entry point that connects the Hawker AI managers.

Run with ``python main.py`` after installing the dependencies required by
``ai_manager.py``.  This module intentionally coordinates the existing
managers instead of changing their responsibilities.
"""

import Input_output_manager as io_manager
import forecast_adapter
import logic_manager


def collect_forecast_request() -> dict:
    """Collect a usable forecast dictionary without changing the IO module."""
    # Input_output_manager.collect_forecast_request is retained unchanged, so
    # the coordinator gathers the same four fields in the shape logic_manager
    # and forecast_adapter expect.
    print("\nEnter forecast information")
    return {
        "user_name": io_manager.read_name("Your name: "),
        "food_item": io_manager.read_words("Forecast food item: ", "Forecast food item"),
        "target_date": io_manager.read_future_date("Target date (YYYY-MM-DD): "),
        "future_context": io_manager.read_optional_context("Optional future context: "),
    }


def add_sales_record() -> None:
    """Validate a record before allowing the unchanged IO module to save it."""
    # collect_sales_record currently writes the CSV itself when the user
    # confirms.  Temporarily defer that one write so the logic-manager check
    # happens first, without changing the IO module's source code.
    original_save = io_manager.save_record_to_csv
    original_business_cache = io_manager.registered_business.copy()
    collected_record: dict | None = None

    def defer_save(record: dict) -> None:
        nonlocal collected_record
        collected_record = record

    io_manager.save_record_to_csv = defer_save
    try:
        record = io_manager.collect_sales_record()
        logic_manager.validate_sales_record(record)
    except Exception:
        # Do not leave a business-type cache entry for a record that failed
        # validation and was therefore not written to the CSV file.
        io_manager.registered_business.clear()
        io_manager.registered_business.update(original_business_cache)
        raise
    finally:
        io_manager.save_record_to_csv = original_save

    # The confirmation path always supplies a record; retain this guard in
    # case the unchanged UI collection flow is altered later.
    if collected_record is None:
        raise RuntimeError("No sales record was confirmed for saving.")
    original_save(collected_record)
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
