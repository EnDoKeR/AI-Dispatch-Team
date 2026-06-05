"""Static RateCon load candidate adapter provenance audit.

This local-only audit uses AST/text analysis only. It does not import project
modules, execute resolver/evaluator/extraction code, process PDFs, run OCR,
call Google, or call model/cloud services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_load_candidate_adapter_provenance_audit")

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

TEXT_MARKERS = (
    "adapt_ratecon_candidate_to_field_candidate",
    "adapt_candidate_result_to_field_candidates",
    "FieldCandidate",
    "candidate_id",
    "page_number",
    "line_number",
    "line_index",
    "source_line",
    "pairing_method",
    "metadata_summary",
    "resolver_trace",
    "candidate_adapter",
    "adapter_roundtrip",
    "load_candidate",
    "load_identifier",
    "dedupe_lineage",
    "merged_provenance",
)

SYMBOL_MARKERS = (
    "ADAPTER",
    "PROVENANCE",
    "FIELD_CANDIDATE",
    "CANDIDATE_ID",
    "PAGE_NUMBER",
    "LINE_NUMBER",
    "LINE_INDEX",
    "PAIRING_METHOD",
    "SOURCE_LINE",
    "METADATA",
    "ROUNDTRIP",
)

FUNCTION_MARKERS = (
    "adapt_",
    "provenance",
    "candidate_id",
    "source_line",
    "page_number",
    "line_number",
    "line_index",
    "pairing",
    "roundtrip",
)

FIELD_MARKERS = (
    "candidate_id",
    "source",
    "source_family",
    "parser_name",
    "page_number",
    "line_number",
    "line_index",
    "source_line",
    "bbox",
    "bbox_available",
    "pairing_method",
    "label_text_status",
    "value_text_status",
    "neighbor_context_status",
    "adapter_roundtrip_status",
    "adapter_loss_reason",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static RateCon load candidate adapter provenance audit."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _require_output_under_local_outputs(repo_root: Path, output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    local_root = (repo_root / ".local_outputs").resolve()
    if not resolved.is_relative_to(local_root):
        raise ValueError("Output directory must be under .local_outputs")
    return resolved


def _is_ignored(path: Path, repo_root: Path) -> bool:
    if set(path.parts) & EXCLUDED_DIR_NAMES:
        return True
    try:
        rel = _relative(path, repo_root)
    except ValueError:
        return True
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in IGNORED_RELATIVE_PREFIXES)


def _paths(repo_root: Path, suffixes: set[str]) -> list[Path]:
    roots = [repo_root / "app", repo_root / "scripts", repo_root / "tests", repo_root / "docs"]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes and not _is_ignored(path, repo_root):
                paths.append(path)
    return sorted(paths)


def _python_paths(repo_root: Path) -> list[Path]:
    return _paths(repo_root, {".py"})


def _text_paths(repo_root: Path) -> list[Path]:
    return _paths(repo_root, {".py", ".md", ".json", ".csv", ".jsonl"})


def _owner_recommendation(rel: str) -> str:
    if rel == "app/document_ai/field_candidate_provenance.py":
        return "adapter_boundary_owner"
    if rel == "app/document_ai/load_identifier_candidate_adapter_provenance.py":
        return "adapter_provenance_helper_owner"
    if rel == "app/document_ai/field_candidate_generators.py":
        return "generator_consumer"
    if rel == "app/document_ai/field_candidate_resolver.py":
        return "resolver_trace_consumer"
    if rel == "app/document_ai/load_identifier_source_line_serialization.py":
        return "serialization_sidecar_consumer"
    if rel == "app/document_ai/load_identifier_source_line_detail.py":
        return "detail_inventory_consumer"
    if rel.startswith("scripts/"):
        return "local_tooling_consumer"
    if rel.startswith("tests/"):
        return "test_fixture_or_guardrail"
    if rel.startswith("docs/"):
        return "documentation"
    return "manual_review_required"


def _node_symbols(tree: ast.AST) -> list[tuple[str, int, str]]:
    symbols: list[tuple[str, int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append((node.name, getattr(node, "lineno", 0), type(node).__name__))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.append((target.id, getattr(node, "lineno", 0), "Assign"))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbols.append((node.target.id, getattr(node, "lineno", 0), "AnnAssign"))
    return symbols


def _symbol_matches(name: str) -> bool:
    upper = name.upper()
    lower = name.lower()
    return any(marker in upper for marker in SYMBOL_MARKERS) or any(
        marker in lower for marker in FUNCTION_MARKERS
    )


def _constant_value(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, float)):
        return str(node.value)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        values = [_constant_value(element) for element in node.elts]
        return "|".join(value for value in values if value)
    if isinstance(node, ast.Dict):
        values = []
        for key, value in zip(node.keys, node.values):
            key_text = _constant_value(key)
            value_text = _constant_value(value)
            if key_text or value_text:
                values.append(f"{key_text}:{value_text}")
        return "|".join(values)
    return ""


def _field_map(tree: ast.AST, rel: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value_node = node.value
        for target in targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            value = _constant_value(value_node)
            matched = [
                field
                for field in FIELD_MARKERS
                if field in value or field.upper() in name.upper()
            ]
            if not matched and not _symbol_matches(name):
                continue
            rows.append(
                {
                    "path": rel,
                    "symbol": name,
                    "line": getattr(node, "lineno", 0),
                    "field_markers": "|".join(sorted(set(matched))),
                    "value": value[:200],
                    "owner_recommendation": _owner_recommendation(rel),
                }
            )
    return rows


def build_audit(repo_root: Path) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = {}
    symbols: list[dict[str, Any]] = []
    field_map: list[dict[str, Any]] = []
    risk_findings: list[dict[str, Any]] = []
    marker_counts: Counter[str] = Counter()

    for path in _text_paths(repo_root):
        rel = _relative(path, repo_root)
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        lowered = text.lower()
        hits = {
            marker: lowered.count(marker.lower())
            for marker in TEXT_MARKERS
            if marker.lower() in lowered
        }
        if not hits:
            continue
        marker_counts.update(hits)
        modules[rel] = {
            "path": rel,
            "marker_hits": sum(hits.values()),
            "matched_markers": sorted(hits),
            "owner_recommendation": _owner_recommendation(rel),
        }

    for path in _python_paths(repo_root):
        rel = _relative(path, repo_root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            risk_findings.append(
                {
                    "path": rel,
                    "risk": "medium",
                    "finding": "syntax_error_skipped",
                    "evidence": str(exc),
                }
            )
            continue
        for name, line, kind in _node_symbols(tree):
            if _symbol_matches(name):
                symbols.append(
                    {
                        "path": rel,
                        "symbol": name,
                        "line": line,
                        "kind": kind,
                        "owner_recommendation": _owner_recommendation(rel),
                    }
                )
        field_map.extend(_field_map(tree, rel))

    recommendation_counts = Counter(row["owner_recommendation"] for row in modules.values())
    return {
        "module_count": len(modules),
        "symbol_count": len(symbols),
        "field_map_count": len(field_map),
        "risk_finding_count": len(risk_findings),
        "recommendation_counts": dict(sorted(recommendation_counts.items())),
        "marker_counts": dict(sorted(marker_counts.items())),
        "modules": sorted(modules.values(), key=lambda row: row["path"]),
        "symbols": sorted(symbols, key=lambda row: (row["path"], row["line"], row["symbol"])),
        "field_map": sorted(field_map, key=lambda row: (row["path"], row["line"], row["symbol"])),
        "risk_findings": risk_findings,
        "static_analysis_only": True,
        "project_modules_imported": False,
        "resolver_or_extraction_executed": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_outputs(output_dir: Path, audit: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        key: audit[key]
        for key in (
            "module_count",
            "symbol_count",
            "field_map_count",
            "risk_finding_count",
            "recommendation_counts",
            "marker_counts",
            "static_analysis_only",
            "project_modules_imported",
            "resolver_or_extraction_executed",
            "pdf_processing_attempted",
            "ocr_attempted",
            "google_called",
            "model_or_cloud_called",
            "private_measurement_run",
        )
    }
    (output_dir / "load_candidate_adapter_provenance_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_lines = [
        "# RateCon Load Candidate Adapter Provenance Audit",
        "",
        "Static AST/text audit for load candidate adapter provenance boundaries.",
        "",
        f"- module_count: {audit['module_count']}",
        f"- symbol_count: {audit['symbol_count']}",
        f"- field_map_count: {audit['field_map_count']}",
        f"- risk_finding_count: {audit['risk_finding_count']}",
        f"- static_analysis_only: {audit['static_analysis_only']}",
        f"- project_modules_imported: {audit['project_modules_imported']}",
        f"- resolver_or_extraction_executed: {audit['resolver_or_extraction_executed']}",
        f"- pdf_processing_attempted: {audit['pdf_processing_attempted']}",
        f"- ocr_attempted: {audit['ocr_attempted']}",
        f"- google_called: {audit['google_called']}",
        f"- model_or_cloud_called: {audit['model_or_cloud_called']}",
        "",
        "## Owner Recommendations",
    ]
    for recommendation, count in audit["recommendation_counts"].items():
        report_lines.append(f"- {recommendation}: {count}")
    (output_dir / "load_candidate_adapter_provenance_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "load_candidate_adapter_modules.csv",
        audit["modules"],
        ["path", "marker_hits", "matched_markers", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_candidate_adapter_symbols.csv",
        audit["symbols"],
        ["path", "symbol", "line", "kind", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_candidate_adapter_field_map.csv",
        audit["field_map"],
        ["path", "symbol", "line", "field_markers", "value", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_candidate_adapter_risk_findings.csv",
        audit["risk_findings"],
        ["path", "risk", "finding", "evidence"],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        raise SystemExit("--confirm-local-audit-run is required for this static audit.")
    repo_root = _resolve(args.repo_root)
    output_dir = _require_output_under_local_outputs(repo_root, _resolve(args.output_dir))
    audit = build_audit(repo_root)
    write_outputs(output_dir, audit)
    print("RateCon load candidate adapter provenance static audit")
    print(f"module_count: {audit['module_count']}")
    print(f"symbol_count: {audit['symbol_count']}")
    print(f"field_map_count: {audit['field_map_count']}")
    print(f"risk_finding_count: {audit['risk_finding_count']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
