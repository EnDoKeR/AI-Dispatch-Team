import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.market_intelligence.telegram_chain_formatter import (
    chain_duplicate_key,
    format_chain_candidate_message,
    important_checklist,
    save_sent_chain_alert,
    get_sent_chain_alerts,
)


class FakeSearchRequest:
    driver_name = "Alex"
    equipment = "Conestoga"
    max_weight = 48000


class FakeLoad:
    def __init__(
        self,
        pickup="Dallas, TX",
        delivery="Houston, TX",
        rate=2200,
        loaded_miles=240,
        empty_miles=20,
        total_miles=260,
        total_rpm=8.46,
        weight=36000,
        pickup_time="10 AM",
        delivery_time="2 PM",
        posted_trailer_type="Flatbed",
        reference_id="REF-123",
        notes="Clean load",
        broker_name="Test Broker",
        broker_mc="123456",
        broker_status="NEEDS CHECK",
        requires_tarp=False,
        is_od=False,
        is_overweight=False,
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.empty_miles = empty_miles
        self.total_miles = total_miles
        self.total_rpm = total_rpm
        self.weight = weight
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time
        self.posted_trailer_type = posted_trailer_type
        self.reference_id = reference_id
        self.notes = notes
        self.broker_name = broker_name
        self.broker_mc = broker_mc
        self.broker_status = broker_status
        self.primary_phone = "555-111-2222"
        self.primary_email = "broker@example.com"
        self.broker_contact = ""
        self.credit_score = "95"
        self.days_to_pay = "18"
        self.requires_tarp = requires_tarp
        self.is_od = is_od
        self.is_overweight = is_overweight
        self.broker = broker_name
        self.pickup_date = "2026-05-28"


class TestTelegramChainFormatter(unittest.TestCase):
    def build_chain_candidate(self):
        first_load = FakeLoad(
            pickup="Dallas, TX",
            delivery="Denver, CO",
            reference_id="FIRST-123",
        )
        reload_load = FakeLoad(
            pickup="Denver, CO",
            delivery="Houston, TX",
            rate=1800,
            loaded_miles=900,
            empty_miles=30,
            total_miles=930,
            total_rpm=1.94,
            reference_id="RELOAD-456",
        )

        return {
            "first_load": first_load,
            "reload_load": reload_load,
            "chain_data": {
                "total_gross": 4000,
                "total_miles": 1190,
                "total_rpm": 3.36,
                "chain_score": 87,
            },
        }

    def test_chain_duplicate_key_uses_driver_and_both_loads(self):
        key = chain_duplicate_key(
            self.build_chain_candidate(),
            FakeSearchRequest(),
        )

        self.assertIn("alex", key)
        self.assertIn("ref:first-123", key.lower())
        self.assertIn("ref:reload-456", key.lower())

    def test_chain_sent_state_saves_and_reads_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sent_file = Path(temp_dir) / "sent_reload_chain_alerts.txt"

            with patch(
                "app.market_intelligence.telegram_chain_formatter.SENT_CHAIN_FILE",
                str(sent_file),
            ):
                candidate = self.build_chain_candidate()
                search_request = FakeSearchRequest()

                self.assertEqual(get_sent_chain_alerts(), set())

                save_sent_chain_alert(candidate, search_request)

                sent_alerts = get_sent_chain_alerts()

                self.assertIn(
                    chain_duplicate_key(candidate, search_request),
                    sent_alerts,
                )

    def test_important_checklist_returns_no_major_checks_when_clean(self):
        search_request = FakeSearchRequest()
        search_request.equipment = "Flatbed"

        text = important_checklist(
            FakeLoad(),
            search_request,
        )

        self.assertEqual(text, "No major missing checks detected.")

    def test_important_checklist_includes_missing_or_risky_items(self):
        load = FakeLoad(
            pickup_time="",
            delivery_time="",
            weight=50000,
            requires_tarp=True,
            is_od=True,
            is_overweight=True,
            broker_status="UNKNOWN",
        )

        text = important_checklist(load, FakeSearchRequest())

        self.assertIn("- pickup time / pickup hours", text)
        self.assertIn("- delivery time / delivery hours", text)
        self.assertIn("- if Conestoga is accepted", text)
        self.assertIn("- tarp requirements", text)
        self.assertIn("- OD / permit details", text)
        self.assertIn("- overweight details", text)
        self.assertIn("- weight approval from driver", text)
        self.assertIn("- broker / factoring status", text)

    def test_format_chain_candidate_message_includes_first_reload_and_total_chain(self):
        message = format_chain_candidate_message(
            chain_candidate=self.build_chain_candidate(),
            search_request=FakeSearchRequest(),
            index=1,
        )

        self.assertIn("LOAD WITH RELOAD PLAN #1", message)
        self.assertIn("Alex", message)

        self.assertIn("FIRST LOAD:", message)
        self.assertIn("Dallas, TX", message)
        self.assertIn("Denver, CO", message)
        self.assertIn("Reference ID: FIRST-123", message)
        self.assertIn("First Load Broker:", message)
        self.assertIn("First Load Notes:", message)
        self.assertIn("First Load Must Check:", message)

        self.assertIn("RELOAD OPTION:", message)
        self.assertIn("Denver, CO", message)
        self.assertIn("Houston, TX", message)
        self.assertIn("Reference ID: RELOAD-456", message)
        self.assertIn("Reload Broker:", message)
        self.assertIn("Reload Notes:", message)
        self.assertIn("Reload Must Check:", message)

        self.assertIn("TOTAL CHAIN:", message)
        self.assertIn("Gross: $4000", message)
        self.assertIn("Total miles: 1190", message)
        self.assertIn("Chain RPM: $3.36", message)
        self.assertIn("Chain Score: 87", message)

        self.assertIn("Why shown:", message)
        self.assertIn("Review as a package.", message)


if __name__ == "__main__":
    unittest.main()
