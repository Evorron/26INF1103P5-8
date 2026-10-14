import csv
from datetime import date
from pathlib import Path
import shutil
import textwrap
import data_manager


def display_welcome():
    ##"Display opening program title"
    print("\n")
    print("--------------------------------")
    print("Welcome to Hawker AI!")
    print("An enhance tools for food preparation forecasting.\n")


def display_all():
    ##"Display main menu"
    print("------------MENU-----------------")
    print("1. Add a historical sales record")
    print("2. Generate a forecast")
    print("3. List my recorded food items")
    print("4. View historical records")
    print("5. View past forecasts")
    print("6. Exit")

    return input("\nChoose an option: ").strip()  ##"To prevent breaking due to typos"


registered_business = {} ##"Save "business_type" entires into a 'dictionary'" 


def check_business_type(user_name: str, business_type: str):

    ## "To check and match against existing users_name to it's business_type" 
    normalized_name = " ".join(user_name.split()).lower()
    registered_type = registered_business.get(normalized_name)

    ## "Check 'sales_records.csv' if it's in memory"
    if not registered_type:
        data_path = Path(__file__).resolve().parent / "data" / "sales_records.csv"
        if data_path.exists():
            try:
                with open(data_path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        ## "Compare normalized CSV name with normalized input"
                        if " ".join(row.get("user_name", "").split()).lower() == normalized_name:
                            registered_type = row.get("business_type")
                            registered_business[normalized_name] = registered_type
                            break
            except Exception:
                pass

    if registered_type and business_type.lower() != registered_type.lower():
        raise ValueError(f"Business type for {user_name} must be '{registered_type}'.")
    ## "Raise an error if input business_type doesn't match the registered record"


def collect_sales_record():
    ## "Collect a record, display it to the user and save or edit"

    print("\nEnter historical sales information")
    user_name = input("Your name: ").strip()
    while not user_name:
        user_name = input("Your name: ").strip() ##Constantly prompt users-inputs

    while True:
            business_type = input("Business type: ").strip()
            ##Validate business type consistency using the checking function
            try:
                check_business_type(user_name, business_type)
                break
            except ValueError as h:
                print(h)
                print("Error! Please try again..")

    record_date = read_historical_date("Record date (YYYY-MM-DD): ")
    food_item = input("Food item: ").strip()
    portions_prepared = check_positive_integer("Portions prepared: ")
    portions_sold = check_sold_portions("Portions sold: ", portions_prepared)
    past_context = input("Optional past context: ").strip()


    record={"user_name": user_name, "business_type": business_type, "record_date" : record_date, 
             "food_item": food_item, "portions_prepared": portions_prepared, "portions_sold": portions_sold,
             "past_context": past_context}  ## "Utilising dictionary"


    while True:
        record_preview(record)

        choice = input("Enter C to confirm and save, or E to edit: ").strip().lower()
            ## "Prompt users selection enter C to confirm and save, or E to edit"

        if choice == "c":
            return record

        elif choice == "e":
            edit_sales_record(record)
            check_business_type(
                record["user_name"],
                record["business_type"]
            )

        else:
            print("Please enter C or E.")
            

def edit_sales_record(record: dict):
    ## To allow users to edits it's records
    print("\nWhich detail would you like to edit?")
    print("1. Name")
    print("2. Business type")
    print("3. Record date")
    print("4. Food item")
    print("5. Portions prepared")
    print("6. Portions sold")
    print("7. Past context")
    choice = input("Choose 1 to 7: ").strip()

    ## Listed the option 1-7
    if choice == "1":
        record["user_name"] = input("Your name: ").strip()
    elif choice == "2":
        record["business_type"] = input("business_type: ").strip()
    elif choice == "3":
        record["record_date"] = read_historical_date("Record date (YYYY-MM-DD): ")
    elif choice == "4":
        record["food_item"] = input("Food item: ").strip()
    elif choice == "5":
        record["portions_prepared"] = check_positive_integer("Portions prepared: ")
        while record["portions_sold"] > record["portions_prepared"]:
            print("Portions sold cannot be greater than portions prepared")
            record["portions_sold"] = check_sold_portions(
                "Portions sold: ", record["portions_prepared"]
            )
    elif choice == "6":
        record["portions_sold"] = check_sold_portions(
            "Portions sold: ", record["portions_prepared"]
        )
    elif choice == "7":
        record["past_context"] = input("Optional past context: ").strip()
    else:
        print("Please choose a number from 1 to 7.")


def collect_forecast_infomation():
    ## "Collect known infomation before preparing food"

    print("\nEnter forecast information")
    
    user_name= input("Your name: ").strip(),
    food_item= input("Forecast food item: ").strip(),
    target_date=read_future_date("Target date (YYYY-MM-DD): "),
    future_context= input("Optional context: ").strip(), 
    ## "Basic Information to be forecast"

    return collect_forecast_infomation


def collect_record_search():
    ##"Viewing historical records"
    print("\nView historical records")

    user_name = input("Your name: ").strip()
    food_item = input("Food item: ").strip()

    ## "Ensure Starting date must be before End date to ensure it's valid"
    start_date = read_historical_date("Start date (YYYY-MM-DD): ")
    while True:
        end_date = read_historical_date("End date (YYYY-MM-DD): ")
        if end_date >= start_date:
            return {
                "user_name": user_name,
                "food_item": food_item,
                "start_date": start_date,
                "end_date": end_date,
            }
        print("End date cannot be earlier than the start date")


def show_items(items: list[str]):
    ##Display saved food items
    if not items:
        print("No food items have been recorded for this name")
        return
    print("Recorded food items:")
    for item in items:
        print(f"• {item}")


def show_records(records: list[dict]):
    ##Display all records that match the selected item and dates
    if not records:
        print("No records were found for that food item and date range")
        return

    headers = ["Date", "Food item", "Prepared", "Sold", "Leftover", "Past context"]
    
    ## Build rows cleanly using a list comprehension
    rows = [
        [
            r["record_date"].isoformat(),
            r["food_item"],
            str(r["portions_prepared"]),
            str(r["portions_sold"]),
            str(r["portions_prepared"] - r["portions_sold"]),
            r["past_context"] or "-"
        ]
        for r in records
    ]

    ## Calculate widths for every column except Past context
    widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers) - 1)
    ]

    ## Fit the Past context column to the available terminal width
    terminal_width = shutil.get_terminal_size(fallback=(120, 20)).columns
    fixed_width = sum(widths) + 3 * len(headers) + 1
    context_width = max(
        12,
        min(
            max(len(headers[-1]), max(len(row[-1]) for row in rows)),
            terminal_width - fixed_width
        )
    )
    widths.append(context_width)
    
    def format_row(values: list[str]) -> list[str]:
            ##Format a row, wrapping long text
            wrapped = [
                textwrap.wrap(str(v), width=widths[i], break_long_words=True, break_on_hyphens=False) or [""]
                for i, v in enumerate(values)
            ]
            row_height = max(len(lines) for lines in wrapped)
    
            formatted_lines = []
            for line_index in range(row_height):
                cells = [
                    lines[line_index].rjust(widths[i]) if i in (2, 3, 4) else lines[line_index].ljust(widths[i])
                    if line_index < len(lines) else "".ljust(widths[i])
                    for i, lines in enumerate(wrapped)
                ]
                ##Format for data display table
                formatted_lines.append("| " + " | ".join(cells) + " |")
            return formatted_lines
    
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    
    print("\nMatching records")
    print(border)
    for line in format_row(headers):
            print(line)
    print(border)
    for row in rows:
            for line in format_row(row):
                print(line)
            print(border)
    print("\n")            

