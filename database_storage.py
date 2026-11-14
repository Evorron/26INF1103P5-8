import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Type
from record import Record
from storage_interface import IStorage


class DatabaseStorage(IStorage):
    def __init__(
        self,
        db_path: Path,
        table_name: str,
        record_type: Type[Record],
    ):
        if not table_name.isidentifier():
            raise ValueError(f"Invalid table name: {table_name}")

        self._db_path = db_path
        self._table_name = table_name
        self._record_type = record_type

    def load(self) -> list[Record]:
        """Load all rows from the table and convert them to Record objects."""
        if not self._db_path.exists():
            return []

        with closing(sqlite3.connect(self._db_path)) as conn:
            conn.row_factory = sqlite3.Row
            table_exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (self._table_name,),
            ).fetchone()
            if table_exists is None:
                return []

            rows = conn.execute(f"SELECT * FROM {self._table_name}").fetchall()
            return [self._record_type.from_dict(dict(row)) for row in rows]

    def save(self, records: list[Record]) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self._db_path)) as conn:
            cursor = conn.cursor()

            # Saving is a complete snapshot, so an empty list must clear the table.
            cursor.execute(f"DELETE FROM {self._table_name}")
            if not records:
                conn.commit()
                return

            first_record_dict = records[0].to_dict()
            columns = list(first_record_dict.keys())
            placeholders = ", ".join(["?" for _ in columns])
            columns_str = ", ".join(columns)

            insert_query = f"INSERT INTO {self._table_name} ({columns_str}) VALUES ({placeholders})"
            for record in records:
                data = record.to_dict()
                values = tuple(data[col] for col in columns)
                cursor.execute(insert_query, values)

            conn.commit()