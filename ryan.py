new_user = input("What is your name? ")
while not new_user.isalpha():
    print("Please enter a valid name containing only letters!")
    new_user = input("What is your name? ")
print("Hello, " + new_user.strip() + "! Welcome!")

