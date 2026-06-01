import unittest

from app.document_ai.field_candidate_generators import (
    FieldCandidateGenerator,
    GENERATOR_LEGACY_FINAL_OUTPUT,
    generate_field_candidates,
    _dedupe,
)
from app.document_ai.field_candidate_provenance import build_field_candidate


def artifact(text):
    return {
        "document_id": "DOC-001",
        "source": "native",
        "pages": [{"page_number": 1, "text": text}],
        "full_text": text,
    }


class FieldCandidateGeneratorTests(unittest.TestCase):
    def test_multiple_generators_run_and_summarize(self):
        result = generate_field_candidates(
            artifact("Load #: FAKE-LOAD-001\nTotal Carrier Pay $1000.00"),
            include_legacy_final_candidates=False,
        )

        self.assertGreaterEqual(len(result["candidates"]), 2)
        self.assertTrue(result["generator_summaries"])
        generator_names = {item["generator_name"] for item in result["generator_summaries"]}
        self.assertIn("document_text_candidate_extractor", generator_names)
        self.assertIn("load_identifier_line_candidate_generator", generator_names)

    def test_generator_errors_are_captured_and_strict_can_raise(self):
        def broken(_artifact, _triage, _legacy_context):
            raise RuntimeError("boom")

        generators = [FieldCandidateGenerator("broken", "fake", broken)]
        result = generate_field_candidates(
            artifact("Load #: FAKE-LOAD-001"),
            include_legacy_final_candidates=False,
            generators=generators,
        )

        self.assertEqual(result["errors"][0]["generator_name"], "broken")
        with self.assertRaises(RuntimeError):
            generate_field_candidates(
                artifact("Load #: FAKE-LOAD-001"),
                include_legacy_final_candidates=False,
                strict=True,
                generators=generators,
            )

    def test_legacy_final_adapter_is_marked_diagnostic_and_can_be_disabled(self):
        legacy_context = {
            "legacy_summary": {
                "_comparison_values": {
                    "load_number": "FAKE-LOAD-001",
                    "total_carrier_rate": "1000.00",
                }
            }
        }
        result = generate_field_candidates(
            artifact("No label here"),
            legacy_context=legacy_context,
            include_legacy_final_candidates=True,
        )

        fallback = [
            candidate
            for candidate in result["candidates"]
            if candidate["parser_name"] == GENERATOR_LEGACY_FINAL_OUTPUT
        ]
        self.assertEqual(len(fallback), 2)
        self.assertTrue(fallback[0]["metadata"]["diagnostic_fallback"])

        disabled = generate_field_candidates(
            artifact("No label here"),
            legacy_context=legacy_context,
            include_legacy_final_candidates=False,
        )
        self.assertFalse(
            [
                candidate
                for candidate in disabled["candidates"]
                if candidate["parser_name"] == GENERATOR_LEGACY_FINAL_OUTPUT
            ]
        )

    def test_load_number_line_labels_and_negative_refs(self):
        result = generate_field_candidates(
            artifact(
                "Load #: FAKE-LOAD-001\n"
                "Shipment ID FAKE-SHIP-002\n"
                "PO #: FAKE-PO-003\n"
                "Reference #: FAKE-REF-004\n"
            ),
            include_legacy_final_candidates=False,
        )

        load_candidates = [
            candidate for candidate in result["candidates"] if candidate["field"] == "load_number"
        ]
        refs = [
            candidate
            for candidate in result["candidates"]
            if candidate["field"] == "reference_numbers"
            and candidate["parser_name"] == "load_identifier_line_candidate_generator"
        ]

        self.assertGreaterEqual(len(load_candidates), 2)
        self.assertTrue(
            any(
                candidate["metadata"].get("label_strength") == "strong"
                for candidate in load_candidates
            )
        )
        self.assertTrue(
            any(candidate["metadata"]["id_type_hint"] == "po" for candidate in refs)
        )
        self.assertTrue(
            all(
                not candidate["metadata"]["is_primary_identifier_candidate"]
                for candidate in refs
            )
        )

    def test_adjacent_and_spaced_load_identifier_lines_emit_candidates(self):
        result = generate_field_candidates(
            artifact("Load #\nFAKE-LOAD-001\nShipment              FAKE-SHIP-002"),
            include_legacy_final_candidates=False,
        )

        load_candidates = [
            candidate for candidate in result["candidates"] if candidate["field"] == "load_number"
        ]
        self.assertGreaterEqual(len(load_candidates), 2)
        generator_summary = [
            item
            for item in result["generator_summaries"]
            if item["generator_name"] == "load_identifier_line_candidate_generator"
        ][0]
        self.assertGreaterEqual(
            generator_summary["diagnostics"]["lines_scanned_count"],
            3,
        )
        self.assertGreaterEqual(
            generator_summary["diagnostics"]["label_hits_count"],
            2,
        )

    def test_adjacent_previous_load_identifier_line_emits_candidate(self):
        result = generate_field_candidates(
            artifact("FAKE-LOAD-001\nLoad #"),
            include_legacy_final_candidates=False,
        )

        load_candidates = [
            candidate
            for candidate in result["candidates"]
            if candidate["field"] == "load_number"
            and candidate["parser_name"] == "load_identifier_line_candidate_generator"
        ]
        self.assertTrue(load_candidates)
        self.assertEqual(
            load_candidates[0]["metadata"]["value_extraction_method"],
            "adjacent_previous",
        )

    def test_full_text_fallback_works_when_page_lines_are_empty(self):
        result = generate_field_candidates(
            {
                "document_id": "DOC-001",
                "source": "native",
                "pages": [],
                "full_text": "Load #: FAKE-LOAD-001",
            },
            include_legacy_final_candidates=False,
        )

        self.assertTrue(
            [
                candidate
                for candidate in result["candidates"]
                if candidate["field"] == "load_number"
            ]
        )

    def test_load_identifier_candidate_metadata_includes_forensic_shape(self):
        result = generate_field_candidates(
            artifact("Load #: FAKE-LOAD-001"),
            include_legacy_final_candidates=False,
        )

        candidate = [
            item
            for item in result["candidates"]
            if item["parser_name"] == "load_identifier_line_candidate_generator"
            and item["field"] == "load_number"
        ][0]
        self.assertEqual(candidate["metadata"]["label_hit_type"], "same_line_value_present")
        self.assertEqual(candidate["metadata"]["value_extraction_method"], "same_line")
        self.assertTrue(candidate["metadata"]["candidate_value_shape"]["has_digits"])
        self.assertGreaterEqual(candidate["confidence"], 0.80)

    def test_load_identifier_rejected_shapes_are_diagnostic(self):
        result = generate_field_candidates(
            artifact(
                "Load #: 06/10/2026\n"
                "Shipment #: 555-123-4567\n"
                "Tender #: 100.00\n"
            ),
            include_legacy_final_candidates=False,
        )

        generator_summary = [
            item
            for item in result["generator_summaries"]
            if item["generator_name"] == "load_identifier_line_candidate_generator"
        ][0]
        skipped = generator_summary["diagnostics"]["skipped_reason_counts"]
        self.assertIn("candidate_looks_like_date", skipped)
        self.assertIn("candidate_looks_like_phone", skipped)
        self.assertIn("candidate_looks_like_money", skipped)
        self.assertIn("load_identity_forensics", generator_summary["diagnostics"])

    def test_candidate_canonical_mapping_preserves_raw_field_and_caps_weak(self):
        candidate = build_field_candidate(
            field="pro_number",
            value="FAKE-PRO-001",
            label="PRO #",
            confidence=0.95,
        )

        self.assertEqual(candidate["field"], "load_number")
        self.assertEqual(candidate["metadata"]["raw_field"], "pro_number")
        self.assertEqual(candidate["metadata"]["canonical_mapping_strength"], "weak")
        self.assertLessEqual(candidate["confidence"], 0.62)

    def test_unmapped_candidate_remains_visible_for_diagnostics(self):
        candidate = build_field_candidate(
            field="custom_template_signal",
            value="FAKE-VALUE-001",
            confidence=0.7,
        )

        self.assertEqual(candidate["field"], "custom_template_signal")
        self.assertEqual(
            candidate["metadata"]["canonical_mapping_strength"],
            "unmapped",
        )

    def test_rate_candidates_classify_total_and_accessorial_separately(self):
        result = generate_field_candidates(
            artifact("Total Carrier Pay $1000.00\nQuick Pay Fee $30.00"),
            include_legacy_final_candidates=False,
        )

        total_rates = [
            candidate
            for candidate in result["candidates"]
            if candidate["field"] == "total_carrier_rate"
        ]
        accessorials = [
            candidate
            for candidate in result["candidates"]
            if candidate["field"] == "accessorial_term"
        ]

        self.assertTrue(total_rates)
        self.assertTrue(accessorials)
        self.assertIn("total_carrier_pay", total_rates[0]["metadata"].get("value_type", ""))

    def test_legacy_stop_set_becomes_pickup_delivery_candidates(self):
        result = generate_field_candidates(
            artifact("Stop summary unavailable"),
            legacy_context={
                "normalized_stop_set": {
                    "pickup_count": 1,
                    "delivery_count": 1,
                    "stops": [
                        {
                            "stop_type": "pickup",
                            "page_numbers": [1],
                            "fields": [
                                {"field_name": "location", "status": "resolved"},
                                {"field_name": "date", "status": "resolved"},
                            ],
                        },
                        {
                            "stop_type": "delivery",
                            "page_numbers": [1],
                            "fields": [
                                {"field_name": "location", "status": "resolved"},
                            ],
                        },
                    ],
                }
            },
            include_legacy_final_candidates=False,
        )

        fields = {candidate["field"] for candidate in result["candidates"]}
        self.assertIn("pickup_stops", fields)
        self.assertIn("delivery_stops", fields)
        structured = [
            candidate
            for candidate in result["candidates"]
            if candidate["metadata"].get("structured_stop_candidate")
        ]
        self.assertEqual(len(structured), 2)
        self.assertTrue(structured[0]["metadata"]["has_location"])

    def test_stop_evidence_assembler_promotes_partial_candidates(self):
        result = generate_field_candidates(
            artifact("Stop evidence is available from legacy candidate result"),
            legacy_context={
                "candidate_result": {
                    "candidates": [
                        {
                            "field_name": "pickup_location",
                            "raw_value": "Fake Origin Facility",
                            "confidence": "HIGH",
                        },
                        {
                            "field_name": "pickup_date",
                            "raw_value": "06/10/2026",
                            "confidence": "HIGH",
                        },
                        {
                            "field_name": "delivery_location",
                            "raw_value": "Fake Destination Facility",
                            "confidence": "HIGH",
                        },
                        {
                            "field_name": "delivery_date",
                            "raw_value": "06/11/2026",
                            "confidence": "HIGH",
                        },
                    ]
                }
            },
            include_legacy_final_candidates=False,
        )

        assembled = [
            candidate
            for candidate in result["candidates"]
            if candidate["parser_name"] == "stop_evidence_assembler"
        ]
        fields = {candidate["field"] for candidate in assembled}
        self.assertIn("pickup_stops", fields)
        self.assertIn("delivery_stops", fields)
        self.assertTrue(assembled[0]["metadata"]["assembled_from_partial_evidence"])
        summary = [
            item
            for item in result["generator_summaries"]
            if item["generator_name"] == "stop_evidence_assembler"
        ][0]
        self.assertEqual(summary["diagnostics"]["stop_evidence_count"], 4)
        self.assertEqual(
            summary["diagnostics"]["assembled_pickup_stop_candidate_count"],
            1,
        )

    def test_structured_stop_dedupe_preserves_distinct_table_rows(self):
        candidates = [
            {
                "field": "pickup_stops",
                "value": "pickup_layout_stop_present",
                "normalized_value": "pickup_layout_stop_present",
                "label": "pickup_layout_stop",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "metadata": {
                    "structured_stop_candidate": True,
                    "stop_role": "pickup",
                    "table_index": 1,
                    "row_index": 1,
                    "cell_indices": [0, 1],
                    "has_location": True,
                    "has_date": True,
                },
            },
            {
                "field": "pickup_stops",
                "value": "pickup_layout_stop_present",
                "normalized_value": "pickup_layout_stop_present",
                "label": "pickup_layout_stop",
                "source": "native_layout",
                "parser_name": "layout_stop_table_candidate_generator",
                "metadata": {
                    "structured_stop_candidate": True,
                    "stop_role": "pickup",
                    "table_index": 1,
                    "row_index": 2,
                    "cell_indices": [0, 1],
                    "has_location": True,
                    "has_date": True,
                },
            },
        ]

        self.assertEqual(len(_dedupe(candidates)), 2)


if __name__ == "__main__":
    unittest.main()
