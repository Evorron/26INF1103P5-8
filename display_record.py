import shutil
from data_formatting import DataFormatting 


class display_records: 

    @staticmethod
    def show_items(items: list[str]):
    ##Display saved food items
        if not items:
            print("No food items have been recorded for this name")
            return
        print("Recorded food items:")
        for item in items:
            print(f"• {item}")
        print("\n")  ##"Add a new line for better readability"

    @staticmethod
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
        format = DataFormatting(widths)
        format.format_table(headers,rows)

    @staticmethod
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


class forecast_display:

    @staticmethod
    def show_forecast(response: dict):
    ##Show AI's forecast without changing its suggested portions."""
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

    # to display forecast history for users
    @staticmethod
    def show_past_forecasts(recommendations: list[dict]) -> None:
        """Display previously saved forecast recommendations."""

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

    @staticmethod
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