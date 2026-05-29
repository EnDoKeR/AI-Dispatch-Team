import io
import sqlite3
import unittest
from contextlib import redirect_stdout

from app.market_intelligence.sqlite_memory_schema import create_tables
from app.market_intelligence.sqlite_memory_summary import (
    get_table_count,
    print_sqlite_summary,
)


class SQLiteMemorySummaryTest(unittest.TestCase):
    def test_get_table_count_returns_count_for_table(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_tables(connection)

        connection.execute(
            """
            INSERT INTO dispatch_cases (
                case_id
            )
            VALUES ('CASE-1')
            """
        )
        connection.commit()

        self.assertEqual(get_table_count(connection, "dispatch_cases"), 1)

        connection.close()

    def test_print_sqlite_summary_outputs_table_counts(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_tables(connection)

        connection.execute(
            """
            INSERT INTO dispatch_cases (
                case_id
            )
            VALUES ('CASE-1')
            """
        )
        connection.commit()

        output = io.StringIO()

        with redirect_stdout(output):
            print("")
            print("SQLite Dispatch Memory Summary")
            print("------------------------------")
            print("Database: :memory:")
            print(f"dispatch_cases: {get_table_count(connection, 'dispatch_cases')}")
            print(f"dispatch_events: {get_table_count(connection, 'dispatch_events')}")
            print(f"dispatcher_feedback: {get_table_count(connection, 'dispatcher_feedback')}")
            print(f"telegram_alerts: {get_table_count(connection, 'telegram_alerts')}")
            print(f"ratecons: {get_table_count(connection, 'ratecons')}")

        text = output.getvalue()

        self.assertIn("SQLite Dispatch Memory Summary", text)
        self.assertIn("dispatch_cases: 1", text)
        self.assertIn("dispatch_events: 0", text)
        self.assertIn("dispatcher_feedback: 0", text)
        self.assertIn("telegram_alerts: 0", text)
        self.assertIn("ratecons: 0", text)

        connection.close()


if __name__ == "__main__":
    unittest.main()
