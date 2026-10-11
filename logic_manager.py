"""Business rules and forecast guardrails for Hawker AI.

The module deliberately has five public operations, arranged in the order the
application uses them: validate inputs, prepare Gemini data, calculate facts,
and validate Gemini's completed forecast. It verifies AI output but never
silently changes an AI recommendation.
"""

from datetime import date
from math import floor


CONTEXT_WORD_LIMIT = 150
LOW_CONFIDENCE_RECORD_COUNT = 7
MAXIMUM_MULTIPLIER = 1.5
WEEKDAY_DEVIATION_LIMIT = 0.50
REQUIRED_SAME_WEEKDAY_RECORDS = 4
HISTORICAL_SHIFT_THRESHOLD = 0.20
EVIDENCE_TOLERANCE = 0.01


def validate_sales_record(record: dict) -> None:
    """Reject incomplete, impossible, or inconsistent historical records."""
    for value, label in ((record["user_name"], "Name"), (record["food_item"], "Food item")):
        cleaned_value = value.strip()
        is_words_only = (
            cleaned_value
            and all(character.isalpha() or character in " -'" for character in cleaned_value)
            and any(character.isalpha() for character in cleaned_value)
        )
        if not is_words_only:
            raise ValueError(
                f"{label} must contain letters only (spaces, hyphens, and apostrophes are allowed)."
            )
    if len(record["past_context"].split()) > CONTEXT_WORD_LIMIT:
        raise ValueError(f"Past context cannot contain more than {CONTEXT_WORD_LIMIT} words.")
    if record["record_date"] > date.today():
        raise ValueError("A historical record date cannot be in the future.")
    if record["portions_prepared"] <= 0:
        raise ValueError("Portions prepared must be a positive whole number.")
    if record["portions_sold"] < 0:
        raise ValueError("Portions sold cannot be negative.")
    if record["portions_sold"] > record["portions_prepared"]:
        raise ValueError("Portions sold cannot be greater than portions prepared.")


def validate_forecast_request(request: dict, historical_records: list[dict]) -> None:
    """Check that a forecast has valid inputs before Gemini is called."""
    for value, label in ((request["user_name"], "Name"), (request["food_item"], "Forecast food item")):
        cleaned_value = value.strip()
        is_words_only = (
            cleaned_value
            and all(character.isalpha() or character in " -'" for character in cleaned_value)
            and any(character.isalpha() for character in cleaned_value)
        )
        if not is_words_only:
            raise ValueError(
                f"{label} must contain letters only (spaces, hyphens, and apostrophes are allowed)."
            )
    if len(request["future_context"].split()) > CONTEXT_WORD_LIMIT:
        raise ValueError(f"Future context cannot contain more than {CONTEXT_WORD_LIMIT} words.")
    if request["target_date"] <= date.today():
        raise ValueError("The forecast target date must be in the future.")
    if not historical_records:
        raise ValueError("No historical records were found for this food item.")


def build_ai_payload(request: dict, historical_records: list[dict]) -> dict:
    """Package raw history for Gemini; no trends or forecast are calculated here."""
    return {
        "forecast_request": {
            "user_name": request["user_name"],
            "food_item": request["food_item"],
            "target_date": request["target_date"].isoformat(),
            "target_weekday": request["target_date"].strftime("%A"),
            "future_context": request["future_context"] or None,
        },
        "historical_records": [
            {
                "record_date": record["record_date"].isoformat(),
                "weekday": record["record_date"].strftime("%A"),
                "food_item": record["food_item"],
                "portions_prepared": record["portions_prepared"],
                "portions_sold": record["portions_sold"],
                "leftover_portions": record["portions_prepared"] - record["portions_sold"],
                "past_context": record["past_context"] or None,
            }
            for record in historical_records
        ],
        "rules_for_ai": {
            "minimum_history_for_normal_confidence": LOW_CONFIDENCE_RECORD_COUNT,
            "maximum_portions_multiplier": MAXIMUM_MULTIPLIER,
            "weekday_deviation_limit": WEEKDAY_DEVIATION_LIMIT,
            "same_weekday_records_for_deviation_check": REQUIRED_SAME_WEEKDAY_RECORDS,
            "historical_shift_threshold": HISTORICAL_SHIFT_THRESHOLD,
        },
    }


