from ai_manager import AIManager
from ai_provider import GroqForecastProvider
from dotenv import load_dotenv
load_dotenv(override=True)                  # load environment variables



def test_live_groq_forecast():
    """Runs a live integration test against the Groq API."""
    print("--- Running Live Groq API Forecast Test ---")

    # Instantiate AIManager without passing a mock provider (defaults to GroqForecastProvider)
    ai_manager = AIManager(provider=GroqForecastProvider())

    sample_evidence = {
        "food_item": "Prata",
        "target_date": "2026-11-20",
        "historical_summary": {
            "total_records": 12,
            "avg_sold": 77,
            "recent_trend": "stable",
        },
        "future_context": "None"
    }

    # Execute live forecast
    result = ai_manager.generate_forecast(sample_evidence)

    print("\nLive Output Response:")
    print(result)

    # Verify response integrity
    print("\n--- Verifying Results ---")
    if result.get("status") == "success":
        print("✅ Live Groq API call succeeded!")
        print(f"• Demand Impact Factor: {result.get('demand_impact_factor')}")
        print(f"• Confidence Score: {result.get('confidence_score')}")
        print(f"• Context Assessment: {result.get('context_assessment')}")
    else:
        print("⚠️ API Call returned fallback mode.")
        print(f"• Context Assessment: {result.get('context_assessment')}")


if __name__ == "__main__":
    test_live_groq_forecast()