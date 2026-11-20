import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock

from data.data_manager import (
    AIRecommendation,
    RecommendationManager,
    SalesRecord,
    SalesRecordManager,
)
from data.database_storage import DatabaseStorage
from data.setup_db import DatabaseSchema


class TestRecordSerialization(unittest.TestCase):
    def test_sales_record_round_trip_accepts_iso_date(self):
        record = SalesRecord.from_dict(
            {
                "user_name": "Ari Tan",
                "business_type": "Hawker",
                "record_date": "2025-03-04",
                "food_item": "Laksa",
                "portions_prepared": "12",
                "portions_sold": "9",
                "past_context": None,
            }
        )

        self.assertEqual(record.record_date, date(2025, 3, 4))
        self.assertEqual(record.to_dict()["portions_sold"], 9)
        self.assertEqual(record.to_dict()["past_context"], "")

    def test_recommendation_round_trip_preserves_dates_and_numbers(self):
        recommendation = AIRecommendation.from_dict(
            {
                "user_name": "Ari Tan",
                "food_item": "Laksa",
                "forecast_date": "2025-03-05",
                "recommended_portions": "14",
                "reason": "Historical median",
                "verified_evidence": "7 records",
                "suggested_next_step": "Review leftovers",
                "forecast_method": "baseline",
                "confidence": "low",
                "generated_at": "2025-03-04T12:30:45",
            }
        )

        self.assertEqual(recommendation.forecast_date, date(2025, 3, 5))
        self.assertEqual(recommendation.to_dict()["recommended_portions"], 14)
        self.assertEqual(recommendation.to_dict()["warning"], "")


class TestSQLiteStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = Path(self.temp_dir.name) / "nested" / "hawker.db"
        DatabaseSchema(self.db_path).initialize()

    def test_sales_are_persisted_and_loaded_as_record_objects(self):
        storage = DatabaseStorage(self.db_path, "sales_records", SalesRecord)
        manager = SalesRecordManager(storage)
        manager.load()
        expected = SalesRecord("Ari", "Hawker", date(2025, 1, 2), "Laksa", 10, 8)
        manager.add(expected)

        loaded = SalesRecordManager(storage)
        loaded.load()
        self.assertEqual(len(loaded.get_all()), 1)
        self.assertEqual(loaded.get_all()[0].to_dict(), expected.to_dict())

    def test_missing_database_or_table_loads_empty_list(self):
        missing = DatabaseStorage(Path(self.temp_dir.name) / "absent.db", "sales_records", SalesRecord)
        missing_table = DatabaseStorage(self.db_path, "not_a_table", SalesRecord)

        self.assertEqual(missing.load(), [])
        self.assertEqual(missing_table.load(), [])

    def test_empty_snapshot_clears_table(self):
        storage = DatabaseStorage(self.db_path, "sales_records", SalesRecord)
        manager = SalesRecordManager(storage)
        manager.add(SalesRecord("Ari", "Hawker", date(2025, 1, 2), "Laksa", 10, 8))

        storage.save([])

        self.assertEqual(storage.load(), [])

    def test_invalid_sql_table_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            DatabaseStorage(self.db_path, "sales; DROP TABLE sales_records", SalesRecord)


class TestManagers(unittest.TestCase):
    def test_sales_manager_prevents_case_insensitive_duplicate_for_same_day(self):
        storage = Mock()
        manager = SalesRecordManager(storage)
        manager.add(SalesRecord("Ari Tan", "Hawker", date(2025, 1, 2), "Laksa", 10, 8))

        with self.assertRaisesRegex(ValueError, "already recorded"):
            manager.add(SalesRecord(" ari tan ", "Hawker", date(2025, 1, 2), "LAKSA", 12, 9))
        storage.save.assert_called_once()

    def test_recommendation_manager_rejects_duplicate_and_replaces_it(self):
        storage = Mock()
        manager = RecommendationManager(storage)
        original = self.make_recommendation("Ari", "Laksa", 10)
        replacement = self.make_recommendation(" ari ", "LAKSA", 15)
        manager.save(original)

        with self.assertRaisesRegex(ValueError, "already exists"):
            manager.save(replacement)

        manager.replace(replacement)
        self.assertEqual(len(manager.get_all()), 1)
        self.assertEqual(manager.get_all()[0].to_dict()["recommended_portions"], 15)
        self.assertEqual(storage.save.call_count, 2)

    @staticmethod
    def make_recommendation(user, item, portions):
        return AIRecommendation(
            user_name=user,
            food_item=item,
            forecast_date=date(2025, 1, 3),
            recommended_portions=portions,
            reason="test",
            verified_evidence="test evidence",
            suggested_next_step="review",
            forecast_method="baseline",
            confidence="low",
            generated_at=datetime(2025, 1, 2, 12, 0),
            warning="limited history",
        )


if __name__ == "__main__":
    unittest.main()
