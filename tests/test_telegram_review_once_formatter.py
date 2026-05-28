import unittest

from app.market_intelligence.telegram_review_once_formatter import (
    _dedupe_review_reasons,
    format_review_once_message,
)


class FakeSearchRequest:
    driver_name = "Alex"
    max_weight = 48000


class FakeLoad:
    def __init__(
        self,
        pickup_time="10 AM",
        delivery_time="2 PM",
        delivery="Houston, TX",
        delivery_zone="",
        driver_match_notes=None,
    ):
        self.pickup = "Dallas, TX"
        self.delivery = delivery
        self.rate = 0
        self.loaded_miles = 240
        self.empty_miles = 20
        self.total_miles = 260
        self.total_rpm = 0
        self.weight = 36000
        self.posted_trailer_type = "Flatbed"
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time
        self.notes = "Rate is missing from broker posting"
        self.delivery_zone = delivery_zone
        self.zone_outlook = ""
        self.delivery_zone_outlook = ""

        self.broker_name = "Test Broker"
        self.broker_mc = "123456"
        self.broker_status = "NEEDS CHECK"
        self.reference_id = "REF-123"
        self.primary_phone = "555-111-2222"
        self.primary_email = "broker@example.com"
        self.broker_contact = ""
        self.credit_score = "95"
        self.days_to_pay = "18"

        self.driver_match_notes = driver_match_notes or [
            "Rate is missing from broker posting",
            "Check rate with broker before booking",
        ]

    def review_category(self):
        return "RATE CHECK"


class TestTelegramReviewOnceFormatter(unittest.TestCase):
    def test_dedupe_review_reasons_keeps_longer_near_duplicate(self):
        reasons = [
            "Tanker endorsement required.",
            "Tanker endorsement required; ask driver and save answer in driver profile.",
            "Rate is missing.",
            "Rate is missing",
            "",
        ]

        result = _dedupe_review_reasons(reasons)

        self.assertEqual(
            result,
            [
                "Tanker endorsement required; ask driver and save answer in driver profile.",
                "Rate is missing.",
            ],
        )

    def test_format_review_once_message_includes_core_details(self):
        message = format_review_once_message(
            load=FakeLoad(),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("REVIEW ONCE", message)
        self.assertIn("RATE CHECK", message)
        self.assertIn("Alex #1", message)
        self.assertIn("Dallas, TX", message)
        self.assertIn("Houston, TX", message)
        self.assertIn("Rate: $0", message)
        self.assertIn("Loaded miles: 240", message)
        self.assertIn("Empty miles: 20", message)
        self.assertIn("Total miles: 260", message)
        self.assertIn("Total RPM: $0", message)
        self.assertIn("Weight: 36000", message)
        self.assertIn("Driver Max Weight: 48000", message)
        self.assertIn("Posted trailer: Flatbed", message)
        self.assertIn("Delivery Zone: GOOD / STRONG RELOAD AREA", message)
        self.assertIn("Pickup Time: 10 AM", message)
        self.assertIn("Delivery Time: 2 PM", message)
        self.assertIn("Notes: Rate is missing from broker posting", message)

    def test_format_review_once_message_includes_broker_and_action(self):
        message = format_review_once_message(
            load=FakeLoad(),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("Broker / Contact:", message)
        self.assertIn("Broker: Test Broker", message)
        self.assertIn("MC: 123456", message)
        self.assertIn("Phone: 555-111-2222", message)
        self.assertIn("Email: broker@example.com", message)
        self.assertIn("Reference ID: REF-123", message)
        self.assertIn("Broker Status:", message)

        self.assertIn("Why shown:", message)
        self.assertIn("- Rate is missing from broker posting", message)
        self.assertIn("- Check rate with broker before booking", message)
        self.assertIn("Action:", message)
        self.assertIn("Review once. Ask dispatcher/driver if this exception is acceptable.", message)

    def test_format_review_once_message_uses_existing_delivery_zone_when_valid(self):
        message = format_review_once_message(
            load=FakeLoad(delivery_zone="CUSTOM ZONE"),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("Delivery Zone: CUSTOM ZONE", message)

    def test_format_review_once_message_adds_risky_reload_warning(self):
        message = format_review_once_message(
            load=FakeLoad(delivery="Billings, MT"),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("Delivery Zone: RISKY / EXIT PLAN NEEDED", message)
        self.assertIn("Reload risk: exit plan should be checked before booking.", message)


if __name__ == "__main__":
    unittest.main()
