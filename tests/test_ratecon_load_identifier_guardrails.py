import ast
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

APPROVED_OWNER_PATHS = {
    "app/document_ai/load_identifier_candidates.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_field_resolution.py",
    "app/document_ai/ratecon_load_table_safety.py",
    "app/document_ai/load_identity_forensics.py",
    "app/document_ai/load_identifier_coverage_audit.py",
    "app/document_ai/load_identifier_source_line_audit.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/run_private_ratecon_measurement.py",
    "scripts/compare_ratecon_private_selected_load_aggregates.py",
    "scripts/audit_ratecon_load_identifier_ownership.py",
}

CURRENT_COMPATIBILITY_ALLOWLIST = {
    "app/document_ai/candidate_coverage_analysis.py",
    "app/document_ai/candidate_coverage_target_selector.py",
    "app/document_ai/core_field_gap_analysis.py",
    "app/document_ai/dispatcher_review_table.py",
    "app/document_ai/document_classification.py",
    "app/document_ai/layout_field_delta_audit.py",
    "app/document_ai/layout_shadow_candidates.py",
    "app/document_ai/local_review_analysis.py",
    "app/document_ai/measurement_cli/ratecon_private_args.py",
    "app/document_ai/measurement_cli/ratecon_private_output_paths.py",
    "app/document_ai/private_measurement_pipeline.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/ratecon_candidates.py",
    "app/document_ai/ratecon_canonical_fields.py",
    "app/document_ai/ratecon_core_field_policy.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/ratecon_ocr_candidate_policy.py",
    "app/document_ai/ratecon_review_workbook.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
    "app/document_ai/ratecon_table_semantics.py",
    "app/document_ai/review_feedback_target_selector.py",
    "app/document_ai/review_issue_taxonomy.py",
    "app/market_intelligence/intake/rate_confirmation_intake.py",
    "app/market_intelligence/market_exit_classifier.py",
    "scripts/analyze_load_identifier_coverage.py",
    "scripts/analyze_load_identifier_source_lines.py",
    "scripts/compare_ratecon_gold_evaluations.py",
    "scripts/run_load_board_simulation.py",
}

SYMBOL_PATTERNS = (
    re.compile(r".*LOAD_IDENTIFIER.*"),
    re.compile(r".*LOAD_NUMBER.*"),
    re.compile(r".*ORDER_NUMBER.*"),
    re.compile(r".*PO_NUMBER.*"),
    re.compile(r".*PRO_NUMBER.*"),
    re.compile(r".*REFERENCE_NUMBER.*"),
    re.compile(r".*TABLE_NEIGHBOR.*"),
    re.compile(r".*NEARBY_ROW.*"),
    re.compile(r".*LOAD_ID.*"),
    re.compile(r"build_.*load.*identifier.*", re.IGNORECASE),
    re.compile(r"classify_.*load.*", re.IGNORECASE),
    re.compile(r"normalize_.*load.*", re.IGNORECASE),
)


def _tracked_python_paths():
    roots = (ROOT / "app", ROOT / "scripts")
    for root in roots:
        for path in root.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if ".local_outputs" in rel or "__pycache__" in rel:
                continue
            yield path


def _matches_guardrail(name: str) -> bool:
    return any(pattern.fullmatch(name) for pattern in SYMBOL_PATTERNS)


class RateconLoadIdentifierGuardrailTests(unittest.TestCase):
    def test_load_identifier_symbols_remain_in_approved_or_allowlisted_modules(self):
        violations = []
        for path in _tracked_python_paths():
            rel = path.relative_to(ROOT).as_posix()
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    names.append(node.name)
                elif isinstance(node, ast.Assign):
                    names.extend(target.id for target in node.targets if isinstance(target, ast.Name))
                for name in names:
                    if not _matches_guardrail(name):
                        continue
                    if rel in APPROVED_OWNER_PATHS or rel in CURRENT_COMPATIBILITY_ALLOWLIST:
                        continue
                    violations.append(f"{rel}:{getattr(node, 'lineno', '')}:{name}")

        self.assertEqual(violations, [])

    def test_documented_owner_modules_are_present(self):
        for rel in (
            "app/document_ai/load_identifier_candidates.py",
            "app/document_ai/load_identity_forensics.py",
            "app/document_ai/load_identifier_coverage_audit.py",
            "app/document_ai/load_identifier_source_line_audit.py",
            "scripts/compare_ratecon_private_selected_load_aggregates.py",
        ):
            self.assertTrue((ROOT / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