def record_preview(record: dict):
    ##Display recent new record before it is saved
    leftovers = record["portions_prepared"] - record["portions_sold"]

    print("\nPlease check the details of the following record: ")
    print(f"Name: {record['user_name']}")
    print(f"Business type: {record['business_type']}")
    print(f"Date: {record['record_date'].isoformat()}")
    ##"iso" dateformat

    print(f"Food item: {record['food_item']}")
    print(f"Prepared: {record['portions_prepared']}")
    print(f"Sold: {record['portions_sold']}")
    print(f"Leftover: {leftovers}")
    print(f"Past context: {record['past_context']}")


def show_forecast(response: dict):
    ##Show AI forecast without changing its suggested portions."""
    recorded_sales = response["recorded_sales"]

    print("\n" + "=" * 50)
    print("             HAWKER AI")
    print("          FORECAST REPORT")
    print("=" * 50)

    print("\n--- SALES OVERVIEW ---")
    if recorded_sales:
        average_recorded_sales = sum(recorded_sales) / len(recorded_sales)
        print("Average recorded sales: " f"{average_recorded_sales:.1f} portions\n")
    else:
        print("Average recorded sales: Not available.\n")

    print("\n--- RECOMMENDATION ---")
    print(f"Suggested portions to prepare: " f"{response['suggested_portions']}")
    print(f"Confidence: {response['confidence'].title()}")

    print("\n--- REASON ---")
    print(response["reasoning"])

    print("\n--- VERIFIED EVIDENCE ---")
    for item in response["evidence"]:
        print(f"  • {item['claim']} ({item['metric']}: {item['value']})")

    print("\n--- SUGGESTED NEXT STEP ---")
    print(response["business_advice"])
    if response["warning"]:
        print("\n--- WARNING ---")
        print(response["warning"])

    print("\n" + "=" * 50 + "\n")


