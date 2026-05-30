import unittest

from app.document_ai.ratecon_candidate_generators import (
    build_stop_candidate_result,
    generate_stop_candidates,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_TIME,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_TIME,
)
from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates
from tests.fixtures.document_ai.ratecon_text.fixture_loader import (
    build_fixture_text_artifact,
)


class RateConStopCandidatesTests(unittest.TestCase):
    def _field_candidates(self, candidates, field_name):
        return [
            candidate
            for candidate in candidates
            if candidate["field_name"] == field_name
        ]

    def test_clean_fixture_produces_pickup_location_date_and_time_candidates(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        candidates = generate_stop_candidates(artifact)
        pickup_locations = self._field_candidates(candidates, FIELD_PICKUP_LOCATION)
        pickup_dates = self._field_candidates(candidates, FIELD_PICKUP_DATE)
        pickup_times = self._field_candidates(candidates, FIELD_PICKUP_TIME)

        self.assertTrue(pickup_locations)
        self.assertEqual(pickup_locations[0]["raw_value"], "Fake Pickup City, IL 60000")
        self.assertEqual(pickup_locations[0]["confidence"], CANDIDATE_CONFIDENCE_HIGH)
        self.assertTrue(pickup_dates)
        self.assertEqual(pickup_dates[0]["raw_value"], "05/31/2026")
        self.assertTrue(pickup_times)
        self.assertIn("08:00 AM", pickup_times[0]["raw_value"])

    def test_clean_fixture_produces_delivery_location_date_and_time_candidates(self):
        artifact = build_fixture_text_artifact("simple_clean_ratecon.txt")

        candidates = generate_stop_candidates(artifact)
        delivery_locations = self._field_candidates(candidates, FIELD_DELIVERY_LOCATION)
        delivery_dates = self._field_candidates(candidates, FIELD_DELIVERY_DATE)
        delivery_times = self._field_candidates(candidates, FIELD_DELIVERY_TIME)

        self.assertTrue(delivery_locations)
        self.assertEqual(delivery_locations[0]["raw_value"], "Fake Delivery City, TX 75201")
        self.assertEqual(delivery_locations[0]["confidence"], CANDIDATE_CONFIDENCE_HIGH)
        self.assertTrue(delivery_dates)
        self.assertEqual(delivery_dates[0]["raw_value"], "06/02/2026")
        self.assertTrue(delivery_times)
        self.assertEqual(delivery_times[0]["raw_value"], "Appt 09:30")

    def test_multi_stop_fixture_yields_multiple_stop_candidates(self):
        artifact = build_fixture_text_artifact("multi_stop_ratecon.txt")

        candidates = generate_stop_candidates(artifact)
        pickup_locations = self._field_candidates(candidates, FIELD_PICKUP_LOCATION)
        delivery_locations = self._field_candidates(candidates, FIELD_DELIVERY_LOCATION)

        self.assertGreaterEqual(len(pickup_locations), 2)
        self.assertGreaterEqual(len(delivery_locations), 1)
        self.assertTrue(
            any(candidate["raw_value"] == "2026-06-10" for candidate in candidates)
        )

    def test_fcfs_is_recognized_as_time_candidate(self):
        artifact = build_fixture_text_artifact("multi_amount_ratecon.txt")

        pickup_times = self._field_candidates(
            generate_stop_candidates(artifact),
            FIELD_PICKUP_TIME,
        )

        self.assertTrue(any(candidate["raw_value"].upper() == "FCFS" for candidate in pickup_times))

    def test_missing_pickup_date_is_not_invented(self):
        artifact = build_fixture_text_artifact("missing_core_fields_ratecon.txt")

        result = build_stop_candidate_result(artifact)

        self.assertIn(FIELD_PICKUP_DATE, result["missing_candidate_fields"])
        self.assertFalse(
            self._field_candidates(result["candidates"], FIELD_PICKUP_DATE)
        )

    def test_generic_stop_labels_are_lower_confidence(self):
        artifact = build_text_extraction_artifact_for_candidates(
            full_text=(
                "Stop 1:\n"
                "Fake Neutral City, IL 60000\n"
                "Date: 06/01/2026\n"
                "Stop 2:\n"
                "Fake Neutral Town, TX 75201\n"
                "Date: 06/02/2026\n"
            ),
            source_name="ambiguous_stop_fake.txt",
        )

        candidates = generate_stop_candidates(artifact)

        self.assertTrue(candidates)
        self.assertTrue(
            any(candidate["confidence"] == CANDIDATE_CONFIDENCE_LOW for candidate in candidates)
        )
        self.assertTrue(
            any("ambiguous_stop_section" in candidate["warnings"] for candidate in candidates)
        )


if __name__ == "__main__":
    unittest.main()
