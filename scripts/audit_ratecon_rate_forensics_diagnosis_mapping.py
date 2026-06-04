"""Static RateCon selected-rate forensics diagnosis mapping audit.

This local-only tool uses AST/text analysis only. It does not import project
modules, execute resolver/evaluator/extraction code, process PDFs, run OCR,
call Google, or call model/cloud services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from pathlib import Path


default_output_dir = Path(".local_outputs/ratecon_rate_forensics_diagnosis_mapping_audit")

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

known_diagnosis_modules = {
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_gold_labels.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "scripts/compare_ratecon_gold_evaluations.py",
    "scripts/adjudicate_ratecon_gold_rates.py",
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py",
    "scripts/audit_ratecon_rate_score_trace_explanation.py",
    "scripts/audit_ratecon_rate_forensics_diagnosis_mapping.py",
    "tests/test_ratecon_rate_forensics_diagnosis_mapping.py",
    "tests/test_ratecon_rate_forensics_diagnosis_guardrails.py",
    "tests/test_compare_ratecon_private_selected_rate_aggregates.py",
}

owner_recommendations = {
    "app/document_ai/rate_candidate_forensics.py": (
        "canonical_forensics_diagnosis_owner",
        "low",
        "Owns selected-rate forensics categories, conflict reasons, and safe summaries.",
    ),
    "app/document_ai/rate_conflict_audit.py": (
        "audit_summary_owner",
        "low",
        "Owns local conflict audit rows and statuses, not canonical diagnosis taxonomy.",
    ),
    "app/document_ai/ratecon_gold_labels.py": (
        "evaluator_current_assignment_compatibility",
        "medium",
        "Current evaluator-side diagnosis assignment; keep pinned until a narrow move.",
    ),
    "app/document_ai/field_candidate_resolver.py": (
        "resolver_trace_owner",
        "low",
        "Owns selected-rate selection/scoring/trace, not forensics diagnosis taxonomy.",
    ),
    "app/document_ai/ratecon_rate_money_safety.py": (
        "taxonomy_input_owner",
        "low",
        "Owns money taxonomy/classifier inputs, not forensics diagnosis taxonomy.",
    ),
    "app/document_ai/rate_candidate_equivalence.py": (
        "support_policy",
        "low",
        "Supports safe candidate equivalence summaries consumed by audits.",
    ),
    "app/document_ai/ratecon_shadow_audit.py": (
        "audit_serializer",
        "low",
        "Serializes local-only audit summaries; not a diagnosis owner.",
    ),
    "app/document_ai/ratecon_shadow_root_cause_analysis.py": (
        "audit_consumer",
        "low",
        "Consumes diagnostic summaries for local-only root-cause analysis.",
    ),
    "scripts/evaluate_ratecon_against_gold.py": (
        "evaluator_reporter",
        "low",
        "Reports/evaluates diagnosis outcomes; should not invent new categories.",
    ),
    "scripts/compare_ratecon_private_selected_rate_aggregates.py": (
        "aggregate_gate_consumer",
        "low",
        "Gates aggregate selected-rate deltas; should not invent new categories.",
    ),
    "scripts/compare_ratecon_gold_evaluations.py": (
        "comparison_consumer",
        "low",
        "Compares selected-rate diagnosis deltas across existing evaluations.",
    ),
    "scripts/adjudicate_ratecon_gold_rates.py": (
        "adjudication_consumer",
        "low",
        "Consumes selected-rate diagnosis labels for local review routing.",
    ),
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py": (
        "local_audit",
        "low",
        "Static ranking ownership audit may mention diagnosis keys as evidence.",
    ),
    "scripts/audit_ratecon_rate_score_trace_explanation.py": (
        "local_audit",
        "low",
        "Static score trace audit may mention diagnosis keys as evidence.",
    ),
    "scripts/audit_ratecon_rate_forensics_diagnosis_mapping.py": (
        "local_audit",
        "low",
        "Static audit tool for forensics diagnosis ownership visibility.",
    ),
}

diagnosis_symbol_markers = (
    "DIAGNOSIS",
    "FORENSICS",
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

function_markers = (
    "diagnose",
    "forensics",
    "wrong_rate",
    "wrong_case",
    "error_reason",
    "conflict_reason",
    "gold_consistency_reason",
)

text_markers = (
    "selected_wrong_money_context",
    "selected_safe_total_but_gold_differs",
    "gold_total_in_candidates_not_selected",
    "gold_total_not_in_candidates",
    "selected_same_amount_but_normalization_failed",
    "selected_amount_correct_but_gold_uncertain",
    "selected_carrier_freight_pay_but_gold_uses_total_carrier_pay",
    "selected_total_carrier_pay_but_gold_uses_carrier_freight_pay",
    "selected_linehaul_but_gold_uses_grand_total",
    "selected_grand_total_but_gold_uses_linehaul",
    "multiple_valid_totals_ambiguous",
    "gold_total_requires_ocr",
    "diagnosis_counts",
    "wrong_reason_counts",
    "rate_wrong_case_summary",
    "residual_wrong_rate_forensics",
    "high_confidence_wrong_count",
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


def _value_contains_diagnosis(value) -> bool:
    text = json.dumps(value, sort_keys=True).lower()
    return any(marker in text for marker in text_markers)


def _imports(source: dict) -> list[dict]:
    tree = source["tree"]
    if tree is None:
        return []
    rows = []
    source_module = _module_name(source["rel_path"])
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [(alias.name, node.lineno) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports = [(node.module or "", node.lineno)]
        else:
            continue
        for imported_module, line in imports:
            rows.append(
                {
                    "importer_path": source["rel_path"],
                    "importer_module": source_module,
                    "imported_module": imported_module,
                    "line": line,
                }
            )
    return rows


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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            lower = name.lower()
            if any(marker in lower for marker in function_markers):
                rows.append(
                    {
                        "module_path": source["rel_path"],
                        "symbol_name": name,
                        "symbol_type": "class" if isinstance(node, ast.ClassDef) else "function",
                        "line": node.lineno,
                        "value": "",
                    }
                )
            continue
        else:
            continue
        value = _literal_value(value_node)
        for name in names:
            upper = name.upper()
            if not any(marker in upper for marker in diagnosis_symbol_markers) and not _value_contains_diagnosis(value):
                continue
            rows.append(
                {
                    "module_path": source["rel_path"],
                    "symbol_name": name,
                    "symbol_type": "constant",
                    "line": node.lineno,
                    "value": value,
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
        return "test_only", "low", "Test-only diagnosis evidence; not a runtime owner."
    if rel_path in known_diagnosis_modules:
        return "compatibility", "medium", "Known diagnosis-related support surface."
    if symbol_count or text_count:
        return "manual_review_required", "high", "Diagnosis evidence outside documented modules."
    return "manual_review_required", "low", "No direct diagnosis evidence."


def analyze_rate_forensics_diagnosis_mapping(repo_root: Path | str) -> dict:
    repo_root = Path(repo_root).resolve()
    sources = _discover_sources(repo_root)
    source_by_path = {source["rel_path"]: source for source in sources}
    relevant_paths = set(known_diagnosis_modules)
    for source in sources:
        text = source["text"].lower()
        if any(marker in text for marker in text_markers):
            relevant_paths.add(source["rel_path"])
    modules = []
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
        for edge in _imports(source):
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
                    "finding": "undocumented_diagnosis_surface",
                    "evidence": "Diagnosis evidence outside documented owner modules.",
                }
            )

    diagnosis_constants = [
        row
        for row in symbols
        if row["symbol_type"] == "constant"
        and (
            "DIAGNOSIS" in row["symbol_name"].upper()
            or "FORENSICS" in row["symbol_name"].upper()
            or "REASON" in row["symbol_name"].upper()
            or _value_contains_diagnosis(row.get("value"))
        )
    ]
    status_counts = {}
    for module in modules:
        status_counts[module["owner_recommendation"]] = (
            status_counts.get(module["owner_recommendation"], 0) + 1
        )
    return {
        "schema_version": "ratecon_rate_forensics_diagnosis_mapping_audit_v1",
        "module_count": len(modules),
        "symbol_count": len(symbols),
        "diagnosis_constant_count": len(diagnosis_constants),
        "text_finding_count": len(text_rows),
        "risk_finding_count": len(risks),
        "status_recommendation_counts": status_counts,
        "modules": modules,
        "symbols": symbols,
        "diagnosis_constants": diagnosis_constants,
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
        "# RateCon Rate Forensics Diagnosis Mapping Audit",
        "",
        "This local-only audit uses static AST/text analysis only.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- diagnosis_constant_count: {summary['diagnosis_constant_count']}",
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
    _write_json(output_dir / "rate_forensics_diagnosis_mapping_summary.json", summary)
    _write_report(output_dir / "rate_forensics_diagnosis_mapping_report.md", summary)
    _write_csv(
        output_dir / "rate_forensics_diagnosis_modules.csv",
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
        output_dir / "rate_forensics_diagnosis_symbols.csv",
        summary["symbols"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_forensics_diagnosis_constants.csv",
        summary["diagnosis_constants"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_forensics_diagnosis_recommendations.csv",
        summary["modules"],
        ["module_path", "owner_recommendation", "risk", "evidence"],
    )
    _write_csv(
        output_dir / "rate_forensics_diagnosis_risk_findings.csv",
        summary["risk_findings"],
        ["module_path", "risk", "finding", "evidence"],
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Audit RateCon forensics diagnosis ownership.")
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
        summary = analyze_rate_forensics_diagnosis_mapping(repo_root)
        write_audit_outputs(output_dir, summary)
    except (OSError, audit_error, json.JSONDecodeError) as exc:
        print(f"rate_forensics_diagnosis_mapping_audit_error: {exc}", flush=True)
        return 1
    print("RateCon rate forensics diagnosis mapping audit")
    print(f"module_count: {summary['module_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
    print(f"diagnosis_constant_count: {summary['diagnosis_constant_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"output_dir: {output_dir}")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
