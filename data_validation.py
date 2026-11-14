from datetime import date
from pathlib import Path
import csv
from abc import ABC, abstractmethod

class validation():

    def check_values(self, prompt):                    
        while True:
            try:
                return self.check(input(prompt).strip())
            except ValueError:
                pass


class positive_integer(validation):

    def check_positive_integer(self, input_str):
        while True:
            try:
                value = int(input_str)
                if value > -1:
                    return value
            except ValueError:
                pass
            print("Enter a valid number.")
            input_str = input("Try again: ").strip()

class sold_portions(validation):

    def __init__(self, portions_prepared):
        self.portions_prepared = portions_prepared

    def check_sold_portions(self, input_str):
        while True:
            try:
                value = int(input_str)
                if 0 <= value <= self.portions_prepared:
                    return value
            except ValueError:
                pass
            print(f"Enter a whole number from 0 to {self.portions_prepared}.")
            input_str = input("Try again: ").strip()



class business_type(validation): 


    def __init__(self, user_name, registered_business):

        self.user_name =user_name
        self.registered_business = registered_business


    def check_business_type(self, text):
        ## "To check and match against existing users_name to it's business_type" 
        normalized_name = " ".join(self.user_name.split()).lower()
        registered_type = self.registered_business.get(normalized_name)

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
                                self.registered_business[normalized_name] = registered_type
                            break
                except Exception:
                    pass

        if registered_type and text.lower() != registered_type.lower():
            raise ValueError(f"Business type for {self.user_name} must be '{registered_type}'.")
    ## "Raise an error if input business_type doesn't match the registered record"