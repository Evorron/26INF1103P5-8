"""Bridge the original demand-factor AI manager to the app forecast contract.

This module deliberately leaves ``ai_manager.py`` unchanged. That module
returns an AI demand-impact factor, while the rest of the app requires one
complete, validated preparation forecast. The adapter keeps that translation
isolated instead of mixing it into AI access, business rules, or the UI.
"""

# This file turns Gemini's demand factor into a full preparation forecast.
# It calculates a suggested quantity from past sales, adds display details,
# and sends the result through the project safety checks.
#
# Program flow:
# 1. generate_logged_forecast receives data from main.py.
# 2. logic_manager filters and validates the relevant sales records.
# 3. ai_manager returns a demand-impact factor from Gemini (or a fallback).
# 4. This adapter converts the factor into a portion quantity and validates it.
# 5. activity_logger writes a safe audit entry without storing API credentials.

from math import ceil, floor, isfinite
from pathlib import Path
from statistics import median
from uuid import uuid4

import activity_logger
import ai_manager
import logic_manager


# Public application integration point

def generate_logged_forecast(
    request: dict, all_records: list[dict], log_path: Path | None = None
) -> dict:
    """Validate, log, and generate one forecast for the command-line application.

    ``generate_forecast`` below is the original adapter implementation.  It is
    retained as the focused AI-to-forecast conversion step; this new wrapper
    connects it to the logic manager and activity logger.
    """
    # Work only with the requested user's records for the requested food item;
    # unrelated sales must never influence this forecast.
    historical_records = logic_manager.records_for_forecast(request, all_records)
    evidence_payload = logic_manager.build_ai_payload(request, historical_records)
    # The ID links the request and response entries in the JSON-lines log.
    activity_id = str(uuid4())
    resolved_log_path = log_path or Path(__file__).resolve().parent / "data" / "forecast_activity.jsonl"
    activity_logger.initialise_log(resolved_log_path)
    activity_logger.log_request(
        resolved_log_path,
        activity_id,
        ai_manager.DEFAULT_MODEL,
        evidence_payload,
        validation_feedback=None,
        provider_attempt=1,
    )
    try:
        # The original adapter builds the user-facing response and asks the
        # logic manager to verify all guardrails before returning it.
        response = generate_forecast(request, historical_records)
    except (RuntimeError, ValueError, KeyError, TypeError) as error:
        activity_logger.log_error(
            resolved_log_path,
            activity_id,
            ai_manager.DEFAULT_MODEL,
            str(error),
            status=None,
            failure_type="forecast_validation",
        )
        raise

    # Logging after validation ensures the recorded result is exactly what the
    # user was shown, rather than an unvalidated intermediate AI response.
    activity_logger.log_response(
        resolved_log_path,
        activity_id,
        ai_manager.DEFAULT_MODEL,
        interaction_id=None,
        response=response,
    )
    return response


# Original adapter implementation (called by generate_logged_forecast)

def generate_forecast(request: dict, historical_records: list[dict]) -> dict:
    """Ask the unchanged AI manager for a factor and create a validated forecast."""
    # Main flow: prepare data, get Gemini's factor, build a forecast, then validate it.
    evidence_payload = logic_manager.build_ai_payload(request, historical_records)
    ai_response = ai_manager.generate_forecast(evidence_payload)
    if ai_response.get("status") != "success":
        # An unavailable API should not crash the app.  Use a conservative,
        # clearly labelled local baseline instead of pretending Gemini replied.
        return baseline_fallback_forecast(request, historical_records)

    factor = valid_demand_factor(ai_response)
    suggested_portions = quantity_from_factor(factor, request, historical_records)
    evidence_metrics = logic_manager.calculate_evidence_metrics(
        historical_records, request["target_date"]
    )
    confidence = normalise_confidence(ai_response, len(historical_records))
    context_assessment = str(ai_response.get("context_assessment", "")).strip()
    factors = normalise_factors(ai_response.get("factors_considered"))
    has_future_context = bool(request["future_context"].strip())

    # This response shape is shared with show_forecast in the IO layer and
    # validate_ai_response in the logic layer.  Extra fields record why an
    # exception to the usual weekday guardrail may be permitted.
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


