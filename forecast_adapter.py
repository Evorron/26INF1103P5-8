"""Translate an AI demand factor into a complete, validated forecast.

The AI manager returns an estimate of how demand may change.  This module
combines that factor with saved sales history to calculate a portion quantity,
create the response expected by the display layer, and ask the logic manager
to verify every safety rule before returning it.  It also records safe request
and outcome details through the activity logger.

This separation keeps AI communication, business rules, CSV handling, and
screen output in their respective modules.
"""

from math import ceil, floor, isfinite
from pathlib import Path
from statistics import median
from uuid import uuid4

import activity_logger
import ai_manager
import logic_manager


# Public integration point: this is the function other modules should call.

def generate_logged_forecast(
    request: dict, all_records: list[dict], log_path: Path | None = None
) -> dict:
    """Produce one safe forecast and record its request and final outcome.

    It selects only the requested item's history, creates an evidence payload,
    records a request event, builds a validated response, then records the
    exact response returned to the user.  Errors are logged before being passed
    to the application coordinator for user-friendly handling.
    """
    # Work only with the requested user's records for the requested food item;
    # unrelated sales must never influence this forecast.
    historical_records = logic_manager.records_for_forecast(request, all_records)
    evidence_payload = logic_manager.build_ai_payload(request, historical_records)
    # The ID links the request, response, and any error entries in one log flow.
    activity_id = str(uuid4())
    resolved_log_path = log_path or Path(__file__).resolve().parent / "data" / "forecast_activity.jsonl"
    activity_logger.initialise_log(resolved_log_path)
    activity_logger.log_request(
        resolved_log_path,
        activity_id,
        ai_manager.DEFAULT_MODEL,
        evidence_payload,
    )
    try:
        # Build the display-ready response and verify it before returning it.
        response = build_validated_forecast(
            request,
            historical_records,
            evidence_payload,
        )
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

    # Log after validation so the recorded result exactly matches what was shown.
    activity_logger.log_response(
        resolved_log_path,
        activity_id,
        ai_manager.DEFAULT_MODEL,
        response,
    )
    return response


# Internal conversion step used by ``generate_logged_forecast``.

