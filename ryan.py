new = input("What is your name? ")
while not new.isalpha():
    print("Please enter a valid name containing only letters!")
    new = input("What is your name? ")
print("Hello, " + new.strip() + "! Welcome!")