import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.sqlite_memory_connection import (
    SQLITE_DB_FILE,
    connect_db,
)


class SQLiteMemoryConnectionTest(unittest.TestCase):
    def test_sqlite_db_file_points_to_dispatch_memory_database(self):
        self.assertEqual(
            str(SQLITE_DB_FILE).replace("\\", "/"),
            "data/dispatch_memory.db",
        )

    def test_connect_db_creates_parent_folder_and_returns_row_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nested" / "dispatch_memory.db"

            connection = connect_db(db_path)
            connection.execute("CREATE TABLE test_table (name TEXT)")
            connection.execute("INSERT INTO test_table (name) VALUES (?)", ("Alex",))
            connection.commit()

            row = connection.execute("SELECT name FROM test_table").fetchone()
            connection.close()

            self.assertTrue(db_path.exists())
            self.assertIsInstance(row, sqlite3.Row)
            self.assertEqual(row["name"], "Alex")


if __name__ == "__main__":
    unittest.main()
