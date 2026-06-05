"""Static RateCon load source-line/evidence diagnostics audit.

This local-only tool uses AST/text analysis only. It does not import project
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


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_load_source_line_evidence_audit")

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
    "source_line",
    "source line",
    "source_page",
    "source page",
    "line_index",
    "page_index",
    "table_neighbor",
    "table neighbor",
    "nearby_row",
    "nearby row",
    "wrong_cell",
    "wrong cell",
    "wrong_pair",
    "wrong pair",
    "footer",
    "barcode",
    "gold_not_in_candidates",
    "gold_in_candidates_not_selected",
    "selected_table_neighbor_wrong_cell",
    "selected_nearby_row_wrong_pair",
)

SYMBOL_MARKERS = (
    "SOURCE_LINE",
    "SOURCE_PAGE",
    "LINE_INDEX",
    "PAGE_INDEX",
    "TABLE_NEIGHBOR",
    "NEARBY_ROW",
    "WRONG_CELL",
    "WRONG_PAIR",
    "FOOTER",
    "BARCODE",
)

FUNCTION_MARKERS = (
    "source_line",
    "source_page",
    "line_index",
    "table_neighbor",
    "nearby_row",
    "pairing",
    "evidence",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Static RateCon load source-line/evidence diagnostics audit."
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
    parts = set(path.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return True
    try:
        rel = _relative(path, repo_root)
    except ValueError:
        return True
    return any(rel == prefix or rel.startswith(prefix + "/") for prefix in IGNORED_RELATIVE_PREFIXES)


def _python_paths(repo_root: Path) -> list[Path]:
    roots = [repo_root / "app", repo_root / "scripts", repo_root / "tests"]
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if not _is_ignored(path, repo_root):
                paths.append(path)
    return sorted(paths)


def _text_paths(repo_root: Path) -> list[Path]:
    roots = [repo_root / "app", repo_root / "scripts", repo_root / "tests", repo_root / "docs"]
    suffixes = {".py", ".md", ".json", ".csv", ".jsonl"}
    paths: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in suffixes and not _is_ignored(path, repo_root):
                paths.append(path)
    return sorted(paths)


def _owner_recommendation(rel: str) -> str:
    if rel == "app/document_ai/load_identifier_source_line_audit.py":
        return "source_line_audit_owner"
    if rel == "app/document_ai/load_identity_forensics.py":
        return "load_identity_forensics_consumer"
    if rel == "app/document_ai/load_identifier_candidates.py":
        return "candidate_taxonomy_consumer"
    if rel in {
        "app/document_ai/field_candidate_generators.py",
        "app/document_ai/ratecon_candidate_generators.py",
    }:
        return "generator_consumer"
    if rel in {
        "app/document_ai/field_candidate_resolver.py",
        "app/document_ai/ratecon_field_resolution.py",
    }:
        return "resolver_consumer"
    if rel.startswith("scripts/"):
        return "local_tooling_consumer"
    if rel.startswith("tests/"):
        return "test_fixture_or_guardrail"
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
    return ""


def _reason_constants(tree: ast.AST, rel: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            name = target.id
            if not _symbol_matches(name):
                continue
            value = _constant_value(node.value)
            if not value:
                continue
            rows.append(
                {
                    "path": rel,
                    "symbol": name,
                    "line": getattr(node, "lineno", 0),
                    "value": value[:200],
                }
            )
    return rows


def build_audit(repo_root: Path) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = {}
    symbols: list[dict[str, Any]] = []
    reason_constants: list[dict[str, Any]] = []
    risk_findings: list[dict[str, Any]] = []
    marker_counts: Counter[str] = Counter()

    for path in _text_paths(repo_root):
        rel = _relative(path, repo_root)
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        lowered = text.lower()
        hits = {marker: lowered.count(marker.lower()) for marker in TEXT_MARKERS if marker.lower() in lowered}
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
            if not _symbol_matches(name):
                continue
            modules.setdefault(
                rel,
                {
                    "path": rel,
                    "marker_hits": 0,
                    "matched_markers": [],
                    "owner_recommendation": _owner_recommendation(rel),
                },
            )
            symbols.append(
                {
                    "path": rel,
                    "symbol": name,
                    "line": line,
                    "kind": kind,
                    "owner_recommendation": _owner_recommendation(rel),
                }
            )
        reason_constants.extend(_reason_constants(tree, rel))

    recommendations = Counter(module["owner_recommendation"] for module in modules.values())
    summary = {
        "module_count": len(modules),
        "symbol_count": len(symbols),
        "reason_constant_count": len(reason_constants),
        "risk_finding_count": len(risk_findings),
        "top_marker_counts": dict(marker_counts.most_common(12)),
        "recommendation_counts": dict(sorted(recommendations.items())),
        "static_analysis_only": True,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    return {
        "summary": summary,
        "modules": sorted(modules.values(), key=lambda row: row["path"]),
        "symbols": sorted(symbols, key=lambda row: (row["path"], row["line"], row["symbol"])),
        "reason_constants": sorted(
            reason_constants,
            key=lambda row: (row["path"], row["line"], row["symbol"]),
        ),
        "risk_findings": risk_findings,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, audit: dict[str, Any]) -> None:
    summary = audit["summary"]
    lines = [
        "# RateCon Load Source-Line Evidence Audit",
        "",
        "Static AST/text analysis only. No resolver, extraction, PDF, OCR, Google, or model/cloud execution.",
        "",
        f"- module_count: {summary['module_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- reason_constant_count: {summary['reason_constant_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        "",
        "## Recommendation Counts",
    ]
    for name, count in summary["recommendation_counts"].items():
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Top Markers"])
    for marker, count in summary["top_marker_counts"].items():
        lines.append(f"- {marker}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, audit: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "load_source_line_evidence_summary.json", audit["summary"])
    _write_report(output_dir / "load_source_line_evidence_report.md", audit)
    _write_csv(
        output_dir / "load_source_line_modules.csv",
        audit["modules"],
        ["path", "marker_hits", "matched_markers", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_source_line_symbols.csv",
        audit["symbols"],
        ["path", "symbol", "line", "kind", "owner_recommendation"],
    )
    _write_csv(
        output_dir / "load_source_line_pairing_reasons.csv",
        audit["reason_constants"],
        ["path", "symbol", "line", "value"],
    )
    _write_csv(
        output_dir / "load_source_line_risk_findings.csv",
        audit["risk_findings"],
        ["path", "risk", "finding", "evidence"],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_local_audit_run:
        raise SystemExit("--confirm-local-audit-run is required for this local-only audit.")
    repo_root = _resolve(args.repo_root)
    output_dir = _require_output_under_local_outputs(repo_root, _resolve(args.output_dir))
    audit = build_audit(repo_root)
    write_outputs(output_dir, audit)
    summary = audit["summary"]
    print("RateCon load source-line evidence audit")
    print(f"module_count: {summary['module_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
    print(f"reason_constant_count: {summary['reason_constant_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
