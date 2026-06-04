import ast
import unittest
from pathlib import Path


root = Path(__file__).resolve().parents[1]

approved_constant_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
}

approved_function_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
}

guarded_constant_markers = (
    "RESOLVER_DECISION_TRACE",
    "RESOLVER_SELECTION_SUMMARY",
    "RATE_SCORE_TRACE",
    "SCORE_TRACE",
    "RANKING_ADJUSTMENT",
    "RATE_NOT_SELECTED",
    "NOT_SELECTED_REASON",
    "SELECTED_RATE_REASON",
    "SELECTED_REASON",
    "BOOST_REASON",
    "PENALTY_REASON",
    "DEMOTION_REASON",
    "ABSTAIN_REASON",
)

guarded_function_markers = (
    "build_resolver_decision_trace",
    "build_resolver_selection_summary",
    "rate_score_trace",
    "score_trace",
    "serialize_rate_trace",
    "serialize_score_trace",
    "explain_rate_score",
    "explain_selected_rate",
    "selected_rate_reason",
    "rate_not_selected_reason",
    "not_selected_reason",
)


def _posix(path):
    return str(path).replace("\\", "/")


def _iter_python_paths():
    for package_root in (root / "app" / "document_ai",):
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
        if "ocr_stop" in name:
            continue
        if any(marker in name for marker in guarded_function_markers):
            names.append(node.name)
    return names


class RateconRateScoreTraceGuardrailTests(unittest.TestCase):
    def test_score_trace_constants_stay_in_documented_modules(self):
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
            "New selected-rate score trace/reason constants must stay in "
            "documented resolver, forensics, audit, or shadow-audit modules.",
        )

    def test_score_trace_functions_stay_in_documented_modules(self):
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
            "New selected-rate score trace/explanation functions must stay in "
            "documented resolver, forensics, audit, or shadow-audit modules.",
        )


if __name__ == "__main__":
    unittest.main()
