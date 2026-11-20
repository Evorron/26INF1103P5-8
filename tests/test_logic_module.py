import unittest
from datetime import date, timedelta

from logic.forecast_rules import ForecastRules
from logic.logic_manager_class import LogicManager


class TestLogicValidationAndSelection(unittest.TestCase):
    def setUp(self):
        self.logic = LogicManager()

    def test_valid_labels_allow_names_apostrophes_hyphens_and_spaces(self):
        self.logic.validate_label("  O'Neil-Smith  ", "Name")

    def test_invalid_labels_and_invalid_portion_relationships_are_rejected(self):
        for value in ("", "123", "Laksa!", "Ari_ Tan"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.logic.validate_label(value, "Name")
        for prepared, sold in ((-1, 0), (5, -1), (5, 6)):
            with self.subTest(prepared=prepared, sold=sold), self.assertRaises(ValueError):
                self.logic.validate_portions(prepared, sold)
        self.logic.validate_portions(0, 0)

    def test_forecast_requires_future_date_context_limit_and_matching_history(self):
        request = {
            "user_name": "Ari Tan",
            "food_item": "Laksa",
            "target_date": date.today() + timedelta(days=1),
            "future_context": "",
        }
        with self.assertRaisesRegex(ValueError, "No historical records"):
            self.logic.validate_forecast_request(request, [])
        with self.assertRaisesRegex(ValueError, "must be in the future"):
            self.logic.validate_forecast_request(
                {**request, "target_date": date.today()}, [{"record": 1}]
            )
        with self.assertRaisesRegex(ValueError, "more than 150 words"):
            self.logic.validate_forecast_request(
                {**request, "future_context": "word " * 151}, [{"record": 1}]
            )

    def test_search_is_casefolded_sorted_and_inclusive_of_range_boundaries(self):
        records = [
            self.record("Ari Tan", "laksa", date(2025, 1, 3), 9),
            self.record("ARI TAN", "Laksa", date(2025, 1, 1), 7),
            self.record("Other", "Laksa", date(2025, 1, 2), 8),
            self.record("Ari Tan", "Cake", date(2025, 1, 2), 4),
        ]
        filters = {
            "user_name": " ari   tan ",
            "food_item": "LAKSA",
            "start_date": date(2025, 1, 1),
            "end_date": date(2025, 1, 3),
        }

        matches = self.logic.records_for_search(filters, records)

        self.assertEqual([item["portions_sold"] for item in matches], [7, 9])
        with self.assertRaisesRegex(ValueError, "End date"):
            self.logic.validate_search_filters({**filters, "start_date": date(2025, 1, 4)})

    def test_food_items_are_unique_per_user_and_case_insensitive(self):
        records = [
            self.record("Ari", "Laksa", date(2025, 1, 1), 2),
            self.record("ari", "LAKSA", date(2025, 1, 2), 3),
            self.record("Ari", "Cake", date(2025, 1, 3), 4),
            self.record("Other", "Noodles", date(2025, 1, 1), 1),
        ]

        self.assertEqual(self.logic.food_items_for_user("ARI", records), ["Cake", "Laksa"])

    def test_ai_payload_is_chronological_and_contains_derived_leftovers(self):
        records = [
            self.record("Ari", "Laksa", date(2025, 1, 2), 7, prepared=10),
            self.record("Ari", "Laksa", date(2025, 1, 1), 5, prepared=8),
        ]
        request = {
            "user_name": "Ari",
            "food_item": "Laksa",
            "target_date": date(2025, 1, 8),
            "future_context": "Community event",
        }

        payload = self.logic.build_ai_payload(request, records)

        self.assertEqual(payload["historical_records"][0]["record_date"], "2025-01-01")
        self.assertEqual(payload["historical_records"][1]["leftover_portions"], 3)
        self.assertEqual(payload["forecast_request"]["target_weekday"], "Wednesday")
        self.assertEqual(payload["forecast_request"]["future_context"], "Community event")

    def test_metrics_and_quantity_rules_match_expected_bounds(self):
        records = [
            self.record("Ari", "Laksa", date(2025, 1, day), sold)
            for day, sold in enumerate(range(1, 9), start=1)
        ]
        metrics = self.logic.calculate_evidence_metrics(records, date(2025, 1, 10))

        self.assertEqual(metrics["record_count"], 8.0)
        self.assertEqual(metrics["historical_maximum_sold"], 8.0)
        self.assertEqual(metrics["last_4_overall_average"], 6.5)
        self.assertEqual(metrics["previous_4_overall_average"], 2.5)
        self.assertEqual(self.logic.calculate_quantity(99, [10, 20, 30, 40], {
            "historical_maximum_sold": 40,
            "last_4_same_weekday_average": None,
        }, False), 38)
        self.assertEqual(self.logic.calculate_quantity(0, [10, 20, 30, 40], {
            "historical_maximum_sold": 40,
            "last_4_same_weekday_average": None,
        }, False), 19)
        with self.assertRaisesRegex(RuntimeError, "all saved sales are zero"):
            self.logic.calculate_quantity(1, [0, 0], {
                "historical_maximum_sold": 0,
                "last_4_same_weekday_average": None,
            }, False)

    def test_forecast_response_rejects_bad_evidence_and_unbounded_quantity(self):
        records = [self.record("Ari", "Laksa", date(2025, 1, day), 10) for day in range(1, 8)]
        request = {
            "user_name": "Ari",
            "food_item": "Laksa",
            "target_date": date(2025, 1, 10),
            "future_context": "",
        }
        response = {
            "suggested_portions": 99,
            "confidence": "high",
            "reasoning": "Reason",
            "business_advice": "Advice",
            "factors_considered": ["sales"],
            "evidence": [{"metric": "record_count", "value": 99, "claim": "records"}],
            "warning": "",
            "uses_future_context": False,
            "exception_justification": None,
            "uses_historical_shift": False,
            "historical_shift_justification": None,
        }

        issues = self.logic.validate_ai_response(response, request, records)

        self.assertTrue(any("evidence value" in issue for issue in issues))
        self.assertTrue(any("maximum allowed" in issue for issue in issues))
        self.assertTrue(any("confidence must be low" in issue for issue in issues))
        self.assertTrue(any("warning is required" in issue for issue in issues))

    @staticmethod
    def record(user, item, record_date, sold, prepared=20):
        return {
            "user_name": user,
            "business_type": "Hawker",
            "record_date": record_date,
            "food_item": item,
            "portions_prepared": prepared,
            "portions_sold": sold,
            "past_context": "",
        }


class TestForecastRules(unittest.TestCase):
    def test_history_threshold_maximum_and_weekday_deviation_edges(self):
        rules = ForecastRules()
        self.assertTrue(rules.has_limited_history(6))
        self.assertFalse(rules.has_limited_history(7))
        self.assertEqual(rules.maximum_quantity(9), 13)
        self.assertFalse(rules.outside_weekday_limit(15, 10))
        self.assertTrue(rules.outside_weekday_limit(16, 10))
        self.assertFalse(rules.outside_weekday_limit(0, None))
        self.assertTrue(rules.outside_weekday_limit(1, 0))


if __name__ == "__main__":
    unittest.main()
