from demand_factor_strategy import DemandFactorStrategy
from demand_factor_result import DemandFactorResult

"""
Overall responsibility: Supplies neutral historical-fallback settings when selected.

Main components:
- BaselineFactorStrategy — the fallback implementation.
- get_factor_result() — returns factor 1.0, low confidence, explanation, and warning.
- baseline_factor_strategy — the default instance.

It supplies the fallback factor; ForecastRules calculates the preparation quantity afterward.
"""
class BaselineFactorStrategy(DemandFactorStrategy):
    def get_factor_result(self, payload: dict) -> DemandFactorResult:
        return DemandFactorResult(
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

baseline_factor_strategy = BaselineFactorStrategy()
            
    
