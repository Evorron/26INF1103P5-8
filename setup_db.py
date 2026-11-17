import sqlite3
from contextlib import closing
from pathlib import Path


class DatabaseSchema:
    """Creates and manages the SQLite schema for the hawker application."""

    def __init__(self, db_path: Path):
        self._db_path = db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self._db_path)) as conn:
            cursor = conn.cursor()
            self._create_sales_table(cursor)
            self._create_recommendations_table(cursor)
            self._create_indexes(cursor)
            conn.commit()

    def _create_sales_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_records (
                user_name TEXT,
                business_type TEXT,
                record_date TEXT,
                food_item TEXT,
                portions_prepared INTEGER,
                portions_sold INTEGER,
                past_context TEXT
            )
        """)

    def _create_recommendations_table(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_recommendations (
                user_name TEXT,
                food_item TEXT,
                forecast_date TEXT,
                recommended_portions INTEGER,
                reason TEXT,
                verified_evidence TEXT,
                suggested_next_step TEXT,
                forecast_method TEXT,
                confidence TEXT,
                generated_at TEXT,
                warning TEXT
            )
        """)

    def _create_indexes(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_sales_record_key
            ON sales_records (
                TRIM(user_name) COLLATE NOCASE,
                TRIM(food_item) COLLATE NOCASE,
                record_date
            )
        """)
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_forecast_key
            ON ai_recommendations (
                TRIM(user_name) COLLATE NOCASE,
                TRIM(food_item) COLLATE NOCASE,
                forecast_date
            )
        """)


if __name__ == "__main__":
    schema = DatabaseSchema(Path(__file__).resolve().parent / "data" / "hawker.db")
    schema.initialize()
    print("Database and tables created successfully!")