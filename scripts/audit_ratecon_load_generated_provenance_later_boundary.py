"""Static RateCon load generated provenance later-boundary audit.

This local-only audit uses AST/text analysis only. It does not import project
modules, execute resolver/evaluator/extraction code, process PDFs, run OCR,
call Google, call model/cloud services, or read private/local output dirs.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_load_generated_provenance_later_boundary_audit")

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
    "load_generated_resolver_provenance",
    "generated_resolver",
    "generated_candidates",
    "adapter_roundtrip",
    "dedupe_lineage",
    "resolver_visible",
    "resolver_decision_traces",
    "shadow_audit",
    "ratecon_shadow_document_pipeline_audit",
    "candidate_id",
    "page_number",
    "line_index",
    "pairing_method",
    "boundary",
)

SYMBOL_MARKERS = (
    "GENERATED",
    "RESOLVER",
    "ADAPTER",
    "DEDUPE",
    "BOUNDARY",
    "PROVENANCE",
    "CANDIDATE_ID",
    "PAGE_NUMBER",
    "LINE_INDEX",
    "PAIRING_METHOD",
    "SIDECAR",
)

FIELD_MARKERS = (
    "candidate_id",
    "source",
    "source_family",
    "parser_name",
    "pairing_method",
    "page_number",
    "line_index",
    "bbox_available",
    "generated",
    "adapter_input",
    "adapter_output",
    "dedupe_input",
    "dedupe_output",
    "resolver_input",
    "resolver_selected",
    "resolver_trace_available",
    "detail_loss_stage",
    "detail_loss_reason",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static RateCon load generated provenance later-boundary audit."
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


def _owner_recommendation(rel: str) -> str:
    if rel == "app/document_ai/load_identifier_generated_provenance_boundary.py":
        return "later_boundary_compare_owner"
    if rel == "app/document_ai/load_identifier_generated_resolver_provenance.py":
        return "generated_resolver_sidecar_owner"
    if rel == "app/document_ai/load_identifier_candidate_adapter_provenance.py":
        return "adapter_provenance_consumer"
    if rel == "app/document_ai/load_identifier_source_line_detail.py":
        return "detail_inventory_consumer"
    if rel == "app/document_ai/load_identifier_source_line_serialization.py":
        return "serialization_sidecar_consumer"
    if rel == "app/document_ai/field_candidate_generators.py":
        return "generator_diagnostic_consumer"
    if rel == "app/document_ai/field_candidate_resolver.py":
        return "resolver_trace_consumer"
    if rel == "app/document_ai/private_measurement_pipeline.py":
        return "private_measurement_diagnostic_consumer"
    if rel.startswith("app/document_ai/measurement_cli/"):
        return "private_measurement_cli_consumer"
    if rel == "app/document_ai/ratecon_shadow_audit.py":
        return "shadow_audit_consumer"
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
        marker.lower() in lower for marker in TEXT_MARKERS
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


def _field_rows(path: Path, rel: str) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    rows = []
    for field in FIELD_MARKERS:
        count = text.count(field)
        if count:
            rows.append(
                {
                    "module_path": rel,
                    "field_name": field,
                    "reference_count": count,
                    "owner_recommendation": _owner_recommendation(rel),
                }
            )
    return rows


def _module_rows(repo_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    modules: list[dict[str, Any]] = []
    symbols: list[dict[str, Any]] = []
    fields: list[dict[str, Any]] = []
    for path in _paths(repo_root, {".py", ".md", ".json", ".csv", ".jsonl"}):
        rel = _relative(path, repo_root)
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        marker_hits = sorted(marker for marker in TEXT_MARKERS if marker in text)
        field_hits = _field_rows(path, rel)
        if marker_hits or field_hits:
            modules.append(
                {
                    "module_path": rel,
                    "marker_count": len(marker_hits),
                    "markers": "|".join(marker_hits),
                    "owner_recommendation": _owner_recommendation(rel),
                }
            )
            fields.extend(field_hits)
        if path.suffix.lower() != ".py":
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for name, line, kind in _node_symbols(tree):
            if _symbol_matches(name):
                symbols.append(
                    {
                        "module_path": rel,
                        "symbol_name": name,
                        "line": line,
                        "symbol_kind": kind,
                        "owner_recommendation": _owner_recommendation(rel),
                    }
                )
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and _symbol_matches(target.id):
                        value = _constant_value(node.value)
                        if value:
                            symbols.append(
                                {
                                    "module_path": rel,
                                    "symbol_name": target.id,
                                    "line": getattr(node, "lineno", 0),
                                    "symbol_kind": "ConstantValue",
                                    "owner_recommendation": _owner_recommendation(rel),
                                }
                            )
    return modules, symbols, fields


def _risk_rows(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    boundary_specific_markers = {
        "load_generated_resolver_provenance",
        "generated_resolver",
        "adapter_roundtrip",
    }
    risks: list[dict[str, Any]] = []
    for row in modules:
        rel = str(row["module_path"])
        markers = set(str(row.get("markers", "")).split("|"))
        if (
            rel.startswith("app/")
            and _owner_recommendation(rel) == "manual_review_required"
            and markers & boundary_specific_markers
        ):
            risks.append(
                {
                    "module_path": rel,
                    "risk": "manual_review_required_for_boundary_logic",
                    "reason": "Generated provenance boundary markers appear outside approved local-only owners.",
                }
            )
    return risks


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# RateCon Load Generated Provenance Later-Boundary Audit",
        "",
        "Static AST/text audit only. No extraction, resolver execution, PDFs, OCR, Google, or model/cloud calls.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- field_reference_count: {summary['field_reference_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        f"- private_paths_read: {summary['private_paths_read']}",
        f"- local_outputs_read: {summary['local_outputs_read']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Owner Recommendations",
    ]
    for owner, count in summary["owner_recommendation_counts"].items():
        lines.append(f"- {owner}: {count}")
    return "\n".join(lines) + "\n"


def run_audit(repo_root: Path) -> dict[str, Any]:
    modules, symbols, fields = _module_rows(repo_root)
    risks = _risk_rows(modules)
    owner_counts = Counter(row["owner_recommendation"] for row in modules)
    summary = {
        "schema_version": "ratecon_load_generated_provenance_later_boundary_audit_v1",
        "module_count": len(modules),
        "symbol_count": len(symbols),
        "field_reference_count": len(fields),
        "risk_finding_count": len(risks),
        "owner_recommendation_counts": dict(sorted(owner_counts.items())),
        "private_paths_read": False,
        "local_outputs_read": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
    }
    return {
        "summary": summary,
        "modules": modules,
        "symbols": symbols,
        "fields": fields,
        "risks": risks,
    }


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "load_generated_provenance_later_boundary_summary.json",
        payload["summary"],
    )
    (output_dir / "load_generated_provenance_later_boundary_report.md").write_text(
        _report(payload["summary"]),
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "load_generated_provenance_boundary_modules.csv",
        payload["modules"],
        ["module_path", "marker_count", "markers", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_generated_provenance_boundary_symbols.csv",
        payload["symbols"],
        ["module_path", "symbol_name", "line", "symbol_kind", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_generated_provenance_boundary_fields.csv",
        payload["fields"],
        ["module_path", "field_name", "reference_count", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_generated_provenance_boundary_risk_findings.csv",
        payload["risks"],
        ["module_path", "risk", "reason"],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        raise SystemExit("--confirm-local-audit-run is required for this local-only audit.")
    repo_root = _resolve(args.repo_root)
    output_dir = _require_output_under_local_outputs(repo_root, _resolve(args.output_dir))
    payload = run_audit(repo_root)
    write_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load generated provenance later-boundary audit")
    print(f"module_count: {summary['module_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
    print(f"field_reference_count: {summary['field_reference_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"private_paths_read: {summary['private_paths_read']}")
    print(f"local_outputs_read: {summary['local_outputs_read']}")
    print(f"pdf_processing_attempted: {summary['pdf_processing_attempted']}")
    print(f"ocr_attempted: {summary['ocr_attempted']}")
    print(f"google_called: {summary['google_called']}")
    print(f"model_or_cloud_called: {summary['model_or_cloud_called']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
