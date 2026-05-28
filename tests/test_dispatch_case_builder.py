import unittest

from app.market_intelligence.dispatch_case import build_cases_and_events


class TestDispatchCaseBuilder(unittest.TestCase):
    def test_build_cases_and_events_builds_full_case_timeline(self):
        decision_records = [
            {
                "timestamp_utc": "2026-05-28T10:00:00+00:00",
                "driver_name": "Alex",
                "driver_location": "Dallas, TX",
                "driver_equipment": "Flatbed",
                "load_id": "LOAD-123",
                "reference_id": "REF-123",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": 2200,
                "loaded_miles": 240,
                "empty_miles": 20,
                "total_miles": 260,
                "total_rpm": 8.46,
                "weight": 36000,
                "posted_trailer_type": "Flatbed",
                "commodity": "Steel",
                "broker_name": "Test Broker",
                "broker_mc": "123456",
                "broker_contact": "broker@example.com",
                "broker_status": "UNKNOWN",
                "credit_score": 95,
                "days_to_pay": 18,
                "decision": "MATCH",
                "category": "LOAD OPPORTUNITY",
                "score": 91,
                "priority": "HIGH",
                "suggested_action": "SEND",
                "reasons": ["clean fit"],
            }
        ]

        telegram_outbox_records = [
            {
                "timestamp_utc": "2026-05-28T10:05:00+00:00",
                "driver_name": "Alex",
                "send_success": True,
                "message_type": "LOAD_OPPORTUNITY",
                "category": "LOAD OPPORTUNITY",
                "telegram_message_id": "777",
                "reference_id": "REF-123",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": 2200,
                "broker": "Test Broker",
                "broker_mc": "123456",
            }
        ]

        simulation_event_records = [
            {
                "timestamp_utc": "2026-05-28T10:06:00+00:00",
                "simulation_step": 1,
                "event_time": "2026-05-28T10:06:00",
                "event_type": "LOAD_APPEARED",
                "load_id": "REF-123",
                "payload": {
                    "load": {
                        "pickup": "Dallas, TX",
                        "delivery": "Houston, TX",
                        "rate": 2200,
                        "broker_name": "Test Broker",
                        "broker_mc": "123456",
                        "reference_id": "REF-123",
                    }
                },
            }
        ]

        feedback_records = [
            {
                "timestamp_utc": "2026-05-28T10:10:00+00:00",
                "driver_name": "Alex",
                "load_id": "LOAD-123",
                "reference_id": "REF-123",
                "broker_mc": "123456",
                "dispatcher_feedback": "ratecon_received",
                "dispatcher_note": "Ratecon uploaded",
                "source": "telegram_document",
                "document_path": "data/ratecons/test.pdf",
            }
        ]

        cases, events = build_cases_and_events(
            decision_records=decision_records,
            feedback_records=feedback_records,
            telegram_outbox_records=telegram_outbox_records,
            simulation_event_records=simulation_event_records,
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(len(events), 5)

        case = cases[0]

        self.assertEqual(case["driver_name"], "Alex")
        self.assertEqual(case["load_id"], "LOAD-123")
        self.assertEqual(case["reference_id"], "REF-123")
        self.assertEqual(case["status"], "RATECON_RECEIVED")
        self.assertEqual(case["final_outcome"], "RATECON_RECEIVED")
        self.assertEqual(case["events_count"], 5)

        self.assertEqual(len(case["telegram_alerts"]), 1)
        self.assertEqual(len(case["dispatcher_feedback"]), 1)
        self.assertEqual(len(case["ratecons"]), 1)

        event_types = [event["event_type"] for event in events]

        self.assertEqual(
            event_types,
            [
                "AI_DECISION_CREATED",
                "TELEGRAM_ALERT_SENT",
                "LOAD_APPEARED",
                "DISPATCHER_FEEDBACK_ADDED",
                "RATECON_RECEIVED",
            ],
        )

    def test_build_cases_and_events_ignores_failed_outbox(self):
        decision_records = [
            {
                "timestamp_utc": "2026-05-28T10:00:00+00:00",
                "driver_name": "Alex",
                "load_id": "LOAD-123",
                "reference_id": "REF-123",
                "broker_mc": "123456",
                "decision": "MATCH",
                "category": "LOAD OPPORTUNITY",
            }
        ]

        telegram_outbox_records = [
            {
                "timestamp_utc": "2026-05-28T10:05:00+00:00",
                "driver_name": "Alex",
                "send_success": False,
                "message_type": "LOAD_OPPORTUNITY",
                "reference_id": "REF-123",
            }
        ]

        cases, events = build_cases_and_events(
            decision_records=decision_records,
            feedback_records=[],
            telegram_outbox_records=telegram_outbox_records,
            simulation_event_records=[],
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(cases[0]["telegram_alerts"], [])
        self.assertEqual(cases[0]["events_count"], 1)

    def test_build_cases_and_events_creates_case_from_outbox_when_no_decision_match(self):
        telegram_outbox_records = [
            {
                "timestamp_utc": "2026-05-28T10:05:00+00:00",
                "driver_name": "Alex",
                "send_success": True,
                "message_type": "REVIEW_ONCE",
                "category": "RATE CHECK",
                "telegram_message_id": "777",
                "reference_id": "REF-OUTBOX-ONLY",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": "",
                "broker": "Outbox Broker",
                "broker_mc": "654321",
            }
        ]

        cases, events = build_cases_and_events(
            decision_records=[],
            feedback_records=[],
            telegram_outbox_records=telegram_outbox_records,
            simulation_event_records=[],
        )

        self.assertEqual(len(cases), 1)
        self.assertEqual(len(events), 1)

        case = cases[0]
        self.assertEqual(case["driver_name"], "Alex")
        self.assertEqual(case["reference_id"], "REF-OUTBOX-ONLY")
        self.assertEqual(case["broker_name"], "Outbox Broker")
        self.assertEqual(case["ai_decision"]["category"], "RATE CHECK")
        self.assertEqual(case["events_count"], 1)

        self.assertEqual(events[0]["event_type"], "TELEGRAM_ALERT_SENT")


if __name__ == "__main__":
    unittest.main()
