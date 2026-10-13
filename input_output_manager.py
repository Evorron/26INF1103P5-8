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