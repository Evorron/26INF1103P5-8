"""Privacy-conscious local logging for Gemini forecasting activity.

Logging is separated from AI access so audit events can be recorded consistently
without exposing credentials or adding console-output concerns to other modules.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path


# Log setup and request lifecycle events

def initialise_log(log_path: Path) -> None:
    """Create the log directory and an empty log file when the app starts."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)


def log_request(
    log_path: Path,
    activity_id: str,
    model: str,
    evidence_payload: dict,
    validation_feedback: list[str] | None,
    provider_attempt: int,
) -> None:
    """Log safe metadata before one Gemini request; never log a credential."""
    request = evidence_payload["forecast_request"]
    details = {
        "activity_id": activity_id,
        "provider": "Gemini",
        "model": model,
        "provider_attempt": provider_attempt,
        "user_name": request["user_name"],
        "food_item": request["food_item"],
        "target_date": request["target_date"],
        "historical_record_count": len(evidence_payload["historical_records"]),
        "future_context_provided": bool(request["future_context"]),
        "correction_feedback": validation_feedback or [],
    }
    if os.getenv("AI_LOG_FULL_CONTENT", "false").lower() == "true":
        details["full_evidence_payload"] = evidence_payload
    write_event(log_path, "gemini_request_started", details)


def log_response(
    log_path: Path, activity_id: str, model: str, interaction_id: str | None, response: dict
) -> None:
    """Log Gemini's parsed forecast response including its suggested quantity."""
    write_event(
        log_path,
        "gemini_response_received",
        {
            "activity_id": activity_id,
            "provider": "Gemini",
            "model": model,
            "interaction_id": interaction_id,
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
    """Log a transient failure that will be retried after exponential backoff."""
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
    """Log a Gemini-to-Gemini fallback after the primary model is unavailable."""
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


# Validation, failure, and quota events

def log_validation_rejection(log_path: Path, model: str, attempt: int, violations: list[str]) -> None:
    """Log why Gemini was asked to correct an otherwise complete response."""
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
    """Log configuration, network, API, and parsing failures safely."""
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
    """Log the exhausted AI-only forecast route after all retries and fallbacks."""
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
    """Record a deliberate wait used to avoid a Gemini request-rate spike."""
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
    """Record when the local quota guard stops a request before it is sent."""
    write_event(
        log_path,
        "gemini_quota_guard_blocked",
        {"provider": "Gemini", "model": model, "message": message},
    )


# Shared writer

def write_event(log_path: Path, event: str, details: dict) -> None:
    """Append a newline-delimited JSON event that can be read by humans or tools."""
    singapore_timezone = timezone(timedelta(hours=8))
    entry = {
        "timestamp_sgt": datetime.now(singapore_timezone).isoformat(),
        "event": event,
        **details,
    }
    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
