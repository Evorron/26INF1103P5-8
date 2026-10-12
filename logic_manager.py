"""Business rules and forecast guardrails for Hawker AI.

The module deliberately has five public operations, arranged in the order the
application uses them: validate inputs, prepare Gemini data, calculate facts,
and validate Gemini's completed forecast. It verifies AI output but never
silently changes an AI recommendation.
"""

# This file is the project's rule checker. It validates user input, prepares
# sales facts for Gemini, and checks that the final forecast follows the
# project limits before it can be shown to the user.
#
# Program flow:
# 1. main.py supplies records or a forecast request.
# 2. This module validates and filters the data.
# 3. forecast_adapter.py receives only valid, relevant records.
# 4. This module checks the adapter's completed response before it is displayed.

from datetime import date
from math import floor


# Input-quality rules used for both interactive input and future data sources.
CONTEXT_WORD_LIMIT = 150
LOW_CONFIDENCE_RECORD_COUNT = 7

# Forecast safety rules.  They limit unusually high recommendations unless
# there is sufficient weekday history, a genuine historical shift, or context.
MAXIMUM_MULTIPLIER = 1.5
WEEKDAY_DEVIATION_LIMIT = 0.50
REQUIRED_SAME_WEEKDAY_RECORDS = 4
HISTORICAL_SHIFT_THRESHOLD = 0.20

# Gemini-provided evidence is compared with local calculations.  A small
# tolerance prevents harmless decimal-rounding differences from causing failure.
EVIDENCE_TOLERANCE = 0.01


def normalise_text(value: str) -> str:
    """Return text in the comparison format used for names and food items."""
    # For example, "  Chicken   Rice " and "chicken rice" should match the
    # same saved food item, while the original spelling remains for display.
    return " ".join(value.split()).casefold()


def records_for_forecast(request: dict, all_records: list[dict]) -> list[dict]:
    """Select and validate the saved history belonging to one forecast request.

    This is the boundary between the user interface's complete CSV data set and
    the adapter's forecast-only data set.  Matching ignores capitalisation and
    extra spaces, while the returned records keep their original display text.
    """
    matching_records = [
        record
        for record in all_records
        if normalise_text(record["user_name"]) == normalise_text(request["user_name"])
        and normalise_text(record["food_item"]) == normalise_text(request["food_item"])
    ]
    matching_records.sort(key=lambda record: record["record_date"])
    # Sorting makes "last four" calculations consistently mean the four most
    # recent dates, even when CSV rows were entered out of date order.
    validate_forecast_request(request, matching_records)
    return matching_records


def food_items_for_user(user_name: str, all_records: list[dict]) -> list[str]:
    """Return a user's recorded food items, without case-insensitive duplicates."""
    seen_items: set[str] = set()
    items: list[str] = []
    normalised_user = normalise_text(user_name)
    for record in all_records:
        if normalise_text(record["user_name"]) != normalised_user:
            continue
        normalised_item = normalise_text(record["food_item"])
        if normalised_item not in seen_items:
            seen_items.add(normalised_item)
            items.append(record["food_item"])
    return sorted(items, key=str.casefold)


def records_for_search(search_filters: dict, all_records: list[dict]) -> list[dict]:
    """Return one user's item records within the requested inclusive date range."""
    matching_records = [
        record
        for record in all_records
        if normalise_text(record["user_name"]) == normalise_text(search_filters["user_name"])
        and normalise_text(record["food_item"]) == normalise_text(search_filters["food_item"])
        and search_filters["start_date"] <= record["record_date"] <= search_filters["end_date"]
    ]
    return sorted(matching_records, key=lambda record: record["record_date"])


def validate_sales_record(record: dict) -> None:
    """Reject incomplete, impossible, or inconsistent historical records."""
    # Check saved sales data first so inaccurate records do not affect forecasts.
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
    # A forecast needs a future date and at least one matching past sales record.
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
    # Give Gemini the raw records and rule values, without changing the sales
    # data.  The adapter, rather than Gemini, remains responsible for deciding
    # whether the completed response is safe to display.
    # Sort before selecting the focused groups so "recent" has the same
    # meaning even when the CSV records were entered out of date order.
    ordered_records = sorted(historical_records, key=lambda record: record["record_date"])

    def serialise_record(record: dict) -> dict:
        """Convert one local record into JSON-safe factual evidence for Gemini."""
        return {
            "record_date": record["record_date"].isoformat(),
            "weekday": record["record_date"].strftime("%A"),
            "food_item": record["food_item"],
            "portions_prepared": record["portions_prepared"],
            "portions_sold": record["portions_sold"],
            "leftover_portions": record["portions_prepared"] - record["portions_sold"],
            "past_context": record["past_context"] or None,
        }

    same_weekday_records = [
        record
        for record in ordered_records
        if record["record_date"].weekday() == request["target_date"].weekday()
    ]

    return {
        "forecast_request": {
            "user_name": request["user_name"],
            "food_item": request["food_item"],
            "target_date": request["target_date"].isoformat(),
            "target_weekday": request["target_date"].strftime("%A"),
            "future_context": request["future_context"] or None,
        },
        # The complete history is retained, but these focused groups make the
        # intended weekday and recency comparisons explicit for Gemini.
        "historical_records": [serialise_record(record) for record in ordered_records],
        "same_weekday_records": [serialise_record(record) for record in same_weekday_records],
        "recent_records": [
            serialise_record(record) for record in ordered_records[-REQUIRED_SAME_WEEKDAY_RECORDS:]
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
    # These averages and totals are used as evidence when checking the AI result.
    # They are not a second forecasting algorithm: their purpose is to verify
    # factual claims such as record counts and historical averages.
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
    # Return every failed rule so the adapter can stop an unsafe forecast.
    # Collect every issue in one pass so the adapter can report a useful error
    # instead of repeatedly asking the AI to fix one unknown problem at a time.
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
        # A small data set can still produce a forecast, but it must make its
        # uncertainty visible to the hawker.
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
        # Day-of-week demand can differ significantly (for example, weekends),
        # so compare against recent records from the target weekday when able.
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
            # A large, evidenced change in recent demand may justify moving
            # beyond the weekday range, even when no future context was given.
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
