import unittest

from app.market_intelligence.market_document_triggers import apply_document_triggers


class FakeLoad:
    def __init__(self):
        self.match_reasons = []
        self.review_reasons = []
        self.block_reasons = []
        self.is_review_once = False
        self.is_blocked = False


class FakeSearchRequest:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestMarketDocumentTriggers(unittest.TestCase):
    def test_apply_document_triggers_does_nothing_for_clean_text(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()

        result = apply_document_triggers(load, search_request, "clean flatbed load")

        self.assertIs(result, load)
        self.assertEqual(load.match_reasons, [])
        self.assertEqual(load.review_reasons, [])
        self.assertEqual(load.block_reasons, [])
        self.assertFalse(load.is_review_once)
        self.assertFalse(load.is_blocked)

    def test_apply_document_triggers_detects_hazmat(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_hazmat=True)

        apply_document_triggers(load, search_request, "hazmat load")

        self.assertEqual(
            load.match_reasons,
            ["Hazmat certificate confirmed in driver profile."],
        )

    def test_apply_document_triggers_detects_tanker_endorsement(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_tanker_endorsement=None)

        apply_document_triggers(load, search_request, "tanker endorsement required")

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Tanker endorsement required; ask driver and save answer in driver profile."],
        )

    def test_apply_document_triggers_detects_twic(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_twic=False)

        apply_document_triggers(load, search_request, "twic card required")

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["TWIC card required, but driver profile says driver does not have it."],
        )

    def test_apply_document_triggers_detects_us_legal_status(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            driver_us_citizen=False,
            driver_green_card_holder=True,
            driver_work_permit=None,
        )

        apply_document_triggers(load, search_request, "green card required")

        self.assertEqual(
            load.match_reasons,
            ["US legal status confirmed in driver profile: Green card."],
        )

    def test_apply_document_triggers_detects_ramps(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_ramps=True)

        apply_document_triggers(load, search_request, "ramps required")

        self.assertEqual(
            load.match_reasons,
            ["Ramps confirmed in driver profile."],
        )

    def test_apply_document_triggers_detects_dunnage(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_dunnage=None)

        apply_document_triggers(load, search_request, "dunnage required")

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Dunnage / wood / blocking material required; ask driver and save answer in driver profile."],
        )


if __name__ == "__main__":
    unittest.main()
