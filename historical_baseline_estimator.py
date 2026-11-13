"""Provide the existing historical fallback when Groq is unavailable"""

from demand_estimator import DemandEstimator
from forecast_estimate import ForecastEstimate

class HistoricalBaselineEstimator(DemandEstimator):
    def estimate(self, payload: dict) -> ForecastEstimate:
        return ForecastEstimate(
            factor=1.0,
            confidence="low",
            method="historical_baseline",
            reasoning="Groq is unavailable, so this forecast uses the middle value of the save sales records without an AI adjustment",
            factors=["Historical median baseline", "Groq unavailable"],
            advice_ending="before relying on future forecasts.",
            warning="Groq is unavailable. This is a low-confidence baseline based only on saved sales",
            evidence_name="baseline",
            error_name="baseline_forecast"
        )

historical_baseline_estimator = HistoricalBaselineEstimator()
            
    