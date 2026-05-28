import unittest

from app.market_intelligence.case_factory import (
    build_case_from_decision,
    build_case_from_feedback,
    build_case_from_outbox,
    safe,
)


class TestCaseFactory(unittest.TestCase):
    def test_safe_returns_default_for_none(self):
        self.assertEqual(safe(None), "")
        self.assertEqual(safe(None, default="UNKNOWN"), "UNKNOWN")

    def test_safe_keeps_valid_falsey_values(self):
        self.assertEqual(safe(0), 0)
        self.assertEqual(safe(False), False)
        self.assertEqual(safe(""), "")

    def test_build_case_from_decision_creates_full_case_record(self):
        decision = {
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

        case = build_case_from_decision(decision)

        self.assertTrue(case["case_id"].startswith("CASE-"))
        self.assertEqual(case["created_at_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(case["updated_at_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(case["status"], "OPEN")
        self.assertIsNone(case["final_outcome"])

        self.assertEqual(case["driver_name"], "Alex")
        self.assertEqual(case["driver_location"], "Dallas, TX")
        self.assertEqual(case["driver_equipment"], "Flatbed")

        self.assertEqual(case["load_id"], "LOAD-123")
        self.assertEqual(case["reference_id"], "REF-123")
        self.assertEqual(case["pickup"], "Dallas, TX")
        self.assertEqual(case["delivery"], "Houston, TX")
        self.assertEqual(case["rate"], 2200)
        self.assertEqual(case["loaded_miles"], 240)
        self.assertEqual(case["empty_miles"], 20)
        self.assertEqual(case["total_miles"], 260)
        self.assertEqual(case["total_rpm"], 8.46)
        self.assertEqual(case["weight"], 36000)
        self.assertEqual(case["posted_trailer_type"], "Flatbed")
        self.assertEqual(case["commodity"], "Steel")

        self.assertEqual(case["broker_name"], "Test Broker")
        self.assertEqual(case["broker_mc"], "123456")
        self.assertEqual(case["broker_contact"], "broker@example.com")
        self.assertEqual(case["broker_status"], "UNKNOWN")
        self.assertEqual(case["credit_score"], 95)
        self.assertEqual(case["days_to_pay"], 18)

        self.assertEqual(case["ai_decision"]["decision"], "MATCH")
        self.assertEqual(case["ai_decision"]["category"], "LOAD OPPORTUNITY")
        self.assertEqual(case["ai_decision"]["score"], 91)
        self.assertEqual(case["ai_decision"]["priority"], "HIGH")
        self.assertEqual(case["ai_decision"]["suggested_action"], "SEND")
        self.assertEqual(case["ai_decision"]["reasons"], ["clean fit"])
        self.assertEqual(
            case["ai_decision"]["timestamp_utc"],
            "2026-05-28T10:00:00+00:00",
        )

        self.assertEqual(case["telegram_alerts"], [])
        self.assertEqual(case["dispatcher_feedback"], [])
        self.assertEqual(case["ratecons"], [])
        self.assertEqual(case["events_count"], 0)

    def test_build_case_from_decision_preserves_zero_rate(self):
        decision = {
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "driver_name": "Alex",
            "load_id": "LOAD-RATECHECK",
            "reference_id": "REF-RATECHECK",
            "broker_mc": "123456",
            "rate": 0,
            "decision": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "score": 75,
        }

        case = build_case_from_decision(decision)

        self.assertEqual(case["rate"], 0)
        self.assertEqual(case["ai_decision"]["decision"], "REVIEW_ONCE")
        self.assertEqual(case["ai_decision"]["category"], "RATE CHECK")

    def test_build_case_from_decision_converts_none_fields_to_empty_string(self):
        decision = {
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "driver_name": None,
            "driver_location": None,
            "driver_equipment": None,
            "load_id": None,
            "reference_id": None,
            "pickup": None,
            "delivery": None,
            "broker_name": None,
            "broker_mc": None,
            "broker_contact": None,
            "broker_status": None,
        }

        case = build_case_from_decision(decision)

        self.assertEqual(case["driver_name"], "")
        self.assertEqual(case["driver_location"], "")
        self.assertEqual(case["driver_equipment"], "")
        self.assertEqual(case["load_id"], "")
        self.assertEqual(case["reference_id"], "")
        self.assertEqual(case["pickup"], "")
        self.assertEqual(case["delivery"], "")
        self.assertEqual(case["broker_name"], "")
        self.assertEqual(case["broker_mc"], "")
        self.assertEqual(case["broker_contact"], "")
        self.assertEqual(case["broker_status"], "")

    def test_build_case_from_outbox_creates_case_record(self):
        outbox = {
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "driver_name": "Alex",
            "reference_id": "REF-123",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": "",
            "broker": "Telegram Broker",
            "broker_mc": "654321",
            "category": "RATE CHECK",
        }

        case = build_case_from_outbox(outbox)

        self.assertTrue(case["case_id"].startswith("CASE-"))
        self.assertEqual(case["created_at_utc"], "2026-05-28T10:05:00+00:00")
        self.assertEqual(case["updated_at_utc"], "2026-05-28T10:05:00+00:00")
        self.assertEqual(case["status"], "OPEN")
        self.assertIsNone(case["final_outcome"])

        self.assertEqual(case["driver_name"], "Alex")
        self.assertEqual(case["driver_location"], "")
        self.assertEqual(case["driver_equipment"], "")

        self.assertEqual(case["load_id"], "")
        self.assertEqual(case["reference_id"], "REF-123")
        self.assertEqual(case["pickup"], "Dallas, TX")
        self.assertEqual(case["delivery"], "Houston, TX")
        self.assertEqual(case["rate"], "")

        self.assertEqual(case["loaded_miles"], 0)
        self.assertEqual(case["empty_miles"], 0)
        self.assertEqual(case["total_miles"], 0)
        self.assertEqual(case["total_rpm"], 0)
        self.assertEqual(case["weight"], 0)
        self.assertEqual(case["posted_trailer_type"], "")
        self.assertEqual(case["commodity"], "")

        self.assertEqual(case["broker_name"], "Telegram Broker")
        self.assertEqual(case["broker_mc"], "654321")
        self.assertEqual(case["broker_contact"], "")
        self.assertEqual(case["broker_status"], "")
        self.assertEqual(case["credit_score"], "")
        self.assertEqual(case["days_to_pay"], "")

        self.assertEqual(case["ai_decision"]["decision"], "")
        self.assertEqual(case["ai_decision"]["category"], "RATE CHECK")
        self.assertEqual(case["ai_decision"]["score"], 0)
        self.assertEqual(case["ai_decision"]["priority"], "")
        self.assertEqual(case["ai_decision"]["suggested_action"], "")
        self.assertEqual(case["ai_decision"]["reasons"], [])
        self.assertEqual(case["ai_decision"]["timestamp_utc"], "")

        self.assertEqual(case["telegram_alerts"], [])
        self.assertEqual(case["dispatcher_feedback"], [])
        self.assertEqual(case["ratecons"], [])
        self.assertEqual(case["events_count"], 0)

    def test_build_case_from_outbox_uses_empty_load_id_for_case_id(self):
        outbox = {
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "driver_name": "Alex",
            "reference_id": "REF-123",
            "broker_mc": "654321",
        }

        expected_case_id = build_case_from_outbox(outbox)["case_id"]

        outbox_with_unused_load_id = dict(outbox)
        outbox_with_unused_load_id["load_id"] = "SHOULD-NOT-BE-USED"

        actual_case_id = build_case_from_outbox(outbox_with_unused_load_id)["case_id"]

        self.assertEqual(actual_case_id, expected_case_id)


    def test_build_case_from_feedback_creates_fallback_case(self):
        feedback = {
            "timestamp_utc": "2026-05-28T10:30:00+00:00",
            "driver_name": "Alex",
            "load_id": "LOAD-FEEDBACK",
            "reference_id": "REF-FEEDBACK",
            "pickup": "Dallas, TX",
            "delivery": "Austin, TX",
            "rate": 1800,
            "broker_name": "Feedback Broker",
            "broker_mc": "777777",
            "dispatcher_feedback": "driver_rejected",
            "ai_decision": "REVIEW_ONCE",
            "ai_category": "RATE CHECK",
            "ai_score": 70,
            "ai_reasons": ["created from feedback only"],
        }

        case = build_case_from_feedback(
            feedback_record=feedback,
            case_id="CASE-FEEDBACK",
        )

        self.assertEqual(case["case_id"], "CASE-FEEDBACK")
        self.assertEqual(case["created_at_utc"], "2026-05-28T10:30:00+00:00")
        self.assertEqual(case["updated_at_utc"], "2026-05-28T10:30:00+00:00")
        self.assertEqual(case["status"], "REJECTED")
        self.assertEqual(case["final_outcome"], "REJECTED")

        self.assertEqual(case["driver_name"], "Alex")
        self.assertEqual(case["driver_location"], "")
        self.assertEqual(case["driver_equipment"], "")

        self.assertEqual(case["load_id"], "LOAD-FEEDBACK")
        self.assertEqual(case["reference_id"], "REF-FEEDBACK")
        self.assertEqual(case["pickup"], "Dallas, TX")
        self.assertEqual(case["delivery"], "Austin, TX")
        self.assertEqual(case["rate"], 1800)

        self.assertEqual(case["broker_name"], "Feedback Broker")
        self.assertEqual(case["broker_mc"], "777777")
        self.assertEqual(case["broker_contact"], "")
        self.assertEqual(case["broker_status"], "")

        self.assertEqual(case["ai_decision"]["decision"], "REVIEW_ONCE")
        self.assertEqual(case["ai_decision"]["category"], "RATE CHECK")
        self.assertEqual(case["ai_decision"]["score"], 70)
        self.assertEqual(case["ai_decision"]["reasons"], ["created from feedback only"])

        self.assertEqual(case["telegram_alerts"], [])
        self.assertEqual(case["dispatcher_feedback"], [])
        self.assertEqual(case["ratecons"], [])
        self.assertEqual(case["events_count"], 0)

if __name__ == "__main__":
    unittest.main()
