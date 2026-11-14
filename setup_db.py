import sqlite3
from contextlib import closing
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "hawker.db"

def setup_database():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cursor = conn.cursor()

        # Create Sales Table
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

        # Create AI Recommendations Table
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
        conn.commit()
        print("Database and tables created successfully!")

if __name__ == "__main__":
    setup_database()