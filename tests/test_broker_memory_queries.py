import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.broker_memory_queries import (
    connect_db,
    get_broker_case_counts,
    get_broker_feedback_counts,
)


def create_test_schema(connection):
    connection.execute(
        """
        CREATE TABLE dispatch_cases (
            case_id TEXT PRIMARY KEY,
            broker_mc TEXT,
            status TEXT,
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
    broker_mc="123456",
    status="BOOKED",
    ai_category="LOAD OPPORTUNITY",
    telegram_alert_count=1,
    dispatcher_feedback_count=1,
    ratecon_count=1,
):
    connection.execute(
        """
        INSERT INTO dispatch_cases (
            case_id,
            broker_mc,
            status,
            ai_category,
            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            broker_mc,
            status,
            ai_category,
            telegram_alert_count,
            dispatcher_feedback_count,
            ratecon_count,
        ),
    )


class BrokerMemoryQueriesTest(unittest.TestCase):
    def test_connect_db_returns_row_factory_connection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "memory.db"

            connection = connect_db(db_path)
            connection.execute("CREATE TABLE test_table (name TEXT)")
            connection.execute("INSERT INTO test_table (name) VALUES (?)", ("Broker",))
            connection.commit()

            row = connection.execute("SELECT name FROM test_table").fetchone()
            connection.close()

            self.assertEqual(row["name"], "Broker")

    def test_get_broker_feedback_counts_groups_feedback(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        insert_case(connection, "CASE-1", broker_mc="123456")
        insert_case(connection, "CASE-2", broker_mc="123456")
        insert_case(connection, "CASE-3", broker_mc="999999")

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
                ("CASE-3", "bad_broker"),
            ],
        )
        connection.commit()

        result = get_broker_feedback_counts(connection, "123456")
        connection.close()

        self.assertEqual(result, {"booked": 1, "rate_too_low": 1})

    def test_get_broker_case_counts_returns_aggregated_counts(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        insert_case(
            connection,
            "CASE-1",
            broker_mc="123456",
            status="BOOKED",
            ai_category="LOAD OPPORTUNITY",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=1,
        )
        insert_case(
            connection,
            "CASE-2",
            broker_mc="123456",
            status="REJECTED",
            ai_category="RATE CHECK",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=0,
        )
        insert_case(
            connection,
            "CASE-3",
            broker_mc="999999",
            status="BOOKED",
            ai_category="LOAD OPPORTUNITY",
            telegram_alert_count=1,
            dispatcher_feedback_count=1,
            ratecon_count=1,
        )
        connection.commit()

        result = get_broker_case_counts(connection, "123456")
        connection.close()

        self.assertEqual(result["total_cases"], 2)
        self.assertEqual(result["booked_cases"], 1)
        self.assertEqual(result["rejected_cases"], 1)
        self.assertEqual(result["load_opportunity_cases"], 1)
        self.assertEqual(result["rate_check_cases"], 1)
        self.assertEqual(result["telegram_alerts"], 2)
        self.assertEqual(result["feedback_items"], 2)
        self.assertEqual(result["ratecons"], 1)

    def test_invalid_mc_returns_empty_results(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        create_test_schema(connection)

        self.assertEqual(get_broker_feedback_counts(connection, "NEEDS CHECK"), {})
        self.assertEqual(get_broker_case_counts(connection, "NEEDS CHECK"), {})

        connection.close()


if __name__ == "__main__":
    unittest.main()
