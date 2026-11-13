"""Validate sales records and prepare evidence for forecasting"""


from datetime import date
from forecast_rules import ForecastRules

class LogicManager:
    CONTEXT_WORD_LIMIT = 150
    EVIDENCE_TOLERANCE = 0.01

    def __init__(self):
        self._forecast_rules = ForecastRules()

    def has_limited_history(self, record_count: int) -> bool:
        return self._forecast_rules.has_limited_history(record_count)

    def calculate_quantity(self, factor: float, sales: list[int], metrics: dict, uses_future_context: bool) -> int:
        return self._forecast_rules.calculate_quantity(factor, sales, metrics, uses_future_context)

    def validate_label(self, value: str, label: str) -> None:
        value = value.strip()
        has_letter = any(char.isalpha() for char in value)
        allowed_characters = all(char.isalpha() or char in " -'" for char in value)

        if not has_letter or not allowed_characters:
            raise ValueError(f"{label} must contain letters only (spaces, hypens, and apostrophes are allowed).")


    def validate_historical_date(self, record_date: date) -> None:
        if record_date > date.today():
            raise ValueError("A historical record date cannot be in the future")

    def validate_forecast_date(self, target_date: date) -> None:
        if target_date <= date.today():
            raise ValueError("The forecast date must be in the future")

    def validate_portions(self, portions_prepared: int, portions_sold: int) -> None:
        if portions_prepared < 0:
            raise ValueError("Portions prepared cannot be negative.")
        if portions_sold < 0:
            raise ValueError("Portions sold cannot be negative.")
        if portions_sold > portions_prepared:
            raise ValueError("Portions sold cannot be greater than portions prepared.")

    def validate_context(self, context: str, context_type: str) -> None:
        if len(context.split()) > self.CONTEXT_WORD_LIMIT:
            raise ValueError(
                f"{context_type} cannot contain more than {self.CONTEXT_WORD_LIMIT} words."
            )

    def validate_sales_record(self, record: dict) -> None:
        self.validate_label(record["user_name"], "Name")
        self.validate_label(record["food_item"], "Food item")
        self.validate_context(record["past_context"], "Past context")
        self.validate_historical_date(record["record_date"])
        self.validate_portions(record["portions_prepared"], record["portions_sold"])

    def validate_forecast_request(self, request: dict, historical_records: list[dict]) -> None:
        self.validate_label(request["user_name"], "Name")
        self.validate_label(request["food_item"], "Forecast food item")
        self.validate_context(request["future_context"], "Future context")
        self.validate_forecast_date(request["target_date"])

        if not historical_records:
            raise ValueError("No historical records were found for this food item.")

    def validate_search_filters(self, search_filters: dict) -> None:
        self.validate_label(search_filters["user_name"], "Name")
        self.validate_label(search_filters["food_item"], "Food item")

        if search_filters["start_date"] > search_filters["end_date"]:
            raise ValueError("End date cannot be earlier than the start date.")

    def normalise_text(self, value: str) -> str:
        return " ".join(value.split()).casefold()

    def _matching_item_records(self, selection: dict, all_records: list[dict]) -> list[dict]:
        """Use the same name and item comparison for searches and forecasts."""
        user_name = self.normalise_text(selection["user_name"])
        food_item = self.normalise_text(selection["food_item"])
        matches = []

        for record in all_records:
            if self.normalise_text(record["user_name"]) != user_name:
                continue
            if self.normalise_text(record["food_item"]) == food_item:
                matches.append(record)

        return sorted(matches, key=lambda record: record["record_date"])

    def records_for_forecast(self, request: dict, all_records: list[dict]) -> list[dict]:
        records = self._matching_item_records(request, all_records)
        self.validate_forecast_request(request, records)
        return records

    def records_for_search(self, search_filters: dict, all_records: list[dict]) -> list[dict]:
        self.validate_search_filters(search_filters)
        records = self._matching_item_records(search_filters, all_records)
        start_date = search_filters["start_date"]
        end_date = search_filters["end_date"]
        return [record for record in records if start_date <= record["record_date"] <= end_date]

    def food_items_for_user(self, user_name: str, all_records: list[dict]) -> list[str]:
        normalised_user = self.normalise_text(user_name)
        seen_items = set()
        items = []

        for record in all_records:
            if self.normalise_text(record["user_name"]) == normalised_user:
                food_item = record["food_item"]
                normalised_item = self.normalise_text(food_item)
                if normalised_item not in seen_items:
                    seen_items.add(normalised_item)
                    items.append(food_item)

        return sorted(items, key=str.casefold)

    def build_ai_payload(self, request: dict, historical_records: list[dict]) -> dict:
        """Prepare the dates and sales figures that go into the AI request."""
        target_date = request["target_date"]
        target_weekday = target_date.strftime("%A")
        records = []
        same_weekday_records = []

        for record in sorted(historical_records, key=lambda record: record["record_date"]):
            record_date = record["record_date"]
            prepared = record["portions_prepared"]
            sold = record["portions_sold"]
            entry = {
                "record_date": record_date.isoformat(),
                "weekday": record_date.strftime("%A"),
                "food_item": record["food_item"],
                "portions_prepared": prepared,
                "portions_sold": sold,
                "leftover_portions": prepared - sold,
                "past_context": record["past_context"] or None,
            }
            records.append(entry)
            if record_date.weekday() == target_date.weekday():
                same_weekday_records.append(entry)

        return {
            "forecast_request": {
                "user_name": request["user_name"],
                "food_item": request["food_item"],
                "target_date": target_date.isoformat(),
                "target_weekday": target_weekday,
                "future_context": request["future_context"] or None,
            },
            "historical_records": records,
            "same_weekday_records": same_weekday_records,
            "recent_records": records[-self._forecast_rules.REQUIRED_SAME_WEEKDAY_RECORDS:],
            "rules_for_ai": self._forecast_rules.for_ai_payload(),
        }

    def _average_of_four(self, sales: list[int]) -> float | None:
        if len(sales) < self._forecast_rules.REQUIRED_SAME_WEEKDAY_RECORDS:
            return None
        return sum(sales) / len(sales)

    def calculate_evidence_metrics(
        self,
        historical_records: list[dict], target_date: date
    ) -> dict[str, float | None]:
        """Calculate the sales figures used to build and check a forecast."""
        records = sorted(historical_records, key=lambda record: record["record_date"])
        all_sales = []
        weekday_sales = []
        target_weekday = target_date.weekday()

        for record in records:
            sold = record["portions_sold"]
            all_sales.append(sold)
            if record["record_date"].weekday() == target_weekday:
                weekday_sales.append(sold)

        count = self._forecast_rules.REQUIRED_SAME_WEEKDAY_RECORDS
        return {
            "record_count": float(len(records)),
            "historical_maximum_sold": float(max(all_sales)),
            "last_4_overall_average": self._average_of_four(all_sales[-count:]),
            "previous_4_overall_average": self._average_of_four(all_sales[-2 * count:-count]),
            "last_4_same_weekday_average": self._average_of_four(weekday_sales[-count:]),
            "previous_4_same_weekday_average": self._average_of_four(weekday_sales[-2 * count:-count]),
        }

    def validate_ai_response(self, response: dict, request: dict, historical_records: list[dict]) -> list[str]:
        """Return the reasons a forecast cannot be shown to the user."""
        issues = []
        quantity = response["suggested_portions"]
        confidence = response["confidence"]

        if quantity <= 0:
            issues.append("suggested_portions must be a positive whole number")
        if confidence not in {"high", "medium", "low"}:
            issues.append("confidence must be high, medium, or low")
        for field in ("reasoning", "business_advice"):
            if not response[field]:
                issues.append(f"{field} must not be empty")
        if not response["factors_considered"]:
            issues.append("factors_considered must contain at least one factor")

        metrics = self.calculate_evidence_metrics(historical_records, request["target_date"])
        if not response["evidence"]:
            issues.append("evidence must contain at least one verifiable metric")

        for item in response["evidence"]:
            metric = item["metric"]
            if metric not in metrics:
                issues.append(f"evidence metric is not recognised: {metric}")
            elif metrics[metric] is None:
                issues.append(f"evidence metric is unavailable from the current record set: {metric}")
            elif abs(item["value"] - metrics[metric]) > self.EVIDENCE_TOLERANCE:
                issues.append(f"evidence value for {metric} does not match stored records")
            if not item["claim"]:
                issues.append(f"evidence claim for {metric} must not be empty")

        if self.has_limited_history(len(historical_records)):
            if confidence != "low":
                issues.append(
                    "confidence must be low because fewer than "
                    f"{self._forecast_rules.LOW_CONFIDENCE_RECORD_COUNT} historical records exist"
                )
            if not response["warning"]:
                issues.append("warning is required when historical records are limited")

        maximum_allowed = self._forecast_rules.maximum_quantity(metrics["historical_maximum_sold"])
        if quantity > maximum_allowed:
            issues.append(f"suggested_portions exceeds the maximum allowed value of {maximum_allowed}")

        weekday_average = metrics["last_4_same_weekday_average"]
        if self._forecast_rules.outside_weekday_limit(quantity, weekday_average):
            uses_context = request["future_context"].strip() and response["uses_future_context"]
            if uses_context and not response["exception_justification"]:
                issues.append("exception_justification is required for a future-context deviation")
            if not uses_context and not self._forecast_rules.has_historical_shift(response, metrics):
                issues.append(
                    "suggested_portions exceeds the same-weekday deviation limit "
                    "without validated historical-shift evidence or supplied future context"
                )

        return issues