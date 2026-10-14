import unittest
from unittest.mock import patch
import json
import sys
from datetime import date, timedelta
from pathlib import Path
import tempfile
import data_manager
import forecast_adapter
import input_output_manager as io_manager


class TestActualApplicationOutputOffline(unittest.TestCase):

    @patch('ai_manager.requests.post')
    def test_print_actual_forecast_report(self, mock_post):
        """Run the actual forecast pipeline offline and print the real visual report output."""
        
        # 1. Create a temporary environment / CSV path so it runs safely offline
        with tempfile.TemporaryDirectory() as temp_dir:
            sales_file = Path(temp_dir) / "sales_records.csv"

            # 2. Put some fake historical sales records so the logic rules pass
            past_date = date.today() - timedelta(days=5)
            for i in range(5):
                sample_record = {
                    "user_name": "Nisha Jain",
                    "business_type": "Hawker",
                    "record_date": past_date + timedelta(days=i),
                    "food_item": "Roti Prata",
                    "portions_prepared": 100,
                    "portions_sold": 80,
                    "past_context": "Normal rainy day"
                }
                data_manager.add_record(sales_file, sample_record)

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
                "user_name": "Nisha Jain",
                "food_item": "Roti Prata",
                "target_date": date.today() + timedelta(days=1),
                "future_context": "Community event nearby"
            }

            # 6. Load the records and invoke the actual adapter function
            all_records = data_manager.load_records(sales_file)
            
            # This triggers the actual production pipeline (adapter -> logic -> ai_manager mock)
            forecast_response = forecast_adapter.generate_logged_forecast(request, all_records)

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