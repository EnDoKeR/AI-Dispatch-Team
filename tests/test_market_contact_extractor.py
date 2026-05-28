import unittest

from app.market_intelligence.market_contact_extractor import (
    extract_email,
    extract_phone,
)


class TestMarketContactExtractor(unittest.TestCase):
    def test_extract_email_from_parsed_contact(self):
        self.assertEqual(
            extract_email(
                parsed_contact={"email": "dispatch@example.com"},
            ),
            "dispatch@example.com",
        )

    def test_extract_email_from_parsed_contact_list(self):
        self.assertEqual(
            extract_email(
                parsed_contact={"emails": ["first@example.com", "second@example.com"]},
            ),
            "first@example.com",
        )

    def test_extract_email_from_broker_contact_raw(self):
        self.assertEqual(
            extract_email(
                parsed_contact={},
                broker_contact_raw="Call 555-111-2222 or email dispatch@example.com",
            ),
            "dispatch@example.com",
        )

    def test_extract_email_fixes_dat_style_text(self):
        self.assertEqual(
            extract_email(
                parsed_contact={},
                notes="Email dispatch at example dot com",
            ),
            "dispatch@example.com",
        )

    def test_extract_email_fixes_backtick_dot(self):
        self.assertEqual(
            extract_email(
                parsed_contact={},
                notes="Email dispatch@example`com",
            ),
            "dispatch@example.com",
        )

    def test_extract_email_returns_empty_when_missing(self):
        self.assertEqual(
            extract_email(
                parsed_contact={},
                notes="Call broker only",
            ),
            "",
        )

    def test_extract_phone_from_parsed_contact(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={"phone": "555-111-2222"},
            ),
            "555-111-2222",
        )

    def test_extract_phone_from_parsed_contact_list(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={"phones": ["555-111-2222", "555-333-4444"]},
            ),
            "555-111-2222",
        )

    def test_extract_phone_from_notes(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={},
                notes="Contact broker at (555) 111-2222",
            ),
            "(555) 111-2222",
        )

    def test_extract_phone_adds_extension(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={},
                broker_contact_raw="Phone 555-111-2222 ext 345",
            ),
            "555-111-2222 x345",
        )

    def test_extract_phone_adds_ref_as_extension(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={},
                broker_contact_raw="Phone 555-111-2222 ref: 987",
            ),
            "555-111-2222 x987",
        )

    def test_extract_phone_returns_empty_when_missing(self):
        self.assertEqual(
            extract_phone(
                parsed_contact={},
                notes="Email only",
            ),
            "",
        )


if __name__ == "__main__":
    unittest.main()
