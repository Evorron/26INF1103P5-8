"""Keep the numerical forecast rules together"""


from math import ceil, floor
from statistics import median

class ForecastRules:
    LOW_CONFIDENCE_RECORD_COUNT = 7
    MAXIMUM_MULTIPLIER = 1.5
    MINIMUM_DEMAND_FACTOR = 0.75
    MINIMUM_RECOMMENDATION_RATIO = 0.75
    WEEKDAY_DEVIATION_LIMIT = 0.50
    REQUIRED_SAME_WEEKDAY_RECORDS = 4
    HISTORICAL_SHIFT_THRESHOLD = 0.20

    def has_limited_history(self, record_count: int) -> bool:
        return record_count < self.LOW_CONFIDENCE_RECORD_COUNT

    def maximum_quantity(self, historical_maximum: float) -> int:
        return floor(historical_maximum * self.MAXIMUM_MULTIPLIER)

    def for_ai_payload(self) -> dict:
        return {
            "minimum_history_for_normal_confidence": self.LOW_CONFIDENCE_RECORD_COUNT,
            "maximum_portions_multiplier": self.MAXIMUM_MULTIPLIER,
            "weekday_deviation_limit": self.WEEKDAY_DEVIATION_LIMIT,
            "same_weekday_records_for_deviation_check": self.REQUIRED_SAME_WEEKDAY_RECORDS,
            "historical_shift_threshold": self.HISTORICAL_SHIFT_THRESHOLD,
        }

    def outside_weekday_limit(self, quantity: int, weekday_average: float | None) -> bool:
        if weekday_average is None:
            return False
        if weekday_average == 0:
            return quantity != 0
        deviation = abs(quantity - weekday_average) / weekday_average
        return deviation > self.WEEKDAY_DEVIATION_LIMIT

    def calculate_quantity(self, factor: float, sales: list[int], metrics: dict, has_future_context: bool) -> int:
        maximum_sold = metrics["historical_maximum_sold"]
        if maximum_sold == 0:
            raise RuntimeError("A positive forecast cannot be produced because all saved sales are zero")

        typical_sales = median(sales)
        minimum_ratio = self.MINIMUM_RECOMMENDATION_RATIO
        maximum_multiplier = self.MAXIMUM_MULTIPLIER

        factor = max(self.MINIMUM_DEMAND_FACTOR, min(factor,  maximum_multiplier))
        quantity = max(1, round(typical_sales * factor))
        minimum = max(1, ceil(typical_sales * minimum_ratio))
        maximum = self.maximum_quantity(maximum_sold)
        quantity = max(minimum, min(quantity, maximum))

        weekday_average = metrics["last_4_same_weekday_average"]
        if weekday_average is not None and weekday_average > 0 and not has_future_context:
            minimum = max(1, ceil(weekday_average * minimum_ratio))
            maximum = floor(weekday_average * maximum_multiplier)
            quantity = max(minimum, min(quantity, maximum))

        return quantity

    def has_historical_shift(self, response: dict, metrics: dict) -> bool:
        if not response["uses_historical_shift"] or not response["historical_shift_justification"]:
            return False

        cited_metrics = {item["metric"] for item in response["evidence"]}
        comparisons = [
            ("last_4_overall_average", "previous_4_overall_average"),
            ("last_4_same_weekday_average", "previous_4_same_weekday_average"),
        ]

        for recent_name, earlier_name in comparisons:
            if recent_name not in cited_metrics or earlier_name not in cited_metrics:
                continue

            recent = metrics[recent_name]
            earlier = metrics[earlier_name]
            if recent is None or earlier is None:
                continue

            if earlier == 0:
                if recent != 0:
                    return True

            elif abs(recent - earlier) / earlier >= self.HISTORICAL_SHIFT_THRESHOLD:
                return True

        return False    