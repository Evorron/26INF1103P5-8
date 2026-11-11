from ai_provider import AbstractAIForecastProvider
from forecast_result import ForecastResult

class MockForecastProvider(AbstractAIForecastProvider):

    def generate_forecast (
        self, evidence_payload: dict, feedback: list | None = None
    ) -> ForecastResult:
        food_item = evidence_payload.get("food_item", "Item")

        return ForecastResult (
            demand_impact_factor=1.17,
            context_assessment=f"Mocked AI forecast for {food_item} for offline automated testing.",
            confidence_score="high",
            factors_considered=["Historical Sales", "Mock Context Tag"],
            weekday_analysis="Steady weekend growth detected.",
            data_limitations="None (This is a mock data to test!)).",
            status="success", )