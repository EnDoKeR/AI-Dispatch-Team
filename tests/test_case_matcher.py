import unittest

from app.market_intelligence.case_matcher import (
    feedback_matches_case,
    outbox_matches_case,
    simulation_event_matches_case,
)


class TestCaseMatcher(unittest.TestCase):
    def test_feedback_matches_by_load_id(self):
        feedback = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "",
        }
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-999",
        }

        self.assertTrue(feedback_matches_case(feedback, case))

    def test_feedback_matches_by_reference_id(self):
        feedback = {
            "driver_name": "Alex",
            "load_id": "",
            "reference_id": "REF-123",
        }
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-999",
            "reference_id": "REF-123",
        }

        self.assertTrue(feedback_matches_case(feedback, case))

    def test_feedback_does_not_match_different_driver(self):
        feedback = {
            "driver_name": "Alex",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }
        case = {
            "driver_name": "Mike",
            "load_id": "LOAD-123",
            "reference_id": "REF-123",
        }

        self.assertFalse(feedback_matches_case(feedback, case))

    def test_feedback_matches_cross_load_id_and_reference_id(self):
        feedback = {
            "driver_name": "Alex",
            "load_id": "REF-123",
            "reference_id": "",
        }
        case = {
            "driver_name": "Alex",
            "load_id": "LOAD-999",
            "reference_id": "REF-123",
        }

        self.assertTrue(feedback_matches_case(feedback, case))

    def test_outbox_matches_by_valid_reference_id_and_driver(self):
        outbox = {
            "driver_name": "Alex",
            "reference_id": "REF-123",
            "pickup": "",
            "delivery": "",
            "broker_mc": "",
        }
        case = {
            "driver_name": "Alex",
            "reference_id": "REF-123",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "123456",
        }

        self.assertTrue(outbox_matches_case(outbox, case))

    def test_outbox_no_id_does_not_match_by_reference_id_only(self):
        outbox = {
            "driver_name": "Alex",
            "reference_id": "NO ID",
            "pickup": "",
            "delivery": "",
            "broker_mc": "",
        }
        case = {
            "driver_name": "Alex",
            "reference_id": "NO ID",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "123456",
        }

        self.assertFalse(outbox_matches_case(outbox, case))

    def test_outbox_matches_by_driver_pickup_delivery_when_broker_mc_missing(self):
        outbox = {
            "driver_name": "Alex",
            "reference_id": "NO ID",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "",
        }
        case = {
            "driver_name": "Alex",
            "reference_id": "",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "123456",
        }

        self.assertTrue(outbox_matches_case(outbox, case))

    def test_outbox_matches_by_driver_pickup_delivery_and_same_broker_mc(self):
        outbox = {
            "driver_name": "Alex",
            "reference_id": "",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "123456",
        }
        case = {
            "driver_name": "Alex",
            "reference_id": "",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "123456",
        }

        self.assertTrue(outbox_matches_case(outbox, case))

    def test_outbox_does_not_match_same_lane_with_different_broker_mc(self):
        outbox = {
            "driver_name": "Alex",
            "reference_id": "",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "111111",
        }
        case = {
            "driver_name": "Alex",
            "reference_id": "",
            "pickup": "Dallas, TX",
            "delivery": "Houston, TX",
            "broker_mc": "222222",
        }

        self.assertFalse(outbox_matches_case(outbox, case))

    def test_simulation_event_matches_by_simulation_load_id_to_case_reference_id(self):
        simulation_event = {
            "load_id": "SIM-CLEAN-001",
            "payload": {},
        }
        case = {
            "load_id": "",
            "reference_id": "SIM-CLEAN-001",
        }

        self.assertTrue(simulation_event_matches_case(simulation_event, case))

    def test_simulation_event_matches_by_payload_reference_id(self):
        simulation_event = {
            "load_id": "",
            "payload": {
                "load": {
                    "reference_id": "SIM-RATECHECK-001",
                }
            },
        }
        case = {
            "load_id": "SIM-RATECHECK-001",
            "reference_id": "",
        }

        self.assertTrue(simulation_event_matches_case(simulation_event, case))

    def test_simulation_event_does_not_match_unrelated_case(self):
        simulation_event = {
            "load_id": "SIM-CLEAN-001",
            "payload": {
                "load": {
                    "reference_id": "SIM-CLEAN-001",
                }
            },
        }
        case = {
            "load_id": "OTHER-LOAD",
            "reference_id": "OTHER-REF",
        }

        self.assertFalse(simulation_event_matches_case(simulation_event, case))


if __name__ == "__main__":
    unittest.main()
