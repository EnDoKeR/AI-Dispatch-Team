"""Static OCR ownership/status audit for RateCon shadow diagnostics.

This tool is intentionally local-only. It parses source files with ``ast`` and
text scanning only. It never imports project modules, executes OCR code, checks
Tesseract availability, processes PDFs, calls Google, or calls model/cloud
services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_ocr_ownership_status_audit")

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

KNOWN_OCR_MODULES = {
    "app/document_ai/ocr_provider_contract.py",
    "app/document_ai/tesseract_ocr_provider.py",
    "app/document_ai/ocr_stop_block_assembler.py",
    "app/document_ai/ocr_stop_geometry_assembler.py",
    "app/document_ai/ocr_stop_table_reconstructor.py",
    "app/document_ai/ratecon_ocr_candidate_policy.py",
    "scripts/check_ratecon_ocr_dependencies.py",
    "scripts/run_private_ratecon_measurement.py",
    "app/document_ai/measurement_cli/ratecon_private_args.py",
    "app/document_ai/measurement_cli/ratecon_private_config.py",
    "app/document_ai/measurement_cli/ratecon_private_safety.py",
    "app/document_ai/private_measurement_pipeline.py",
    "app/document_ai/ratecon_document_pipeline.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/field_candidate_resolver.py",
}

OPTIONAL_OCR_DEPENDENCIES = {
    "pytesseract",
    "pypdfium2",
    "fitz",
    "pdf2image",
    "PIL.Image",
}

FORBIDDEN_RUNTIME_IMPORT_PREFIXES = (
    "app.market_intelligence.decision_engine",
    "app.market_intelligence.dispatch_case",
    "app.market_intelligence.case_event_builder",
    "app.market_intelligence.event_logger",
    "app.market_intelligence.telegram",
    "app.integrations.google",
    "google.oauth",
    "googleapiclient",
    "gspread",
    "openai",
    "anthropic",
    "google.generativeai",
)


class OcrOwnershipAuditError(ValueError):
    """Raised for safe user-facing audit failures."""


@dataclass(frozen=True)
class SourceFile:
    rel_path: str
    module_name: str
    path: Path
    text: str
    tree: ast.AST | None


@dataclass(frozen=True)
class ImportEdge:
    importer_path: str
    importer_module: str
    imported_module: str
    imported_path: str
    is_internal: bool
    line: int


def _posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _is_within(path: Path, parent: Path) -> bool:
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def _resolve_repo_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.exists():
        raise OcrOwnershipAuditError(f"repo root does not exist: {root}")
    if not root.is_dir():
        raise OcrOwnershipAuditError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise OcrOwnershipAuditError("Output directory must be under .local_outputs.")
    return output_dir


def _should_skip_path(repo_root: Path, path: Path) -> bool:
    rel = _posix(path.relative_to(repo_root))
    rel_parts = Path(rel).parts
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
        return True
    return any(
        rel == prefix or rel.startswith(prefix + "/")
        for prefix in IGNORED_RELATIVE_PREFIXES
    )


def _module_name_from_path(rel_path: str) -> str:
    without_suffix = Path(rel_path).with_suffix("")
    parts = list(without_suffix.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _parse_source(path: Path, text: str) -> ast.AST | None:
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError:
        return None


def _discover_python_sources(repo_root: Path) -> list[SourceFile]:
    sources: list[SourceFile] = []
    for path in sorted(repo_root.rglob("*.py")):
        if _should_skip_path(repo_root, path):
            continue
        rel_path = _posix(path.relative_to(repo_root))
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        sources.append(
            SourceFile(
                rel_path=rel_path,
                module_name=_module_name_from_path(rel_path),
                path=path,
                text=text,
                tree=_parse_source(path, text),
            )
        )
    return sources


def _literal_or_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        value = ast.literal_eval(node)
    except Exception:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            current: ast.AST | None = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        if isinstance(node, ast.Call):
            return _call_name(node)
        return ""
    return repr(value) if isinstance(value, (tuple, list, dict, set)) else str(value)


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _iter_import_edges(sources: list[SourceFile]) -> list[ImportEdge]:
    module_to_path = {source.module_name: source.rel_path for source in sources}
    edges: list[ImportEdge] = []
    for source in sources:
        if source.tree is None:
            continue
        for node in ast.walk(source.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    edges.append(
                        ImportEdge(
                            importer_path=source.rel_path,
                            importer_module=source.module_name,
                            imported_module=imported,
                            imported_path=module_to_path.get(imported, ""),
                            is_internal=imported in module_to_path,
                            line=getattr(node, "lineno", 0),
                        )
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = node.module
                imported_path = module_to_path.get(imported, "")
                if not imported_path:
                    for alias in node.names:
                        candidate = f"{imported}.{alias.name}"
                        if candidate in module_to_path:
                            imported_path = module_to_path[candidate]
                            imported = candidate
                            break
                edges.append(
                    ImportEdge(
                        importer_path=source.rel_path,
                        importer_module=source.module_name,
                        imported_module=imported,
                        imported_path=imported_path,
                        is_internal=bool(imported_path),
                        line=getattr(node, "lineno", 0),
                    )
                )
    return edges


def _is_ocr_related_source(source: SourceFile) -> bool:
    lower_path = source.rel_path.lower()
    lower_text = source.text.lower()
    if source.rel_path in KNOWN_OCR_MODULES:
        return True
    if "/ocr" in lower_path or "ocr_" in lower_path or "_ocr" in lower_path:
        return True
    if source.rel_path.startswith("tests/"):
        return False
    return source.rel_path.startswith(("app/document_ai/", "scripts/")) and "ocr" in lower_text


def _module_status_recommendation(rel_path: str, text: str) -> str:
    if rel_path == "app/document_ai/ocr_provider_contract.py":
        return "active_shadow_local"
    if rel_path in {
        "scripts/check_ratecon_ocr_dependencies.py",
        "scripts/audit_ratecon_ocr_ownership_status.py",
    }:
        return "active_shadow_local"
    if rel_path in {
        "app/document_ai/tesseract_ocr_provider.py",
        "app/document_ai/ocr_stop_block_assembler.py",
        "app/document_ai/ocr_stop_geometry_assembler.py",
        "app/document_ai/ocr_stop_table_reconstructor.py",
        "app/document_ai/ratecon_ocr_candidate_policy.py",
    }:
        return "experimental_shadow_local"
    if rel_path.startswith("tests/"):
        return "manual_review_required"
    if "production ocr" in text.lower():
        return "production_forbidden"
    if "compat" in text.lower():
        return "compatibility"
    return "manual_review_required"


def _owner_layer(rel_path: str) -> str:
    if rel_path == "app/document_ai/ocr_provider_contract.py":
        return "document_ai_shadow_ocr_contract"
    if rel_path == "app/document_ai/tesseract_ocr_provider.py":
        return "document_ai_shadow_ocr_provider"
    if rel_path.startswith("app/document_ai/ocr_stop_"):
        return "document_ai_shadow_ocr_stop_diagnostics"
    if rel_path == "app/document_ai/ratecon_ocr_candidate_policy.py":
        return "document_ai_shadow_ocr_candidate_policy"
    if rel_path.startswith("app/document_ai/measurement_cli/"):
        return "local_private_measurement_cli"
    if rel_path.startswith("scripts/"):
        return "local_only_script"
    if rel_path.startswith("tests/"):
        return "test_only"
    return "document_ai_shadow_ocr_reference"


def _dependency_status(source: SourceFile, imports: list[ImportEdge]) -> tuple[str, str]:
    if source.rel_path.startswith("tests/"):
        return "test_only", "test module"
    direct_optional_imports = sorted(
        {
            edge.imported_module
            for edge in imports
            if edge.importer_path == source.rel_path
            and edge.imported_module in OPTIONAL_OCR_DEPENDENCIES
        }
    )
    dynamic_imports = _dynamic_imports(source)
    optional_dynamic = sorted(
        item for item in dynamic_imports if item in OPTIONAL_OCR_DEPENDENCIES
    )
    if optional_dynamic:
        return "optional_dynamic_import", ", ".join(optional_dynamic)
    if direct_optional_imports:
        return "mandatory", ", ".join(direct_optional_imports)
    if source.rel_path == "app/document_ai/ocr_provider_contract.py":
        return "unknown", "standard-library contract only"
    return "unknown", "no OCR dependency import detected"


def _dynamic_imports(source: SourceFile) -> list[str]:
    if source.tree is None:
        return []
    imports: list[str] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        if name not in {"import_module", "_safe_import", "__import__"}:
            continue
        if not node.args:
            continue
        module_name = _literal_or_name(node.args[0]).strip("'\"")
        if module_name:
            imports.append(module_name)
    return sorted(set(imports))


def _output_behavior(rel_path: str, text: str) -> str:
    lower = text.lower()
    if "production" in lower and "ocr" in lower and "not implemented" in lower:
        return "safe audit only"
    if "safe_ocr_provider_summary" in text or "raw_text_included" in text:
        return "safe audit only"
    if rel_path.startswith("scripts/"):
        return "private/local-only"
    if "pages" in lower and "text" in lower and "ocr" in lower:
        return "private/local-only"
    return "unknown"


def _production_reachability(rel_path: str, text: str) -> str:
    lower = text.lower()
    if rel_path.startswith("tests/"):
        return "test_only"
    if rel_path.startswith("scripts/"):
        return "local_only"
    if "shadow" in lower or "default none" in lower or "diagnostic" in lower:
        return "shadow/local-only"
    if rel_path.startswith("app/document_ai/ocr_") or "ratecon_ocr" in rel_path:
        return "shadow/local-only"
    return "manual_review_required"


def _risk(rel_path: str, status: str, dependency_status: str) -> str:
    if rel_path == "scripts/audit_ratecon_ocr_ownership_status.py":
        return "low"
    if status == "production_forbidden" or dependency_status == "mandatory":
        return "high"
    if rel_path == "app/document_ai/tesseract_ocr_provider.py":
        return "medium"
    if status == "experimental_shadow_local":
        return "medium"
    return "low"


def _default_enabled_from_flags(flags: list[dict[str, str]]) -> str:
    provider_flags = [
        flag
        for flag in flags
        if flag.get("flag") == "--ratecon-shadow-ocr-provider"
    ]
    if provider_flags:
        default = provider_flags[0].get("default", "").strip("'\"").lower()
        return "yes" if default not in {"none", "", "false"} else "no"
    return "no"


def _collect_cli_flags(source: SourceFile) -> list[dict[str, str]]:
    if source.tree is None:
        return []
    flags: list[dict[str, str]] = []
    for node in ast.walk(source.tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node.func) != "parser.add_argument":
            continue
        flag_values = [
            _literal_or_name(arg).strip("'\"")
            for arg in node.args
            if _literal_or_name(arg).startswith("--")
        ]
        ocr_flags = [flag for flag in flag_values if "ocr" in flag.lower()]
        if not ocr_flags:
            continue
        kwargs = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        for flag in ocr_flags:
            flags.append(
                {
                    "source_path": source.rel_path,
                    "flag": flag,
                    "default": _literal_or_name(kwargs.get("default")),
                    "choices": _literal_or_name(kwargs.get("choices")),
                    "action": _literal_or_name(kwargs.get("action")),
                    "help": _literal_or_name(kwargs.get("help")),
                    "activation": "requires explicit local/private flag or provider selection",
                }
            )
    return flags


def _forbidden_import_findings(source: SourceFile, imports: list[ImportEdge]) -> list[str]:
    findings: list[str] = []
    for edge in imports:
        if edge.importer_path != source.rel_path:
            continue
        for prefix in FORBIDDEN_RUNTIME_IMPORT_PREFIXES:
            if edge.imported_module == prefix or edge.imported_module.startswith(prefix + "."):
                findings.append(f"forbidden import {edge.imported_module} at line {edge.line}")
    return findings


def _module_evidence(
    source: SourceFile,
    imports: list[ImportEdge],
    importers: list[str],
    cli_flags: list[dict[str, str]],
) -> str:
    bits = []
    if "shadow" in source.text.lower():
        bits.append("shadow references")
    if "default none" in source.text.lower() or "--ratecon-shadow-ocr-provider" in source.text:
        bits.append("disabled/default-none flag")
    dynamic = _dynamic_imports(source)
    if dynamic:
        bits.append("dynamic imports: " + ", ".join(dynamic))
    if cli_flags:
        bits.append("ocr CLI flags: " + ", ".join(flag["flag"] for flag in cli_flags))
    if importers:
        bits.append("importers: " + ", ".join(importers[:5]))
    forbidden = _forbidden_import_findings(source, imports)
    if forbidden:
        bits.append("; ".join(forbidden))
    return "; ".join(bits) or "static OCR reference detected"


def _build_module_rows(
    sources: list[SourceFile],
    imports: list[ImportEdge],
    cli_flags: list[dict[str, str]],
) -> list[dict[str, str]]:
    ocr_sources = [source for source in sources if _is_ocr_related_source(source)]
    rows: list[dict[str, str]] = []
    for source in ocr_sources:
        importers = sorted(
            {
                edge.importer_path
                for edge in imports
                if edge.imported_path == source.rel_path
                and edge.importer_path != source.rel_path
            }
        )
        imported_deps = sorted(
            {
                edge.imported_module
                for edge in imports
                if edge.importer_path == source.rel_path
            }
        )
        module_flags = [flag for flag in cli_flags if flag["source_path"] == source.rel_path]
        dependency_status, dependency_evidence = _dependency_status(source, imports)
        status = _module_status_recommendation(source.rel_path, source.text)
        risk = _risk(source.rel_path, status, dependency_status)
        forbidden = _forbidden_import_findings(source, imports)
        if forbidden:
            risk = "high"
        rows.append(
            {
                "module_path": source.rel_path,
                "module_name": source.module_name,
                "owner_layer": _owner_layer(source.rel_path),
                "importers": "; ".join(importers),
                "imported_dependencies": "; ".join(imported_deps),
                "cli_flags": "; ".join(flag["flag"] for flag in module_flags),
                "default_enabled": _default_enabled_from_flags(module_flags),
                "production_reachability": _production_reachability(source.rel_path, source.text),
                "dependency_status": dependency_status,
                "dependency_evidence": dependency_evidence,
                "output_behavior": _output_behavior(source.rel_path, source.text),
                "status_recommendation": status,
                "risk": risk,
                "evidence": _module_evidence(source, imports, importers, module_flags),
            }
        )
    return sorted(rows, key=lambda row: row["module_path"])


def _status_recommendations(module_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = [
        {
            "subject": "production_ocr_path",
            "status_recommendation": "production_forbidden",
            "rationale": "No production OCR path is approved or implemented by this audit.",
            "required_action": "Require separate approval, tests, and default-off behavior before any production OCR path.",
        },
        {
            "subject": "local_tesseract_provider",
            "status_recommendation": "experimental_shadow_local",
            "rationale": "Tesseract support uses optional dynamic imports and should remain explicit local diagnostics only.",
            "required_action": "Keep disabled by default and never commit OCR temp text/images/TSV.",
        },
        {
            "subject": "ocr_stop_reconstruction",
            "status_recommendation": "experimental_shadow_local",
            "rationale": "OCR stop block, geometry, and table reconstruction are diagnostic profiles, not production stop selection.",
            "required_action": "Keep review-required and no auto-accept stops.",
        },
    ]
    manual_review = [
        row["module_path"]
        for row in module_rows
        if row["status_recommendation"] == "manual_review_required"
    ]
    if manual_review:
        rows.append(
            {
                "subject": "manual_review_required_modules",
                "status_recommendation": "manual_review_required",
                "rationale": "; ".join(manual_review[:10]),
                "required_action": "Review before changing or deleting these OCR references.",
            }
        )
    return rows


def _risk_findings(module_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in module_rows:
        if row["risk"] in {"medium", "high"}:
            rows.append(
                {
                    "module_path": row["module_path"],
                    "risk": row["risk"],
                    "finding": row["evidence"],
                    "required_guardrail": (
                        "Keep OCR disabled by default, local-only, explicit, "
                        "review-required, and out of production output."
                    ),
                }
            )
    return rows


def _dependency_findings(module_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "module_path": row["module_path"],
            "dependency_status": row["dependency_status"],
            "dependency_evidence": row["dependency_evidence"],
            "risk": row["risk"],
        }
        for row in module_rows
    ]


def _reference_counts(repo_root: Path) -> dict[str, int]:
    counts = {"app": 0, "scripts": 0, "tests": 0, "docs": 0}
    for base in counts:
        root = repo_root / base
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or _should_skip_path(repo_root, path):
                continue
            if path.suffix.lower() not in {".py", ".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore").lower()
            if "ocr" in text or "tesseract" in text or "pytesseract" in text:
                counts[base] += 1
    return counts


def analyze_ocr_ownership(repo_root: Path) -> dict[str, object]:
    sources = _discover_python_sources(repo_root)
    imports = _iter_import_edges(sources)
    cli_flags = [
        flag
        for source in sources
        for flag in _collect_cli_flags(source)
    ]
    module_rows = _build_module_rows(sources, imports, cli_flags)
    ocr_paths = {row["module_path"] for row in module_rows}
    import_edges = [
        edge.__dict__
        for edge in imports
        if edge.importer_path in ocr_paths
        or edge.imported_path in ocr_paths
        or "ocr" in edge.imported_module.lower()
    ]
    status_recommendations = _status_recommendations(module_rows)
    risk_findings = _risk_findings(module_rows)
    dependency_findings = _dependency_findings(module_rows)
    cli_flag_rows = sorted(cli_flags, key=lambda row: (row["source_path"], row["flag"]))
    reference_counts = _reference_counts(repo_root)

    return {
        "schema_version": "ratecon_ocr_ownership_status_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "module_count": len(module_rows),
        "import_edge_count": len(import_edges),
        "cli_flag_count": len(cli_flag_rows),
        "dependency_finding_count": len(dependency_findings),
        "risk_finding_count": len(risk_findings),
        "reference_counts": reference_counts,
        "production_ocr_path_implemented": False,
        "ocr_disabled_by_default": True,
        "ocr_dependencies_mandatory": False,
        "ocr_output_auto_accepted": False,
        "module_status_counts": _count_by(module_rows, "status_recommendation"),
        "risk_counts": _count_by(module_rows, "risk"),
        "modules": module_rows,
        "import_edges": import_edges,
        "cli_flags": cli_flag_rows,
        "dependency_findings": dependency_findings,
        "status_recommendations": status_recommendations,
        "risk_findings": risk_findings,
        "safety": {
            "static_ast_only": True,
            "project_modules_imported": False,
            "ocr_attempted": False,
            "tesseract_dependency_checked": False,
            "pdf_processing_attempted": False,
            "local_outputs_read": False,
            "private_ratecons_read": False,
            "google_called": False,
            "model_or_cloud_called": False,
            "ignored_private_paths": list(IGNORED_RELATIVE_PREFIXES),
        },
        "recommendation": (
            "Keep OCR as disabled-by-default local/shadow diagnostics. "
            "Review audit findings before deleting or productionizing OCR modules."
        ),
    }


def _count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, summary: dict[str, object]) -> None:
    lines = [
        "# RateCon OCR Ownership Status Audit",
        "",
        "This report is generated by static AST/text analysis only. It does not import",
        "project modules, execute OCR, check Tesseract, process PDFs, call Google, or",
        "call model/cloud services.",
        "",
        "## Summary",
        "",
        f"- module_count: {summary['module_count']}",
        f"- import_edge_count: {summary['import_edge_count']}",
        f"- cli_flag_count: {summary['cli_flag_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        f"- production_ocr_path_implemented: {summary['production_ocr_path_implemented']}",
        f"- ocr_disabled_by_default: {summary['ocr_disabled_by_default']}",
        f"- ocr_dependencies_mandatory: {summary['ocr_dependencies_mandatory']}",
        "",
        "## Module Recommendations",
        "",
    ]
    for row in summary["modules"]:
        lines.append(
            f"- `{row['module_path']}`: {row['status_recommendation']} "
            f"({row['risk']} risk; {row['production_reachability']})"
        )
    lines.extend(["", "## CLI Flags", ""])
    if summary["cli_flags"]:
        for row in summary["cli_flags"]:
            lines.append(
                f"- `{row['flag']}` in `{row['source_path']}` "
                f"default=`{row['default']}`"
            )
    else:
        lines.append("- none detected")
    lines.extend(["", "## Status Recommendations", ""])
    for row in summary["status_recommendations"]:
        lines.append(
            f"- {row['subject']}: {row['status_recommendation']}. "
            f"{row['required_action']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- OCR was not executed.",
            "- Tesseract dependency availability was not checked.",
            "- PDFs were not processed.",
            "- `.local_outputs/` and `data/private_ratecons/` were not read.",
            "- No Google, AI/model, or cloud calls were made.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(summary: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_json": output_dir / "ocr_ownership_status_summary.json",
        "report_md": output_dir / "ocr_ownership_status_report.md",
        "modules_csv": output_dir / "ocr_modules.csv",
        "import_edges_csv": output_dir / "ocr_import_edges.csv",
        "cli_flags_csv": output_dir / "ocr_cli_flags.csv",
        "dependency_findings_csv": output_dir / "ocr_dependency_findings.csv",
        "status_recommendations_csv": output_dir / "ocr_status_recommendations.csv",
        "risk_findings_csv": output_dir / "ocr_risk_findings.csv",
    }
    _write_json(paths["summary_json"], summary)
    _write_report(paths["report_md"], summary)
    _write_csv(
        paths["modules_csv"],
        summary["modules"],
        [
            "module_path",
            "module_name",
            "owner_layer",
            "importers",
            "imported_dependencies",
            "cli_flags",
            "default_enabled",
            "production_reachability",
            "dependency_status",
            "dependency_evidence",
            "output_behavior",
            "status_recommendation",
            "risk",
            "evidence",
        ],
    )
    _write_csv(
        paths["import_edges_csv"],
        summary["import_edges"],
        [
            "importer_path",
            "importer_module",
            "imported_module",
            "imported_path",
            "is_internal",
            "line",
        ],
    )
    _write_csv(
        paths["cli_flags_csv"],
        summary["cli_flags"],
        ["source_path", "flag", "default", "choices", "action", "help", "activation"],
    )
    _write_csv(
        paths["dependency_findings_csv"],
        summary["dependency_findings"],
        ["module_path", "dependency_status", "dependency_evidence", "risk"],
    )
    _write_csv(
        paths["status_recommendations_csv"],
        summary["status_recommendations"],
        ["subject", "status_recommendation", "rationale", "required_action"],
    )
    _write_csv(
        paths["risk_findings_csv"],
        summary["risk_findings"],
        ["module_path", "risk", "finding", "required_guardrail"],
    )
    return {key: _posix(path) for key, path in paths.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local-only static OCR ownership/status audit."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Local-only output directory under .local_outputs.",
    )
    parser.add_argument(
        "--confirm-local-audit-run",
        action="store_true",
        help="Required confirmation that this static local audit should run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_local_audit_run:
        parser.error("--confirm-local-audit-run is required for this local-only audit.")

    try:
        repo_root = _resolve_repo_root(args.repo_root)
        output_dir = _resolve_output_dir(repo_root, args.output_dir)
        summary = analyze_ocr_ownership(repo_root)
        output_paths = write_outputs(summary, output_dir)
    except OcrOwnershipAuditError as exc:
        print(f"OCR ownership audit could not start. Reason: {exc}")
        return 2

    print("RateCon OCR ownership/status audit")
    print(f"module_count: {summary['module_count']}")
    print(f"import_edge_count: {summary['import_edge_count']}")
    print(f"cli_flag_count: {summary['cli_flag_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"production_ocr_path_implemented: {summary['production_ocr_path_implemented']}")
    print(f"ocr_disabled_by_default: {summary['ocr_disabled_by_default']}")
    print(f"recommendation: {summary['recommendation']}")
    print(f"output_dir: {_posix(output_dir)}")
    for label, path in output_paths.items():
        print(f"{label}: {path}")
    print("project_modules_imported: False")
    print("ocr_attempted: False")
    print("pdf_processing_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
