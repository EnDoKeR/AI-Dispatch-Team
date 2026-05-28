import unittest

from app.market_intelligence.notes_parser_equipment import (
    detect_conestoga_ok,
    detect_flatbed_preferred,
    detect_flatbed_required,
    detect_no_box_truck,
    detect_no_conestoga,
    detect_stepdeck_allowed,
)


class TestNotesParserEquipment(unittest.TestCase):
    def test_detect_no_conestoga_blocks_hard_terms(self):
        for text in [
            "no conestoga",
            "no stoga",
            "flatbed only",
            "flat only",
            "must be flatbed",
            "conestoga would not work",
            "conestoga won't work",
            "no con",
        ]:
            with self.subTest(text=text):
                self.assertTrue(detect_no_conestoga(text))

    def test_detect_conestoga_ok_acceptance_terms(self):
        for text in [
            "conestoga ok",
            "stoga ok",
            "conestoga accepted",
            "conestoga works",
            "tarps/conestoga ok",
        ]:
            with self.subTest(text=text):
                self.assertTrue(detect_conestoga_ok(text))

    def test_detect_flatbed_required(self):
        self.assertTrue(detect_flatbed_required("flatbed only"))
        self.assertTrue(detect_flatbed_required("flat only"))
        self.assertTrue(detect_flatbed_required("flatbed required"))
        self.assertFalse(detect_flatbed_required("flatbed preferred"))

    def test_detect_flatbed_preferred_for_conestoga_verify(self):
        self.assertTrue(detect_flatbed_preferred("flatbed preferred"))
        self.assertTrue(detect_flatbed_preferred("prefer flatbed"))
        self.assertTrue(detect_flatbed_preferred("preferred flatbed"))

        self.assertFalse(detect_no_conestoga("flatbed preferred"))
        self.assertFalse(detect_flatbed_required("flatbed preferred"))

    def test_detect_stepdeck_allowed(self):
        self.assertTrue(detect_stepdeck_allowed("flatbed or step deck"))
        self.assertTrue(detect_stepdeck_allowed("flatbed/step deck"))
        self.assertTrue(detect_stepdeck_allowed("fd or sd"))
        self.assertTrue(detect_stepdeck_allowed("stepdeck ok"))
        self.assertFalse(detect_stepdeck_allowed("flatbed only"))

    def test_detect_no_box_truck(self):
        self.assertTrue(detect_no_box_truck("no box truck"))
        self.assertTrue(detect_no_box_truck("no box trucks"))
        self.assertTrue(detect_no_box_truck("no box"))
        self.assertFalse(detect_no_box_truck("flatbed load"))


if __name__ == "__main__":
    unittest.main()
