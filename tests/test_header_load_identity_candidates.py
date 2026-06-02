import unittest

from app.document_ai.field_candidate_generators import (
    GENERATOR_HEADER_LOAD_IDENTITY,
    LOAD_CANDIDATE_PROFILE_BASELINE,
    LOAD_CANDIDATE_PROFILE_HEADER_RECALL_V1,
    _header_load_identity_generator,
    generate_field_candidates,
)


def _artifact(lines):
    return {
        "document_id": "DOC-1",
        "full_text": "\n".join(lines),
        "pages": [
            {
                "page_number": 1,
                "height": 1000,
                "text": "\n".join(lines),
                "lines": [
                    {"text": line, "line_index": index, "bbox": [0, index * 10, 500, index * 10 + 8]}
                    for index, line in enumerate(lines)
                ],
            }
        ],
    }


class HeaderLoadIdentityCandidateGeneratorTests(unittest.TestCase):
    def _load_candidates(self, line):
        candidates, _warnings, diagnostics = _header_load_identity_generator(_artifact([line]))
        self.assertGreaterEqual(
            diagnostics["header_load_identity_summary"]["label_hits_count"],
            1,
        )
        return candidates

    def test_header_load_examples_emit_primary_load_candidates(self):
        cases = [
            ("Load#: EXP7339264", "load"),
            ("Load Number: SPT-484333", "load"),
            ("Order(s) # 12470 LOAD CONFIRMATION", "order"),
            ("TQL RATE CONFIRMATION FOR PO# 36979531", "po"),
            ("Freight Bill # 9492965", "freight_bill"),
            ("IEL PO#: 2679031", "po"),
            ("PRO# 42233054", "pro"),
        ]
        for line, expected_hint in cases:
            with self.subTest(line=line):
                candidates = self._load_candidates(line)
                primary = [candidate for candidate in candidates if candidate["field"] == "load_number"]
                self.assertTrue(primary)
                metadata = primary[0]["metadata"]
                self.assertEqual(metadata["id_type_hint"], expected_hint)
                self.assertTrue(metadata["is_primary_identifier_candidate"])
                self.assertIn(metadata["label_strength"], {"strong", "medium"})
                self.assertGreaterEqual(primary[0]["confidence"], 0.65)

    def test_stop_reference_and_bol_are_not_strong_primary_load(self):
        candidates, _warnings, _diagnostics = _header_load_identity_generator(
            _artifact(["Pickup Information", "PU# 12345", "BOL# 99999"])
        )

        self.assertFalse([candidate for candidate in candidates if candidate["field"] == "load_number"])
        self.assertTrue(candidates)
        self.assertTrue(all(candidate["confidence"] <= 0.55 for candidate in candidates))

    def test_truck_trailer_driver_ids_are_rejected(self):
        candidates, _warnings, diagnostics = _header_load_identity_generator(
            _artifact(["Truck # 12345", "Driver # 98765", "Trailer # 55555"])
        )

        self.assertEqual(candidates, [])
        self.assertIn(
            "driver_truck_trailer_noise",
            diagnostics["header_load_identity_summary"]["rejection_reason_counts"],
        )

    def test_header_recall_profile_is_explicit(self):
        artifact = _artifact(["TQL RATE CONFIRMATION FOR PO# 36979531"])

        baseline = generate_field_candidates(
            artifact,
            include_legacy_final_candidates=False,
            load_candidate_profile=LOAD_CANDIDATE_PROFILE_BASELINE,
        )
        experiment = generate_field_candidates(
            artifact,
            include_legacy_final_candidates=False,
            load_candidate_profile=LOAD_CANDIDATE_PROFILE_HEADER_RECALL_V1,
        )

        self.assertFalse(
            [
                summary
                for summary in baseline["generator_summaries"]
                if summary["generator_name"] == GENERATOR_HEADER_LOAD_IDENTITY
            ]
        )
        self.assertTrue(
            [
                summary
                for summary in experiment["generator_summaries"]
                if summary["generator_name"] == GENERATOR_HEADER_LOAD_IDENTITY
            ]
        )


if __name__ == "__main__":
    unittest.main()
