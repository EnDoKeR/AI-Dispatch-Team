import unittest
from unittest.mock import patch

from app.market_intelligence.telegram_broker_block import (
    broker_block,
    get_broker_status_text,
)


class FakeLoad:
    def __init__(self, **kwargs):
        self.broker_name = kwargs.get("broker_name", "")
        self.broker_mc = kwargs.get("broker_mc", "")
        self.broker_status = kwargs.get("broker_status", "")
        self.reference_id = kwargs.get("reference_id", "")
        self.primary_phone = kwargs.get("primary_phone", "")
        self.primary_email = kwargs.get("primary_email", "")
        self.broker_contact = kwargs.get("broker_contact", "")
        self.credit_score = kwargs.get("credit_score", "")
        self.days_to_pay = kwargs.get("days_to_pay", "")
        self.notes = kwargs.get("notes", "")


class TestTelegramBrokerBlock(unittest.TestCase):
    def test_get_broker_status_text_requires_valid_mc(self):
        for broker_mc in ["", "NEEDS CHECK", "NO MC", "UNKNOWN", "NONE"]:
            load = FakeLoad(broker_mc=broker_mc, broker_status="BUY")

            self.assertEqual(get_broker_status_text(load), "NEEDS MC CHECK")

    def test_get_broker_status_text_uses_memory_status_when_available(self):
        load = FakeLoad(broker_mc="123456", broker_status="BUY")

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "BLOCKED", "reason": "Bad history"},
        ), patch(
            "app.market_intelligence.telegram_broker_block.format_broker_memory_status",
            return_value="BLOCKED - Bad history",
        ):
            self.assertEqual(
                get_broker_status_text(load),
                "BLOCKED - Bad history",
            )

    def test_get_broker_status_text_keeps_existing_non_buy_status(self):
        load = FakeLoad(broker_mc="123456", broker_status="NEEDS CHECK")

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "UNKNOWN"},
        ):
            self.assertEqual(get_broker_status_text(load), "NEEDS CHECK")

    def test_get_broker_status_text_does_not_show_buy_without_memory_confirmation(self):
        load = FakeLoad(broker_mc="123456", broker_status="BUY")

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "UNKNOWN"},
        ):
            self.assertEqual(get_broker_status_text(load), "UNKNOWN")

    def test_broker_block_uses_structured_fields(self):
        load = FakeLoad(
            broker_name="Test Broker",
            broker_mc="123456",
            reference_id="REF-123",
            primary_phone="555-111-2222",
            primary_email="broker@example.com",
            credit_score="95",
            days_to_pay="18",
            broker_status="NEEDS CHECK",
        )

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "UNKNOWN"},
        ):
            text = broker_block(load)

        self.assertIn("Broker / Contact:", text)
        self.assertIn("Broker: Test Broker", text)
        self.assertIn("MC: 123456", text)
        self.assertIn("Phone: 555-111-2222", text)
        self.assertIn("Email: broker@example.com", text)
        self.assertIn("Reference ID: REF-123", text)
        self.assertIn("Credit Score: 95", text)
        self.assertIn("Days to Pay: 18", text)
        self.assertIn("Broker Status: NEEDS CHECK", text)

    def test_broker_block_extracts_missing_fields_from_notes(self):
        load = FakeLoad(
            notes=(
                "Notes Broker | MC# 777777 | Contact: 555-333-4444 | "
                "Reference ID: REF-NOTES | Credit Score: 88 | Days to Pay: 21 | "
                "Factoring eligible"
            ),
            broker_contact="555-333-4444",
        )

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "UNKNOWN"},
        ):
            text = broker_block(load)

        self.assertIn("Broker: Notes Broker", text)
        self.assertIn("MC: 777777", text)
        self.assertIn("Phone: 555-333-4444", text)
        self.assertIn("Email: NEEDS CHECK", text)
        self.assertIn("Reference ID: REF-NOTES", text)
        self.assertIn("Credit Score: 88", text)
        self.assertIn("Days to Pay: 21", text)
        self.assertIn("Factoring: Eligible", text)
        self.assertIn("Broker Status: UNKNOWN", text)

    def test_broker_block_does_not_treat_email_as_phone(self):
        load = FakeLoad(
            broker_name="Email Broker",
            broker_mc="999999",
            broker_contact="dispatch@example.com",
            primary_phone="phone@example.com",
            reference_id="REF-EMAIL",
        )

        with patch(
            "app.market_intelligence.telegram_broker_block.get_broker_memory_status",
            return_value={"status": "UNKNOWN"},
        ):
            text = broker_block(load)

        self.assertIn("Phone: NEEDS CHECK", text)
        self.assertIn("Email: dispatch@example.com", text)


if __name__ == "__main__":
    unittest.main()
