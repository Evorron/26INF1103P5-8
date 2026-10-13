"""Write privacy-conscious local audit events for forecasting activity.

This module records what happened during a forecast—request, completed result,
or failure—using newline-delimited JSON.  It is deliberately separate from the
AI manager so API access and audit recording do not become mixed together.
Credentials are never written to the log; full AI evidence is included only
when the ``AI_LOG_FULL_CONTENT`` environment variable is explicitly enabled.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


# Public functions are grouped by the stage of a forecasting request they log.

def initialise_log(log_path: Path) -> None:
    """Ensure the requested log folder and empty JSON-lines file exist.

    This is safe to call for every forecast because existing files are retained.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)


def log_request(
    log_path: Path,
    activity_id: str,
    model: str,
    evidence_payload: dict,
) -> None:
    """Record safe request metadata before the adapter calls the AI manager.

    The event records the requested item, date, amount of history, and whether
    future context exists.  API keys and other credentials are never recorded.
    """
    request = evidence_payload["forecast_request"]
    details = {
        "activity_id": activity_id,
        "provider": "Gemini",
        "model": model,
        "user_name": request["user_name"],
        "food_item": request["food_item"],
        "target_date": request["target_date"],
        "historical_record_count": len(evidence_payload["historical_records"]),
        "future_context_provided": bool(request["future_context"]),
    }
    if os.getenv("AI_LOG_FULL_CONTENT", "false").lower() == "true":
        details["full_evidence_payload"] = evidence_payload
    write_event(log_path, "gemini_request_started", details)


def log_response(
    log_path: Path,
    activity_id: str,
    model: str,
    response: dict,
) -> None:
    """Record the final forecast only after the adapter has validated it.

    The neutral event name is also correct for a locally generated fallback,
    not only for a successful AI response.
    """
    write_event(
        log_path,
        "forecast_generated",
        {
            "activity_id": activity_id,
            "provider": "Gemini",
            "model": model,
            "forecast_response": response,
        },
    )


def log_retry(
    log_path: Path,
    activity_id: str,
    model: str,
    attempt: int,
    delay_seconds: float,
    status: int | None,
    failure_type: str,
) -> None:
    """Record a temporary failure and the planned delay before a retry.

    This helper is reserved for a future retry strategy; it does not itself
    wait or repeat an AI request.
    """
    write_event(
        log_path,
        "gemini_retry_scheduled",
        {
            "activity_id": activity_id,
            "provider": "Gemini",
            "model": model,
            "attempt": attempt,
            "delay_seconds": round(delay_seconds, 2),
            "http_status": status,
            "failure_type": failure_type,
        },
    )


def log_provider_switch(
    log_path: Path,
    from_model: str,
    to_model: str,
    status: int | None,
    failure_type: str,
) -> None:
    """Record a switch from one AI model to another after a failure.

    This helper supports a future multi-model strategy; it does not select or
    call the replacement model itself.
    """
    write_event(
        log_path,
        "gemini_model_fallback",
        {
            "provider": "Gemini",
            "from_model": from_model,
            "to_model": to_model,
            "http_status": status,
            "failure_type": failure_type,
        },
    )


# Optional validation, failure, and quota events for future AI-service features.

def log_validation_rejection(log_path: Path, model: str, attempt: int, violations: list[str]) -> None:
    """Record why an AI response was rejected before a future correction attempt."""
    write_event(
        log_path,
        "gemini_response_rejected",
        {"provider": "Gemini", "model": model, "attempt": attempt, "violations": violations},
    )


def log_error(
    log_path: Path,
    activity_id: str,
    model: str,
    message: str,
    status: int | None,
    failure_type: str,
) -> None:
    """Record a safely printable configuration, network, API, or validation failure."""
    write_event(
        log_path,
        "gemini_request_failed",
        {
            "activity_id": activity_id,
            "provider": "Gemini",
            "model": model,
            "http_status": status,
            "failure_type": failure_type,
            "error": message,
        },
    )


def log_final_failure(log_path: Path, models: list[str], attempts: int, reason: str) -> None:
    """Record that all planned retries and model fallbacks were exhausted."""
    write_event(
        log_path,
        "gemini_forecast_unavailable",
        {
            "provider": "Gemini",
            "models_tried": models,
            "attempts_per_model": attempts,
            "reason": reason,
        },
    )


def log_quota_wait(log_path: Path, activity_id: str, model: str, wait_seconds: float) -> None:
    """Record a future deliberate wait used to avoid exceeding an AI rate limit."""
    write_event(
        log_path,
        "gemini_rate_limit_wait",
        {
            "activity_id": activity_id,
            "provider": "Gemini",
            "model": model,
            "wait_seconds": round(wait_seconds, 2),
        },
    )


def log_quota_block(log_path: Path, model: str, message: str) -> None:
    """Record when a future quota guard blocks a request before it is sent."""
    write_event(
        log_path,
        "gemini_quota_guard_blocked",
        {"provider": "Gemini", "model": model, "message": message},
    )


# Private-style shared writer used by every public logging helper above.

def write_event(log_path: Path, event: str, details: dict) -> None:
    """Append one timestamped JSON event to the log without overwriting prior events.

    Singapore time is used so event times match the project's local operating
    context.  JSON Lines stores one complete event per line for easy inspection
    and later analysis.
    """
    singapore_timezone = timezone(timedelta(hours=8))
    entry = {
        "timestamp_sgt": datetime.now(singapore_timezone).isoformat(),
        "event": event,
        **details,
    }
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
