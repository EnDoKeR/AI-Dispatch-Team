import inspect
import unittest

from app.market_intelligence import telegram_load_metadata
from app.market_intelligence.telegram_load_metadata import (
    build_load_opportunity_metadata,
)


class FakeLoad:
    def __init__(self, **overrides):
        self.driver_name = "Load Driver"
        self.pickup = "Dallas, TX"
        self.delivery = "Houston, TX"
        self.rate = 2200
        self.broker_name = "Primary Broker"
        self.broker = "Fallback Broker"
        self.broker_mc = "123456"
        self.reference_id = "REF-123"

        for key, value in overrides.items():
            setattr(self, key, value)


class FakeSearchRequest:
    def __init__(self, driver_name="Alex"):
        self.driver_name = driver_name


class TestTelegramLoadMetadata(unittest.TestCase):
    def test_builds_full_load_opportunity_metadata(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(),
            FakeSearchRequest(),
        )

        self.assertEqual(
            metadata,
            {
                "message_type": "LOAD_OPPORTUNITY",
                "category": "LOAD OPPORTUNITY",
                "driver_name": "Alex",
                "pickup": "Dallas, TX",
                "delivery": "Houston, TX",
                "rate": 2200,
                "broker": "Primary Broker",
                "broker_mc": "123456",
                "reference_id": "REF-123",
            },
        )

    def test_driver_name_falls_back_to_load_when_search_request_missing(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(driver_name="Load Driver"),
            search_request=None,
        )

        self.assertEqual(metadata["driver_name"], "Load Driver")

    def test_driver_name_falls_back_to_load_when_search_request_field_empty(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(driver_name="Load Driver"),
            FakeSearchRequest(driver_name=""),
        )

        self.assertEqual(metadata["driver_name"], "Load Driver")

    def test_broker_falls_back_to_legacy_broker_field(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(broker_name="", broker="Legacy Broker"),
            FakeSearchRequest(),
        )

        self.assertEqual(metadata["broker"], "Legacy Broker")

    def test_missing_reference_id_becomes_no_id(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(reference_id=""),
            FakeSearchRequest(),
        )

        self.assertEqual(metadata["reference_id"], "NO ID")

    def test_missing_fields_are_safe_defaults(self):
        load = object()

        metadata = build_load_opportunity_metadata(load)

        self.assertEqual(metadata["message_type"], "LOAD_OPPORTUNITY")
        self.assertEqual(metadata["category"], "LOAD OPPORTUNITY")
        self.assertEqual(metadata["driver_name"], "")
        self.assertEqual(metadata["pickup"], "")
        self.assertEqual(metadata["delivery"], "")
        self.assertEqual(metadata["rate"], "")
        self.assertEqual(metadata["broker"], "")
        self.assertEqual(metadata["broker_mc"], "")
        self.assertEqual(metadata["reference_id"], "NO ID")

    def test_custom_category_is_preserved(self):
        metadata = build_load_opportunity_metadata(
            FakeLoad(),
            FakeSearchRequest(),
            category="CUSTOM CATEGORY",
        )

        self.assertEqual(metadata["message_type"], "LOAD_OPPORTUNITY")
        self.assertEqual(metadata["category"], "CUSTOM CATEGORY")

    def test_helper_does_not_mutate_load_or_search_request(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()
        load_before = dict(load.__dict__)
        search_request_before = dict(search_request.__dict__)

        build_load_opportunity_metadata(load, search_request)

        self.assertEqual(load.__dict__, load_before)
        self.assertEqual(search_request.__dict__, search_request_before)

    def test_helper_does_not_import_sender_notifier_formatter_or_logger(self):
        source = inspect.getsource(telegram_load_metadata)

        self.assertNotIn("telegram_sender", source)
        self.assertNotIn("telegram_notifier", source)
        self.assertNotIn("telegram_opportunity_formatter", source)
        self.assertNotIn("telegram_outbox_logger", source)
        self.assertNotIn("parse_", source)

    def test_metadata_keys_match_outbox_logger_fields(self):
        metadata = build_load_opportunity_metadata(FakeLoad(), FakeSearchRequest())

        self.assertEqual(
            set(metadata.keys()),
            {
                "message_type",
                "category",
                "driver_name",
                "pickup",
                "delivery",
                "rate",
                "broker",
                "broker_mc",
                "reference_id",
            },
        )


if __name__ == "__main__":
    unittest.main()
