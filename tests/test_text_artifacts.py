import json
import unittest

from app.document_ai.text_artifacts import (
    TEXT_ARTIFACT_VERSION,
    build_text_extraction_artifact_for_candidates,
    build_text_page_artifact,
)


FAKE_PAGE_TEXT = "Customer: FAKE BROKER LLC\nLoad No: FAKE-LOAD-001"


class TextArtifactTests(unittest.TestCase):
    def test_build_text_page_artifact_from_fake_text(self):
        page = build_text_page_artifact(
            page_number=1,
            text=FAKE_PAGE_TEXT,
            source_method="synthetic_fixture",
        )

        self.assertEqual(page["page_number"], 1)
        self.assertEqual(page["char_count"], len(FAKE_PAGE_TEXT))
        self.assertEqual(page["line_count"], 2)
        self.assertEqual(page["source_method"], "synthetic_fixture")

    def test_build_artifact_from_fake_pages(self):
        artifact = build_text_extraction_artifact_for_candidates(
            artifact_id="ART-TEXT-001",
            document_id="DOC-001",
            source_name="simple_clean_ratecon.txt",
            pages=[
                build_text_page_artifact(page_number=1, text=FAKE_PAGE_TEXT),
                build_text_page_artifact(page_number=2, text="Rate: $0000.00"),
            ],
        )

        self.assertEqual(artifact["artifact_id"], "ART-TEXT-001")
        self.assertEqual(artifact["document_id"], "DOC-001")
        self.assertEqual(artifact["source_name"], "simple_clean_ratecon.txt")
        self.assertEqual(artifact["page_count"], 2)
        self.assertEqual(
            artifact["char_count"],
            len(FAKE_PAGE_TEXT) + len("Rate: $0000.00"),
        )
        self.assertIn("FAKE-LOAD-001", artifact["full_text"])

    def test_serialization_round_trip(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text=FAKE_PAGE_TEXT,
            source_name="fake.txt",
        )

        payload = json.loads(json.dumps(artifact))

        self.assertEqual(payload["source_name"], "fake.txt")
        self.assertEqual(payload["artifact_version"], TEXT_ARTIFACT_VERSION)

    def test_contains_private_text_defaults_to_false(self):
        artifact = build_text_extraction_artifact_for_candidates(full_text=FAKE_PAGE_TEXT)

        self.assertFalse(artifact["contains_private_text"])
        self.assertNotIn("contains_private_text", artifact["warnings"])

    def test_private_text_flag_is_explicit_warning(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text=FAKE_PAGE_TEXT,
            contains_private_text=True,
        )

        self.assertTrue(artifact["contains_private_text"])
        self.assertIn("contains_private_text", artifact["warnings"])

    def test_artifact_can_exist_without_document_metadata(self):
        artifact = build_text_extraction_artifact_for_candidates(full_text=FAKE_PAGE_TEXT)

        self.assertEqual(artifact["artifact_id"], "")
        self.assertEqual(artifact["document_id"], "")
        self.assertEqual(artifact["page_count"], 1)


if __name__ == "__main__":
    unittest.main()
