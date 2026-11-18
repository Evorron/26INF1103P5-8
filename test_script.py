import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import forecast_coordinator
import input_output_manager as io_manager
from data_manager import SalesRecord, SalesRecordManager
from database_storage import DatabaseStorage
from setup_db import DatabaseSchema


class TestActualApplicationOutputOffline(unittest.TestCase):

    @patch('ai_manager.requests.post')
    def test_print_actual_forecast_report(self, mock_post):
        """Run the actual forecast pipeline offline and print the real visual report output."""
        
        # 1. Create a temporary environment / CSV path so it runs safely offline
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            db_path = temp_path / "test_hawker.db"

            # Create an isolated SQLite schema and sales-record manager.
            DatabaseSchema(db_path).initialize()
            sales_storage = DatabaseStorage(
                db_path=db_path,
                table_name="sales_records",
                record_type=SalesRecord,
            )
            sales_manager = SalesRecordManager(sales_storage)
            sales_manager.load()

            # 2. Put some fake historical sales records so the logic rules pass
            past_date = date.today() - timedelta(days=5)
            for i in range(5):
                sales_manager.add(
                    SalesRecord(
                        user_name="John Doe",
                        business_type="Hawker",
                        record_date=past_date + timedelta(days=i),
                        food_item="Ice Cream",
                        portions_prepared=100,
                        portions_sold=80,
                        past_context="Normal rainy day",
                    )
                )

            # The forecasting logic expects dictionaries with record_date as a date.
            all_records = []
            for record in sales_manager.get_all():
                record_data = record.to_dict()
                record_data["record_date"] = record.record_date
                all_records.append(record_data)

            # 3. Define the hardcoded sample AI response matching your JSON schema
            hardcoded_ai_response = {
                "demand_impact_factor": 1.15,
                "context_assessment": "Expected slightly higher demand due to nearby community event.",
                "confidence_score": "medium",
                "factors_considered": ["Community event", "Past sales trend"],
                "weekday_analysis": "Target weekday shows stable historical demand patterns.",
                "data_limitations": "Limited past records available."
            }

            # 4. Configure the mock post request to return HTTP 200 with the hardcoded response
            mock_response = mock_post.return_value
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(hardcoded_ai_response)
                        }
                    }
                ]
            }

            # 5. Construct a real forecast request payload
            request = {
                "user_name": "John Doe",
                "food_item": "Ice Cream",
                "target_date": date.today() + timedelta(days=1),
                "future_context": "Community event nearby"
            }
            
            # This triggers the actual production pipeline (adapter -> logic -> ai_manager mock)
            forecast_response = forecast_coordinator.generate_logged_forecast(request, all_records, log_path=temp_path / "forecast_activity.jsonl")

            # 7. Print the exact visual report using your actual IO display function
            io_manager.show_forecast(forecast_response)

            print("=" * 60)

            # Assertions to ensure it successfully processed everything
            self.assertEqual(forecast_response["forecast_method"], "gemini_ai")
            self.assertGreater(forecast_response["suggested_portions"], 0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestActualApplicationOutputOffline)
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)