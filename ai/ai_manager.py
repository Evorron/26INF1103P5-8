import os

import requests  # noqa: F401

from ai.ai_provider import AbstractAIForecastProvider, GroqForecastProvider
from logic.forecast_result import ForecastResult

DEFAULT_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

# AI Manager class that manages the AI forecast provider and generates forecasts
class AIManager:

    # Accepts any subclass of AbstractAIForecastProvider
    # Default provider set to GroqForecastProvider if none is provided
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

        # Converts ForecastResult object to dictionary
        return result.to_dict()

_default_manager = AIManager()

def generate_forecast(
    evidence_payload: dict, feedback: list | None = None
) -> dict:
    return _default_manager.generate_forecast(evidence_payload, feedback)
