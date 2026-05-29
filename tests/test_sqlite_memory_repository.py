import json
import sqlite3
import unittest

from app.market_intelligence.sqlite_memory_schema import create_tables
from app.market_intelligence.sqlite_memory_repository import (
    insert_case,
    insert_case_children,
    insert_event,
)


def fetch_one(connection, query, params=()):
    return connection.execute(query, params).fetchone()


class SQLiteMemoryRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.row_factory = sqlite3.Row
        create_tables(self.connection)

    def tearDown(self):
        self.connection.close()

    def test_insert_case_writes_dispatch_case_row(self):
        case = {
            "case_id": "CASE-1",
            "created_at_utc": "2026-05-28T10:00:00+00:00",
            "updated_at_utc": "2026-05-28T10:05:00+00:00",
            "status": "BOOKED",
            "final_outcome": "BOOKED",
            "driver_name": "Alex",
            "driver_location": "Dallas, TX",
            "driver_equipment": "Flatbed",
            "load_id": "LOAD-1",
            "reference_id": "REF-1",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 1200,
            "loaded_miles": 250,
            "empty_miles": 20,
            "total_miles": 270,
            "total_rpm": 4.44,
            "weight": 42000,
            "posted_trailer_type": "Flatbed",
            "commodity": "Steel",
            "broker_name": "Test Broker",
            "broker_mc": "123456",
            "broker_contact": "555-111-2222",
            "broker_status": "UNKNOWN",
            "credit_score": "95",
            "days_to_pay": "18",
            "ai_decision": {
                "decision": "MATCH",
                "category": "LOAD OPPORTUNITY",
                "score": 91,
                "priority": "HIGH",
                "suggested_action": "SEND",
                "reasons": ["Good rate"],
            },
            "telegram_alerts": [{"telegram_message_id": "777"}],
            "dispatcher_feedback": [{"feedback": "booked"}],
            "ratecons": [{"document_path": "data/ratecons/test.pdf"}],
            "events_count": 3,
        }

        insert_case(self.connection, case)

        row = fetch_one(
            self.connection,
            "SELECT * FROM dispatch_cases WHERE case_id = ?",
            ("CASE-1",),
        )

        self.assertEqual(row["case_id"], "CASE-1")
        self.assertEqual(row["status"], "BOOKED")
        self.assertEqual(row["driver_name"], "Alex")
        self.assertEqual(row["broker_mc"], "123456")
        self.assertEqual(row["ai_decision"], "MATCH")
        self.assertEqual(row["ai_category"], "LOAD OPPORTUNITY")
        self.assertEqual(row["ai_score"], 91)
        self.assertEqual(row["telegram_alert_count"], 1)
        self.assertEqual(row["dispatcher_feedback_count"], 1)
        self.assertEqual(row["ratecon_count"], 1)
        self.assertEqual(row["events_count"], 3)

        reasons = json.loads(row["ai_reasons_json"])
        raw = json.loads(row["raw_json"])

        self.assertEqual(reasons, ["Good rate"])
        self.assertEqual(raw["case_id"], "CASE-1")

    def test_insert_event_writes_dispatch_event_row(self):
        event = {
            "event_id": "EVENT-1",
            "case_id": "CASE-1",
            "event_type": "AI_DECISION_CREATED",
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "driver_name": "Alex",
            "load_id": "LOAD-1",
            "reference_id": "REF-1",
            "source": "unit_test",
            "payload": {
                "decision": "MATCH",
            },
        }

        insert_event(self.connection, event)

        row = fetch_one(
            self.connection,
            "SELECT * FROM dispatch_events WHERE event_id = ?",
            ("EVENT-1",),
        )

        self.assertEqual(row["event_id"], "EVENT-1")
        self.assertEqual(row["case_id"], "CASE-1")
        self.assertEqual(row["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(row["source"], "unit_test")

        payload = json.loads(row["payload_json"])
        raw = json.loads(row["raw_json"])

        self.assertEqual(payload["decision"], "MATCH")
        self.assertEqual(raw["event_id"], "EVENT-1")

    def test_insert_case_children_writes_feedback_alerts_and_ratecons(self):
        case = {
            "case_id": "CASE-1",
            "dispatcher_feedback": [
                {
                    "timestamp_utc": "2026-05-28T10:05:00+00:00",
                    "feedback": "booked",
                    "note": "Booked with broker",
                    "source": "telegram_callback",
                }
            ],
            "telegram_alerts": [
                {
                    "timestamp_utc": "2026-05-28T10:01:00+00:00",
                    "message_type": "MATCH",
                    "category": "LOAD OPPORTUNITY",
                    "telegram_message_id": 777,
                    "send_success": True,
                    "source": "telegram_outbox",
                }
            ],
            "ratecons": [
                {
                    "timestamp_utc": "2026-05-28T10:10:00+00:00",
                    "document_path": "data/ratecons/test.pdf",
                    "note": "Ratecon uploaded",
                    "source": "telegram_document",
                }
            ],
        }

        insert_case_children(self.connection, case)

        feedback = fetch_one(
            self.connection,
            "SELECT * FROM dispatcher_feedback WHERE case_id = ?",
            ("CASE-1",),
        )
        alert = fetch_one(
            self.connection,
            "SELECT * FROM telegram_alerts WHERE case_id = ?",
            ("CASE-1",),
        )
        ratecon = fetch_one(
            self.connection,
            "SELECT * FROM ratecons WHERE case_id = ?",
            ("CASE-1",),
        )

        self.assertEqual(feedback["feedback"], "booked")
        self.assertEqual(feedback["note"], "Booked with broker")
        self.assertEqual(feedback["source"], "telegram_callback")

        self.assertEqual(alert["message_type"], "MATCH")
        self.assertEqual(alert["category"], "LOAD OPPORTUNITY")
        self.assertEqual(alert["telegram_message_id"], "777")
        self.assertEqual(alert["send_success"], 1)

        self.assertEqual(ratecon["document_path"], "data/ratecons/test.pdf")
        self.assertEqual(ratecon["note"], "Ratecon uploaded")
        self.assertEqual(ratecon["source"], "telegram_document")


if __name__ == "__main__":
    unittest.main()
