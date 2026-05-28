import unittest

from app.market_intelligence.notes_parser_documents import (
    detect_document_required,
    detect_hazmat_required,
    detect_iso_tank_required,
    detect_tanker_required,
    detect_twic_required,
)


class TestNotesParserDocuments(unittest.TestCase):
    def test_detect_hazmat_required(self):
        self.assertTrue(detect_hazmat_required("hazmat"))
        self.assertTrue(detect_hazmat_required("haz mat"))
        self.assertTrue(detect_hazmat_required("hazmat required"))
        self.assertFalse(detect_hazmat_required("regular steel load"))

    def test_detect_tanker_required(self):
        self.assertTrue(detect_tanker_required("tanker"))
        self.assertTrue(detect_tanker_required("tanker endorsement"))
        self.assertTrue(detect_tanker_required("tanker endorsment"))
        self.assertFalse(detect_tanker_required("flatbed only"))

    def test_detect_twic_required(self):
        self.assertTrue(detect_twic_required("TWIC"))
        self.assertTrue(detect_twic_required("twic card"))
        self.assertTrue(detect_twic_required("twic required"))
        self.assertFalse(detect_twic_required("regular legal load"))

    def test_detect_document_required(self):
        self.assertTrue(detect_document_required("US citizen required"))
        self.assertTrue(detect_document_required("U.S. citizen"))
        self.assertTrue(detect_document_required("green card"))
        self.assertTrue(detect_document_required("work permit"))
        self.assertTrue(detect_document_required("passport"))
        self.assertTrue(detect_document_required("driver license"))
        self.assertTrue(detect_document_required("DL required"))
        self.assertFalse(detect_document_required("regular delivery"))

    def test_detect_iso_tank_required_creates_document_review_warning(self):
        self.assertTrue(detect_iso_tank_required("ISO tank load"))
        self.assertTrue(detect_iso_tank_required("iso tanks"))
        self.assertTrue(detect_iso_tank_required("isotank"))
        self.assertTrue(detect_iso_tank_required("isotanks"))
        self.assertFalse(detect_iso_tank_required("regular steel load"))


if __name__ == "__main__":
    unittest.main()
