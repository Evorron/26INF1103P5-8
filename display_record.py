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