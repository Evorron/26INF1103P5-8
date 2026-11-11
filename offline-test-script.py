# test_ai_module.py
from ai_manager import AIManager
from mock_forecast_result import MockForecastProvider


def test_ai_manager_offline_mock():
    """Verifies that AIManager processes mock forecasts without hitting external APIs."""
    sample_payload = {
        "food_item": "Laksa",
        "target_date": "2026-11-20",
        "historical_records": 10,
    }

    # Pass MockForecastProvider directly via Dependency Injection
    ai_manager = AIManager(provider=MockForecastProvider())
    result = ai_manager.generate_forecast(sample_payload)

    print("\n--- Running Offline Mock AI Test ---")
    print("Output Dictionary:", result)

    # Assert schema requirements
    assert result["status"] == "success"
    assert isinstance(result["demand_impact_factor"], float)
    assert result["demand_impact_factor"] == 1.17
    assert result["confidence_score"] in ["high", "medium", "low"]
    assert isinstance(result["factors_considered"], list)

    print("✅ Offline Mock AI Unit Test Passed!")


if __name__ == "__main__":
    test_ai_manager_offline_mock()