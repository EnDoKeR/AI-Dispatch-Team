"""Static RateCon load identifier ownership audit.

This local-only tool uses AST/text analysis only. It does not import project
modules, execute resolver/evaluator/extraction code, process PDFs, run OCR,
call Google, or call model/cloud services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_load_identifier_ownership_audit")

EXCLUDED_DIR_NAMES = {
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

IGNORED_RELATIVE_PREFIXES = (
    ".local_outputs",
    ".local_private",
    "data/private_ratecons",
)

LOAD_IDENTIFIER_TEXT_MARKERS = (
    "load_number",
    "load identifier",
    "load id",
    "load #",
    "order number",
    "order #",
    "po number",
    "pro number",
    "shipment id",
    "freight bill",
    "reference number",
    "broker reference",
    "customer reference",
    "table_neighbor",
    "nearby_row",
    "selected_table_neighbor_wrong_cell",
    "selected_nearby_row_wrong_pair",
    "gold_not_in_candidates",
    "gold_in_candidates_not_selected",
)

SYMBOL_MARKERS = (
    "LOAD_IDENTIFIER",
    "LOAD_NUMBER",
    "LOAD_ID",
    "ORDER_NUMBER",
    "PO_NUMBER",
    "PRO_NUMBER",
    "REFERENCE_NUMBER",
    "TABLE_NEIGHBOR",
    "NEARBY_ROW",
)

FUNCTION_MARKERS = (
    "load_identifier",
    "load_number",
    "load_identity",
    "table_neighbor",
    "nearby_row",
)

OWNER_RECOMMENDATIONS = {
    "app/document_ai/load_identifier_candidates.py": (
        "canonical_load_identifier_candidate_owner",
        "low",
        "Intended canonical owner for load identifier candidate taxonomy/policy.",
    ),
    "app/document_ai/field_candidate_generators.py": (
        "generator_consumer",
        "medium",
        "Generates candidates; should consume canonical load identifier policy.",
    ),
    "app/document_ai/field_candidate_resolver.py": (
        "resolver_consumer",
        "low",
        "Owns selected value choice and resolver reasons, not candidate taxonomy.",
    ),
    "app/document_ai/load_identity_forensics.py": (
        "forensics_consumer",
        "low",
        "Reports safe load identity diagnostics, not canonical candidate taxonomy.",
    ),
    "app/document_ai/load_identifier_coverage_audit.py": (
        "audit_consumer",
        "low",
        "Local-only load identifier coverage audit labels and statuses.",
    ),
    "app/document_ai/load_identifier_source_line_audit.py": (
        "audit_consumer",
        "low",
        "Local-only source-line diagnostic labels and statuses.",
    ),
    "scripts/evaluate_ratecon_against_gold.py": (
        "evaluator_consumer",
        "medium",
        "Reports load-number outcomes; should not own extraction/ranking rules.",
    ),
    "scripts/run_private_ratecon_measurement.py": (
        "evaluator_consumer",
        "medium",
        "Runs local private measurement only; should consume load identifier outputs.",
    ),
    "scripts/compare_ratecon_private_selected_load_aggregates.py": (
        "aggregate_gate",
        "low",
        "Local-only load-number aggregate comparison gate.",
    ),
    "scripts/audit_ratecon_load_identifier_ownership.py": (
        "local_audit",
        "low",
        "Static ownership audit for load identifier cleanup.",
    ),
}

FORBIDDEN_IMPORT_PREFIXES = (
    "app.integrations.google",
    "google.oauth",
    "googleapiclient",
    "gspread",
    "openai",
    "anthropic",
    "google.generativeai",
)


class AuditError(ValueError):
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
        raise AuditError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise AuditError("Output directory must be under .local_outputs.")
    return output_dir


def _should_skip_path(repo_root: Path, path: Path) -> bool:
    rel = _posix(path.relative_to(repo_root))
    rel_parts = Path(rel).parts
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
        return True
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in IGNORED_RELATIVE_PREFIXES)


def _discover_sources(repo_root: Path) -> list[dict[str, Any]]:
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


def _literal_value(node: ast.AST | None) -> Any:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [_literal_value(item) for item in node.elts]
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Dict):
        return {
            _literal_value(key): _literal_value(value)
            for key, value in zip(node.keys, node.values)
        }
    return ""


def _imports(tree: ast.AST | None) -> list[str]:
    if tree is None:
        return []
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
    return sorted(set(imports))


def _symbols(source: dict[str, Any]) -> list[dict[str, Any]]:
    tree = source["tree"]
    if tree is None:
        return []
    rows = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            lowered = name.lower()
            if any(marker in lowered for marker in FUNCTION_MARKERS):
                rows.append(
                    {
                        "module_path": source["rel_path"],
                        "symbol": name,
                        "symbol_type": type(node).__name__,
                        "line": node.lineno,
                        "value": "",
                    }
                )
        elif isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            for name in targets:
                upper = name.upper()
                lowered = name.lower()
                if any(marker in upper for marker in SYMBOL_MARKERS) or any(
                    marker in lowered for marker in FUNCTION_MARKERS
                ):
                    rows.append(
                        {
                            "module_path": source["rel_path"],
                            "symbol": name,
                            "symbol_type": "Assign",
                            "line": node.lineno,
                            "value": _literal_value(node.value),
                        }
                    )
    return rows


def _module_recommendation(rel_path: str) -> tuple[str, str, str]:
    if rel_path in OWNER_RECOMMENDATIONS:
        return OWNER_RECOMMENDATIONS[rel_path]
    if rel_path.startswith("tests/"):
        return ("test_coverage", "low", "Test-only fixture/assertion surface.")
    if rel_path.startswith("docs/"):
        return ("documentation", "low", "Documentation only.")
    if "load" in rel_path.lower() and "identifier" in rel_path.lower():
        return ("manual_review_required", "medium", "Load identifier ownership should be classified explicitly.")
    return ("compatibility", "medium", "Current compatibility/reference surface.")


def _analyze(repo_root: Path) -> dict[str, Any]:
    sources = _discover_sources(repo_root)
    module_rows = []
    import_rows = []
    symbol_rows = []
    risk_rows = []
    value_to_symbols: dict[str, list[str]] = defaultdict(list)

    for source in sources:
        text_lower = source["text"].lower()
        marker_hits = [marker for marker in LOAD_IDENTIFIER_TEXT_MARKERS if marker in text_lower]
        symbols = _symbols(source)
        if not marker_hits and not symbols:
            continue

        recommendation, risk, evidence = _module_recommendation(source["rel_path"])
        imports = _imports(source["tree"])
        forbidden = [
            imported
            for imported in imports
            if any(imported == prefix or imported.startswith(prefix + ".") for prefix in FORBIDDEN_IMPORT_PREFIXES)
        ]
        if forbidden:
            risk_rows.append(
                {
                    "module_path": source["rel_path"],
                    "risk": "high",
                    "finding": "forbidden_import",
                    "evidence": ";".join(forbidden),
                }
            )

        module_rows.append(
            {
                "module_path": source["rel_path"],
                "owner_recommendation": recommendation,
                "risk": "high" if forbidden else risk,
                "marker_hits": ";".join(marker_hits[:20]),
                "evidence": evidence,
            }
        )
        for imported in imports:
            if any(token in imported for token in ("load", "ratecon", "field_candidate")):
                import_rows.append(
                    {
                        "module_path": source["rel_path"],
                        "imports": imported,
                    }
                )
        for symbol in symbols:
            symbol_rows.append(symbol)
            value = symbol.get("value")
            if isinstance(value, str) and value:
                value_to_symbols[value].append(f"{symbol['module_path']}::{symbol['symbol']}")

    duplicate_rows = []
    for value, owners in sorted(value_to_symbols.items()):
        if len(set(owners)) > 1:
            duplicate_rows.append(
                {
                    "constant_value": value,
                    "owner_count": len(set(owners)),
                    "owners": ";".join(sorted(set(owners))),
                }
            )

    recommendation_counts = Counter(row["owner_recommendation"] for row in module_rows)
    summary = {
        "module_count": len(module_rows),
        "import_edge_count": len(import_rows),
        "symbol_count": len(symbol_rows),
        "duplicate_constant_count": len(duplicate_rows),
        "risk_finding_count": len(risk_rows),
        "status_recommendation_counts": dict(sorted(recommendation_counts.items())),
        "static_analysis_only": True,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    return {
        "summary": summary,
        "modules": module_rows,
        "imports": import_rows,
        "symbols": symbol_rows,
        "duplicates": duplicate_rows,
        "recommendations": module_rows,
        "risks": risk_rows,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_report(path: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    lines = [
        "# RateCon Load Identifier Ownership Audit",
        "",
        "Static AST/text analysis only. No resolver, extraction, PDF, OCR, Google, model, or cloud execution.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- import_edge_count: {summary['import_edge_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- duplicate_constant_count: {summary['duplicate_constant_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        "",
        "## Recommendation Counts",
        "",
    ]
    for key, value in summary["status_recommendation_counts"].items():
        lines.append(f"- {key}: {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_audit(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    result = _analyze(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "load_identifier_ownership_summary.json").write_text(
        json.dumps(result["summary"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_report(output_dir / "load_identifier_ownership_report.md", result)
    _write_csv(
        output_dir / "load_identifier_modules.csv",
        result["modules"],
        ["module_path", "owner_recommendation", "risk", "marker_hits", "evidence"],
    )
    _write_csv(
        output_dir / "load_identifier_symbols.csv",
        result["symbols"],
        ["module_path", "symbol", "symbol_type", "line", "value"],
    )
    _write_csv(
        output_dir / "load_identifier_duplicate_constants.csv",
        result["duplicates"],
        ["constant_value", "owner_count", "owners"],
    )
    _write_csv(
        output_dir / "load_identifier_recommendations.csv",
        result["recommendations"],
        ["module_path", "owner_recommendation", "risk", "marker_hits", "evidence"],
    )
    _write_csv(
        output_dir / "load_identifier_risk_findings.csv",
        result["risks"],
        ["module_path", "risk", "finding", "evidence"],
    )
    return result["summary"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Static RateCon load identifier ownership audit.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        raise SystemExit("--confirm-local-audit-run is required for this local-only audit.")
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        output_dir = _resolve_output_dir(repo_root, args.output_dir)
        summary = run_audit(repo_root, output_dir)
    except AuditError as exc:
        raise SystemExit(str(exc)) from exc
    print("RateCon load identifier ownership audit")
    for key in (
        "module_count",
        "import_edge_count",
        "symbol_count",
        "duplicate_constant_count",
        "risk_finding_count",
    ):
        print(f"{key}: {summary[key]}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
