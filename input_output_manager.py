import csv
from datetime import date
from pathlib import Path
import shutil
import textwrap


def show_welcome():
    ##"Display opening program title"
    print("--------------------------------")
    print("Welcome to Hawker AI!")
    print("An enhance tools for food preparation forecasting.\n")
   

def choose_action():
    ##"Display main menu"
    print("------------MENU-----------------")
    print("1. Add a historical sales record")
    print("2. Generate a Gemini forecast")
    print("3. List my recorded food items")
    print("4. View my records by food item and date range")
    print("5. Exit")
    return input("Choose an option: ").strip()  ##"To prevent breaking due to typos"


registered_business = {} ##"Save business entires "business_type" into a 'dictionary'" 


def check_business_type(user_name: str, business_type: str) -> None:
    normalized_name = " ".join(user_name.split()).lower()
    registered_type = registered_business.get(normalized_name)

    ## "Check sales_records.csv if it's in memory"
    if not registered_type:
        data_path = Path(__file__).resolve().parent / "data" / "sales_records.csv"
        if data_path.exists():
            try:
                with open(data_path, encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        ##Compare normalized CSV name with normalized input
                        if " ".join(row.get("user_name", "").split()).lower() == normalized_name:
                            registered_type = row.get("business_type")
                            registered_business[normalized_name] = registered_type
                            break
            except Exception:
                pass

    if registered_type and business_type.lower() != registered_type.lower():
        raise ValueError(f"Business type for {user_name} must be '{registered_type}'.")
    ##"Raise an error if input business type doesn't match the registered record"



def save_record_to_csv(record: dict) -> None:
    ## "Append a confirmed sales record to sales_records.csv"
    data_path = Path(__file__).resolve().parent / "data" / "sales_records.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = data_path.exists()

    with open(data_path, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=record.keys())
        if not file_exists:
            writer.writeheader()
        
        ## "Convert date object to ISO format string for CSV storage"
        row_data = record.copy()
        row_data["record_date"] = record["record_date"].isoformat()
        writer.writerow(row_data)



def load_records_from_csv() -> list[dict]:
    ## "load and parse all sales records from sales_records.csv"
    data_path = Path(__file__).resolve().parent / "data" / "sales_records.csv"
    if not data_path.exists():
        return []
    
    records = []
    with open(data_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["portions_prepared"] = int(row["portions_prepared"])
            row["portions_sold"] = int(row["portions_sold"])
            row["record_date"] = date.fromisoformat(row["record_date"])
            records.append(row)
    return records


def collect_sales_record():
    ##Collect a record, display it to the user and save or edit

    print("\nEnter historical sales information")
    user_name = read_name("Your name: ")
    business_type = read_words("Business type: ", "Business type")
    
    ##Validate business type consistency using the checking function
    check_business_type(user_name, business_type)

    record_date = read_historical_date("Record date (YYYY-MM-DD): ")
    food_item = read_words("Food item: ", "Food item")
    portions_prepared = read_positive_integer("Portions prepared: ")
    portions_sold = read_sold_portions("Portions sold: ", portions_prepared)
    past_context = read_optional_context("Optional past context: ")


    record={"user_name": user_name, "business_type": business_type, "record_date" : record_date, 
             "food_item": food_item, "portions_prepared": portions_prepared, "portions_sold": portions_sold,
             "past_context": past_context}


    while True:
        show_record_preview(record)
        choice = input("Enter C to confirm and save, or E to edit: ").strip().lower()
        if choice == "c":
            ## Save to in-memory cache upon confirmation
            registered_business[" ".join(user_name.split()).lower()] = business_type
            save_record_to_csv(record)
            return record
        if choice == "e":
            edit_sales_record(record)
            ## Re-validating after editing in case name or business type changed
            check_business_type(record["user_name"], record["business_type"])
        else:
            print("Please enter C or E.")


def edit_sales_record(record: dict):
    ##To allow users to edits it's records
    print("\nWhich detail would you like to edit?")
    print("1. Name")
    print("2. Business type")
    print("3. Record date")
    print("4. Food item")
    print("5. Portions prepared")
    print("6. Portions sold")
    print("7. Past context")
    choice = input("Choose 1 to 7: ").strip()

    if choice == "1":
        record["user_name"] = read_name("Your name: ")
    elif choice == "2":
        record["business_type"] = read_words("Business type: ", "Business type")
    elif choice == "3":
        record["record_date"] = read_historical_date("Record date (YYYY-MM-DD): ")
    elif choice == "4":
        record["food_item"] = read_words("Food item: ", "Food item")
    elif choice == "5":
        record["portions_prepared"] = read_positive_integer("Portions prepared: ")
        while record["portions_sold"] > record["portions_prepared"]:
            print("Portions sold cannot be greater than portions prepared.")
            record["portions_sold"] = read_sold_portions(
                "Portions sold: ", record["portions_prepared"]
            )
    elif choice == "6":
        record["portions_sold"] = read_sold_portions(
            "Portions sold: ", record["portions_prepared"]
        )
    elif choice == "7":
        record["past_context"] = read_optional_context("Optional past context: ")
    else:
        print("Please choose a number from 1 to 7.")


def collect_forecast_request():
    ##Collect the details that are known before preparing food

    print("\nEnter forecast information")
    
    user_name=read_name("Your name: "),
    food_item=read_words("Forecast food item: ", "Forecast food item"),
    target_date=read_future_date("Target date (YYYY-MM-DD): "),
    future_context=read_optional_context("Optional future context: "),

    return collect_forecast_request


def collect_record_search():
    """Collect filters for viewing saved historical records."""
    print("\nView historical records")

    user_name = read_name("Your name: ")
    food_item = read_words("Food item: ", "Food item")

    ##Starting date and End date to ensure it's a valid past-present date
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
        print("End date cannot be earlier than the start date.")


def show_items(items: list[str]):
    ##Display saved food items saved
    if not items:
        print("No food items have been recorded for this name.")
        return
    print("Recorded food items:")
    for item in items:
        print(f"- {item}")


def show_records(records: list[dict]):
    ##Display all records that match the selected item and dates
    if not records:
        print("No records were found for that food item and date range.")
        return

    headers = ["Date", "Food item", "Prepared", "Sold", "Leftover", "Past context"]
    
    # Build rows cleanly using a list comprehension
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

    # Calculate widths for every column except Past context
    widths = [
        max(len(headers[i]), max(len(row[i]) for row in rows))
        for i in range(len(headers) - 1)
    ]

    # Fit the Past context column to the available terminal width
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
        """Format a row, wrapping long text onto additional lines."""
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

def show_record_preview(record: dict):
    ##Show a new record before it is saved
    leftovers = record["portions_prepared"] - record["portions_sold"]
    print("\nPlease check this record")
    print(f"Name: {record['user_name']}")
    print(f"Business type: {record['business_type']}")
    print(f"Date: {record['record_date'].isoformat()}")
    print(f"Food item: {record['food_item']}")
    print(f"Prepared: {record['portions_prepared']}")
    print(f"Sold: {record['portions_sold']}")
    print(f"Leftover: {leftovers}")
    print(f"Past context: {record['past_context'] or '-'}")


def show_forecast(response: dict):
    ##Show Gemini's forecast without changing its suggested portions."""
    print("\nGemini Forecast")
    print(f"Suggested portions to prepare: {response['suggested_portions']}")
    print(f"Confidence: {response['confidence'].title()}")
    print(f"Reasoning: {response['reasoning']}")
    print("Factors considered: " + ", ".join(response["factors_considered"]))
    print("Verified evidence:")
    for item in response["evidence"]:
        print(f"- {item['claim']} ({item['metric']}: {item['value']})")
    if response["warning"]:
        print(f"Warning: {response['warning']}")


def read_name(prompt: str):
    ##Read in a users-name inputs** Main Integration 
    return read_words(prompt, "Name")


def read_words(prompt: str, label: str):
    ##Read a name or label that contains letters, spaces, hyphens, or apostrophes
    while True:
        value = input(prompt).strip()
        allowed = all(character.isalpha() or character in " -'" for character in value)
        if value and allowed and any(character.isalpha() for character in value):
            return value
        print(f"{label} must contain letters only (spaces, hyphens, and apostrophes are allowed).")


def read_positive_integer(prompt: str):
    ##Ensure each whole number greater than zero
    while True:
        try:
            value = int(input(prompt).strip())
            if value > 0:
                return value
        except ValueError:
            pass
        print("Enter a positive whole number.")


def read_sold_portions(prompt: str, portions_prepared: int):
    ##Read sold portions and compare them with prepared portions
    while True:
        try:
            value = int(input(prompt).strip())
            if 0 <= value <= portions_prepared:
                return value
        except ValueError:
            pass
        print(f"Enter a whole number from 0 to {portions_prepared}.")


def read_historical_date(prompt: str):
    ##Read a valid date that is today or earlier
    while True:
        entered_date = read_date(prompt)
        if entered_date <= date.today():
            return entered_date
        print("A historical record date cannot be in the future.")


def read_future_date(prompt: str):
    ##Read a valid date after today for forecasting
    while True:
        entered_date = read_date(prompt)
        if entered_date > date.today():
            return entered_date
        print("The forecast target date must be in the future.")


def read_date(prompt: str):
    ##Read an ISO date and immediately reject an invalid format
    while True:
        try:
            return date.fromisoformat(input(prompt).strip())
        except ValueError:
            print("Enter the date in YYYY-MM-DD format.")


def read_optional_context(prompt: str):
    ##"Read optional notes and immediately enforce the word limit" 
    while True:
        value = input(prompt).strip()
        if len(value.split()):
            return value
        print(f"Context cannot contain more than words.")


#show_welcome()
#while True:
        action = choose_action()
        try:
            if action == "1":
                record = collect_sales_record()
                print("Historical sales record collected successfully!")
            elif action == "2":
                request = collect_forecast_request()
                print("Forecast request collected successfully!")
            elif action == "3":
                user_name = read_name("Your name: ")
                print(f"Listing items for {user_name}...")
            elif action == "4":
                search_filters = collect_record_search()
                print("Search criteria collected successfully!")
            elif action == "5":
                print("bye-bye")
                break
            else:
                print("Please choose an option from 1 to 5.")
        except ValueError as error:
            print(f"\nUnable to continue: {error}\n")
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break