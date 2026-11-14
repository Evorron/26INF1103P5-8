import sqlite3
from pathlib import Path
from typing import Type, TypeVar
from record import Record
from storage_interface import IStorage

T = TypeVar("T", bound=Record)

class DatabaseStorage(IStorage):
    def __init__(
        self,
        db_path: Path,
        table_name: str,
        record_type: Type[T],
    ):
        self._db_path = db_path
        self._table_name = table_name
        self._record_type = record_type

    def load(self) -> list[T]:
        """Load all rows from the table and convert them to Record objects."""
        if not self._db_path.exists():
            return []

        with sqlite3.connect(self._db_path) as conn:
            # This makes the rows behave like dictionaries so from_dict works easily
            conn.row_factory = sqlite3.Row 
            cursor = conn.cursor()
            
            try:
                cursor.execute(f"SELECT * FROM {self._table_name}")
                rows = cursor.fetchall()
                return [self._record_type.from_dict(dict(row)) for row in rows]
            except sqlite3.OperationalError:
                # Table doesn't exist yet
                return []

    def save(self, records: list[T]) -> None:
        """Wipe the table and insert the new records."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            if not records:
                return

            # 1. Get the column names from the first record
            first_record_dict = records[0].to_dict()
            columns = list(first_record_dict.keys())
            
            # 2. Build the SQL queries dynamically
            placeholders = ", ".join(["?" for _ in columns])
            columns_str = ", ".join(columns)
            
            # Delete existing data to prevent duplicates
            cursor.execute(f"DELETE FROM {self._table_name}")

            # 3. Insert new data
            insert_query = f"INSERT INTO {self._table_name} ({columns_str}) VALUES ({placeholders})"
            
            for record in records:
                data = record.to_dict()
                # Convert values to a tuple in the correct order
                values = tuple(data[col] for col in columns)
                cursor.execute(insert_query, values)

            conn.commit()