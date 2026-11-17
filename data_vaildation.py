
class validation:

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