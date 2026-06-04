import json
import unittest

from app.document_ai import field_candidate_provenance as canonical_candidates
from app.document_ai import ratecon_candidates as legacy_candidates
from app.document_ai import ratecon_field_resolution
from app.market_intelligence.intake import rate_confirmation_intake


class RateconCandidateCompatibilityPinningTests(unittest.TestCase):
    def test_legacy_candidate_constants_are_pinned(self):
        self.assertEqual(
            legacy_candidates.CONFIDENCE_LEVELS,
            ("HIGH", "MEDIUM", "LOW", "UNKNOWN"),
        )
        self.assertEqual(
            legacy_candidates.CANDIDATE_FIELD_NAMES,
            (
                "broker_name",
                "broker_mc",
                "broker_contact",
                "carrier_name",
                "load_number",
                "reference",
                "rate",
                "pickup_location",
                "pickup_date",
                "pickup_time",
                "delivery_location",
                "delivery_date",
                "delivery_time",
                "equipment",
                "weight",
                "commodity",
                "special_requirement",
                "accessorial_term",
                "unknown",
            ),
        )
        self.assertEqual(
            legacy_candidates.CANDIDATE_SOURCES,
            (
                "regex",
                "label_pattern",
                "section_pattern",
                "table_pattern_future",
                "broker_template_future",
                "ocr_future",
                "vision_future",
                "manual_review",
                "synthetic_fixture",
            ),
        )
        self.assertEqual(
            legacy_candidates.CANDIDATE_EXTRACTOR_VERSION,
            "ratecon_candidate_contract_v1",
        )

    def test_legacy_candidate_normalizers_are_pinned(self):
        self.assertEqual(legacy_candidates.normalize_confidence(" high "), "HIGH")
        self.assertEqual(legacy_candidates.normalize_confidence("low-confidence"), "UNKNOWN")
        self.assertEqual(legacy_candidates.normalize_confidence(None), "UNKNOWN")

        self.assertEqual(legacy_candidates.normalize_field_name("load number"), "load_number")
        self.assertEqual(legacy_candidates.normalize_field_name("pickup-location"), "pickup_location")
        self.assertEqual(legacy_candidates.normalize_field_name("new_field"), "unknown")

        self.assertEqual(legacy_candidates.normalize_source("label pattern"), "label_pattern")
        self.assertEqual(legacy_candidates.normalize_source(""), "regex")
        self.assertEqual(legacy_candidates.normalize_source("new_source"), "new_source")

    def test_legacy_build_field_candidate_shape_is_pinned(self):
        candidate = legacy_candidates.build_field_candidate(
            candidate_id="rate-p1-l4",
            field_name=legacy_candidates.FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=legacy_candidates.CANDIDATE_CONFIDENCE_HIGH,
            confidence_reasons=("strong total rate label",),
            page_number=1,
            line_number=4,
            label="Total Rate",
            context_before="Line before",
            context_after="Line after",
            source=legacy_candidates.SOURCE_LABEL_PATTERN,
            evidence_ref="p1-l4",
            warnings=("not_final_assignment",),
            value_type="money",
        )

        self.assertEqual(
            tuple(candidate.keys()),
            (
                "candidate_id",
                "field_name",
                "raw_value",
                "normalized_value",
                "value_type",
                "confidence",
                "confidence_reasons",
                "page_number",
                "line_number",
                "label",
                "context_before",
                "context_after",
                "source",
                "evidence_ref",
                "warnings",
            ),
        )
        self.assertEqual(candidate["candidate_id"], "rate-p1-l4")
        self.assertEqual(candidate["field_name"], "rate")
        self.assertEqual(candidate["raw_value"], "$2,850.00")
        self.assertEqual(candidate["normalized_value"], "2850.00")
        self.assertEqual(candidate["value_type"], "money")
        self.assertEqual(candidate["confidence"], "HIGH")
        self.assertEqual(candidate["confidence_reasons"], ["strong total rate label"])
        self.assertEqual(candidate["page_number"], 1)
        self.assertEqual(candidate["line_number"], 4)
        self.assertEqual(candidate["label"], "Total Rate")
        self.assertEqual(candidate["source"], "label_pattern")
        self.assertEqual(candidate["evidence_ref"], "p1-l4")
        self.assertEqual(candidate["warnings"], ["not_final_assignment"])
        json.dumps(candidate)

    def test_legacy_missing_and_unknown_defaults_are_pinned(self):
        candidate = legacy_candidates.build_field_candidate(
            field_name="unsupported field",
            raw_value=None,
            normalized_value="",
            confidence="maybe",
            confidence_reasons="single reason",
            page_number=None,
            line_number=None,
            source="",
            warnings=None,
        )

        self.assertEqual(candidate["field_name"], "unknown")
        self.assertEqual(candidate["raw_value"], "")
        self.assertEqual(candidate["normalized_value"], "")
        self.assertEqual(candidate["confidence"], "UNKNOWN")
        self.assertEqual(candidate["confidence_reasons"], ["single reason"])
        self.assertEqual(candidate["page_number"], "")
        self.assertEqual(candidate["line_number"], "")
        self.assertEqual(candidate["source"], "regex")
        self.assertEqual(candidate["warnings"], [])

    def test_legacy_candidate_extraction_result_shape_is_pinned(self):
        candidate = legacy_candidates.build_field_candidate(
            field_name=legacy_candidates.FIELD_LOAD_NUMBER,
            raw_value="FAKE-LOAD-001",
        )
        result = legacy_candidates.build_candidate_extraction_result(
            document_id=" doc-1 ",
            artifact_id=" artifact-1 ",
            candidates=[candidate, "ignored"],
            missing_candidate_fields=("rate", ""),
            warnings="candidate_extraction_only",
        )

        self.assertEqual(
            tuple(result.keys()),
            (
                "document_id",
                "artifact_id",
                "candidates",
                "missing_candidate_fields",
                "warnings",
                "extractor_version",
            ),
        )
        self.assertEqual(result["document_id"], "doc-1")
        self.assertEqual(result["artifact_id"], "artifact-1")
        self.assertEqual(result["candidates"], [candidate])
        self.assertEqual(result["missing_candidate_fields"], ["rate"])
        self.assertEqual(result["warnings"], ["candidate_extraction_only"])
        self.assertEqual(result["extractor_version"], "ratecon_candidate_contract_v1")
        json.dumps(result)

    def test_legacy_field_resolution_contract_shape_is_pinned(self):
        candidate = legacy_candidates.build_field_candidate(
            candidate_id="rate-p1-l4",
            field_name=legacy_candidates.FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=legacy_candidates.CANDIDATE_CONFIDENCE_HIGH,
            label="Carrier Pay",
            page_number=1,
            line_number=4,
            evidence_ref="p1-l4",
        )
        resolution = ratecon_field_resolution.build_field_resolution(
            field_name=legacy_candidates.FIELD_RATE,
            status=ratecon_field_resolution.FIELD_RESOLUTION_STATUS_RESOLVED,
            selected_candidate=candidate,
            confidence=legacy_candidates.CANDIDATE_CONFIDENCE_HIGH,
            reasons=["selected_highest_confidence_candidate"],
            evidence_refs=["p1-l4"],
        )

        self.assertEqual(
            tuple(resolution.keys()),
            (
                "field_name",
                "status",
                "selected_candidate",
                "selected_candidate_id",
                "selected_candidate_value",
                "selected_candidate_label",
                "selected_candidate_source",
                "selected_candidate_page",
                "selected_candidate_line",
                "rejected_candidates",
                "rejected_candidate_ids",
                "conflict_candidate_ids",
                "confidence",
                "reasons",
                "evidence_refs",
                "warnings",
                "warning_codes",
                "template_id",
                "template_version",
            ),
        )
        self.assertEqual(resolution["field_name"], "rate")
        self.assertEqual(resolution["status"], "resolved")
        self.assertEqual(resolution["selected_candidate_id"], "rate-p1-l4")
        self.assertEqual(resolution["selected_candidate_value"], "2850.00")
        self.assertEqual(resolution["selected_candidate_label"], "Carrier Pay")
        self.assertEqual(resolution["selected_candidate_source"], "regex")
        self.assertEqual(resolution["selected_candidate_page"], 1)
        self.assertEqual(resolution["selected_candidate_line"], 4)

    def test_intake_boundary_candidate_builder_shape_is_pinned(self):
        candidate = rate_confirmation_intake.build_field_candidate(
            field_name=" rate ",
            candidate_value={"amount": 2850},
            normalized_value="",
            confidence="high",
            source_method=" legacy_regex ",
            evidence_ref=" evidence-1 ",
            warnings=("needs review",),
        )

        self.assertEqual(
            tuple(candidate.keys()),
            (
                "field_name",
                "candidate_value",
                "normalized_value",
                "confidence",
                "source_method",
                "evidence_ref",
                "warnings",
            ),
        )
        self.assertEqual(candidate["field_name"], "rate")
        self.assertEqual(candidate["candidate_value"], {"amount": 2850})
        self.assertEqual(candidate["normalized_value"], {"amount": 2850})
        self.assertEqual(candidate["confidence"], "HIGH")
        self.assertEqual(candidate["source_method"], "legacy_regex")
        self.assertEqual(candidate["evidence_ref"], "evidence-1")
        self.assertEqual(candidate["warnings"], ["needs review"])
        self.assertEqual(
            rate_confirmation_intake.CRITICAL_FIELDS,
            [
                "document_id",
                "broker_name",
                "load_number",
                "rate",
                "pickup_location",
                "pickup_date",
                "delivery_location",
                "delivery_date",
                "commodity",
                "weight",
            ],
        )

    def test_canonical_field_candidate_contract_shape_is_pinned(self):
        candidate = canonical_candidates.build_field_candidate(
            field="rate",
            value="$2,850.00",
            normalized_value="2850.00",
            label="Total Rate",
            evidence_text="Total Rate $2,850.00",
            page="1",
            bbox=[1, 2, 3, 4],
            source=canonical_candidates.SOURCE_NATIVE_TEXT,
            parser_name="fake_parser",
            confidence="HIGH",
            metadata={"raw_field": "rate"},
        )

        self.assertEqual(
            tuple(candidate.keys()),
            (
                "field",
                "value",
                "normalized_value",
                "label",
                "evidence_text",
                "page",
                "bbox",
                "source",
                "parser_name",
                "confidence",
                "metadata",
            ),
        )
        self.assertEqual(candidate["field"], "total_carrier_rate")
        self.assertEqual(candidate["value"], "$2,850.00")
        self.assertEqual(candidate["normalized_value"], "2850.00")
        self.assertEqual(candidate["page"], 1)
        self.assertEqual(candidate["bbox"], [1, 2, 3, 4])
        self.assertEqual(candidate["source"], "native_text")
        self.assertEqual(candidate["parser_name"], "fake_parser")
        self.assertEqual(candidate["confidence"], 0.75)
        self.assertEqual(candidate["metadata"]["raw_field"], "rate")
        self.assertEqual(candidate["metadata"]["canonical_field"], "total_carrier_rate")
        self.assertEqual(candidate["metadata"]["semantic_role"], "main_rate")

    def test_existing_legacy_to_canonical_adapter_behavior_is_pinned(self):
        legacy = legacy_candidates.build_field_candidate(
            candidate_id="rate-p1-l4",
            field_name=legacy_candidates.FIELD_RATE,
            raw_value="$2,850.00",
            normalized_value="2850.00",
            confidence=legacy_candidates.CANDIDATE_CONFIDENCE_HIGH,
            confidence_reasons=["strong total rate label"],
            page_number=1,
            line_number=4,
            label="Total Rate",
            context_before="Line before",
            context_after="Line after",
            source=legacy_candidates.SOURCE_LABEL_PATTERN,
            evidence_ref="p1-l4",
            warnings=["review"],
            value_type="money",
        )

        candidate = canonical_candidates.adapt_ratecon_candidate_to_field_candidate(legacy)

        self.assertEqual(candidate["field"], "total_carrier_rate")
        self.assertEqual(candidate["value"], "$2,850.00")
        self.assertEqual(candidate["normalized_value"], "2850.00")
        self.assertEqual(candidate["label"], "Total Rate")
        self.assertEqual(candidate["evidence_text"], "Total Rate $2,850.00")
        self.assertEqual(candidate["page"], 1)
        self.assertEqual(candidate["source"], "native_text")
        self.assertEqual(candidate["parser_name"], "ratecon_candidate_extraction")
        self.assertEqual(candidate["confidence"], 0.75)
        self.assertEqual(candidate["metadata"]["candidate_id"], "rate-p1-l4")
        self.assertEqual(candidate["metadata"]["original_source"], "label_pattern")
        self.assertEqual(candidate["metadata"]["value_type"], "money")
        self.assertEqual(candidate["metadata"]["confidence_reasons"], ["strong total rate label"])
        self.assertEqual(candidate["metadata"]["warnings"], ["review"])


if __name__ == "__main__":
    unittest.main()