def calculate_evidence_metrics(historical_records: list[dict], target_date: date) -> dict[str, float | None]:
    """Calculate facts only to verify Gemini's claims, never to forecast."""
    all_sales = [record["portions_sold"] for record in historical_records]
    same_weekday_sales = [
        record["portions_sold"]
        for record in historical_records
        if record["record_date"].weekday() == target_date.weekday()
    ]
    last_four_sales = all_sales[-REQUIRED_SAME_WEEKDAY_RECORDS:]
    previous_four_sales = all_sales[-2 * REQUIRED_SAME_WEEKDAY_RECORDS:-REQUIRED_SAME_WEEKDAY_RECORDS]
    last_four_weekday_sales = same_weekday_sales[-REQUIRED_SAME_WEEKDAY_RECORDS:]
    previous_four_weekday_sales = same_weekday_sales[-2 * REQUIRED_SAME_WEEKDAY_RECORDS:-REQUIRED_SAME_WEEKDAY_RECORDS]
    return {
        "record_count": float(len(historical_records)),
        "historical_maximum_sold": float(max(all_sales)),
        "last_4_overall_average": (
            sum(last_four_sales) / REQUIRED_SAME_WEEKDAY_RECORDS
            if len(last_four_sales) == REQUIRED_SAME_WEEKDAY_RECORDS else None
        ),
        "previous_4_overall_average": (
            sum(previous_four_sales) / REQUIRED_SAME_WEEKDAY_RECORDS
            if len(previous_four_sales) == REQUIRED_SAME_WEEKDAY_RECORDS else None
        ),
        "last_4_same_weekday_average": (
            sum(last_four_weekday_sales) / REQUIRED_SAME_WEEKDAY_RECORDS
            if len(last_four_weekday_sales) == REQUIRED_SAME_WEEKDAY_RECORDS else None
        ),
        "previous_4_same_weekday_average": (
            sum(previous_four_weekday_sales) / REQUIRED_SAME_WEEKDAY_RECORDS
            if len(previous_four_weekday_sales) == REQUIRED_SAME_WEEKDAY_RECORDS else None
        ),
    }


def validate_ai_response(response: dict, request: dict, historical_records: list[dict]) -> list[str]:
    """Return failed guardrails; this function never changes an AI quantity."""
    issues = []
    if response["suggested_portions"] <= 0:
        issues.append("suggested_portions must be a positive whole number")
    if response["confidence"] not in {"high", "medium", "low"}:
        issues.append("confidence must be high, medium, or low")
    for field in ("reasoning", "business_advice"):
        if not response[field]:
            issues.append(f"{field} must not be empty")
    if not response["factors_considered"]:
        issues.append("factors_considered must contain at least one factor")

    evidence_metrics = calculate_evidence_metrics(historical_records, request["target_date"])
    if not response["evidence"]:
        issues.append("evidence must contain at least one verifiable metric")
    for item in response["evidence"]:
        metric = item["metric"]
        expected_value = evidence_metrics.get(metric)
        if metric not in evidence_metrics:
            issues.append(f"evidence metric is not recognised: {metric}")
        elif expected_value is None:
            issues.append(f"evidence metric is unavailable from the current record set: {metric}")
        elif abs(item["value"] - expected_value) > EVIDENCE_TOLERANCE:
            issues.append(f"evidence value for {metric} does not match stored records")
        if not item["claim"]:
            issues.append(f"evidence claim for {metric} must not be empty")

    if len(historical_records) < LOW_CONFIDENCE_RECORD_COUNT:
        if response["confidence"] != "low":
            issues.append(
                "confidence must be low because fewer than "
                f"{LOW_CONFIDENCE_RECORD_COUNT} historical records exist"
            )
        if not response["warning"]:
            issues.append("warning is required when historical records are limited")

    maximum_allowed = floor(
        max(record["portions_sold"] for record in historical_records) * MAXIMUM_MULTIPLIER
    )
    if response["suggested_portions"] > maximum_allowed:
        issues.append(f"suggested_portions exceeds the maximum allowed value of {maximum_allowed}")

    same_weekday_sales = [
        record["portions_sold"]
        for record in historical_records
        if record["record_date"].weekday() == request["target_date"].weekday()
    ]
    if len(same_weekday_sales) >= REQUIRED_SAME_WEEKDAY_RECORDS:
        weekday_average = sum(same_weekday_sales[-REQUIRED_SAME_WEEKDAY_RECORDS:]) / REQUIRED_SAME_WEEKDAY_RECORDS
        deviation = (
            float("inf")
            if weekday_average == 0 and response["suggested_portions"] != 0
            else abs(response["suggested_portions"] - weekday_average) / weekday_average
            if weekday_average != 0
            else 0.0
        )
        if deviation > WEEKDAY_DEVIATION_LIMIT:
            context_allows_exception = bool(
                request["future_context"].strip() and response["uses_future_context"]
            )
            if context_allows_exception and not response["exception_justification"]:
                issues.append("exception_justification is required for a future-context deviation")

            cited_metrics = {item["metric"] for item in response["evidence"]}
            shift_allows_exception = False
            if response["uses_historical_shift"] and response["historical_shift_justification"]:
                for recent_metric, earlier_metric in (
                    ("last_4_overall_average", "previous_4_overall_average"),
                    ("last_4_same_weekday_average", "previous_4_same_weekday_average"),
                ):
                    recent = evidence_metrics[recent_metric]
                    earlier = evidence_metrics[earlier_metric]
                    if recent_metric not in cited_metrics or earlier_metric not in cited_metrics:
                        continue
                    if recent is None or earlier is None:
                        continue
                    if earlier == 0 and recent != 0:
                        shift_allows_exception = True
                        break
                    if earlier != 0 and abs(recent - earlier) / earlier >= HISTORICAL_SHIFT_THRESHOLD:
                        shift_allows_exception = True
                        break

            if not context_allows_exception and not shift_allows_exception:
                issues.append(
                    "suggested_portions exceeds the same-weekday deviation limit "
                    "without validated historical-shift evidence or supplied future context"
                )
    return issues
