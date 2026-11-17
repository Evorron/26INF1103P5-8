from data_validation import date_vaildation, positive_integer, sold_portions
from display_record import display_records


class Hawker:

    def clean_name(text):
        return" ".join(text.split()).lower()


    def __init__(self, user_name, business_type):
        self.user_name = user_name
        self.business_type = business_type
        self.foods = {}
        self.dates = date_vaildation() 
        self.postive_int = positive_integer()
        self.sold_portions = sold_portions
        self.display_records = display_records   


    def collect_sales_record(self):
        ##"Collect a record, display it to the user and save or edit"
 
        print("\nEnter historical sales information")
        ##name and business type are already known: self.user_name, self.business_type
 
        record_date = self.dates.read_historical_date(input("Record date (YYYY-MM-DD): ").strip())
        food_item = input("Food item: ").strip()
        portions_prepared = self.postive_int.check_positive_integer(input("Portions prepared: ").strip())
        sold_validator = self.sold_portions(portions_prepared) # Instantiate with prepared amount
        portions_sold = sold_validator.check_sold_portions(input("Portions sold: ").strip())
        past_context = input("Optional past context: ").strip()
 
 
        record={"user_name": self.user_name, "business_type": self.business_type, "record_date" : record_date,
                 "food_item": food_item, "portions_prepared": portions_prepared, "portions_sold": portions_sold,
                 "past_context": past_context}  ## "Utilising dictionary"
 
 
        while True:
            self.display_records.record_preview(record) 
 
            choice = input("Enter C to confirm and save, or E to edit: ").strip().lower()
                ## "Prompt users selection enter C to confirm and save, or E to edit"
 
            if choice == "c":
                return record
 
            elif choice == "e":
                self.edit_sales_record(record)
 
            else:
                print("Please enter C or E.")
 
 
    def edit_sales_record(self, record: dict):
        ## To allow users to edits it's records
        print("\nWhich detail would you like to edit?")
        print("1. Record date")
        print("2. Food item")
        print("3. Portions prepared")
        print("4. Portions sold")
        print("5. Past context")
        choice = input("Choose 1 to 5: ").strip()
 
        ## Listed the option 1-5
        if choice == "1":
            record["record_date"] = self.dates.read_historical_date(input("Record date (YYYY-MM-DD): ").strip())
        elif choice == "2":
            record["food_item"] = input("Food item: ").strip()
        elif choice == "3":
            record["portions_prepared"] = self.postive_int.check_positive_integer(input("Portions prepared: ").strip())
            while record["portions_sold"] > record["portions_prepared"]:
                print("Portions sold cannot be greater than portions prepared")
                sold_validator = self.sold_portions(record["portions_prepared"])
                record["portions_sold"] = sold_validator.check_sold_portions(input("Portions sold: ").strip())
        elif choice == "4":
            sold_validator = self.sold_portions(record["portions_prepared"])
            record["portions_sold"] = sold_validator.check_sold_portions(input("Portions sold: ").strip())
        elif choice == "5":
            record["past_context"] = input("Optional past context: ").strip()
        else:
            print("Please choose a number from 1 to 5.")
 
 
    def collect_forecast_infomation(self) -> dict:
        ## "Collect known infomation before preparing food"
        print("\nEnter forecast information")
 
        return {
            "user_name": self.user_name,
            "food_item": input("Forecast food item: ").strip(),
            "target_date": self.dates.read_future_date(input("(YYYY-MM-DD): ").strip()),
            "future_context": input("Optional context (Free Text): ").strip(),
        }
 
 
    def collect_record_search(self):
        ##"Viewing historical records"
        print("\nView historical records")
 
        food_item = input("Food item: ").strip()
 
        ## "Ensure Starting date must be before End date to ensure it's valid"
        start_date = self.dates.read_historical_date(input("Start date (YYYY-MM-DD): ").strip())
        while True:
            end_date = self.dates.read_historical_date(input("End date (YYYY-MM-DD): ").strip())
            if end_date >= start_date:
                return {
                    "user_name": self.user_name,
                    "food_item": food_item,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            print("End date cannot be earlier than the start date")
 


