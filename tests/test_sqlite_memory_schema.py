import sqlite3
import unittest

from app.market_intelligence.sqlite_memory_schema import (
    clear_tables,
    create_tables,
)


EXPECTED_TABLES = {
    "dispatch_cases",
    "dispatch_events",
    "dispatcher_feedback",
    "telegram_alerts",
    "ratecons",
}


class SQLiteMemorySchemaTest(unittest.TestCase):
    def test_create_tables_creates_expected_tables(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row

        create_tables(connection)

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
        table_names = {row["name"] for row in rows}

        connection.close()

        self.assertTrue(EXPECTED_TABLES.issubset(table_names))

    def test_create_tables_creates_expected_indexes(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row

        create_tables(connection)

        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            """
        ).fetchall()
        index_names = {row["name"] for row in rows}

        connection.close()

        self.assertIn("idx_cases_driver", index_names)
        self.assertIn("idx_cases_status", index_names)
        self.assertIn("idx_cases_reference", index_names)
        self.assertIn("idx_cases_broker_mc", index_names)
        self.assertIn("idx_events_case", index_names)
        self.assertIn("idx_events_type", index_names)

    def test_clear_tables_removes_records_from_all_memory_tables(self):
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
        connection.execute(
            """
            INSERT INTO dispatch_events (
                event_id,
                case_id
            )
            VALUES ('EVENT-1', 'CASE-1')
            """
        )
        connection.execute(
            """
            INSERT INTO dispatcher_feedback (
                case_id
            )
            VALUES ('CASE-1')
            """
        )
        connection.execute(
            """
            INSERT INTO telegram_alerts (
                case_id
            )
            VALUES ('CASE-1')
            """
        )
        connection.execute(
            """
            INSERT INTO ratecons (
                case_id
            )
            VALUES ('CASE-1')
            """
        )
        connection.commit()

        clear_tables(connection)

        for table_name in EXPECTED_TABLES:
            row = connection.execute(
                f"SELECT COUNT(*) AS count FROM {table_name}"
            ).fetchone()
            self.assertEqual(row["count"], 0)

        connection.close()


if __name__ == "__main__":
    unittest.main()
