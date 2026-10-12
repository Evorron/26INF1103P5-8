# test_full_pipeline.py
from datetime import date, timedelta
import forecast_adapter
import logic_manager

def run_integration_test():
    print("========================================")
    print("   Hawker AI Full Pipeline Integration Test")
    print("========================================")

    # 1. Simulate a mock forecast request from the user
    mock_request = {
        "user_name": "Ahmad",
        "food_item": "Chicken Rice",
        "target_date": date.today() + timedelta(days=1),  # Tomorrow
        "future_context": "Heavy rain expected during lunch hours."
    }

    # 2. Simulate mock historical records matching business rules (at least 7 records for high confidence, proper naming)
    mock_historical_records = [
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=7),
            "portions_prepared": 60,
            "portions_sold": 50,
            "past_context": "Normal weather."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=6),
            "portions_prepared": 60,
            "portions_sold": 52,
            "past_context": "Normal weather."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=5),
            "portions_prepared": 65,
            "portions_sold": 55,
            "past_context": "Sunny day."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=4),
            "portions_prepared": 60,
            "portions_sold": 48,
            "past_context": "Normal weather."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=3),
            "portions_prepared": 60,
            "portions_sold": 50,
            "past_context": "Normal weather."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=2),
            "portions_prepared": 70,
            "portions_sold": 60,
            "past_context": "Weekend crowd."
        },
        {
            "user_name": "Ahmad",
            "food_item": "Chicken Rice",
            "record_date": date.today() - timedelta(days=1),
            "portions_prepared": 60,
            "portions_sold": 51,
            "past_context": "Normal weather."
        }
    ]

    print("\n[Step 1] Validating request and historical inputs using logic_manager...")
    try:
        logic_manager.validate_forecast_request(mock_request, mock_historical_records)
        for rec in mock_historical_records:
            logic_manager.validate_sales_record(rec)
        print("-> Validation passed successfully!")
    except Exception as e:
        print(f"-> Validation failed: {e}")
        return

    print("\n[Step 2] Triggering forecast_adapter (which calls your ai_manager)...")
    try:
        # This calls the adapter, which packages data, hits your ai_manager, 
        # calculates portions, and validates safety guardrails.
        final_forecast = forecast_adapter.generate_forecast(mock_request, mock_historical_records)
        
        print("\n[Success] Final Forecast Output Generated:")
        print("-" * 40)
        for key, value in final_forecast.items():
            print(f"  {key}: {value}")
        print("-" * 40)
        print("\n--- Pipeline Integration Test Passed! ---")

    except Exception as e:
        print(f"\n[Pipeline Error] Failed to generate forecast: {e}")

if __name__ == "__main__":
    run_integration_test()