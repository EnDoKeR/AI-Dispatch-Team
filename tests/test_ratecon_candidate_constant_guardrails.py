import ast
import unittest
from pathlib import Path

from scripts.audit_ratecon_candidate_model_ownership import (
    analyze_candidate_model_ownership,
)


root = Path(__file__).resolve().parents[1]

constant_name_markers = (
    "CANDIDATE",
    "CONFIDENCE",
    "SOURCE",
    "FIELD",
    "STATUS",
)

approved_constant_modules = {
    "app/document_ai/broker_templates.py",
    "app/document_ai/broker_template_candidate_extraction.py",
    "app/document_ai/broker_template_matcher.py",
    "app/document_ai/broker_template_registry.py",
    "app/document_ai/broker_template_scoring.py",
    "app/document_ai/candidate_coverage_analysis.py",
    "app/document_ai/candidate_coverage_target_selector.py",
    "app/document_ai/candidate_fusion.py",
    "app/document_ai/core_field_gap_analysis.py",
    "app/document_ai/dispatcher_review_table.py",
    "app/document_ai/document_classification.py",
    "app/document_ai/document_extraction_artifact.py",
    "app/document_ai/extraction_readiness.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/field_candidate_provenance.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/layout_candidate_extraction.py",
    "app/document_ai/layout_field_delta_audit.py",
    "app/document_ai/layout_pipeline.py",
    "app/document_ai/layout_provider.py",
    "app/document_ai/layout_provider_contract.py",
    "app/document_ai/layout_provider_diagnostics.py",
    "app/document_ai/load_identifier_coverage_audit.py",
    "app/document_ai/load_identifier_candidate_adapter_provenance.py",
    "app/document_ai/load_identifier_generated_provenance_boundary.py",
    "app/document_ai/load_identifier_generated_resolver_provenance.py",
    "app/document_ai/load_identifier_resolver_to_audit_provenance.py",
    "app/document_ai/load_identifier_source_line_audit.py",
    "app/document_ai/load_identifier_source_line_detail.py",
    "app/document_ai/load_identifier_source_line_serialization.py",
    "app/document_ai/local_review_analysis.py",
    "app/document_ai/measurement_integrity.py",
    "app/document_ai/normalized_stops.py",
    "app/document_ai/ocr_provider_contract.py",
    "app/document_ai/ocr_stop_block_assembler.py",
    "app/document_ai/operational_fusion.py",
    "app/document_ai/pdf_triage_contract.py",
    "app/document_ai/pdfplumber_layout_provider.py",
    "app/document_ai/private_measurement.py",
    "app/document_ai/private_measurement_blockers.py",
    "app/document_ai/private_measurement_pipeline.py",
    "app/document_ai/private_measurement_reports.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_fusion.py",
    "app/document_ai/ratecon_candidates.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/ratecon_candidate_extraction.py",
    "app/document_ai/ratecon_canonical_fields.py",
    "app/document_ai/ratecon_core_field_policy.py",
    "app/document_ai/ratecon_field_resolution.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/ratecon_hybrid_contract.py",
    "app/document_ai/ratecon_intake_draft.py",
    "app/document_ai/ratecon_local_provider_readiness.py",
    "app/document_ai/ratecon_model_assisted_contract.py",
    "app/document_ai/ratecon_model_provider_contract.py",
    "app/document_ai/ratecon_ocr_candidate_policy.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_load_table_safety.py",
    "app/document_ai/ratecon_review_workbook.py",
    "app/document_ai/ratecon_schema.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
    "app/document_ai/ratecon_stop_component_policy.py",
    "app/document_ai/review_feedback_import.py",
    "app/document_ai/review_issue_taxonomy.py",
    "app/document_ai/stop_association.py",
    "app/document_ai/stop_group_provenance.py",
    "app/document_ai/stop_normalization.py",
    "app/document_ai/stop_review_pattern_classifier.py",
    "app/document_ai/stop_span_extractor.py",
    "app/document_ai/structured_stop_values.py",
    "app/document_ai/target_disposition.py",
    "app/market_intelligence/intake/anonymized_ratecon_scenario_report.py",
    "app/market_intelligence/intake/case_link_candidate.py",
    "app/market_intelligence/intake/parser_confidence.py",
    "app/market_intelligence/intake/pasted_text_parser_adapter.py",
    "app/market_intelligence/intake/rate_confirmation_intake.py",
    "app/market_intelligence/intake/rate_confirmation_validation.py",
    "app/market_intelligence/intake/ratecon_core_fields.py",
    "app/market_intelligence/intake/ratecon_dry_run_csv_export.py",
    "app/market_intelligence/intake/ratecon_field_diagnostics.py",
    "app/market_intelligence/intake/ratecon_layout_diagnostics.py",
    "app/market_intelligence/intake/ratecon_parser_coverage.py",
    "app/market_intelligence/intake/ratecon_pdf_dry_run.py",
    "app/market_intelligence/intake/record.py",
    "app/market_intelligence/intake/report.py",
    "app/market_intelligence/intake/status.py",
    "app/market_intelligence/intake/summary.py",
}


def _posix(path):
    return str(path).replace("\\", "/")


def _iter_python_paths():
    roots = [
        root / "app" / "document_ai",
        root / "app" / "market_intelligence" / "intake",
    ]
    for package_root in roots:
        for path in sorted(package_root.glob("*.py")):
            if path.name == "__init__.py":
                continue
            yield path


def _constant_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            targets = []
        names.extend(
            name
            for name in targets
            if name.isupper() and any(marker in name for marker in constant_name_markers)
        )
    return names


class RateconCandidateConstantGuardrailTests(unittest.TestCase):
    def test_candidate_like_constants_stay_in_documented_modules(self):
        unexpected = []
        for path in _iter_python_paths():
            names = _constant_names(path)
            if not names:
                continue
            rel_path = _posix(path.relative_to(root))
            if rel_path not in approved_constant_modules:
                unexpected.append((rel_path, names))

        self.assertEqual(
            [],
            unexpected,
            "New candidate/source/confidence/field/status constants must be added "
            "only in canonical, support-policy, or documented compatibility modules.",
        )

    def test_known_candidate_duplicate_constant_debt_is_pinned(self):
        summary = analyze_candidate_model_ownership(root)
        duplicates = summary["duplicate_constants"]
        duplicate_names = {row["constant_name"] for row in duplicates}

        self.assertEqual(37, summary["duplicate_constant_count"])
        self.assertIn(
            "CANDIDATE_CONFIDENCE_HIGH;CONFIDENCE_HIGH",
            duplicate_names,
        )
        self.assertIn(
            "FIELD_RESOLUTION_STATUS_RESOLVED;NORMALIZED_STOP_FIELD_STATUS_RESOLVED",
            duplicate_names,
        )
        self.assertIn("SOURCE_OCR", duplicate_names)


if __name__ == "__main__":
    unittest.main()