def build_validated_forecast(
    request: dict,
    historical_records: list[dict],
    evidence_payload: dict | None = None,
) -> dict:
    """Convert the AI response into a guarded, display-ready forecast.

    A provided payload is reused to avoid rebuilding identical evidence.  When
    the AI service is unavailable, the function returns a clearly labelled
    median-sales fallback instead of presenting it as an AI response.
    """
    if evidence_payload is None:
        evidence_payload = logic_manager.build_ai_payload(
            request,
            historical_records,
        )

    ai_response = ai_manager.generate_forecast(evidence_payload)
    if ai_response.get("status") != "success":
        # An unavailable API should not crash the app.  Use a conservative,
        # clearly labelled local baseline instead of pretending Groq replied.
        return baseline_fallback_forecast(request, historical_records)

    factor = valid_demand_factor(ai_response)
    suggested_portions = quantity_from_factor(factor, request, historical_records)
    evidence_metrics = logic_manager.calculate_evidence_metrics(
        historical_records, request["target_date"]
    )
    confidence = normalise_confidence(
        ai_response,
        len(historical_records),
    )

    context_assessment = str(
        ai_response.get("context_assessment", "")
    ).strip()

    weekday_analysis = str(
        ai_response.get("weekday_analysis", "")
    ).strip()

    data_limitations = str(
        ai_response.get("data_limitations", "")
    ).strip()

    factors = normalise_factors(
        ai_response.get("factors_considered")
    )

    reasoning_parts = [
        context_assessment
        or "The recommendation begins with your usual recorded sales."
    ]

    if weekday_analysis:
        reasoning_parts.append(weekday_analysis)

    if data_limitations:
        reasoning_parts.append(data_limitations)

    if factors:
        reasoning_parts.append(
            "This recommendation considered: "
            + "; ".join(factors)
            + "."
        )

    reasoning = "\n".join(
        f"• {item}"
        for item in reasoning_parts
    )

    has_future_context = bool(
        request["future_context"].strip()
    )

    # This response shape is shared with show_forecast in the IO layer and
    # validate_ai_response in the logic layer.  Extra fields record why an
    # exception to the usual weekday guardrail may be permitted.
    response = {
        "forecast_method": "gemini_ai",
        "suggested_portions": suggested_portions,
        "recorded_sales": [record["portions_sold"] for record in historical_records],
        "confidence": confidence,
        "reasoning": reasoning,
        "business_advice": (
            f"Prepare {suggested_portions} portions, then compare sales and leftovers "
            "after service to refine future records."
        ),
        "factors_considered": factors,
        # These explanatory details are displayed to the user, but never alter
        # the quantity; logic_manager remains the numerical source of truth.
        "weekday_analysis": weekday_analysis,
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
            "Groq received the supplied future context when it selected the demand-impact factor."
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
    """Return a low-confidence median-sales forecast when the AI is unavailable.

    Future context is deliberately ignored because no AI assessment was
    received.  The normal logic-manager validation still applies to the result.
    """
    # This local fallback makes a useful forecast without sending another API
    # request.  It deliberately ignores future context because Groq was not
    # available to assess the likely impact of that context.
    baseline_request = {**request, "future_context": ""}
    suggested_portions = quantity_from_factor(1.0, baseline_request, historical_records)
    evidence_metrics = logic_manager.calculate_evidence_metrics(
        historical_records, request["target_date"]
    )
    response = {
        "forecast_method": "historical_baseline",
        "suggested_portions": suggested_portions,
        "recorded_sales": [record["portions_sold"] for record in historical_records],
        "confidence": "low",
        "reasoning": (
            "Groq is unavailable, so this forecast uses the middle value "
            "of the saved sales records without an AI adjustment."
        ),
        "business_advice": (
            f"Prepare {suggested_portions} portions, then compare sales and leftovers "
            "after service before relying on future forecasts."
        ),
        "factors_considered": ["Historical median baseline", "Groq unavailable"],
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
            "Groq is unavailable. This is a low-confidence baseline based only on saved sales."
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


# Helper functions for checking AI values and calculating a safe quantity.

def valid_demand_factor(ai_response: dict) -> float:
    """Return a valid positive AI demand factor, capped by the project maximum."""
    # A malformed or extreme AI value must not influence a preparation quantity.
    try:
        factor = float(ai_response.get("demand_impact_factor", 1.0))
    except (TypeError, ValueError):
        return 1.0

    return max(
        logic_manager.MINIMUM_DEMAND_FACTOR,
        min(factor, logic_manager.MAXIMUM_MULTIPLIER),
    )

def quantity_from_factor(factor: float, request: dict, historical_records: list[dict]) -> int:
    """Apply a demand factor to typical sales while enforcing local quantity limits.

    Median sales provide the baseline because one unusually busy or quiet day
    has less influence than it would in a simple average.  A maximum based on
    observed sales and, when available, a target-weekday range prevent extreme
    recommendations.
    """
    sales = [record["portions_sold"] for record in historical_records]
    typical_sales = median(sales)
    historical_maximum = max(sales)
    if historical_maximum == 0:
        raise RuntimeError("A positive forecast cannot be produced because all saved sales are zero.")

    # factor is applied only after a robust historical baseline exists.
    quantity = max(1, round(typical_sales * factor))
    minimum_allowed = max(1,ceil(typical_sales * logic_manager.MINIMUM_RECOMMENDATION_RATIO),)
    maximum_allowed = floor(historical_maximum* logic_manager.MAXIMUM_MULTIPLIER)
    quantity = max(minimum_allowed,min(quantity, maximum_allowed),)
    same_weekday_sales = [record["portions_sold"] for record in historical_records if record["record_date"].weekday() == request["target_date"].weekday()]
    if len(same_weekday_sales) >= logic_manager.REQUIRED_SAME_WEEKDAY_RECORDS:
        weekday_average = sum(same_weekday_sales[-logic_manager.REQUIRED_SAME_WEEKDAY_RECORDS:]) / 4
        if weekday_average > 0 and not request["future_context"].strip():
            # Without a supplied reason for a change, keep the quantity within
            # ±50% of the recent target-weekday average.
            weekday_minimum = max(1,ceil(weekday_average* logic_manager.MINIMUM_RECOMMENDATION_RATIO),)
            weekday_maximum = floor( weekday_average* logic_manager.MAXIMUM_MULTIPLIER)
            quantity = max(weekday_minimum,min(quantity, weekday_maximum),)
    return quantity


def normalise_confidence(ai_response: dict, record_count: int) -> str:
    """Return a recognised confidence label, forcing low confidence for short history."""
    # Limited history is uncertain even when the AI gives a more optimistic label.
    if record_count < logic_manager.LOW_CONFIDENCE_RECORD_COUNT:
        return "low"
    confidence = str(ai_response.get("confidence_score", "medium")).lower().strip()
    return confidence if confidence in {"high", "medium", "low"} else "medium"


def normalise_factors(value: object) -> list[str]:
    """Return up to three readable factors for display, with a fallback message."""
    # Keep display content concise and avoid an empty factors section.
    if isinstance(value, list):
        factors = [str(item).strip() for item in value if str(item).strip()]
        if factors:
            return factors[:3]
    return ["Groq demand-impact assessment"]
