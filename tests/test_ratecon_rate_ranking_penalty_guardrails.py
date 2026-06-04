import ast
import unittest
from pathlib import Path


root = Path(__file__).resolve().parents[1]

approved_constant_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/ratecon_stop_component_policy.py",
}

approved_function_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
}

guarded_constant_markers = (
    "RATE_RANKING_PROFILE",
    "RATE_MONEY_RANKING",
    "RATE_MONEY_PENALTY",
    "RATE_MONEY_BOOST",
    "RATE_MONEY_DEMOTION",
    "RATE_SELECTION_ABSTAIN",
    "RATE_SELECTION_WEAK_ONLY",
    "TOTAL_CARRIER_RATE_PENALTY",
    "TOTAL_CARRIER_RATE_BOOST",
    "TOTAL_CARRIER_RATE_DEMOTION",
    "TOTAL_CARRIER_RATE_ABSTAIN",
    "SELECTED_WRONG_MONEY_CONTEXT",
)

guarded_function_markers = (
    "rank_rate",
    "rank_total_carrier_rate",
    "score_rate",
    "score_total_carrier_rate",
    "penalize_rate",
    "penalize_total_carrier_rate",
    "demote_rate",
    "demote_total_carrier_rate",
    "abstain_rate",
    "abstain_total_carrier_rate",
    "rate_not_selected",
    "selected_rate_not_selected",
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
        if any(marker in name for marker in guarded_function_markers):
            names.append(node.name)
    return names


class RateconRateRankingPenaltyGuardrailTests(unittest.TestCase):
    def test_rate_ranking_penalty_constants_stay_in_documented_modules(self):
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
            "New rate-ranking penalty/boost/abstain constants must stay in "
            "documented owner, taxonomy, forensics, audit, or compatibility modules.",
        )

    def test_rate_ranking_penalty_functions_stay_in_documented_modules(self):
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
            "New rate-ranking score/penalty/demotion/abstention functions must stay "
            "in documented owner or reporting modules.",
        )


if __name__ == "__main__":
    unittest.main()
