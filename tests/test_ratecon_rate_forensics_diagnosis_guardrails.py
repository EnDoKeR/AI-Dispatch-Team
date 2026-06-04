import ast
import unittest
from pathlib import Path


root = Path(__file__).resolve().parents[1]

approved_constant_modules = {
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
    "app/document_ai/field_candidate_resolver.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "scripts/compare_ratecon_gold_evaluations.py",
}

approved_function_modules = {
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/field_candidate_resolver.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "scripts/compare_ratecon_gold_evaluations.py",
    "scripts/audit_ratecon_rate_forensics_diagnosis_mapping.py",
}

guarded_constant_markers = (
    "RATE_DIAGNOSIS",
    "RATE_FORENSICS",
    "WRONG_REASON",
    "ERROR_REASON",
    "REVIEW_REASON",
    "CONFLICT_REASON",
    "MONEY_CONTEXT_REASON",
    "SELECTED_WRONG_MONEY_CONTEXT",
    "SELECTED_SAFE_TOTAL_BUT_GOLD_DIFFERS",
    "GOLD_TOTAL_IN_CANDIDATES_NOT_SELECTED",
    "GOLD_TOTAL_NOT_IN_CANDIDATES",
)

guarded_function_markers = (
    "diagnose_rate",
    "classify_rate_error",
    "classify_rate_wrong",
    "rate_forensics_diagnosis",
    "build_residual_wrong_rate_forensics",
    "build_rate_wrong_case_summary",
    "classify_error_reason",
    "classify_residual_wrong_rate",
    "gold_consistency_reason",
    "normalize_rate_conflict_reason",
    "recommended_rate_fix_bucket",
    "normalize_rate_conflict_audit_reason",
    "recommended_rate_conflict_fix_bucket",
)


def _posix(path):
    return str(path).replace("\\", "/")


def _iter_python_paths():
    for package_root in (root / "app" / "document_ai", root / "scripts"):
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
            if any(marker in name for marker in guarded_constant_markers):
                names.append(name)
    return names


def _guarded_function_names(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        name = node.name.lower()
        if any(marker in name for marker in guarded_function_markers):
            names.append(node.name)
    return names


class RateconRateForensicsDiagnosisGuardrailTests(unittest.TestCase):
    def test_diagnosis_constants_stay_in_documented_modules(self):
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
            "New selected-rate diagnosis/reason constants must stay in "
            "documented forensics, audit, evaluator, aggregate-gate, or resolver modules.",
        )

    def test_diagnosis_functions_stay_in_documented_modules(self):
        unexpected = []
        for path in _iter_python_paths():
            names = _guarded_function_names(path)
            if not names:
                continue
            rel_path = _posix(path.relative_to(root))
            if rel_path not in approved_function_modules:
                unexpected.append((rel_path, names))

        self.assertEqual(
            [],
            unexpected,
            "New selected-rate diagnosis mapping functions must stay in "
            "documented forensics, audit, evaluator, aggregate-gate, or resolver modules.",
        )


if __name__ == "__main__":
    unittest.main()
