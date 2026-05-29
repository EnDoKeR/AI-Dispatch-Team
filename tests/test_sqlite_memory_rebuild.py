import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.market_intelligence.sqlite_memory_rebuild import (
    rebuild_sqlite_memory,
)


def write_jsonl(path, records):
    with open(path, "w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record) + "\n")


class SQLiteMemoryRebuildTest(unittest.TestCase):
    def test_rebuild_sqlite_memory_loads_cases_and_events(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            cases_file = temp_path / "dispatch_cases.jsonl"
            events_file = temp_path / "dispatch_events.jsonl"
            db_path = temp_path / "dispatch_memory.db"

            write_jsonl(
                cases_file,
                [
                    {
                        "case_id": "CASE-1",
                        "created_at_utc": "2026-05-28T10:00:00+00:00",
                        "updated_at_utc": "2026-05-28T10:05:00+00:00",
                        "status": "BOOKED",
                        "final_outcome": "BOOKED",
                        "driver_name": "Alex",
                        "broker_mc": "123456",
                        "reference_id": "REF-1",
                        "ai_decision": {
                            "decision": "MATCH",
                            "category": "LOAD OPPORTUNITY",
                            "score": 90,
                            "priority": "HIGH",
                            "suggested_action": "SEND",
                            "reasons": ["Good load"],
                        },
                        "telegram_alerts": [
                            {
                                "timestamp_utc": "2026-05-28T10:01:00+00:00",
                                "message_type": "MATCH",
                                "category": "LOAD OPPORTUNITY",
                                "telegram_message_id": "777",
                                "send_success": True,
                                "source": "telegram_outbox",
                            }
                        ],
                        "dispatcher_feedback": [
                            {
                                "timestamp_utc": "2026-05-28T10:05:00+00:00",
                                "feedback": "booked",
                                "note": "Booked",
                                "source": "telegram_callback",
                            }
                        ],
                        "ratecons": [
                            {
                                "timestamp_utc": "2026-05-28T10:10:00+00:00",
                                "document_path": "data/ratecons/test.pdf",
                                "note": "Ratecon received",
                                "source": "telegram_document",
                            }
                        ],
                        "events_count": 1,
                    }
                ],
            )
            write_jsonl(
                events_file,
                [
                    {
                        "event_id": "EVENT-1",
                        "case_id": "CASE-1",
                        "event_type": "AI_DECISION_CREATED",
                        "timestamp_utc": "2026-05-28T10:00:00+00:00",
                        "driver_name": "Alex",
                        "load_id": "LOAD-1",
                        "reference_id": "REF-1",
                        "source": "unit_test",
                        "payload": {"decision": "MATCH"},
                    }
                ],
            )

            result = rebuild_sqlite_memory(
                cases_file=cases_file,
                events_file=events_file,
                db_path=db_path,
            )

            self.assertEqual(result["cases_loaded"], 1)
            self.assertEqual(result["events_loaded"], 1)
            self.assertEqual(result["db_path"], str(db_path))

            connection = sqlite3.connect(db_path)
            connection.row_factory = sqlite3.Row

            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dispatch_cases"
                ).fetchone()["count"],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dispatch_events"
                ).fetchone()["count"],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM dispatcher_feedback"
                ).fetchone()["count"],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM telegram_alerts"
                ).fetchone()["count"],
                1,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) AS count FROM ratecons"
                ).fetchone()["count"],
                1,
            )

            connection.close()


if __name__ == "__main__":
    unittest.main()
