import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.driver_preference_queries import (
    connect_db,
    get_driver_case_counts,
    get_driver_feedback_counts,
    get_driver_lane_feedback,
)


def create_test_schema(connection):
    connection.execute(
        """
        CREATE TABLE dispatch_cases (
            case_id TEXT PRIMARY KEY,
            driver_name TEXT,
            pickup TEXT,
            delivery TEXT,
            rate REAL,
            total_miles REAL,
            total_rpm REAL,
            status TEXT,
            final_outcome TEXT,
            ai_decision TEXT,
            ai_category TEXT,
            telegram_alert_count INTEGER,
            dispatcher_feedback_count INTEGER,
            ratecon_count INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE dispatcher_feedback (
            case_id TEXT,
            feedback TEXT
        )
        """
    )


def insert_case(
    connection,
    case_id,
    driver_name="Alex",
    pickup="Dallas, TX",
    delivery="Houston, TX",
    rate=1200,
    total_miles=250,
    total_rpm=4.8,
    status="BOOKED",
    final_outcome="BOOKED",
    ai_decision="MATCH",
    ai_category="LOAD OPPORTUNITY",
    telegram_alert_count=1,
    dispatcher_feedback_count=1,
    ratecon_count=1,
):
    connection.execute(
        """
        INSERT INTO dispatch_cases (
            case_id,
            driver_name,
            pickup,
            delivery,
            rate,
            total_miles,
            total_rpm,
            status,
            final_outcome,
            ai_decision,
            ai_category,
            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            driver_name,
            pickup,
            delivery,
            rate,
            total_miles,
            total_rpm,
            status,
            final_outcome,
            ai_decision,
            ai_category,
            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count,
        ),
    )


class DriverPreferenceQueriesTest(unittest.TestCase):
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

    def test_get_driver_feedback_counts_groups_feedback(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        insert_case(connection, "CASE-1", driver_name="Alex")
        insert_case(connection, "CASE-2", driver_name="Alex")
        insert_case(connection, "CASE-3", driver_name="Other")

        connection.executemany(
            """
            INSERT INTO dispatcher_feedback (
                case_id,
                feedback
            )
            VALUES (?, ?)
            """,
            [
                ("CASE-1", "booked"),
                ("CASE-2", "rate_too_low"),
                ("CASE-3", "booked"),
            ],
        )
        connection.commit()

        result = get_driver_feedback_counts(connection, "Alex")
        connection.close()

        self.assertEqual(result, {"booked": 1, "rate_too_low": 1})

    def test_get_driver_case_counts_returns_aggregated_case_counts(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        insert_case(
            connection,
            "CASE-1",
            driver_name="Alex",
            status="BOOKED",
            final_outcome="BOOKED",
            ai_decision="MATCH",
            ai_category="LOAD OPPORTUNITY",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=1,
        )
        insert_case(
            connection,
            "CASE-2",
            driver_name="Alex",
            status="REJECTED",
            final_outcome="REJECTED",
            ai_decision="REVIEW_ONCE",
            ai_category="RATE CHECK",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=0,
        )
        insert_case(
            connection,
            "CASE-3",
            driver_name="Other",
            status="BOOKED",
            final_outcome="BOOKED",
            ai_decision="MATCH",
            ai_category="LOAD OPPORTUNITY",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=1,
        )
        connection.commit()

        result = get_driver_case_counts(connection, "Alex")
        connection.close()

        self.assertEqual(result["total_cases"], 2)
        self.assertEqual(result["booked_cases"], 1)
        self.assertEqual(result["rejected_cases"], 1)
        self.assertEqual(result["final_booked"], 1)
        self.assertEqual(result["final_rejected"], 1)
        self.assertEqual(result["match_cases"], 1)
        self.assertEqual(result["review_once_cases"], 1)
        self.assertEqual(result["load_opportunity_cases"], 1)
        self.assertEqual(result["rate_check_cases"], 1)
        self.assertEqual(result["telegram_alerts"], 2)
        self.assertEqual(result["feedback_items"], 2)
        self.assertEqual(result["ratecons"], 1)

    def test_get_driver_lane_feedback_returns_lane_rows(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        insert_case(
            connection,
            "CASE-1",
            driver_name="Alex",
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate=1200,
            total_miles=250,
            total_rpm=4.8,
        )
        insert_case(
            connection,
            "CASE-2",
            driver_name="Alex",
            pickup="Dallas, TX",
            delivery="Houston, TX",
            rate=1000,
            total_miles=250,
            total_rpm=4.0,
        )

        connection.executemany(
            """
            INSERT INTO dispatcher_feedback (
                case_id,
                feedback
            )
            VALUES (?, ?)
            """,
            [
                ("CASE-1", "booked"),
                ("CASE-2", "booked"),
            ],
        )
        connection.commit()

        rows = get_driver_lane_feedback(connection, "Alex", limit=10)
        connection.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pickup"], "Dallas, TX")
        self.assertEqual(rows[0]["delivery"], "Houston, TX")
        self.assertEqual(rows[0]["feedback"], "booked")
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[0]["avg_rate"], 1100)
        self.assertEqual(rows[0]["avg_total_miles"], 250)
        self.assertEqual(rows[0]["avg_rpm"], 4.4)

    def test_invalid_driver_returns_empty_results(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        self.assertEqual(get_driver_feedback_counts(connection, "UNKNOWN"), {})
        self.assertEqual(get_driver_case_counts(connection, "UNKNOWN"), {})
        self.assertEqual(get_driver_lane_feedback(connection, "UNKNOWN"), [])

        connection.close()


if __name__ == "__main__":
    unittest.main()
