import unittest
from app.market_intelligence.decision_serializer import serialize_load_decision
from app.market_intelligence.decision_logger_helpers import (
    build_load_id,
    build_reason_list,
    get_decision,
    get_decision_category,
    safe_list,
    safe_value,
    stable_text_hash,
)


class FakeSearchRequest:
    driver_name = "Alex"
    current_location = "Dallas, TX"
    equipment = "Flatbed"
    max_weight = 48000
    target_direction = "TX"
    target_city = "Houston, TX"


class FakeLoad:
    pickup = "Dallas, TX"
    delivery = "Houston, TX"
    rate = 2200
    loaded_miles = 240
    empty_miles = 20
    total_miles = 260
    total_rpm = 8.46
    weight = 36000
    posted_trailer_type = "Flatbed"
    commodity = "Steel"
    pickup_time = "10 AM"
    delivery_time = "2 PM"
    broker_name = "Test Broker"
    broker_mc = "123456"
    broker_contact = "broker@example.com"
    reference_id = "REF-123"
    broker_status = "UNKNOWN"
    credit_score = 95
    days_to_pay = 18
    driver_match_status = "MATCH"
    target_relation = "TARGET"
    driver_fit_status = "GOOD"
    notes = "Clean load"

    driver_match_notes = ["clean match"]
    match_reasons = ["good RPM"]
    review_reasons = []
    block_reasons = []

    def opportunity_score(self):
        return 91

    def priority(self):
        return "HIGH"

    def suggested_action(self):
        return "SEND"

    def is_good(self):
        return True

    def is_qualified(self):
        return True


class ReviewLoad(FakeLoad):
    driver_match_status = "REVIEW_ONCE"

    def review_category(self):
        return "RATE CHECK"


class TestDecisionLogger(unittest.TestCase):
    def test_safe_value_returns_default_for_none(self):
        self.assertEqual(safe_value(None), "")
        self.assertEqual(safe_value(None, default="UNKNOWN"), "UNKNOWN")
        self.assertEqual(safe_value(0), 0)
        self.assertEqual(safe_value(""), "")

    def test_safe_list_normalizes_values(self):
        self.assertEqual(safe_list(["a", "b"]), ["a", "b"])
        self.assertEqual(safe_list("single reason"), ["single reason"])
        self.assertEqual(safe_list(None), [])
        self.assertEqual(safe_list(""), [])

    def test_stable_text_hash_is_stable_and_12_chars(self):
        first = stable_text_hash("Dallas -> Houston")
        second = stable_text_hash(" Dallas -> Houston ")

        self.assertEqual(first, second)
        self.assertEqual(len(first), 12)

    def test_build_load_id_uses_reference_and_broker_mc(self):
        load = FakeLoad()

        self.assertEqual(build_load_id(load), "MC123456-REFREF-123")

    def test_build_load_id_uses_reference_without_broker_mc(self):
        load = FakeLoad()
        load.broker_mc = ""

        self.assertEqual(build_load_id(load), "REFREF-123")

    def test_build_load_id_falls_back_to_hash_when_reference_missing(self):
        load = FakeLoad()
        load.reference_id = "NO ID"

        load_id = build_load_id(load)

        self.assertTrue(load_id.startswith("LOAD-"))
        self.assertEqual(len(load_id), len("LOAD-") + 12)

    def test_get_decision_category_for_match_block_and_review(self):
        match_load = FakeLoad()
        self.assertEqual(get_decision_category(match_load), "LOAD OPPORTUNITY")

        block_load = FakeLoad()
        block_load.driver_match_status = "BLOCK"
        self.assertEqual(get_decision_category(block_load), "BLOCK")

        review_load = ReviewLoad()
        self.assertEqual(get_decision_category(review_load), "RATE CHECK")

    def test_get_decision_returns_known_or_unknown(self):
        load = FakeLoad()
        self.assertEqual(get_decision(load), "MATCH")

        load.driver_match_status = ""
        self.assertEqual(get_decision(load), "UNKNOWN")

    def test_build_reason_list_dedupes_reasons_preserving_order(self):
        load = FakeLoad()
        load.driver_match_notes = ["clean match", "good RPM"]
        load.match_reasons = ["good RPM", "good lane"]
        load.review_reasons = ["manual check"]
        load.block_reasons = ["manual check"]

        self.assertEqual(
            build_reason_list(load),
            ["clean match", "good RPM", "good lane", "manual check"],
        )

    def test_serialize_load_decision_builds_expected_record(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()
        recommendation = {
            "market_activity": "MEDIUM",
            "driver_fit": "WORKABLE",
            "action_status": "SOME_MATCHES_AVAILABLE",
            "best_bucket": "700-1300",
        }

        record = serialize_load_decision(
            load=load,
            search_request=search_request,
            run_id="RUN-123",
            timestamp_utc="2026-05-28T10:00:00+00:00",
            recommendation=recommendation,
        )

        self.assertEqual(record["timestamp_utc"], "2026-05-28T10:00:00+00:00")
        self.assertEqual(record["run_id"], "RUN-123")
        self.assertEqual(record["driver_name"], "Alex")
        self.assertEqual(record["driver_location"], "Dallas, TX")
        self.assertEqual(record["driver_equipment"], "Flatbed")
        self.assertEqual(record["driver_max_weight"], 48000)
        self.assertEqual(record["target_direction"], "TX")
        self.assertEqual(record["target_city"], "Houston, TX")

        self.assertEqual(record["load_id"], "MC123456-REFREF-123")
        self.assertEqual(record["pickup"], "Dallas, TX")
        self.assertEqual(record["delivery"], "Houston, TX")
        self.assertEqual(record["rate"], 2200)
        self.assertEqual(record["loaded_miles"], 240)
        self.assertEqual(record["empty_miles"], 20)
        self.assertEqual(record["total_miles"], 260)
        self.assertEqual(record["total_rpm"], 8.46)
        self.assertEqual(record["weight"], 36000)

        self.assertEqual(record["broker_name"], "Test Broker")
        self.assertEqual(record["broker_mc"], "123456")
        self.assertEqual(record["broker_contact"], "broker@example.com")
        self.assertEqual(record["reference_id"], "REF-123")

        self.assertEqual(record["decision"], "MATCH")
        self.assertEqual(record["category"], "LOAD OPPORTUNITY")
        self.assertEqual(record["score"], 91)
        self.assertEqual(record["priority"], "HIGH")
        self.assertEqual(record["suggested_action"], "SEND")
        self.assertTrue(record["is_good"])
        self.assertTrue(record["is_qualified"])
        self.assertEqual(record["reasons"], ["clean match", "good RPM"])

        self.assertEqual(record["market_activity"], "MEDIUM")
        self.assertEqual(record["market_driver_fit"], "WORKABLE")
        self.assertEqual(record["market_action_status"], "SOME_MATCHES_AVAILABLE")
        self.assertEqual(record["market_best_bucket"], "700-1300")

        self.assertIsNone(record["telegram_sent"])
        self.assertIsNone(record["dispatcher_feedback"])
        self.assertIsNone(record["final_result"])
        self.assertIsNone(record["final_notes"])


if __name__ == "__main__":
    unittest.main()
