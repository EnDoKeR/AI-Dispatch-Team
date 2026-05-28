import unittest

from app.market_intelligence.market_document_requirements import (
    document_status,
    require_driver_document,
    require_one_of_driver_documents,
)


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


class TestMarketDocumentRequirements(unittest.TestCase):
    def test_document_status_reads_driver_profile_value(self):
        search_request = FakeSearchRequest(driver_hazmat=True)

        self.assertTrue(document_status(search_request, "driver_hazmat"))
        self.assertIsNone(document_status(search_request, "driver_twic"))

    def test_require_driver_document_adds_match_reason_when_confirmed(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_hazmat=True)

        result = require_driver_document(
            load,
            search_request,
            "driver_hazmat",
            "Hazmat certificate",
        )

        self.assertIs(result, load)
        self.assertEqual(
            load.match_reasons,
            ["Hazmat certificate confirmed in driver profile."],
        )
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_require_driver_document_blocks_when_profile_says_no(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(driver_hazmat=False)

        require_driver_document(
            load,
            search_request,
            "driver_hazmat",
            "Hazmat certificate",
        )

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["Hazmat certificate required, but driver profile says driver does not have it."],
        )

    def test_require_driver_document_reviews_when_unknown(self):
        load = FakeLoad()
        search_request = FakeSearchRequest()

        require_driver_document(
            load,
            search_request,
            "driver_hazmat",
            "Hazmat certificate",
        )

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["Hazmat certificate required; ask driver and save answer in driver profile."],
        )

    def test_require_one_of_driver_documents_matches_when_any_confirmed(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            driver_us_citizen=False,
            driver_green_card_holder=True,
            driver_work_permit=None,
        )

        require_one_of_driver_documents(
            load,
            search_request,
            [
                ("driver_us_citizen", "US citizen"),
                ("driver_green_card_holder", "Green card"),
                ("driver_work_permit", "Work permit"),
            ],
            "US legal status",
        )

        self.assertEqual(
            load.match_reasons,
            ["US legal status confirmed in driver profile: Green card."],
        )
        self.assertFalse(load.is_blocked)
        self.assertFalse(load.is_review_once)

    def test_require_one_of_driver_documents_reviews_when_some_unknown(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            driver_us_citizen=False,
            driver_green_card_holder=None,
            driver_work_permit=None,
        )

        require_one_of_driver_documents(
            load,
            search_request,
            [
                ("driver_us_citizen", "US citizen"),
                ("driver_green_card_holder", "Green card"),
                ("driver_work_permit", "Work permit"),
            ],
            "US legal status",
        )

        self.assertTrue(load.is_review_once)
        self.assertEqual(
            load.review_reasons,
            ["US legal status required; ask driver about: Green card, Work permit and save answer in driver profile."],
        )

    def test_require_one_of_driver_documents_blocks_when_all_rejected(self):
        load = FakeLoad()
        search_request = FakeSearchRequest(
            driver_us_citizen=False,
            driver_green_card_holder=False,
            driver_work_permit=False,
        )

        require_one_of_driver_documents(
            load,
            search_request,
            [
                ("driver_us_citizen", "US citizen"),
                ("driver_green_card_holder", "Green card"),
                ("driver_work_permit", "Work permit"),
            ],
            "US legal status",
        )

        self.assertTrue(load.is_blocked)
        self.assertEqual(
            load.block_reasons,
            ["US legal status required, but driver profile has no accepted document/status."],
        )


if __name__ == "__main__":
    unittest.main()
