import unittest

from app.document_ai.section_context import (
    SECTION_DELIVERY,
    SECTION_INSTRUCTIONS,
    SECTION_LOAD_INFO,
    SECTION_PICKUP,
    SECTION_RATE,
    classify_line_section_context,
    section_context_summary,
)


class SectionContextTests(unittest.TestCase):
    def test_pickup_delivery_rate_instructions_and_load_contexts(self):
        self.assertEqual(classify_line_section_context("Pickup: Fake Origin"), SECTION_PICKUP)
        self.assertEqual(
            classify_line_section_context("Consignee Delivery Location"),
            SECTION_DELIVERY,
        )
        self.assertEqual(classify_line_section_context("Carrier Pay"), SECTION_RATE)
        self.assertEqual(
            classify_line_section_context("Special Instructions"),
            SECTION_INSTRUCTIONS,
        )
        self.assertEqual(classify_line_section_context("Load Information"), SECTION_LOAD_INFO)

    def test_section_context_summary_counts_lines(self):
        summary = section_context_summary(
            {
                "pages": [
                    {
                        "page_number": 1,
                        "text": "Load Information\nPickup\nDelivery\nCarrier Pay",
                    }
                ]
            }
        )

        self.assertEqual(summary["lines_with_section_context"], 4)
        self.assertEqual(summary["section_counts"][SECTION_PICKUP], 1)
        self.assertEqual(summary["section_counts"][SECTION_DELIVERY], 1)


if __name__ == "__main__":
    unittest.main()
