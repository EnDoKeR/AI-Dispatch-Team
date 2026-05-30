import json
import unittest

from app.document_ai.private_template_patterns import (
    TOKEN_DATE,
    TOKEN_MC_NUMBER,
    TOKEN_MONEY,
    TOKEN_REFERENCE,
    build_redacted_line_pattern,
    build_redacted_pattern_token,
    build_redacted_template_pattern_summary,
    build_template_family_candidate,
)


class PrivateTemplatePatternContractTests(unittest.TestCase):
    def test_redacted_pattern_summary_serializes_safely(self):
        summary = build_redacted_template_pattern_summary(
            document_alias="RATECON_001",
            page_count=2,
            char_count=1000,
            section_markers=["Carrier Pay", "Pickup", "Delivery"],
            redacted_rate_label_patterns=[
                build_redacted_line_pattern(
                    page_number=1,
                    line_index_bucket="beginning",
                    redacted_line="Carrier Pay: <MONEY>",
                    token_types=[TOKEN_MONEY],
                    looks_like_rate_section=True,
                )
            ],
        )

        payload = json.dumps(summary)

        self.assertTrue(summary["private_values_redacted"])
        self.assertFalse(summary["raw_text_included"])
        self.assertIn("<MONEY>", payload)
        self.assertNotIn("$1234.56", payload)

    def test_redacted_token_defaults_to_placeholder_value(self):
        cases = [
            (TOKEN_MONEY, "$1234.56", "<MONEY>"),
            (TOKEN_DATE, "2026-05-30", "<DATE>"),
            (TOKEN_MC_NUMBER, "MC 123456", "<MC>"),
            (TOKEN_REFERENCE, "LOAD-123", "<REF>"),
        ]

        for token_type, raw_value, expected in cases:
            with self.subTest(token_type=token_type):
                token = build_redacted_pattern_token(token_type, raw_value)
                self.assertEqual(token["redacted_value"], expected)

    def test_family_candidate_uses_aliases_and_redacted_markers(self):
        family = build_template_family_candidate(
            family_alias="TEMPLATE_FAMILY_001",
            aliases=["RATECON_001", "RATECON_002"],
            common_redacted_markers=["Carrier Pay: <MONEY>"],
            confidence_bucket="medium",
        )

        payload = json.dumps(family)

        self.assertEqual(family["family_alias"], "TEMPLATE_FAMILY_001")
        self.assertIn("RATECON_001", family["aliases"])
        self.assertIn("<MONEY>", payload)
        self.assertNotIn("FAKE BROKER LLC", payload)


if __name__ == "__main__":
    unittest.main()
