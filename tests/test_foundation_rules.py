import unittest
from types import SimpleNamespace

from app.market_intelligence.case_status_engine import status_update_from_feedback
from app.market_intelligence.dispatch_case import apply_feedback_to_case

from app.market_intelligence.driver_preference_rules import (
    get_sample_quality as get_driver_sample_quality,
)
from app.market_intelligence.driver_lane_preference_rules import (
    get_sample_quality as get_lane_sample_quality,
)
from app.market_intelligence.telegram_notifier import get_broker_status_text


def make_case_record():
    return {
        "case_id": "TEST-CASE-001",
        "created_at_utc": "2026-01-01T00:00:00Z",
        "updated_at_utc": "2026-01-01T00:00:00Z",
        "status": "OPEN",
        "final_outcome": None,
        "driver_name": "TestDriver",
        "load_id": "TEST-LOAD-001",
        "reference_id": "TEST-REF-001",
        "dispatcher_feedback": [],
        "ratecons": [],
    }


def make_feedback(feedback_type, timestamp="2026-01-01T01:00:00Z"):
    return {
        "timestamp_utc": timestamp,
        "dispatcher_feedback": feedback_type,
        "dispatcher_note": f"Test feedback: {feedback_type}",
        "source": "unit_test",
        "document_path": "",
    }


class DispatchCaseStatusRulesTest(unittest.TestCase):
    def test_called_broker_maps_to_called(self):
        status_update = status_update_from_feedback("called_broker")

        self.assertEqual(status_update["status"], "CALLED")
        self.assertIsNone(status_update["final_outcome"])

    def test_sent_to_driver_maps_to_working_status(self):
        status_update = status_update_from_feedback("sent_to_driver")

        self.assertEqual(status_update["status"], "SENT_TO_DRIVER")
        self.assertIsNone(status_update["final_outcome"])

    def test_booked_maps_to_final_status(self):
        status_update = status_update_from_feedback("booked")

        self.assertEqual(status_update["status"], "BOOKED")
        self.assertEqual(status_update["final_outcome"], "BOOKED")

    def test_bad_broker_maps_to_rejected(self):
        status_update = status_update_from_feedback("bad_broker")

        self.assertEqual(status_update["status"], "REJECTED")
        self.assertEqual(status_update["final_outcome"], "REJECTED")

    def test_ratecon_received_is_final_outcome(self):
        case = make_case_record()

        case = apply_feedback_to_case(
            case,
            make_feedback("ratecon_received"),
        )

        self.assertEqual(case["status"], "RATECON_RECEIVED")
        self.assertEqual(case["final_outcome"], "RATECON_RECEIVED")

    def test_final_outcome_is_not_downgraded_by_sent_to_driver(self):
        case = make_case_record()

        case = apply_feedback_to_case(
            case,
            make_feedback("ratecon_received", "2026-01-01T01:00:00Z"),
        )

        case = apply_feedback_to_case(
            case,
            make_feedback("sent_to_driver", "2026-01-01T02:00:00Z"),
        )

        self.assertEqual(case["status"], "RATECON_RECEIVED")
        self.assertEqual(case["final_outcome"], "RATECON_RECEIVED")

    def test_working_status_moves_forward(self):
        case = make_case_record()

        case = apply_feedback_to_case(
            case,
            make_feedback("called_broker", "2026-01-01T01:00:00Z"),
        )

        case = apply_feedback_to_case(
            case,
            make_feedback("sent_to_driver", "2026-01-01T02:00:00Z"),
        )

        self.assertEqual(case["status"], "SENT_TO_DRIVER")
        self.assertIsNone(case["final_outcome"])

    def test_working_status_does_not_move_backward(self):
        case = make_case_record()

        case = apply_feedback_to_case(
            case,
            make_feedback("sent_to_driver", "2026-01-01T01:00:00Z"),
        )

        case = apply_feedback_to_case(
            case,
            make_feedback("called_broker", "2026-01-01T02:00:00Z"),
        )

        self.assertEqual(case["status"], "SENT_TO_DRIVER")
        self.assertIsNone(case["final_outcome"])


class SampleSizeProtectionTest(unittest.TestCase):
    def test_driver_sample_under_10_is_insufficient(self):
        result = get_driver_sample_quality(9)

        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(result["can_affect_decision"])

    def test_driver_sample_10_to_24_is_early_signal(self):
        result = get_driver_sample_quality(10)

        self.assertEqual(result["sample_quality"], "EARLY_SIGNAL")
        self.assertFalse(result["can_affect_decision"])

    def test_driver_sample_25_to_49_is_developing_pattern(self):
        result = get_driver_sample_quality(25)

        self.assertEqual(result["sample_quality"], "DEVELOPING_PATTERN")
        self.assertFalse(result["can_affect_decision"])

    def test_driver_sample_50_plus_can_affect_decision(self):
        result = get_driver_sample_quality(50)

        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertTrue(result["can_affect_decision"])

    def test_lane_sample_under_10_is_insufficient(self):
        result = get_lane_sample_quality(9)

        self.assertEqual(result["sample_quality"], "INSUFFICIENT_SAMPLE")
        self.assertFalse(result["can_affect_decision"])

    def test_lane_sample_50_plus_can_affect_decision(self):
        result = get_lane_sample_quality(50)

        self.assertEqual(result["sample_quality"], "RELIABLE_PATTERN")
        self.assertTrue(result["can_affect_decision"])


class BrokerStatusSafetyTest(unittest.TestCase):
    def test_missing_broker_mc_does_not_show_buy(self):
        load = SimpleNamespace(
            broker_mc="",
            broker_status="BUY",
        )

        result = get_broker_status_text(load)

        self.assertEqual(result, "NEEDS MC CHECK")

    def test_needs_check_broker_mc_does_not_show_buy(self):
        load = SimpleNamespace(
            broker_mc="NEEDS CHECK",
            broker_status="BUY",
        )

        result = get_broker_status_text(load)

        self.assertEqual(result, "NEEDS MC CHECK")


if __name__ == "__main__":
    unittest.main()