def baseline_fallback_forecast(request: dict, historical_records: list[dict]) -> dict:
    """Return a low-confidence median-sales forecast when Gemini is unavailable."""
    # This local fallback makes a useful forecast without sending another API
    # request.  It deliberately ignores future context because Gemini was not
    # available to assess the likely impact of that context.
    baseline_request = {**request, "future_context": ""}
    suggested_portions = quantity_from_factor(1.0, baseline_request, historical_records)
    evidence_metrics = logic_manager.calculate_evidence_metrics(
        historical_records, request["target_date"]
    )
    response = {
        "suggested_portions": suggested_portions,
        "confidence": "low",
        "reasoning": (
            "Gemini is unavailable, so this forecast uses the middle value "
            "of the saved sales records without an AI adjustment."
        ),
        "business_advice": (
            f"Prepare {suggested_portions} portions, then compare sales and leftovers "
            "after service before relying on future forecasts."
        ),
        "factors_considered": ["Historical median baseline", "Gemini unavailable"],
        "evidence": [
            {
                "metric": "record_count",
                "value": evidence_metrics["record_count"],
                "claim": f"The baseline uses {int(evidence_metrics['record_count'])} saved sales records.",
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
            "Gemini is unavailable. This is a low-confidence baseline based only on saved sales."
        ),
        "uses_future_context": False,
        "exception_justification": None,
        "uses_historical_shift": False,
        "historical_shift_justification": None,
    }
    violations = logic_manager.validate_ai_response(response, request, historical_records)
    if violations:
        raise RuntimeError("The baseline forecast could not meet the safety rules: " + "; ".join(violations))
    return response


# AI response normalisation and quantity calculation

def valid_demand_factor(ai_response: dict) -> float:
    """Validate the factor supplied by the unchanged AI manager."""
    # Gemini's factor must be a real positive number before it affects the quantity.
    try:
        factor = float(ai_response["demand_impact_factor"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Gemini returned no usable demand-impact factor.") from error
    if not isfinite(factor) or factor <= 0:
        raise RuntimeError("Gemini returned an invalid demand-impact factor.")
    return min(factor, logic_manager.MAXIMUM_MULTIPLIER)


def quantity_from_factor(factor: float, request: dict, historical_records: list[dict]) -> int:
    """Apply Gemini's factor to median demand, while retaining local guardrails."""
    # Use typical past sales as the baseline, then keep the quantity within safe limits.
    sales = [record["portions_sold"] for record in historical_records]
    historical_maximum = max(sales)
    if historical_maximum == 0:
        raise RuntimeError("A positive forecast cannot be produced because all saved sales are zero.")

    # Median sales are less affected by an unusually busy or quiet single day
    # than a simple average.  Gemini's factor is applied to that typical value.
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
            # Without a supplied reason for a change, keep the quantity within
            # ±50% of the recent target-weekday average.
            quantity = max(ceil(weekday_average * 0.5), min(quantity, floor(weekday_average * 1.5)))
    return quantity


def normalise_confidence(ai_response: dict, record_count: int) -> str:
    """Keep Gemini's label when valid, enforcing low confidence for short history."""
    # Limited sales history always means the forecast should be labelled low confidence.
    if record_count < logic_manager.LOW_CONFIDENCE_RECORD_COUNT:
        return "low"
    confidence = str(ai_response.get("confidence_score", "medium")).lower().strip()
    return confidence if confidence in {"high", "medium", "low"} else "medium"


def normalise_factors(value: object) -> list[str]:
    """Return concise non-empty factors suitable for the display layer."""
    # Keep the displayed reasons short and provide a fallback when Gemini gives none.
    if isinstance(value, list):
        factors = [str(item).strip() for item in value if str(item).strip()]
        if factors:
            return factors[:3]
    return ["Gemini demand-impact assessment"]
