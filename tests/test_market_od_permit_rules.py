import unittest

from app.market_intelligence.market_od_permit_rules import (
    apply_od_permit_rules,
    is_od_or_permit_load,
)


class FakeLoad:
    def __init__(self):
        self.is_od = False
        self.is_blocked = False
        self.is_review_once = False
        self.block_reasons = []
        self.review_reasons = []


class FakeSearchRequest:
    def __init__(self, equipment="Flatbed"):
        self.equipment = equipment


class TestMarketOdPermitRules(unittest.TestCase):
    def test_is_od_or_permit_load_detects_parsed_notes_flags(self):
        for key in [
            "is_od",
            "is_oversize",
            "is_wide",
            "requires_permit",
            "permit_load",
        ]:
            self.assertTrue(is_od_or_permit_load({key: True}, ""))

    def test_is_od_or_permit_load_detects_keywords(self):
        for text in [
            "permit load",
            "permits required",
            "permit required",
            "over dimension",
            "over-dimensional",
            "overdimensional",
            "oversize",
            "over size",
            "wide load",
            "od load",
            "os/ow",
        ]:
            self.assertTrue(is_od_or_permit_load({}, text))

    def test_is_od_or_permit_load_returns_false_for_clean_load(self):
        self.assertFalse(is_od_or_permit_load({}, "clean legal load"))

    def test_apply_od_permit_rules_does_nothing_for_clean_load(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(equipment="Flatbed")

        result = apply_od_permit_rules(
            load,
            search_request,
            parsed_notes={},
            notes_lower="clean legal load",
        )

        self.assertIs(result, load)
        self.assertFalse(load.is_od)
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(load.block_reasons, [])
        self.assertEqual(load.review_reasons, [])

    def test_apply_od_permit_rules_blocks_conestoga(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(equipment="Conestoga")

        apply_od_permit_rules(
            load,
            search_request,
            parsed_notes={"is_od": True},
            notes_lower="",
        )

        self.assertTrue(load.is_od)
        self.assertTrue(load.is_blocked)
        self.assertFalse(load.is_review_once)
        self.assertEqual(
            load.block_reasons,
            ["OD / permit / wide load detected; Conestoga should not take OD loads."],
        )

    def test_apply_od_permit_rules_reviews_non_conestoga(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(equipment="Flatbed")

        apply_od_permit_rules(
            load,
            search_request,
            parsed_notes={},
            notes_lower="wide load",
        )

        self.assertTrue(load.is_od)
        self.assertFalse(load.is_blocked)
        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["OD / permit / wide load detected; dispatcher must verify permits/dimensions."],
        )


if __name__ == "__main__":
    unittest.main()
