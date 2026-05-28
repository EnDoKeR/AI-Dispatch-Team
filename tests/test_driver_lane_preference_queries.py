import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.driver_lane_preference_queries import (
    connect_db,
    get_lane_feedback_rows,
)


def create_test_schema(connection):
    connection.execute(
        """
        CREATE TABLE dispatch_cases (
            case_id TEXT PRIMARY KEY,
            driver_name TEXT,
            pickup TEXT,
            delivery TEXT,
            broker_mc TEXT,
            rate REAL,
            total_miles REAL,
            total_rpm REAL,
            weight REAL,
            status TEXT,
            final_outcome TEXT,
            ai_decision TEXT,
            ai_category TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE dispatcher_feedback (
            case_id TEXT,
            feedback TEXT,
            timestamp_utc TEXT
        )
        """
    )


class DriverLanePreferenceQueriesTest(unittest.TestCase):
    def test_connect_db_returns_row_factory_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "memory.db"

            connection = connect_db(db_path)
            connection.execute("CREATE TABLE test_table (name TEXT)")
            connection.execute("INSERT INTO test_table (name) VALUES (?)", ("Alex",))
            connection.commit()

            row = connection.execute("SELECT name FROM test_table").fetchone()
            connection.close()

            self.assertEqual(row["name"], "Alex")

    def test_get_lane_feedback_rows_groups_feedback_for_lane(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        cases = [
            (
                "CASE-1",
                "Alex",
                "Dallas, TX",
                "Houston, TX",
                "123456",
                1200,
                250,
                4.8,
                40000,
                "BOOKED",
                "BOOKED",
                "MATCH",
                "LOAD OPPORTUNITY",
            ),
            (
                "CASE-2",
                "Alex",
                "Dallas, TX",
                "Houston, TX",
                "123456",
                900,
                250,
                3.6,
                40000,
                "REJECTED",
                "REJECTED",
                "REVIEW_ONCE",
                "RATE CHECK",
            ),
            (
                "CASE-3",
                "Other",
                "Dallas, TX",
                "Houston, TX",
                "123456",
                1000,
                250,
                4.0,
                40000,
                "BOOKED",
                "BOOKED",
                "MATCH",
                "LOAD OPPORTUNITY",
            ),
        ]

        connection.executemany(
            """
            INSERT INTO dispatch_cases (
                case_id,
                driver_name,
                pickup,
                delivery,
                broker_mc,
                rate,
                total_miles,
                total_rpm,
                weight,
                status,
                final_outcome,
                ai_decision,
                ai_category
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            cases,
        )

        feedback_rows = [
            ("CASE-1", "booked", "2026-01-01T10:00:00Z"),
            ("CASE-2", "rate_too_low", "2026-01-02T10:00:00Z"),
            ("CASE-3", "booked", "2026-01-03T10:00:00Z"),
        ]

        connection.executemany(
            """
            INSERT INTO dispatcher_feedback (
                case_id,
                feedback,
                timestamp_utc
            )
            VALUES (?, ?, ?)
            """,
            feedback_rows,
        )
        connection.commit()

        rows = get_lane_feedback_rows(
            connection=connection,
            driver_name="Alex",
            pickup="Dallas",
            delivery="Houston",
            limit=10,
        )

        connection.close()

        self.assertEqual(len(rows), 2)

        feedback_counts = {
            row["feedback"]: row["feedback_count"]
            for row in rows
        }

        self.assertEqual(feedback_counts["booked"], 1)
        self.assertEqual(feedback_counts["rate_too_low"], 1)

        for row in rows:
            self.assertEqual(row["driver_name"], "Alex")
            self.assertEqual(row["pickup"], "Dallas, TX")
            self.assertEqual(row["delivery"], "Houston, TX")

    def test_get_lane_feedback_rows_filters_by_broker_and_feedback(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        connection.execute(
            """
            INSERT INTO dispatch_cases (
                case_id,
                driver_name,
                pickup,
                delivery,
                broker_mc,
                rate,
                total_miles,
                total_rpm,
                weight,
                status,
                final_outcome,
                ai_decision,
                ai_category
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "CASE-1",
                "Alex",
                "Dallas, TX",
                "Houston, TX",
                "999999",
                1200,
                250,
                4.8,
                40000,
                "BOOKED",
                "BOOKED",
                "MATCH",
                "LOAD OPPORTUNITY",
            ),
        )
        connection.execute(
            """
            INSERT INTO dispatcher_feedback (
                case_id,
                feedback,
                timestamp_utc
            )
            VALUES (?, ?, ?)
            """,
            ("CASE-1", "booked", "2026-01-01T10:00:00Z"),
        )
        connection.commit()

        rows = get_lane_feedback_rows(
            connection=connection,
            driver_name="Alex",
            broker_mc="999999",
            feedback="booked",
            limit=10,
        )

        no_rows = get_lane_feedback_rows(
            connection=connection,
            driver_name="Alex",
            broker_mc="000000",
            feedback="booked",
            limit=10,
        )

        connection.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(len(no_rows), 0)


if __name__ == "__main__":
    unittest.main()
