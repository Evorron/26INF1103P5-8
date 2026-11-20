import io
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from unittest.mock import Mock, patch

from data.data_manager import SalesRecord
from input_output.data_validation import (
    business_type,
    date_vaildation,
    positive_integer,
    sold_portions,
)
from input_output.in_out_main import IOManager


class InMemorySalesManager:
    def __init__(self, records=None):
        self.records = list(records or [])

    def get_all(self):
        return list(self.records)

    def add(self, record):
        self.records.append(record)


class TestInputValidation(unittest.TestCase):
    def test_positive_integer_accepts_zero_and_retries_bad_or_negative_values(self):
        with patch("builtins.input", side_effect=["-1", "nope", "0"]):
            result = positive_integer().check_positive_integer("-2")
        self.assertEqual(result, 0)

    def test_sold_portions_enforces_inclusive_zero_to_prepared_range(self):
        with patch("builtins.input", side_effect=["11", "-1", "0"]):
            result = sold_portions(10).check_sold_portions("abc")
        self.assertEqual(result, 0)
        self.assertEqual(sold_portions(10).check_sold_portions("10"), 10)

    def test_iso_date_parser_retries_invalid_input(self):
        with patch("builtins.input", return_value="2025-02-28"):
            parsed = date_vaildation().read_date("2025-02-30")
        self.assertEqual(parsed, date(2025, 2, 28))

    def test_historical_and_forecast_dates_enforce_opposite_sides_of_today(self):
        validator = date_vaildation()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        with patch("builtins.input", return_value=yesterday):
            self.assertEqual(validator.read_historical_date(tomorrow), date.fromisoformat(yesterday))
        with patch("builtins.input", return_value=tomorrow):
            self.assertEqual(validator.read_future_date(yesterday), date.fromisoformat(tomorrow))

    def test_registered_business_type_is_case_insensitive_but_mismatch_is_rejected(self):
        validator = business_type("  Ari   Tan ", {"ari tan": "Hawker"})
        validator.check_business_type("HAWKER")
        with self.assertRaisesRegex(ValueError, "must be 'Hawker'"):
            validator.check_business_type("Cafe")


class TestIOManager(unittest.TestCase):
    def setUp(self):
        self.sales = InMemorySalesManager()
        self.recommendations = Mock()
        self.io = IOManager(self.sales, self.recommendations)

    def test_save_valid_record_converts_and_adds_record(self):
        record = {
            "user_name": "Ari Tan",
            "business_type": "Hawker",
            "record_date": date.today() - timedelta(days=1),
            "food_item": "Laksa",
            "portions_prepared": 12,
            "portions_sold": 9,
            "past_context": "Rainy day",
        }
        output = io.StringIO()
        with redirect_stdout(output):
            self.io.save_sales_record(record)

        self.assertEqual(len(self.sales.records), 1)
        self.assertIsInstance(self.sales.records[0], SalesRecord)
        self.assertIn("successfully saved", output.getvalue())

    def test_invalid_sales_record_is_not_added_and_error_is_reported(self):
        record = {
            "user_name": "Ari Tan",
            "business_type": "Hawker",
            "record_date": date.today() + timedelta(days=1),
            "food_item": "Laksa",
            "portions_prepared": 10,
            "portions_sold": 11,
            "past_context": "",
        }
        output = io.StringIO()
        with redirect_stdout(output):
            self.io.save_sales_record(record)

        self.assertEqual(self.sales.records, [])
        self.assertIn("[Error]", output.getvalue())

    def test_load_sales_records_filters_user_case_and_whitespace(self):
        self.sales.records = [
            SalesRecord(" Ari  Tan ", "Hawker", date(2025, 1, 1), "Laksa", 10, 8),
            SalesRecord("Other User", "Cafe", date(2025, 1, 1), "Cake", 5, 3),
        ]

        records = self.io.load_sales_records("ari tan")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["food_item"], "Laksa")
        self.assertEqual(records[0]["portions_sold"], 8)

    def test_application_displays_welcome_and_exits_cleanly_from_menu(self):
        with patch.object(self.io, "authenticate_user", return_value=("Ari", "Hawker")), \
             patch("input_output.in_out_main.display_welcome") as welcome, \
             patch("input_output.in_out_main.display_all", return_value="7"):
            output = io.StringIO()
            with redirect_stdout(output):
                self.io.run_application()

        welcome.assert_called_once()
        self.assertIn("Goodbye", output.getvalue())

    def test_application_reports_invalid_menu_choice_then_accepts_exit(self):
        with patch.object(self.io, "authenticate_user", return_value=("Ari", "Hawker")), \
             patch("input_output.in_out_main.display_welcome"), \
             patch("input_output.in_out_main.display_all", side_effect=["0", "7"]):
            output = io.StringIO()
            with redirect_stdout(output):
                self.io.run_application()

        self.assertIn("Invalid option", output.getvalue())
        self.assertIn("Goodbye", output.getvalue())


if __name__ == "__main__":
    unittest.main()