def check_positive_integer(prompt: int):
    ##Ensure each whole number = zero or greater then zero
    while True:
        try:
            value = int(input(prompt).strip())
            if value > -1:
                return value
        except ValueError:
            pass
        print("Enter a vaild number.")


def check_sold_portions(prompt: int, portions_prepared: int):
    ##Read 'sold portions' and compare them with 'prepared portions'
    while True:
        try:
            value = int(input(prompt).strip())
            if 0 <= value <= portions_prepared:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number from 0 to {portions_prepared}.")


def read_historical_date(prompt: date):
    ##Read a valid date that is today or earlier
    while True:
        entered_date = read_date(prompt)
        if entered_date <= date.today():
            return entered_date
        print("A historical record date cannot be in the future.")


def read_future_date(prompt: date):
    ##Read a valid date after today for forecasting
    while True:
        entered_date = read_date(prompt)
        if entered_date > date.today():
            return entered_date
        print("The forecast target date must be in the future.")


def read_date(prompt: date):
    ##Read an ISO date and immediately reject an invalid format
    while True:
        try:
            return date.fromisoformat(input(prompt).strip())
        except ValueError:
            print("Enter the date in YYYY-MM-DD format.")

# to display forecast history for users
def show_past_forecasts(recommendations: list[dict]) -> None:
    ##Display previously saved forecast recommendations

    if not recommendations:
        print("\nNo past forecasts found.")
        return

    for record in recommendations:
        print("\n" + "=" * 50)
        print("          HAWKER AI - PAST FORECAST")
        print("=" * 50)

        print(f"Forecast date : {record['forecast_date']}")
        print(f"Owner         : {record['user_name']}")
        print(f"Food item     : {record['food_item']}")

        print("\n--- RECOMMENDATION ---")
        print(f"Portions      : {record['recommended_portions']}")

        print("\n--- EXPLANATION ---")
        print(record['reason'])

        
        print("\n--- SUPPORTING EVIDENCE ---")

        evidence = record['verified_evidence'].strip()

        if evidence:
            for item in evidence.split("; "):
                print(f"  • {item}")
        else:
            print("  No evidence available.")


        print("\n--- SUGGESTED NEXT STEP ---")
        print(
            record['suggested_next_step']
            or "No additional advice available."
        )

        print("\n--- FORECAST DETAILS ---")
        # print(f"Method        : {record['forecast_method']}")
        print(f"Confidence    : {record['confidence']}")
        print(f"Generated at  : {record['generated_at']}")
        print(f"Warning       : {record['warning'] or 'None'}")

        print("=" * 50)


def ask_duplicate_forecast_action() -> str:
    """Ask the user what to do when a forecast already exists."""

    print("\nA forecast already exists for this food item and date.")
    print("1. View the existing forecast")
    print("2. Regenerate and replace the existing forecast")
    print("3. Cancel and return to the main menu")

    while True:
        choice = input("\nChoose an option (1-3): ").strip()

        if choice == "1":
            return "view"
        elif choice == "2":
            return "replace"
        elif choice == "3":
            return "cancel"
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

display_welcome()
while True:
        action = display_all()  ## Display Menu

        if action == "1":
                record = collect_sales_record()

                ## Save the confirmed record through Data Manager
                data_manager.add_record(
                    data_manager.RECORDS_FILE,
                    record
                )
                ## "Check against exsisting users record to it's business_type"
                normalized_name = " ".join(
                    record["user_name"].split()
                ).casefold() ## Take-note of the case-sensitive users-inputs

                registered_business[normalized_name] = record["business_type"]

                print("Historical sales record saved successfully!")

        elif action == "2":
                request = collect_forecast_infomation()
                print("Forecast request collected successfully!")
        elif action == "3":
                user_name = input("Your name: ").strip()

                items = data_manager.item_names_for_user(
                    data_manager.RECORDS_FILE,
                    user_name
                )
                show_items(items)
                
        elif action == "4":
                search_filters = collect_record_search()
                ## Searching records via Data Manager csv file
                records = data_manager.records_in_date_range(
                    data_manager.RECORDS_FILE,
                    search_filters["user_name"],
                    search_filters["food_item"],
                    search_filters["start_date"],
                    search_filters["end_date"],
                )

                show_records(records)

        elif action == "5":  ## Exiting Program
                print("Exiting the programme...")
                print("Thank you for using Hawker AI! Have a pleasant day ahead!")
                break