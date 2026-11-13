"""The result shared by the Groq and historical estimators"""

from dataclasses import dataclass

@dataclass
class ForecastEstimate:
    factor: float
    confidence: str
    method: str
    reasoning: str
    factors: list[str]
    advice_ending: str
    warning: str | None = None
    weekday_analysis: str | None = None
    context_justification: str | None = None
    evidence_name: str = "recommendation"
    error_name: str = "forecast"