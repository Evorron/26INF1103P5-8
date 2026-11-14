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