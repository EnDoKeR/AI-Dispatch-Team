import unittest
from app.market_intelligence.case_id_resolver import (
    build_case_id,
    has_valid_reference_id,
    same_reference_id,
    stable_hash,
)

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


class CaseIdResolverTest(unittest.TestCase):
    def test_stable_hash_is_stable(self):
        first_hash = stable_hash("Test Value")
        second_hash = stable_hash("Test Value")

        self.assertEqual(first_hash, second_hash)

    def test_stable_hash_is_case_insensitive(self):
        first_hash = stable_hash("Test Value")
        second_hash = stable_hash("test value")

        self.assertEqual(first_hash, second_hash)

    def test_build_case_id_uses_reference_id_when_available(self):
        case_id = build_case_id(
            driver_name="TestDriver",
            load_id="LOAD-001",
            reference_id="REF-001",
            broker_mc="123456",
        )

        expected = f"CASE-{stable_hash('TestDriver|REF:REF-001|MC:123456')}"

        self.assertEqual(case_id, expected)

    def test_build_case_id_uses_load_id_when_reference_missing(self):
        case_id = build_case_id(
            driver_name="TestDriver",
            load_id="LOAD-001",
            reference_id="",
            broker_mc="123456",
        )

        expected = f"CASE-{stable_hash('TestDriver|LOAD:LOAD-001|MC:123456')}"

        self.assertEqual(case_id, expected)

    def test_build_case_id_ignores_no_id_reference(self):
        case_id = build_case_id(
            driver_name="TestDriver",
            load_id="LOAD-001",
            reference_id="NO ID",
            broker_mc="123456",
        )

        expected = f"CASE-{stable_hash('TestDriver|LOAD:LOAD-001|MC:123456')}"

        self.assertEqual(case_id, expected)

    def test_build_case_id_falls_back_to_driver_and_mc(self):
        case_id = build_case_id(
            driver_name="TestDriver",
            load_id="",
            reference_id="",
            broker_mc="123456",
        )

        expected = f"CASE-{stable_hash('TestDriver|MC:123456')}"

        self.assertEqual(case_id, expected)

    def test_valid_reference_id(self):
        self.assertTrue(has_valid_reference_id("REF-001"))

    def test_invalid_reference_id_no_id(self):
        self.assertFalse(has_valid_reference_id("NO ID"))

    def test_invalid_reference_id_needs_check(self):
        self.assertFalse(has_valid_reference_id("NEEDS CHECK"))

    def test_same_reference_id(self):
        self.assertTrue(same_reference_id("REF-001", "ref-001"))

    def test_same_reference_id_rejects_invalid_values(self):
        self.assertFalse(same_reference_id("NO ID", "NO ID"))

if __name__ == "__main__":
    unittest.main()