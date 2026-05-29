import json
import unittest

from app.market_intelligence.case_event_builder import (
    build_ai_decision_created_event,
    build_dispatcher_feedback_added_event,
    build_load_board_simulation_event,
    build_ratecon_received_event,
    build_telegram_alert_sent_event,
)
from app.market_intelligence.case_event_types import (
    EVENT_GROUP_LOAD_BOARD_SIMULATION,
    EVENT_GROUP_LOAD_LEVEL,
    event_type_group,
    is_known_event_type,
    normalize_event_type,
)


def sample_case():
    return {
        "driver_name": "Alex",
        "load_id": "LOAD-123",
        "reference_id": "REF-123",
    }


def sample_decision_event():
    return build_ai_decision_created_event(
        case_id="CASE-123",
        case_record=sample_case(),
        decision_record={
            "timestamp_utc": "2026-05-28T10:00:00+00:00",
            "decision": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "score": 90,
            "reasons": ["clean fit"],
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 3200,
        },
    )


def sample_telegram_event():
    return build_telegram_alert_sent_event(
        case_id="CASE-123",
        case_record=sample_case(),
        outbox_record={
            "timestamp_utc": "2026-05-28T10:05:00+00:00",
            "message_type": "LOAD_OPPORTUNITY",
            "category": "LOAD OPPORTUNITY",
            "telegram_message_id": "777",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "rate": 3200,
            "broker": "Test Broker",
            "broker_mc": "123456",
            "reference_id": "REF-123",
        },
    )


def sample_feedback_event():
    return build_dispatcher_feedback_added_event(
        case_id="CASE-123",
        case_record=sample_case(),
        feedback_record={
            "timestamp_utc": "2026-05-28T10:10:00+00:00",
            "source": "dispatcher_feedback",
            "dispatcher_feedback": "calling",
            "dispatcher_note": "Synthetic feedback.",
            "document_path": "",
        },
    )


def sample_ratecon_event():
    return build_ratecon_received_event(
        case_id="CASE-123",
        case_record=sample_case(),
        feedback_record={
            "timestamp_utc": "2026-05-28T10:20:00+00:00",
            "source": "telegram_document",
            "document_path": "data/ratecons/test.pdf",
            "dispatcher_note": "RateCon received.",
        },
    )


def sample_simulation_event(event_type):
    payload_by_type = {
        "LOAD_APPEARED": {
            "load": {
                "pickup": "Stockton, CA",
                "delivery": "Dallas, TX",
                "rate": 4100,
                "broker_name": "Simulation Broker",
                "broker_mc": "777001",
                "reference_id": "SIM-CLEAN-001",
            }
        },
        "LOAD_UPDATED": {"updates": {"rate": 4300}},
        "LOAD_REMOVED": {},
    }

    return build_load_board_simulation_event(
        case_id="CASE-SIM",
        case_record={
            "driver_name": "Alex",
            "load_id": "SIM-CLEAN-001",
            "reference_id": "SIM-CLEAN-001",
        },
        simulation_event={
            "timestamp_utc": "2026-05-28T10:30:00+00:00",
            "simulation_step": 1,
            "event_time": "2026-05-28T10:00:00",
            "event_type": event_type,
            "load_id": "SIM-CLEAN-001",
            "reason": "covered",
            "payload": payload_by_type[event_type],
        },
    )


def all_builder_events():
    return [
        sample_decision_event(),
        sample_telegram_event(),
        sample_feedback_event(),
        sample_ratecon_event(),
        sample_simulation_event("LOAD_APPEARED"),
        sample_simulation_event("LOAD_UPDATED"),
        sample_simulation_event("LOAD_REMOVED"),
    ]


class CaseEventBuilderCompatibilityTest(unittest.TestCase):
    def test_all_current_builder_event_types_are_known(self):
        for event in all_builder_events():
            with self.subTest(event_type=event["event_type"]):
                self.assertTrue(is_known_event_type(event["event_type"]))

    def test_builder_output_event_type_normalizes_through_taxonomy(self):
        for event in all_builder_events():
            with self.subTest(event_type=event["event_type"]):
                self.assertEqual(
                    normalize_event_type(event["event_type"]),
                    event["event_type"],
                )

    def test_load_level_builder_events_map_to_load_level_group(self):
        for event in [
            sample_decision_event(),
            sample_telegram_event(),
            sample_feedback_event(),
            sample_ratecon_event(),
        ]:
            with self.subTest(event_type=event["event_type"]):
                self.assertEqual(
                    event_type_group(event["event_type"]),
                    EVENT_GROUP_LOAD_LEVEL,
                )

    def test_telegram_alert_event_maps_to_load_level_group(self):
        event = sample_telegram_event()

        self.assertEqual(event["event_type"], "TELEGRAM_ALERT_SENT")
        self.assertEqual(event_type_group(event["event_type"]), EVENT_GROUP_LOAD_LEVEL)

    def test_feedback_event_maps_to_load_level_group(self):
        event = sample_feedback_event()

        self.assertEqual(event["event_type"], "DISPATCHER_FEEDBACK_ADDED")
        self.assertEqual(event_type_group(event["event_type"]), EVENT_GROUP_LOAD_LEVEL)

    def test_ratecon_event_maps_to_load_level_group(self):
        event = sample_ratecon_event()

        self.assertEqual(event["event_type"], "RATECON_RECEIVED")
        self.assertEqual(event_type_group(event["event_type"]), EVENT_GROUP_LOAD_LEVEL)

    def test_simulation_events_map_to_simulation_group(self):
        for event_type in ["LOAD_APPEARED", "LOAD_UPDATED", "LOAD_REMOVED"]:
            event = sample_simulation_event(event_type)

            with self.subTest(event_type=event_type):
                self.assertEqual(
                    event_type_group(event["event_type"]),
                    EVENT_GROUP_LOAD_BOARD_SIMULATION,
                )

    def test_builder_payloads_remain_json_serializable(self):
        for event in all_builder_events():
            with self.subTest(event_type=event["event_type"]):
                json.dumps(event)


if __name__ == "__main__":
    unittest.main()
