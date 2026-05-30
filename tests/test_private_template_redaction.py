import unittest

from app.document_ai.private_template_redaction import (
    redact_city_state_like_fragments,
    redact_company_like_fragments,
    redact_dates,
    redact_line_for_pattern_collection,
    redact_mc_numbers,
    redact_money,
    redact_phone_email,
    redact_reference_like_values,
    redact_times,
)


class PrivateTemplateRedactionTests(unittest.TestCase):
    def test_money_redacted_and_label_preserved(self):
        redacted = redact_money("Carrier Pay: USD $2,850.00")

        self.assertIn("Carrier Pay", redacted)
        self.assertIn("<MONEY>", redacted)
        self.assertNotIn("2,850.00", redacted)

    def test_mc_redacted(self):
        redacted = redact_mc_numbers("Broker MC: MC 123456")

        self.assertIn("<MC>", redacted)
        self.assertNotIn("123456", redacted)

    def test_reference_values_redacted(self):
        redacted = redact_reference_like_values("Load #: FAKE-REF-001")

        self.assertEqual(redacted, "Load #: <REF>")
        self.assertNotIn("FAKE-REF-001", redacted)

    def test_dates_and_times_redacted(self):
        line = redact_times(redact_dates("Pickup Date: 2026-05-30 08:00-12:00"))

        self.assertIn("<DATE>", line)
        self.assertIn("<TIME>", line)
        self.assertNotIn("2026-05-30", line)
        self.assertNotIn("08:00", line)

    def test_phone_email_redacted(self):
        redacted = redact_phone_email("Contact test@example.com 555-111-2222")

        self.assertEqual(redacted.count("<CONTACT>"), 2)
        self.assertNotIn("test@example.com", redacted)
        self.assertNotIn("555-111-2222", redacted)

    def test_company_and_location_values_redacted(self):
        company = redact_company_like_fragments("Broker: FAKE BROKER LLC")
        location = redact_city_state_like_fragments("Pickup: Fake City, ST 00000")

        self.assertEqual(company, "Broker: <COMPANY>")
        self.assertEqual(location, "Pickup: <CITY_STATE_OR_LOCATION>")

    def test_full_line_redaction_removes_fake_sensitive_values(self):
        line = (
            "Broker: FAKE BROKER LLC | MC 123456 | Load #: FAKE-REF-001 | "
            "Pickup: Fake City, ST 00000 | Rate: $2,850.00"
        )

        redacted = redact_line_for_pattern_collection(line)

        self.assertIn("Broker", redacted)
        for forbidden in [
            "FAKE BROKER LLC",
            "123456",
            "FAKE-REF-001",
            "Fake City",
            "2,850.00",
        ]:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, redacted)


if __name__ == "__main__":
    unittest.main()
