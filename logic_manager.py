"""Central business rules for Hawker AI.

This module is the single source of truth for validation and forecast safety.
It checks sales records and forecast requests, selects the relevant historical
records, prepares factual evidence for the AI manager, and verifies the final
forecast.  It never reads files, prints menus, calls an API, or saves data.

Keeping these rules in one module means the same checks apply to interactive
input today and imported CSV records in a future version of the program.
"""

from datetime import date
from math import floor


# Input-quality rules used for interactive input and future data imports.
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

def validate_label(value: str, label: str) -> None:
    """Reject an empty name or food label containing unsupported characters.

    Letters, spaces, hyphens, and apostrophes are accepted so common names and
    food names remain usable.  The ``label`` argument makes an error message
    identify the field that needs correction.
    """
    cleaned_value = value.strip()
    valid = (
        cleaned_value
        and all(char.isalpha() or char in " -'" for char in cleaned_value)
        and any(char.isalpha() for char in cleaned_value)
    )
    if not valid:
        raise ValueError(
            f"{label} must contain letters only "
            "(spaces, hyphens, and apostrophes are allowed)."
        )


def validate_historical_date(record_date: date) -> None:
    """Reject a sales-record date that is later than today."""
    if record_date > date.today():
        raise ValueError("A historical record date cannot be in the future.")


def validate_forecast_date(target_date: date) -> None:
    """Reject a forecast date that is today or in the past."""
    if target_date <= date.today():
        raise ValueError("The forecast target date must be in the future.")


def validate_portions(portions_prepared: int, portions_sold: int) -> None:
    """Ensure quantities are logical: prepared is non-negative and sold is valid."""
    if portions_prepared < 0:
        raise ValueError("Portions prepared cannot be negative.")
    if portions_sold < 0:
        raise ValueError("Portions sold cannot be negative.")
    if portions_sold > portions_prepared:
        raise ValueError("Portions sold cannot be greater than portions prepared.")


def validate_context(context: str, context_type: str) -> None:
    """Limit an optional past or future note to the allowed number of words."""
    if len(context.split()) > CONTEXT_WORD_LIMIT:
        raise ValueError(
            f"{context_type} cannot contain more than {CONTEXT_WORD_LIMIT} words."
        )

def validate_search_filters(search_filters: dict) -> None:
    """Validate the user, food item, and inclusive date range used for a search."""
    validate_label(search_filters["user_name"], "Name")
    validate_label(search_filters["food_item"], "Food item")

    if search_filters["start_date"] > search_filters["end_date"]:
        raise ValueError("End date cannot be earlier than the start date.")


def normalise_text(value: str) -> str:
    """Return text in a consistent form for comparisons, not for display.

    Extra internal spaces are collapsed and letter case is ignored.  For
    example, ``"  Chicken   Rice "`` and ``"chicken rice"`` compare as equal,
    while the original spelling remains available for the user interface.
    """
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
    """Return one user's food items, removing case-insensitive duplicates.

    The original spelling of the first matching item is preserved for display,
    and the resulting list is alphabetically ordered.
    """
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
    """Return one user's item records within an inclusive, validated date range."""
    validate_search_filters(search_filters)

    matching_records = [
        record
        for record in all_records
        if normalise_text(record["user_name"]) == normalise_text(search_filters["user_name"])
        and normalise_text(record["food_item"]) == normalise_text(search_filters["food_item"])
        and search_filters["start_date"] <= record["record_date"] <= search_filters["end_date"]
    ]
    return sorted(matching_records, key=lambda record: record["record_date"])


def validate_sales_record(record: dict) -> None:
    """Apply every business rule required before one sales record is saved."""
    validate_label(record["user_name"], "Name")
    validate_label(record["food_item"], "Food item")
    validate_context(record["past_context"], "Past context")
    validate_historical_date(record["record_date"])
    validate_portions(record["portions_prepared"], record["portions_sold"])


def validate_forecast_request(request: dict, historical_records: list[dict]) -> None:
    """Validate forecast inputs and require matching historical sales data."""
    validate_label(request["user_name"], "Name")
    validate_label(request["food_item"], "Forecast food item")
    validate_context(request["future_context"], "Future context")
    validate_forecast_date(request["target_date"])

    if not historical_records:
        raise ValueError("No historical records were found for this food item.")

def build_ai_payload(request: dict, historical_records: list[dict]) -> dict:
    """Create JSON-safe factual evidence for the AI manager.

    No prediction is calculated here.  The payload contains complete history,
    recent records, target-weekday records, and the rules the AI must respect.
    The adapter remains responsible for converting the AI factor into a final
    quantity and this module later verifies that quantity.
    """
    # Sort first so the terms "recent" and "last four" always mean the latest
    # dates, even if CSV rows were entered out of chronological order.
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
    """Calculate stored-sales facts used to verify a forecast's evidence.

    These metrics are not a second forecasting algorithm.  They provide local,
    reproducible facts—such as record count and recent averages—that the final
    response may cite and that ``validate_ai_response`` can check.
    """

    historical_records = sorted(historical_records, key=lambda record: record["record_date"],)
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
    """Return every violated forecast guardrail without changing the response.

    The adapter uses the returned messages to reject an unsafe forecast.  This
    function checks quantity, confidence, explanatory content, cited evidence,
    limited-history warnings, the overall maximum, and weekday deviations.
    """
    # Collect all issues in one pass so callers receive one useful explanation
    # rather than discovering guardrails one at a time.
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
