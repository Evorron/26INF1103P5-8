from ai_provider import AbstractAIForecastProvider, GroqForecastProvider
from forecast_result import ForecastResult

class AIManager:
    """
    Controller class responsible for coordinating AI prompt execution,
    provider routing, and returning formatted schema responses.
    """

    def __init__(self, provider: AbstractAIForecastProvider | None = None):
        self._provider: AbstractAIForecastProvider = (
            provider if provider else GroqForecastProvider()
        )

    @property
    def provider(self) -> AbstractAIForecastProvider:
        return self._provider

    def generate_forecast(
        self, evidence_payload: dict, feedback: list | None = None
    ) -> dict:
        result: ForecastResult = self._provider.generate_forecast(
            evidence_payload, feedback
        )
        return result.to_dict()