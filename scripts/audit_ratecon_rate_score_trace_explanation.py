"""Static RateCon selected-rate score trace/explanation ownership audit.

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


default_output_dir = Path(".local_outputs/ratecon_rate_score_trace_explanation_audit")

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

known_trace_modules = {
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/ratecon_shadow_audit.py",
    "app/document_ai/ratecon_shadow_root_cause_analysis.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/compare_ratecon_private_selected_rate_aggregates.py",
    "scripts/compare_ratecon_selected_rate_regression_snapshots.py",
    "scripts/run_ratecon_selected_rate_regression_snapshot.py",
    "scripts/adjudicate_ratecon_gold_rates.py",
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py",
    "scripts/compare_ratecon_gold_evaluations.py",
    "scripts/create_ratecon_gold_label_packets.py",
    "scripts/audit_ratecon_rate_score_trace_explanation.py",
    "app/document_ai/ratecon_document_pipeline.py",
    "app/document_ai/ratecon_gold_labels.py",
    "tests/helpers/ratecon_selected_rate_regression.py",
    "tests/test_ratecon_selected_rate_regression_harness.py",
    "tests/test_ratecon_rate_ranking_penalty_pinning.py",
}

owner_recommendations = {
    "app/document_ai/field_candidate_resolver.py": (
        "resolver_score_trace_owner",
        "medium",
        "Current selected-rate scoring and trace construction owner.",
    ),
    "app/document_ai/ratecon_rate_money_safety.py": (
        "taxonomy_input_owner",
        "low",
        "Owns money-context taxonomy/classifier inputs, not score trace semantics.",
    ),
    "app/document_ai/rate_candidate_forensics.py": (
        "forensics_consumer",
        "low",
        "Summarizes selected-rate diagnoses; should not own score traces.",
    ),
    "app/document_ai/rate_conflict_audit.py": (
        "audit_consumer",
        "low",
        "Summarizes conflict/audit labels; should not own score traces.",
    ),
    "app/document_ai/ratecon_shadow_audit.py": (
        "audit_serializer",
        "low",
        "Serializes resolver trace summaries in local-only audit output.",
    ),
    "app/document_ai/ratecon_shadow_root_cause_analysis.py": (
        "audit_consumer",
        "low",
        "Consumes resolver trace summaries for local-only root-cause analysis.",
    ),
    "app/document_ai/ratecon_gold_labels.py": (
        "evaluator_consumer",
        "low",
        "May count selected-rate trace outcomes for evaluation summaries.",
    ),
    "app/document_ai/ratecon_document_pipeline.py": (
        "pipeline_consumer",
        "low",
        "Passes resolver traces through document AI pipeline output.",
    ),
    "scripts/evaluate_ratecon_against_gold.py": (
        "evaluator_consumer",
        "low",
        "Evaluation writer may serialize trace-derived statuses.",
    ),
    "scripts/adjudicate_ratecon_gold_rates.py": (
        "evaluator_consumer",
        "low",
        "Local adjudication helper may report selected-rate diagnoses.",
    ),
    "scripts/compare_ratecon_gold_evaluations.py": (
        "evaluator_consumer",
        "low",
        "Local comparison helper reports selected-rate aggregate deltas.",
    ),
    "scripts/create_ratecon_gold_label_packets.py": (
        "evaluator_consumer",
        "low",
        "Local packet helper may include resolver summaries for review.",
    ),
    "scripts/compare_ratecon_private_selected_rate_aggregates.py": (
        "aggregate_gate_consumer",
        "low",
        "Compares selected-rate aggregates; does not own resolver traces.",
    ),
    "scripts/audit_ratecon_rate_ranking_penalty_ownership.py": (
        "local_audit",
        "low",
        "Static ranking-penalty ownership audit; not a trace owner.",
    ),
    "scripts/compare_ratecon_selected_rate_regression_snapshots.py": (
        "snapshot_gate_consumer",
        "low",
        "Compares sanitized selected-rate snapshot outputs.",
    ),
    "scripts/run_ratecon_selected_rate_regression_snapshot.py": (
        "snapshot_writer",
        "low",
        "Runs sanitized selected-rate fixture snapshots only.",
    ),
    "scripts/audit_ratecon_rate_score_trace_explanation.py": (
        "local_audit",
        "low",
        "Static audit tool for score trace ownership visibility.",
    ),
}

trace_symbol_markers = (
    "TRACE",
    "EXPLANATION",
    "REASON",
    "NOT_SELECTED",
    "SELECTED_REASON",
    "BOOST_REASON",
    "PENALTY_REASON",
    "DEMOTION_REASON",
    "ABSTAIN_REASON",
    "RESOLVER_SCORE",
    "RANKING_ADJUSTMENT",
    "DECISION_STATUS",
    "REJECT",
)

function_markers = (
    "trace",
    "explain",
    "serialize",
    "reason",
    "score",
    "not_selected",
)

text_markers = (
    "score trace",
    "scoring trace",
    "score explanation",
    "score reasons",
    "boost reasons",
    "penalty reasons",
    "demotion reason",
    "abstention reason",
    "not selected reason",
    "selected reason",
    "ranking_adjustment_total",
    "ranking_adjustments",
    "resolver_score",
    "resolver_not_selected_reason",
    "resolver_decision_traces",
    "resolver_selection_summary",
    "decision_status",
    "candidate_eligibility",
    "not_selected_reason_counts",
    "top_rejected_or_not_selected",
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
        for name in names:
            upper = name.upper()
            if not any(marker in upper for marker in trace_symbol_markers):
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
        return "test_only", "low", "Test-only trace evidence; not a runtime owner."
    if rel_path in known_trace_modules:
        return "compatibility", "medium", "Known trace-related support surface."
    if symbol_count or text_count:
        return "manual_review_required", "high", "Trace/explanation evidence outside documented modules."
    return "manual_review_required", "low", "No direct trace/explanation evidence."


def analyze_rate_score_trace_explanation(repo_root: Path | str) -> dict:
    repo_root = Path(repo_root).resolve()
    sources = _discover_sources(repo_root)
    source_by_path = {source["rel_path"]: source for source in sources}
    relevant_paths = set(known_trace_modules)
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
                    "finding": "undocumented_score_trace_surface",
                    "evidence": "Trace/explanation evidence outside documented owner modules.",
                }
            )

    reason_constants = [
        row
        for row in symbols
        if row["symbol_type"] == "constant"
        and (
            "REASON" in row["symbol_name"].upper()
            or "NOT_SELECTED" in row["symbol_name"].upper()
            or row["symbol_name"].upper().startswith("REJECT_")
        )
    ]
    status_counts = {}
    for module in modules:
        status_counts[module["owner_recommendation"]] = (
            status_counts.get(module["owner_recommendation"], 0) + 1
        )
    return {
        "schema_version": "ratecon_rate_score_trace_explanation_audit_v1",
        "module_count": len(modules),
        "symbol_count": len(symbols),
        "reason_constant_count": len(reason_constants),
        "text_finding_count": len(text_rows),
        "risk_finding_count": len(risks),
        "status_recommendation_counts": status_counts,
        "modules": modules,
        "symbols": symbols,
        "reason_constants": reason_constants,
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
        "# RateCon Rate Score Trace/Explanation Audit",
        "",
        "This local-only audit uses static AST/text analysis only.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- reason_constant_count: {summary['reason_constant_count']}",
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
    _write_json(output_dir / "rate_score_trace_explanation_summary.json", summary)
    _write_report(output_dir / "rate_score_trace_explanation_report.md", summary)
    _write_csv(
        output_dir / "rate_score_trace_modules.csv",
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
        output_dir / "rate_score_trace_symbols.csv",
        summary["symbols"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_score_trace_reason_constants.csv",
        summary["reason_constants"],
        ["module_path", "symbol_name", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "rate_score_trace_recommendations.csv",
        summary["modules"],
        ["module_path", "owner_recommendation", "risk", "evidence"],
    )
    _write_csv(
        output_dir / "rate_score_trace_risk_findings.csv",
        summary["risk_findings"],
        ["module_path", "risk", "finding", "evidence"],
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Audit RateCon score trace/explanation ownership.")
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
        summary = analyze_rate_score_trace_explanation(repo_root)
        write_audit_outputs(output_dir, summary)
    except (OSError, audit_error, json.JSONDecodeError) as exc:
        print(f"rate_score_trace_explanation_audit_error: {exc}", flush=True)
        return 1
    print("RateCon rate score trace/explanation audit")
    print(f"module_count: {summary['module_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
    print(f"reason_constant_count: {summary['reason_constant_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"output_dir: {output_dir}")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
