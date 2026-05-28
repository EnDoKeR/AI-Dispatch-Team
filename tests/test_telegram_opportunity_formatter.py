import unittest

from app.market_intelligence.telegram_opportunity_formatter import format_opportunity_message


class FakeSearchRequest:
    driver_name = "Alex"


class FakeLoad:
    def __init__(
        self,
        pickup_time="10 AM",
        delivery_time="2 PM",
        delivery="Houston, TX",
        driver_match_notes=None,
    ):
        self.pickup = "Dallas, TX"
        self.delivery = delivery
        self.rate = 2200
        self.loaded_miles = 240
        self.empty_miles = 20
        self.total_miles = 260
        self.total_rpm = 8.46
        self.bucket = "700-1300"
        self.weight = 36000
        self.posted_trailer_type = "Flatbed"
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time
        self.notes = "Clean load"
        self.broker_name = "Test Broker"
        self.broker_mc = "123456"
        self.broker_status = "NEEDS CHECK"
        self.reference_id = "REF-123"
        self.primary_phone = "555-111-2222"
        self.primary_email = "broker@example.com"
        self.broker_contact = ""
        self.credit_score = "95"
        self.days_to_pay = "18"
        self.driver_match_notes = driver_match_notes or ["Clean match", "Good RPM"]

    def priority(self):
        return "HIGH"

    def opportunity_score(self):
        return 91

    def suggested_action(self):
        return "SEND"

    def opportunity_reason(self):
        return "Good rate and clean lane."


class TestTelegramOpportunityFormatter(unittest.TestCase):
    def test_format_opportunity_message_includes_core_load_details(self):
        message = format_opportunity_message(
            load=FakeLoad(),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("LOAD OPPORTUNITY #1", message)
        self.assertIn("Alex", message)
        self.assertIn("Dallas, TX", message)
        self.assertIn("Houston, TX", message)
        self.assertIn("Rate: $2200", message)
        self.assertIn("Loaded miles: 240", message)
        self.assertIn("Empty miles: 20", message)
        self.assertIn("Total miles: 260", message)
        self.assertIn("Total RPM: $8.46", message)
        self.assertIn("Bucket: 700-1300", message)
        self.assertIn("Weight: 36000", message)
        self.assertIn("Posted trailer: Flatbed", message)
        self.assertIn("Delivery Zone: GOOD / STRONG RELOAD AREA", message)
        self.assertIn("Pickup Time: 10 AM", message)
        self.assertIn("Delivery Time: 2 PM", message)
        self.assertIn("Notes: Clean load", message)

    def test_format_opportunity_message_includes_broker_block_and_scoring(self):
        message = format_opportunity_message(
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
        self.assertIn("Credit Score: 95", message)
        self.assertIn("Days to Pay: 18", message)
        self.assertIn("Broker Status:", message)

        self.assertIn("Priority: HIGH", message)
        self.assertIn("Score: 91", message)
        self.assertIn("Action: SEND", message)
        self.assertIn("Reason:", message)
        self.assertIn("Good rate and clean lane.", message)

    def test_format_opportunity_message_adds_time_and_reload_warnings(self):
        message = format_opportunity_message(
            load=FakeLoad(
                pickup_time="",
                delivery_time="",
                delivery="Billings, MT",
            ),
            index=2,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("Pickup Time: NEEDS CHECK", message)
        self.assertIn("Delivery Time: NEEDS CHECK", message)
        self.assertIn("Delivery Zone: RISKY / EXIT PLAN NEEDED", message)
        self.assertIn("Time check required before booking.", message)
        self.assertIn("Reload risk: check exit plan before booking.", message)

    def test_format_opportunity_message_dedupes_driver_fit_notes(self):
        message = format_opportunity_message(
            load=FakeLoad(
                driver_match_notes=[
                    "Tanker endorsement required.",
                    "Tanker endorsement required; ask driver and save answer.",
                    "Good RPM",
                    "Good RPM.",
                    "",
                ],
            ),
            index=1,
            search_request=FakeSearchRequest(),
        )

        self.assertIn("Driver Fit:", message)
        self.assertIn("- Tanker endorsement required; ask driver and save answer.", message)
        self.assertIn("- Good RPM", message)
        self.assertNotIn("- Tanker endorsement required.\n", message)


if __name__ == "__main__":
    unittest.main()
