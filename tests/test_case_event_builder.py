import unittest

from app.market_intelligence.case_event_builder import (
    build_ai_decision_created_event,
    build_dispatcher_feedback_added_event,
    build_load_board_simulation_event,
    build_ratecon_received_event,
    build_telegram_alert_sent_event,
    dedupe_dispatch_events,
)


class TestCaseEventBuilder(unittest.TestCase):
    def test_build_ai_decision_created_event(self):
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }
        decision = {
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "decision": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "score": 82,
            "reasons": ["rate missing"],
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 0,
        }

        event = build_ai_decision_created_event(
            case_id="CASE-123",
            case_record=case,
            decision_record=decision,
        )

        self.assertEqual(event["case_id"], "CASE-123")
        self.assertEqual(event["event_type"], "AI_DECISION_CREATED")
        self.assertEqual(event["source"], "decision_logger")
        self.assertEqual(event["driver_name"], "Alex")
        self.assertEqual(event["load_id"], "LOAD-123")
        self.assertEqual(event["reference_id"], "REF-123")
        self.assertEqual(event["timestamp_utc"], "2026-05-28T10:00:00+00:00")
        self.assertTrue(event["event_id"].startswith("EVT-"))
        self.assertEqual(event["payload"]["decision"], "REVIEW_ONCE")
        self.assertEqual(event["payload"]["category"], "RATE CHECK")
        self.assertEqual(event["payload"]["score"], 82)
        self.assertEqual(event["payload"]["reasons"], ["rate missing"])
        self.assertEqual(event["payload"]["rate"], 0)

    def test_build_telegram_alert_sent_event(self):
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }
        outbox = {
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "message_type": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "telegram_message_id": "777",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": "",
            "broker": "Test Broker",
            "broker_mc": "123456",
            "reference_id": "REF-123",
        }

        event = build_telegram_alert_sent_event(
            case_id="CASE-123",
            case_record=case,
            outbox_record=outbox,
        )

        self.assertEqual(event["event_type"], "TELEGRAM_ALERT_SENT")
        self.assertEqual(event["source"], "telegram_outbox")
        self.assertEqual(event["payload"]["message_type"], "REVIEW_ONCE")
        self.assertEqual(event["payload"]["telegram_message_id"], "777")
        self.assertEqual(event["payload"]["broker"], "Test Broker")
        self.assertEqual(event["payload"]["broker_mc"], "123456")
        self.assertEqual(event["payload"]["reference_id"], "REF-123")

    def test_build_load_board_simulation_appeared_event(self):
        case = {
            "driver_name": "Alex",
            "load_id": "SIM-CLEAN-001",
            "reference_id": "SIM-CLEAN-001",
        }
        simulation_event = {
            "timestamp_utc": "2026-05-28T10:10:00+00:00",
            "simulation_step": 1,
            "event_time": "2026-05-28T10:00:00",
            "event_type": "LOAD_APPEARED",
            "load_id": "SIM-CLEAN-001",
            "payload": {
                "load": {
                    "pickup": "Stockton, CA",
                    "delivery": "Dallas, TX",
                    "rate": 4100,
                    "broker_name": "Simulation Broker",
                    "broker_mc": "777001",
                    "reference_id": "SIM-CLEAN-001",
                }
            },
        }

        event = build_load_board_simulation_event(
            case_id="CASE-SIM",
            case_record=case,
            simulation_event=simulation_event,
        )

        self.assertEqual(event["event_type"], "LOAD_APPEARED")
        self.assertEqual(event["source"], "load_board_simulation")
        self.assertEqual(event["payload"]["simulation_step"], 1)
        self.assertEqual(event["payload"]["simulation_load_id"], "SIM-CLEAN-001")
        self.assertEqual(event["payload"]["pickup"], "Stockton, CA")
        self.assertEqual(event["payload"]["delivery"], "Dallas, TX")
        self.assertEqual(event["payload"]["rate"], 4100)
        self.assertEqual(event["payload"]["broker"], "Simulation Broker")
        self.assertEqual(event["payload"]["broker_mc"], "777001")

    def test_build_dispatcher_feedback_added_event(self):
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }
        feedback = {
            "timestamp_utc": "2026-05-28T10:15:00+00:00",
            "source": "dispatcher_feedback",
            "dispatcher_feedback": "rejected",
            "dispatcher_note": "Bad lane",
            "document_path": "",
        }

        event = build_dispatcher_feedback_added_event(
            case_id="CASE-123",
            case_record=case,
            feedback_record=feedback,
        )

        self.assertEqual(event["event_type"], "DISPATCHER_FEEDBACK_ADDED")
        self.assertEqual(event["source"], "dispatcher_feedback")
        self.assertEqual(event["payload"]["feedback"], "rejected")
        self.assertEqual(event["payload"]["note"], "Bad lane")
        self.assertEqual(event["payload"]["document_path"], "")

    def test_build_ratecon_received_event(self):
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }
        feedback = {
            "timestamp_utc": "2026-05-28T10:20:00+00:00",
            "source": "telegram_document",
            "document_path": "data/ratecons/test.pdf",
            "dispatcher_note": "Ratecon received",
        }

        event = build_ratecon_received_event(
            case_id="CASE-123",
            case_record=case,
            feedback_record=feedback,
        )

        self.assertEqual(event["event_type"], "RATECON_RECEIVED")
        self.assertEqual(event["source"], "telegram_document")
        self.assertEqual(event["payload"]["document_path"], "data/ratecons/test.pdf")
        self.assertEqual(event["payload"]["note"], "Ratecon received")

    def test_dedupe_dispatch_events_removes_exact_duplicate_event_keys(self):
        event_1 = {
            "case_id": "CASE-123",
            "event_type": "TELEGRAM_ALERT_SENT",
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "source": "telegram_outbox",
            "payload": {
                "telegram_message_id": "777",
            },
        }
        event_2 = dict(event_1)
        event_3 = {
            "case_id": "CASE-123",
            "event_type": "TELEGRAM_ALERT_SENT",
            "timestamp_utc": "2026-05-28T10:01:00+00:00",
            "source": "telegram_outbox",
            "payload": {
                "telegram_message_id": "778",
            },
        }

        deduped = dedupe_dispatch_events([event_1, event_2, event_3])

        self.assertEqual(len(deduped), 2)
        self.assertEqual(deduped[0]["payload"]["telegram_message_id"], "777")
        self.assertEqual(deduped[1]["payload"]["telegram_message_id"], "778")


if __name__ == "__main__":
    unittest.main()
