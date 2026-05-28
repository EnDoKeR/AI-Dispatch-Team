import unittest

from app.market_intelligence.notes_parser_contact import detect_contact_override


class TestNotesParserContact(unittest.TestCase):
    def test_detect_contact_override_detects_phone(self):
        result = detect_contact_override("call 555-111-2222")

        self.assertEqual(result["phone"], "555-111-2222")
        self.assertEqual(result["extension"], "")
        self.assertEqual(result["email"], "")

    def test_detect_contact_override_detects_phone_extension(self):
        result = detect_contact_override("call 555-111-2222 ext 45")

        self.assertEqual(result["phone"], "555-111-2222")
        self.assertEqual(result["extension"], "45")
        self.assertEqual(result["email"], "")

    def test_detect_contact_override_detects_obfuscated_email(self):
        result = detect_contact_override("email dispatch at example dot com")

        self.assertEqual(result["email"], "dispatch@example.com")

    def test_detect_contact_override_detects_more_obfuscated_email_formats(self):
        cases = [
            "email dispatch(at)example(dot)com",
            "email dispatch [at] example [dot] com",
            "email dispatch at example.com",
            "email dispatch@example dot com",
            "email d i s p a t c h at example dot com",
        ]

        for case in cases:
            with self.subTest(case=case):
                result = detect_contact_override(case)
                self.assertEqual(result["email"], "dispatch@example.com")

    def test_detect_contact_override_returns_empty_for_clean_text(self):
        self.assertEqual(
            detect_contact_override("regular load notes"),
            {
                "phone": "",
                "extension": "",
                "email": "",
            },
        )


if __name__ == "__main__":
    unittest.main()
