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
    "CARRIER_PAY_",
    "ACCESSORIAL_",
    "DETENTION_",
    "LINE_HAUL_",
    "LINEHAUL_",
    "FUEL_ADVANCE_",
    "QUICK_PAY_",
    "QUICKPAY_",
)

guarded_contains = (
    "TOTAL_CARRIER_RATE",
    "MONEY_CONTEXT",
    "RATE_SAFETY",
    "CARRIER_PAY",
    "ACCESSORIAL",
    "DETENTION",
    "LINEHAUL",
    "LINE_HAUL",
    "FUEL_ADVANCE",
    "QUICKPAY",
    "QUICK_PAY",
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
    "app/document_ai/stop_span_extractor.py",
    "scripts/driver_learning_report.py",
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

    def test_known_rate_money_duplicate_constant_debt_is_pinned(self):
        summary = analyze_rate_money_safety_ownership(root)
        duplicate_names = {row["constant_name"] for row in summary["duplicate_constants"]}

        self.assertEqual(27, summary["duplicate_constant_count"])
        self.assertIn("FIELD_TOTAL_CARRIER_RATE", duplicate_names)
        self.assertIn("MONEY_CONTEXT_TOTAL_CARRIER_PAY", duplicate_names)
        self.assertIn(
            "RATE_AUDIT_LINEHAUL_TOTAL_CONFLICT;RATE_CONFLICT_LINEHAUL_TOTAL",
            duplicate_names,
        )


if __name__ == "__main__":
    unittest.main()
