import ast
import unittest
from pathlib import Path

from scripts.audit_ratecon_rate_money_safety_ownership import (
    analyze_rate_money_safety_ownership,
)


root = Path(__file__).resolve().parents[1]

guarded_prefixes = (
    "RATE_",
    "MONEY_",
    "TOTAL_PAY_",
    "TOTAL_CARRIER_PAY_",
    "CARRIER_PAY_",
    "CARRIER_FREIGHT_PAY_",
    "MAIN_RATE_",
    "ACCESSORIAL_",
    "DETENTION_",
    "LAYOVER_",
    "LUMPER_",
    "TONU_",
    "TRUCK_ORDER_NOT_USED_",
    "COMCHECK_",
    "GATE_FEE_",
    "LINE_HAUL_PAY_",
    "LINE_HAUL_",
    "LINEHAUL_",
    "NET_FREIGHT_",
    "AGREED_RATE_",
    "FUEL_ADVANCE_",
    "QUICK_PAY_",
    "QUICKPAY_",
    "TRACKING_",
    "ON_TIME_",
    "LATE_FEE_",
    "RATE_DEDUCTION_",
    "PENALTY_",
    "BILLING_NOISE_",
    "PAYMENT_TERMS_",
)

guarded_contains = (
    "TOTAL_CARRIER_RATE",
    "MONEY_CONTEXT",
    "RATE_SAFETY",
    "CARRIER_PAY",
    "ACCESSORIAL",
    "DETENTION",
    "LAYOVER",
    "LUMPER",
    "TONU",
    "COMCHECK",
    "GATE_FEE",
    "LINEHAUL",
    "LINE_HAUL",
    "FUEL_ADVANCE",
    "QUICKPAY",
    "QUICK_PAY",
    "TRACKING",
    "LATE_FEE",
    "RATE_DEDUCTION",
    "PENALTY",
    "BILLING_NOISE",
    "PAYMENT_TERMS",
    "_NOISE_LABELS",
    "_ACCESSORIAL_LABELS",
    "_FEE_LABELS",
    "_PENALTY_LABELS",
)

approved_constant_modules = {
    "app/document_ai/document_classification.py",
    "app/document_ai/document_types.py",
    "app/document_ai/extraction_scope.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/layout_rate_candidates.py",
    "app/document_ai/layout_shadow_candidates.py",
    "app/document_ai/private_template_pattern_collector.py",
    "app/document_ai/private_template_redaction.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_fusion.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/ratecon_candidate_generators.py",
    "app/document_ai/ratecon_candidates.py",
    "app/document_ai/ratecon_canonical_fields.py",
    "app/document_ai/ratecon_core_field_policy.py",
    "app/document_ai/ratecon_field_resolution.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_review_workbook.py",
    "app/document_ai/ratecon_table_semantics.py",
    "app/document_ai/review_issue_taxonomy.py",
    "app/document_ai/stop_group_provenance_report.py",
    "app/document_ai/stop_span_extractor.py",
    "app/document_ai/stop_normalization.py",
    "app/document_ai/stop_review_pattern_classifier.py",
    "app/document_ai/private_measurement_pipeline.py",
    "scripts/driver_learning_report.py",
}

approved_classifier_function_modules = {
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_candidate_context_features.py",
}


def _posix(path):
    return str(path).replace("\\", "/")


def _iter_python_paths():
    roots = [
        root / "app" / "document_ai",
        root / "scripts",
    ]
    for package_root in roots:
        for path in sorted(package_root.glob("*.py")):
            if path.name == "__init__.py":
                continue
            yield path


def _guarded_constant_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        else:
            targets = []
        for name in targets:
            if not name.isupper():
                continue
            if name.startswith("RATECON_"):
                continue
            if (
                name.startswith(guarded_prefixes)
                or name.endswith(("_MONEY_CONTEXT", "_RATE_CONTEXT"))
                or any(marker in name for marker in guarded_contains)
            ):
                names.append(name)
    return names


def _guarded_classifier_function_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names = []
    guarded_markers = (
        "money_context",
        "rate_context",
        "context_classifier",
        "safe_total_context",
        "unsafe_money_context",
        "payment_instruction_context",
        "billing_noise_context",
        "line_item_context",
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = node.name.lower()
        if name.startswith("_"):
            continue
        if name in {"classify_money_context", "classify_rate_candidate_context"}:
            names.append(node.name)
        elif name.startswith("is_") and any(marker in name for marker in guarded_markers):
            names.append(node.name)
        elif name.startswith("classify_") and "money_context" in name:
            names.append(node.name)
    return names


class RateconRateMoneyConstantGuardrailTests(unittest.TestCase):
    def test_rate_money_constants_stay_in_documented_modules(self):
        unexpected = []
        for path in _iter_python_paths():
            names = _guarded_constant_names(path)
            if not names:
                continue
            rel_path = _posix(path.relative_to(root))
            if rel_path not in approved_constant_modules:
                unexpected.append((rel_path, names))

        self.assertEqual(
            [],
            unexpected,
            "New rate/money/accessorial/source/diagnosis constants must be added "
            "only in canonical, support-policy, or documented compatibility modules.",
        )

    def test_money_context_classifier_functions_stay_in_documented_modules(self):
        unexpected = []
        for path in _iter_python_paths():
            names = _guarded_classifier_function_names(path)
            if not names:
                continue
            rel_path = _posix(path.relative_to(root))
            if rel_path not in approved_classifier_function_modules:
                unexpected.append((rel_path, names))

        self.assertEqual(
            [],
            unexpected,
            "New money-context classifier functions must live in "
            "ratecon_rate_money_safety.py or documented compatibility wrappers.",
        )

    def test_known_rate_money_duplicate_constant_debt_is_pinned(self):
        summary = analyze_rate_money_safety_ownership(root)
        duplicate_names = {row["constant_name"] for row in summary["duplicate_constants"]}

        self.assertEqual(29, summary["duplicate_constant_count"])
        self.assertIn("ACCESSORIAL_LABELS", duplicate_names)
        self.assertIn("RATE_NEGATIVE_LABELS", duplicate_names)
        self.assertIn("FIELD_TOTAL_CARRIER_RATE", duplicate_names)
        self.assertIn("MONEY_CONTEXT_TOTAL_CARRIER_PAY", duplicate_names)
        self.assertIn(
            "RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT;RATE_CONFLICT_LINEHAUL_TOTAL",
            duplicate_names,
        )


if __name__ == "__main__":
    unittest.main()
