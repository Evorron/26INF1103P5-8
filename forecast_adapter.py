"""Bridge the original demand-factor AI manager to the app forecast contract.

This module deliberately leaves ``ai_manager.py`` unchanged. That module
returns an AI demand-impact factor, while the rest of the app requires one
complete, validated preparation forecast. The adapter keeps that translation
isolated instead of mixing it into AI access, business rules, or the UI.
"""

from math import ceil, floor, isfinite
from statistics import median

import ai_manager
import logic_manager


# Public integration point

def generate_forecast(request: dict, historical_records: list[dict]) -> dict:
    """Ask the unchanged AI manager for a factor and create a validated forecast."""
    evidence_payload = logic_manager.build_ai_payload(request, historical_records)
    ai_response = ai_manager.generate_forecast(evidence_payload)
    if ai_response.get("status") != "success":
        raise RuntimeError(
            "Gemini is unavailable or has not been configured. "
            "No forecast was created. Set GEMINI_API_KEY and try again."
        )

    factor = valid_demand_factor(ai_response)
    suggested_portions = quantity_from_factor(factor, request, historical_records)
    evidence_metrics = logic_manager.calculate_evidence_metrics(
        historical_records, request["target_date"]
    )
    confidence = normalise_confidence(ai_response, len(historical_records))
    context_assessment = str(ai_response.get("context_assessment", "")).strip()
    factors = normalise_factors(ai_response.get("factors_considered"))
    has_future_context = bool(request["future_context"].strip())

    response = {
        "suggested_portions": suggested_portions,
        "confidence": confidence,
        "reasoning": (
            f"Gemini supplied a demand-impact factor of {factor:.2f}. "
            f"{context_assessment or 'The quantity applies that factor to historical sales.'}"
        ),
        "business_advice": (
            f"Prepare {suggested_portions} portions, then compare sales and leftovers "
            "after service to refine future records."
        ),
        "factors_considered": factors,
        "evidence": [
            {
                "metric": "record_count",
                "value": evidence_metrics["record_count"],
                "claim": f"The recommendation uses {int(evidence_metrics['record_count'])} saved sales records.",
            },
            {
                "metric": "historical_maximum_sold",
                "value": evidence_metrics["historical_maximum_sold"],
                "claim": (
                    "The highest recorded sales value is "
                    f"{int(evidence_metrics['historical_maximum_sold'])} portions."
                ),
            },
        ],
        "warning": (
            "Limited history is available; record more sales before relying on a higher-confidence forecast."
            if confidence == "low" and len(historical_records) < logic_manager.LOW_CONFIDENCE_RECORD_COUNT
            else None
        ),
        "uses_future_context": has_future_context,
        "exception_justification": (
            "Gemini received the supplied future context when it selected the demand-impact factor."
            if has_future_context
            else None
        ),
        "uses_historical_shift": False,
        "historical_shift_justification": None,
    }
    violations = logic_manager.validate_ai_response(response, request, historical_records)
    if violations:
        raise RuntimeError("The forecast could not meet the safety rules: " + "; ".join(violations))
    return response


# AI response normalisation and quantity calculation

def valid_demand_factor(ai_response: dict) -> float:
    """Validate the factor supplied by the unchanged AI manager."""
    try:
        factor = float(ai_response["demand_impact_factor"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Gemini returned no usable demand-impact factor.") from error
    if not isfinite(factor) or factor <= 0:
        raise RuntimeError("Gemini returned an invalid demand-impact factor.")
    return min(factor, logic_manager.MAXIMUM_MULTIPLIER)


def quantity_from_factor(factor: float, request: dict, historical_records: list[dict]) -> int:
    """Apply Gemini's factor to median demand, while retaining local guardrails."""
    sales = [record["portions_sold"] for record in historical_records]
    historical_maximum = max(sales)
    if historical_maximum == 0:
        raise RuntimeError("A positive forecast cannot be produced because all saved sales are zero.")

    quantity = max(1, round(median(sales) * factor))
    maximum_allowed = floor(historical_maximum * logic_manager.MAXIMUM_MULTIPLIER)
    quantity = min(quantity, maximum_allowed)
    same_weekday_sales = [
        record["portions_sold"]
        for record in historical_records
        if record["record_date"].weekday() == request["target_date"].weekday()
    ]
    if len(same_weekday_sales) >= logic_manager.REQUIRED_SAME_WEEKDAY_RECORDS:
        weekday_average = sum(same_weekday_sales[-logic_manager.REQUIRED_SAME_WEEKDAY_RECORDS:]) / 4
        if weekday_average > 0 and not request["future_context"].strip():
            quantity = max(ceil(weekday_average * 0.5), min(quantity, floor(weekday_average * 1.5)))
    return quantity


def normalise_confidence(ai_response: dict, record_count: int) -> str:
    """Keep Gemini's label when valid, enforcing low confidence for short history."""
    if record_count < logic_manager.LOW_CONFIDENCE_RECORD_COUNT:
        return "low"
    confidence = str(ai_response.get("confidence_score", "medium")).lower().strip()
    return confidence if confidence in {"high", "medium", "low"} else "medium"


def normalise_factors(value: object) -> list[str]:
    """Return concise non-empty factors suitable for the display layer."""
    if isinstance(value, list):
        factors = [str(item).strip() for item in value if str(item).strip()]
        if factors:
            return factors[:3]
    return ["Gemini demand-impact assessment"]
