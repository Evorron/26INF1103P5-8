"""Use the AI Manager to obtain a demand estimate from Groq."""


import ai_manager
from demand_estimator import DemandEstimator
from forecast_estimate import ForecastEstimate

class GroqEstimator(DemandEstimator):
    def estimate(self, payload: dict) -> ForecastEstimate | None:
        reply = ai_manager.generate_forecast(payload)
        if reply.get("status") != "success":
            return None


        try:
            factor = float(reply.get("demand_impact_factor", 1.0))
        except (TypeError, ValueError):
            factor = 1.0

        confidence = str(reply.get("confidence_score", "medium")).strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "medium"

        factors = self._normalise_factors(reply.get("factors_considered"))
        context = str(reply.get("context_assessment", "")).strip()
        weekday_analysis = str(reply.get("weekday_analysis", "")).strip()
        data_limitations = str(reply.get("data_limitations", "")).strip()

        notes = [context or "The recommendation begins with your usual recorded sales."]
        if weekday_analysis:
            notes.append(weekday_analysis)
        if data_limitations:
            notes.append(data_limitations)
        notes.append("This recommendation considered: " + "; ".join(factors) + ".")

        return ForecastEstimate(
            factor = factor, 
            confidence = confidence,
            method = "gemini-ai",
            reasoning = "\n".join(f" {note}" for note in notes),
            factors = factors,
            advice_ending = "to refine future records",
            weekday_analysis = weekday_analysis,
            context_justification = ("Groq received the supplied future context when it selected the demand-impact factor."),
        )

    def _normalise_factors(self, value: object) -> list[str]:
        if isinstance(value, list):
            factors = []
            for item in value:
                text = str(item).strip()
                if text:
                    factors.append(text)

            if factors:
                return factors[:3]

        return ["Groq demand-impact assessment"]

groq_estimator = GroqEstimator()    