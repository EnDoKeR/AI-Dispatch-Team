"""Static RateCon rate-ranking penalty ownership audit.

This local-only tool uses AST/text analysis only. It does not import project
modules, execute resolver/extraction code, process PDFs, run OCR, call Google,
or call model/cloud services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path


default_output_dir = Path(".local_outputs/ratecon_rate_ranking_penalty_ownership_audit")

excluded_dir_names = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "env",
    "venv",
}

ignored_relative_prefixes = (
    ".local_outputs",
    ".local_private",
    "data/private_ratecons",
)

known_ranking_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/ratecon_candidate_generators.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/adjudicate_ratecon_gold_rates.py",
    "scripts/compare_ratecon_gold_evaluations.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py",
    "app/document_ai/ratecon_gold_labels.py",
    "tests/helpers/ratecon_selected_rate_regression.py",
    "tests/test_ratecon_selected_rate_regression_harness.py",
}

owner_recommendations = {
    "app/document_ai/field_candidate_resolver.py": (
        "resolver_ranking_owner",
        "medium",
        "Current selected-rate scoring, ranking, profile, and not-selected trace owner.",
    ),
    "app/document_ai/ratecon_rate_money_safety.py": (
        "rate_money_safety_consumer",
        "medium",
        "Owns money-context taxonomy and abstention metadata inputs, not resolver ranking.",
    ),
    "app/document_ai/rate_candidate_forensics.py": (
        "forensics_consumer",
        "low",
        "Reports selected-rate diagnoses; should not own ranking penalties.",
    ),
    "app/document_ai/rate_conflict_audit.py": (
        "audit_consumer",
        "low",
        "Reports conflict/audit labels; should not own ranking penalties.",
    ),
    "app/document_ai/ratecon_gold_labels.py": (
        "evaluator_consumer",
        "low",
        "Evaluation summaries may report selected-rate status; not a ranking owner.",
    ),
    "scripts/evaluate_ratecon_against_gold.py": (
        "evaluator_consumer",
        "low",
        "Evaluation writer may serialize selected-rate statuses; not a ranking owner.",
    ),
    "scripts/adjudicate_ratecon_gold_rates.py": (
        "evaluator_consumer",
        "low",
        "Local adjudication helper may report selected-rate statuses; not a ranking owner.",
    ),
    "scripts/compare_ratecon_gold_evaluations.py": (
        "evaluator_consumer",
        "low",
        "Local comparison helper reports aggregate deltas; not a ranking owner.",
    ),
    "scripts/compare_ratecon_private_selected_rate_aggregates.py": (
        "evaluator_consumer",
        "low",
        "Local aggregate gate reports selected-rate deltas; not a ranking owner.",
    ),
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py": (
        "local_audit",
        "low",
        "Static audit tool for ownership visibility; not a ranking owner.",
    ),
}

penalty_symbol_markers = (
    "RANKING",
    "PENALTY",
    "BOOST",
    "DEMOTION",
    "ABSTAIN",
    "NOT_SELECTED",
    "SELECTED_WRONG",
    "SCORE",
)

function_markers = (
    "rank",
    "score",
    "penal",
    "demot",
    "abstain",
    "not_selected",
)

text_markers = (
    "money_context_penalty",
    "line_item_only_penalty",
    "deduction_fee_penalty_context",
    "payment_terms_amount_penalty",
    "per_unit_rate_penalty",
    "accessorial_only_penalty",
    "rate_money_abstained",
    "rate_money_weak_only",
    "instructions_or_footer_money_penalty",
    "selected_wrong_money_context",
    "gold_total_in_candidates_not_selected",
    "selected_safe_total_but_gold_differs",
)

forbidden_import_prefixes = (
    "app.market_intelligence.decision_engine",
    "app.market_intelligence.dispatch_case",
    "app.integrations.google",
    "google.oauth",
    "googleapiclient",
    "gspread",
    "openai",
    "anthropic",
    "google.generativeai",
)


class audit_error(ValueError):
    """Raised for safe user-facing audit failures."""


def _posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _is_within(path: Path, parent: Path) -> bool:
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def _resolve_repo_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.exists() or not root.is_dir():
        raise audit_error(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else default_output_dir
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise audit_error("Output directory must be under .local_outputs.")
    return output_dir


def _should_skip_path(repo_root: Path, path: Path) -> bool:
    rel = _posix(path.relative_to(repo_root))
    rel_parts = Path(rel).parts
    if any(part in excluded_dir_names for part in rel_parts):
        return True
    return any(
        rel == prefix or rel.startswith(prefix + "/")
        for prefix in ignored_relative_prefixes
    )


def _discover_sources(repo_root: Path) -> list[dict]:
    sources = []
    for path in sorted(repo_root.rglob("*.py")):
        if _should_skip_path(repo_root, path):
            continue
        rel_path = _posix(path.relative_to(repo_root))
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            tree = None
        sources.append({"rel_path": rel_path, "path": path, "text": text, "tree": tree})
    return sources


def _module_name(rel_path: str) -> str:
    parts = list(Path(rel_path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _literal_value(node: ast.AST | None):
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return [_literal_value(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            str(_literal_value(key)): _literal_value(value)
            for key, value in zip(node.keys, node.values)
        }
    return ""


def _import_edges(source: dict, known_modules: set[str]) -> list[dict]:
    tree = source["tree"]
    if tree is None:
        return []
    edges = []
    source_module = _module_name(source["rel_path"])
    known_by_module = {_module_name(path): path for path in known_modules}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [(node.module or "", node.lineno)]
        else:
            continue
        for imported_module, line in imports:
            matched = ""
            for module_name, rel_path in known_by_module.items():
                if imported_module == module_name or imported_module.startswith(module_name + "."):
                    matched = rel_path
                    break
            edges.append(
                {
                    "importer_path": source["rel_path"],
                    "importer_module": source_module,
                    "imported_module": imported_module,
                    "imported_path": matched,
                    "is_known_rate_ranking_module": bool(matched),
                    "line": line,
                }
            )
    return edges


def _symbols(source: dict) -> list[dict]:
    tree = source["tree"]
    if tree is None:
        return []
    rows = []
    for node in ast.walk(tree):
        names: list[str] = []
        value_node = None
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
            value_node = node.value
        elif isinstance(node, ast.FunctionDef):
            name = node.name
            lower = name.lower()
            if any(marker in lower for marker in function_markers):
                rows.append(
                    {
                        "module_path": source["rel_path"],
                        "symbol_name": name,
                        "symbol_type": "function",
                        "line": node.lineno,
                        "value": "",
                    }
                )
            continue
        else:
            continue
        for name in names:
            upper = name.upper()
            if not any(marker in upper for marker in penalty_symbol_markers):
                continue
            rows.append(
                {
                    "module_path": source["rel_path"],
                    "symbol_name": name,
                    "symbol_type": "constant",
                    "line": node.lineno,
                    "value": _literal_value(value_node),
                }
            )
    return rows


def _text_findings(source: dict) -> list[dict]:
    findings = []
    lower_lines = source["text"].lower().splitlines()
    for index, line in enumerate(lower_lines, start=1):
        for marker in text_markers:
            if marker in line:
                findings.append(
                    {
                        "module_path": source["rel_path"],
                        "marker": marker,
                        "line": index,
                        "evidence": line.strip()[:220],
                    }
                )
    return findings


def _status_for_module(rel_path: str, symbol_count: int, text_count: int) -> tuple[str, str, str]:
    if rel_path in owner_recommendations:
        recommendation, risk, evidence = owner_recommendations[rel_path]
        return recommendation, risk, evidence
    if rel_path.startswith("tests/"):
        return "test_only", "low", "Test-only ranking evidence; not a runtime owner."
    if rel_path in known_ranking_modules:
        return "compatibility", "medium", "Known consumer/support surface with ranking-related evidence."
    if symbol_count or text_count:
        return "manual_review_required", "high", "Ranking/penalty evidence outside documented modules."
    return "manual_review_required", "low", "No direct ranking/penalty evidence."


def analyze_rate_ranking_penalty_ownership(repo_root: Path | str) -> dict:
    repo_root = Path(repo_root).resolve()
    sources = _discover_sources(repo_root)
    source_by_path = {source["rel_path"]: source for source in sources}
    relevant_paths = set(known_ranking_modules)
    for source in sources:
        text = source["text"].lower()
        if any(marker in text for marker in text_markers):
            relevant_paths.add(source["rel_path"])
    modules = []
    import_edges = []
    symbols = []
    text_rows = []
    risks = []
    for rel_path in sorted(relevant_paths):
        source = source_by_path.get(rel_path)
        if not source:
            modules.append(
                {
                    "module_path": rel_path,
                    "exists": False,
                    "owner_recommendation": "manual_review_required",
                    "risk": "high",
                    "evidence": "Expected module path does not exist.",
                }
            )
            risks.append(
                {
                    "module_path": rel_path,
                    "risk": "high",
                    "finding": "expected_module_missing",
                    "evidence": "Expected module path does not exist.",
                }
            )
            continue
        module_symbols = _symbols(source)
        module_text = _text_findings(source)
        recommendation, risk, evidence = _status_for_module(
            rel_path,
            len(module_symbols),
            len(module_text),
        )
        modules.append(
            {
                "module_path": rel_path,
                "exists": True,
                "owner_recommendation": recommendation,
                "risk": risk,
                "symbol_count": len(module_symbols),
                "text_finding_count": len(module_text),
                "evidence": evidence,
            }
        )
        symbols.extend(module_symbols)
        text_rows.extend(module_text)
        import_edges.extend(_import_edges(source, known_ranking_modules))
        for edge in import_edges:
            imported = edge["imported_module"]
            if any(imported.startswith(prefix) for prefix in forbidden_import_prefixes):
                risks.append(
                    {
                        "module_path": edge["importer_path"],
                        "risk": "high",
                        "finding": "forbidden_runtime_import",
                        "evidence": imported,
                    }
                )
        if recommendation == "manual_review_required" and (module_symbols or module_text):
            risks.append(
                {
                    "module_path": rel_path,
                    "risk": "high",
                    "finding": "undocumented_ranking_penalty_surface",
                    "evidence": "Ranking/penalty evidence outside documented owner modules.",
                }
            )

    penalty_constants = [row for row in symbols if row["symbol_type"] == "constant"]
    status_counts = {}
    for module in modules:
        status_counts[module["owner_recommendation"]] = (
            status_counts.get(module["owner_recommendation"], 0) + 1
        )
    return {
        "schema_version": "ratecon_rate_ranking_penalty_ownership_audit_v1",
        "module_count": len(modules),
        "import_edge_count": len(import_edges),
        "symbol_count": len(symbols),
        "penalty_constant_count": len(penalty_constants),
        "risk_finding_count": len(risks),
        "status_recommendation_counts": status_counts,
        "modules": modules,
        "import_edges": import_edges,
        "symbols": symbols,
        "penalty_constants": penalty_constants,
        "text_findings": text_rows,
        "risk_findings": risks,
    }


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_report(path: Path, summary: dict) -> None:
    lines = [
        "# RateCon Rate-Ranking Penalty Ownership Audit",
        "",
        "This local-only audit uses static AST/text analysis only.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- import_edge_count: {summary['import_edge_count']}",
        f"- penalty_constant_count: {summary['penalty_constant_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        "",
        "## Status Recommendations",
        "",
    ]
    for status, count in sorted(summary["status_recommendation_counts"].items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Modules", ""])
    for module in summary["modules"]:
        lines.append(
            f"- {module['module_path']}: {module['owner_recommendation']} "
            f"({module['risk']})"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_outputs(output_dir: Path, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "rate_ranking_penalty_ownership_summary.json", summary)
    _write_report(output_dir / "rate_ranking_penalty_ownership_report.md", summary)
    _write_csv(
        output_dir / "rate_ranking_modules.csv",
        summary["modules"],
        [
            "module_path",
            "exists",
            "owner_recommendation",
            "risk",
            "symbol_count",
            "text_finding_count",
            "evidence",
        ],
    )
    _write_csv(
        output_dir / "rate_ranking_import_edges.csv",
        summary["import_edges"],
        [
            "importer_path",
            "importer_module",
            "imported_module",
            "imported_path",
            "is_known_rate_ranking_module",
            "line",
        ],
    )
    _write_csv(
        output_dir / "rate_ranking_symbols.csv",
        summary["symbols"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_ranking_penalty_constants.csv",
        summary["penalty_constants"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_ranking_status_recommendations.csv",
        summary["modules"],
        ["module_path", "owner_recommendation", "risk", "evidence"],
    )
    _write_csv(
        output_dir / "rate_ranking_risk_findings.csv",
        summary["risk_findings"],
        ["module_path", "risk", "finding", "evidence"],
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Audit RateCon rate-ranking penalty ownership.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(default_output_dir))
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        print("--confirm-local-audit-run is required for this local-only audit.", flush=True)
        return 2
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        output_dir = _resolve_output_dir(repo_root, args.output_dir)
        summary = analyze_rate_ranking_penalty_ownership(repo_root)
        write_audit_outputs(output_dir, summary)
    except (OSError, audit_error, json.JSONDecodeError) as exc:
        print(f"rate_ranking_penalty_ownership_audit_error: {exc}", flush=True)
        return 1
    print("RateCon rate-ranking penalty ownership audit")
    print(f"module_count: {summary['module_count']}")
    print(f"import_edge_count: {summary['import_edge_count']}")
    print(f"penalty_constant_count: {summary['penalty_constant_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"output_dir: {output_dir}")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
