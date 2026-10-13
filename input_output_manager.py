import csv
from datetime import date
from pathlib import Path
import shutil
import textwrap
import data_manager


def display_welcome():
    ##"Display opening program title"
    print("--------------------------------")
    print("Welcome to Hawker AI!")
    print("An enhance tools for food preparation forecasting.\n")


def display_all():
    ##"Display main menu"
    print("------------MENU-----------------")
    print("1. Add a historical sales record")
    print("2. Generate a Gemini forecast")
    print("3. List my recorded food items")
    print("4. View my records by food item and date range")
    print("5. Exit")

    return input("Choose an option: ").strip()  ##"To prevent breaking due to typos"


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