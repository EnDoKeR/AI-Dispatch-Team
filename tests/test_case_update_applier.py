import unittest

from app.market_intelligence.case_update_applier import (
    apply_feedback_to_case,
    apply_outbox_to_case,
)


def build_empty_case():
    return {
        "case_id": "CASE-123",
        "updated_at_utc": "2026-05-28T09:00:00+00:00",
        "status": "OPEN",
        "final_outcome": None,
        "telegram_alerts": [],
        "dispatcher_feedback": [],
        "ratecons": [],
    }


class TestCaseUpdateApplier(unittest.TestCase):
    def test_apply_outbox_to_case_adds_telegram_alert(self):
        case = build_empty_case()
        outbox = {
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "message_type": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "telegram_message_id": "777",
            "send_success": True,
        }

        result = apply_outbox_to_case(case, outbox)

        self.assertIs(result, case)
        self.assertEqual(case["updated_at_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(len(case["telegram_alerts"]), 1)

        alert = case["telegram_alerts"][0]
        self.assertEqual(alert["timestamp_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(alert["message_type"], "REVIEW_ONCE")
        self.assertEqual(alert["category"], "RATE CHECK")
        self.assertEqual(alert["telegram_message_id"], "777")
        self.assertTrue(alert["send_success"])
        self.assertEqual(alert["source"], "telegram_outbox")

    def test_apply_outbox_to_case_uses_existing_updated_at_when_timestamp_missing(self):
        case = build_empty_case()
        outbox = {
            "message_type": "LOAD_OPPORTUNITY",
            "category": "LOAD OPPORTUNITY",
            "telegram_message_id": "888",
            "send_success": True,
        }

        apply_outbox_to_case(case, outbox)

        self.assertEqual(case["updated_at_utc"], "2026-05-28T09:00:00+00:00")
        self.assertEqual(case["telegram_alerts"][0]["timestamp_utc"], "")

    def test_apply_feedback_to_case_adds_dispatcher_feedback(self):
        case = build_empty_case()
        feedback = {
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "dispatcher_feedback": "sent_to_driver",
            "dispatcher_note": "Sent to driver for review",
            "source": "telegram_callback",
            "document_path": "",
        }

        result = apply_feedback_to_case(case, feedback)

        self.assertIs(result, case)
        self.assertEqual(case["updated_at_utc"], "2026-05-28T10:05:00+00:00")
        self.assertEqual(len(case["dispatcher_feedback"]), 1)
        self.assertEqual(case["ratecons"], [])

        feedback_item = case["dispatcher_feedback"][0]
        self.assertEqual(feedback_item["timestamp_utc"], "2026-05-28T10:05:00+00:00")
        self.assertEqual(feedback_item["feedback"], "sent_to_driver")
        self.assertEqual(feedback_item["note"], "Sent to driver for review")
        self.assertEqual(feedback_item["source"], "telegram_callback")

    def test_apply_feedback_to_case_adds_ratecon_when_document_path_exists(self):
        case = build_empty_case()
        feedback = {
            "timestamp_utc": "2026-05-28T10:10:00+00:00",
            "dispatcher_feedback": "ratecon_received",
            "dispatcher_note": "Ratecon uploaded",
            "source": "telegram_document",
            "document_path": "data/ratecons/test.pdf",
        }

        apply_feedback_to_case(case, feedback)

        self.assertEqual(len(case["dispatcher_feedback"]), 1)
        self.assertEqual(len(case["ratecons"]), 1)

        ratecon = case["ratecons"][0]
        self.assertEqual(ratecon["timestamp_utc"], "2026-05-28T10:10:00+00:00")
        self.assertEqual(ratecon["document_path"], "data/ratecons/test.pdf")
        self.assertEqual(ratecon["note"], "Ratecon uploaded")
        self.assertEqual(ratecon["source"], "telegram_document")

    def test_apply_feedback_to_case_updates_status_for_rejected_feedback(self):
        case = build_empty_case()
        feedback = {
            "timestamp_utc": "2026-05-28T10:15:00+00:00",
            "dispatcher_feedback": "driver_rejected",
            "dispatcher_note": "Rejected by dispatcher",
            "source": "telegram_callback",
            "document_path": "",
        }

        apply_feedback_to_case(case, feedback)

        self.assertEqual(case["status"], "REJECTED")
        self.assertEqual(case["final_outcome"], "REJECTED")

    def test_apply_feedback_to_case_updates_status_for_ratecon_received(self):
        case = build_empty_case()
        feedback = {
            "timestamp_utc": "2026-05-28T10:20:00+00:00",
            "dispatcher_feedback": "ratecon_received",
            "dispatcher_note": "Ratecon received",
            "source": "telegram_document",
            "document_path": "data/ratecons/test.pdf",
        }

        apply_feedback_to_case(case, feedback)

        self.assertEqual(case["status"], "RATECON_RECEIVED")
        self.assertEqual(case["final_outcome"], "RATECON_RECEIVED")

    def test_apply_feedback_does_not_downgrade_final_ratecon_status(self):
        case = build_empty_case()
        case["status"] = "RATECON_RECEIVED"
        case["final_outcome"] = "RATECON_RECEIVED"

        feedback = {
            "timestamp_utc": "2026-05-28T10:25:00+00:00",
            "dispatcher_feedback": "sent_to_driver",
            "dispatcher_note": "Later working feedback",
            "source": "telegram_callback",
            "document_path": "",
        }

        apply_feedback_to_case(case, feedback)

        self.assertEqual(case["status"], "RATECON_RECEIVED")
        self.assertEqual(case["final_outcome"], "RATECON_RECEIVED")
        self.assertEqual(len(case["dispatcher_feedback"]), 1)


if __name__ == "__main__":
    unittest.main()
