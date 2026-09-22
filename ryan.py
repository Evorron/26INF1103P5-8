new_user = input("What is your name? ")
while not new_user.isalpha():
    print("Please enter a valid name containing only letters!")
    new_user = input("What is your name? ")
print("Hello, " + new_user.strip() + "! Welcome!")

quantity = input("How many items would you like to purchase? ")
while not quantity.isdigit() or int(quantity) <= 0:
    print("Please enter a positive whole number!")
    quantity = input("How many items would you like to purchase? ")
print("You have chosen to purchase " + quantity + " items.")