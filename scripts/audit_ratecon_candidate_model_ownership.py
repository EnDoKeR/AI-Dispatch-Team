"""Static RateCon candidate model ownership audit.

This tool is intentionally local-only. It parses source files with ``ast`` and
text scanning only. It never imports project modules, executes extraction or
resolver code, processes PDFs, runs OCR, calls Google, or calls model/cloud
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


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_candidate_model_ownership_audit")

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

KNOWN_CANDIDATE_MODULES = {
    "app/document_ai/field_candidate_provenance.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/ratecon_candidates.py",
    "app/document_ai/ratecon_candidate_generators.py",
    "app/document_ai/ratecon_candidate_extraction.py",
    "app/document_ai/ratecon_field_resolution.py",
    "app/market_intelligence/intake/rate_confirmation_intake.py",
    "app/document_ai/ratecon_intake_draft.py",
    "app/document_ai/load_identifier_candidates.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/candidate_fusion.py",
    "app/document_ai/layout_candidate_adapter.py",
    "app/document_ai/layout_candidate_extraction.py",
    "app/document_ai/broker_template_candidate_extraction.py",
    "app/document_ai/stop_evidence_assembler.py",
    "app/document_ai/ratecon_stop_component_policy.py",
    "app/document_ai/ratecon_ocr_candidate_policy.py",
}

CANONICAL_RECOMMENDATIONS = {
    "app/document_ai/field_candidate_provenance.py": (
        "document_ai_candidate_contract",
        "canonical_contract",
        "low",
        "Canonical FieldCandidate provenance contract and adapter surface.",
    ),
    "app/document_ai/field_candidate_generators.py": (
        "document_ai_candidate_generation",
        "generator_orchestrator",
        "medium",
        "Generator/orchestration layer that should not own candidate schema.",
    ),
    "app/document_ai/field_candidate_resolver.py": (
        "document_ai_candidate_resolution",
        "resolver_consumer",
        "medium",
        "Resolver consumes candidate contract and owns selection/review policy.",
    ),
    "app/document_ai/ratecon_candidates.py": (
        "legacy_ratecon_candidate_contract",
        "compatibility_legacy",
        "medium",
        "Legacy candidate compatibility contract surface.",
    ),
    "app/document_ai/ratecon_candidate_generators.py": (
        "legacy_ratecon_candidate_generation",
        "compatibility_legacy",
        "medium",
        "Legacy candidate generator compatibility surface.",
    ),
    "app/document_ai/ratecon_candidate_extraction.py": (
        "legacy_ratecon_candidate_extraction",
        "compatibility_legacy",
        "medium",
        "Legacy candidate extraction compatibility surface.",
    ),
    "app/document_ai/ratecon_field_resolution.py": (
        "legacy_ratecon_resolution",
        "compatibility_legacy",
        "medium",
        "Compatibility bridge around field resolution output.",
    ),
    "app/market_intelligence/intake/rate_confirmation_intake.py": (
        "intake_boundary_contract",
        "boundary_adapter",
        "medium",
        "Intake boundary adapter; not the candidate model owner.",
    ),
    "app/document_ai/ratecon_intake_draft.py": (
        "document_ai_intake_boundary_adapter",
        "boundary_adapter",
        "medium",
        "Document AI draft adapter; not the candidate model owner.",
    ),
}

SUPPORT_POLICY_MODULES = {
    "app/document_ai/load_identifier_candidates.py",
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "app/document_ai/candidate_fusion.py",
    "app/document_ai/layout_candidate_adapter.py",
    "app/document_ai/layout_candidate_extraction.py",
    "app/document_ai/broker_template_candidate_extraction.py",
    "app/document_ai/stop_evidence_assembler.py",
    "app/document_ai/ratecon_stop_component_policy.py",
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


class CandidateOwnershipAuditError(ValueError):
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
        raise CandidateOwnershipAuditError(f"repo root does not exist: {root}")
    if not root.is_dir():
        raise CandidateOwnershipAuditError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise CandidateOwnershipAuditError("Output directory must be under .local_outputs.")
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


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _literal_or_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        value = ast.literal_eval(node)
    except Exception:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return _call_name(node)
        if isinstance(node, ast.Call):
            return _call_name(node)
        return ""
    return repr(value) if isinstance(value, (tuple, list, dict, set)) else str(value)


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
                            imported = candidate
                            imported_path = module_to_path[candidate]
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


def _is_candidate_related_source(source: SourceFile) -> bool:
    lower_path = source.rel_path.lower()
    lower_text = source.text.lower()
    if source.rel_path in KNOWN_CANDIDATE_MODULES:
        return True
    if "candidate" in lower_path or "field_resolution" in lower_path:
        return True
    return any(
        term in lower_text
        for term in (
            "fieldcandidate",
            "field_candidate",
            "candidate schema",
            "candidate contract",
            "build_field_candidate",
            "candidate_confidence",
            "source_regex",
        )
    )


def _classify_module(path: str) -> tuple[str, str, str, str]:
    if path in CANONICAL_RECOMMENDATIONS:
        return CANONICAL_RECOMMENDATIONS[path]
    if path in SUPPORT_POLICY_MODULES:
        return (
            "document_ai_candidate_support_policy",
            "support_policy",
            "medium",
            "Candidate-support helper; not the canonical schema owner.",
        )
    if "/ocr_stop_" in path or path.endswith("/ratecon_ocr_candidate_policy.py"):
        return (
            "document_ai_shadow_candidate_diagnostics",
            "experimental_shadow",
            "medium",
            "Shadow/experimental candidate diagnostics; not production schema owner.",
        )
    if path.startswith("tests/"):
        return ("tests", "manual_review_required", "low", "Test reference only.")
    if path.startswith("docs/"):
        return ("docs", "manual_review_required", "low", "Documentation reference only.")
    return (
        "candidate_reference",
        "manual_review_required",
        "medium",
        "Candidate-related reference needs manual ownership review.",
    )


def _is_candidate_symbol(name: str) -> bool:
    lower = name.lower()
    return any(
        term in lower
        for term in ("candidate", "field", "source", "confidence", "normalize", "resolver")
    )


def _collect_class_fields(node: ast.ClassDef) -> list[str]:
    fields: list[str] = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            fields.append(child.target.id)
        elif isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    fields.append(target.id)
    return fields


def _collect_dict_shapes(node: ast.AST) -> list[str]:
    shapes: list[str] = []
    for child in ast.walk(node):
        if not isinstance(child, ast.Dict):
            continue
        keys = [
            key.value
            for key in child.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        ]
        candidate_keys = [
            key
            for key in keys
            if any(
                term in key.lower()
                for term in (
                    "candidate",
                    "field",
                    "value",
                    "confidence",
                    "source",
                    "evidence",
                    "normalized",
                )
            )
        ]
        if len(candidate_keys) >= 2:
            shapes.append("|".join(keys))
    return sorted(set(shapes))


def _collect_symbols(source: SourceFile) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    symbols: list[dict[str, str]] = []
    shapes: list[dict[str, str]] = []
    if source.tree is None:
        return symbols, shapes

    for node in ast.walk(source.tree):
        if isinstance(node, ast.ClassDef) and _is_candidate_symbol(node.name):
            fields = _collect_class_fields(node)
            symbols.append(
                {
                    "module_path": source.rel_path,
                    "symbol_type": "class",
                    "symbol_name": node.name,
                    "category": "candidate_class",
                    "value": "|".join(fields),
                    "line": str(getattr(node, "lineno", 0)),
                }
            )
            if fields:
                shapes.append(
                    {
                        "module_path": source.rel_path,
                        "shape_owner": node.name,
                        "shape_kind": "class_fields",
                        "keys_or_fields": "|".join(fields),
                        "evidence": "candidate class fields from static AST",
                    }
                )
        elif isinstance(node, ast.FunctionDef) and _is_candidate_symbol(node.name):
            category = "build_candidate_function" if "build" in node.name.lower() else "candidate_function"
            if "normalize" in node.name.lower():
                category = "normalize_function"
            symbols.append(
                {
                    "module_path": source.rel_path,
                    "symbol_type": "function",
                    "symbol_name": node.name,
                    "category": category,
                    "value": "",
                    "line": str(getattr(node, "lineno", 0)),
                }
            )
            for shape in _collect_dict_shapes(node):
                shapes.append(
                    {
                        "module_path": source.rel_path,
                        "shape_owner": node.name,
                        "shape_kind": "return_dict_keys",
                        "keys_or_fields": shape,
                        "evidence": "candidate-shaped dict keys from static AST",
                    }
                )
        elif isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            for target in targets:
                if target.isupper() and _is_candidate_symbol(target):
                    symbols.append(
                        {
                            "module_path": source.rel_path,
                            "symbol_type": "constant",
                            "symbol_name": target,
                            "category": _constant_category(target),
                            "value": _literal_or_name(node.value),
                            "line": str(getattr(node, "lineno", 0)),
                        }
                    )

    return symbols, shapes


def _constant_category(name: str) -> str:
    if "CONFIDENCE" in name:
        return "confidence_constant"
    if "SOURCE" in name:
        return "source_constant"
    if "FIELD" in name:
        return "field_constant"
    if "CANDIDATE" in name:
        return "candidate_constant"
    return "constant"


def _build_module_rows(
    sources: list[SourceFile],
    imports: list[ImportEdge],
    symbols: list[dict[str, str]],
    shapes: list[dict[str, str]],
) -> list[dict[str, str]]:
    candidate_sources = [source for source in sources if _is_candidate_related_source(source)]
    candidate_paths = {source.rel_path for source in candidate_sources}
    rows: list[dict[str, str]] = []
    for source in candidate_sources:
        owner_layer, recommendation, risk, evidence = _classify_module(source.rel_path)
        importers = sorted(
            {
                edge.importer_path
                for edge in imports
                if edge.imported_path == source.rel_path and edge.importer_path != source.rel_path
            }
        )
        imported_dependencies = sorted(
            {
                edge.imported_path or edge.imported_module
                for edge in imports
                if edge.importer_path == source.rel_path
            }
        )
        module_symbols = [row for row in symbols if row["module_path"] == source.rel_path]
        module_shapes = [row for row in shapes if row["module_path"] == source.rel_path]
        rows.append(
            {
                "module_path": source.rel_path,
                "module_name": source.module_name,
                "owner_layer": owner_layer,
                "importers": ";".join(importers),
                "imported_dependencies": ";".join(imported_dependencies),
                "candidate_classes": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "candidate_class"
                ),
                "candidate_functions": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if "function" in row["category"]
                ),
                "field_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "field_constant"
                ),
                "confidence_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "confidence_constant"
                ),
                "source_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "source_constant"
                ),
                "candidate_shape_summary": ";".join(
                    row["shape_owner"] for row in module_shapes
                ),
                "canonical_owner_recommendation": recommendation,
                "risk": risk,
                "evidence": evidence,
                "has_forbidden_runtime_import": str(
                    any(
                        edge.importer_path == source.rel_path
                        and any(
                            edge.imported_module == prefix
                            or edge.imported_module.startswith(prefix + ".")
                            for prefix in FORBIDDEN_RUNTIME_IMPORT_PREFIXES
                        )
                        for edge in imports
                    )
                ),
            }
        )

    return sorted(rows, key=lambda row: (row["module_path"] not in candidate_paths, row["module_path"]))


def _duplicate_constant_rows(symbols: list[dict[str, str]]) -> list[dict[str, str]]:
    constants = [
        row
        for row in symbols
        if row["symbol_type"] == "constant"
        and row["category"]
        in {"field_constant", "source_constant", "confidence_constant", "candidate_constant"}
    ]
    by_name: dict[str, list[dict[str, str]]] = {}
    by_value: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in constants:
        by_name.setdefault(row["symbol_name"], []).append(row)
        if row["value"]:
            by_value.setdefault((row["category"], row["value"]), []).append(row)

    duplicates: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for name, rows in by_name.items():
        modules = sorted({row["module_path"] for row in rows})
        if len(modules) <= 1:
            continue
        key = ("name", name, "|".join(modules))
        seen.add(key)
        duplicates.append(
            {
                "duplicate_type": "constant_name",
                "constant_name": name,
                "constant_value": ";".join(sorted({row["value"] for row in rows if row["value"]})),
                "category": rows[0]["category"],
                "modules": ";".join(modules),
                "module_count": str(len(modules)),
                "risk": "medium",
                "evidence": "same candidate-related constant name appears in multiple modules",
            }
        )

    for (category, value), rows in by_value.items():
        modules = sorted({row["module_path"] for row in rows})
        names = sorted({row["symbol_name"] for row in rows})
        if len(modules) <= 1 or len(names) <= 1:
            continue
        key = ("value", value, "|".join(modules))
        if key in seen:
            continue
        duplicates.append(
            {
                "duplicate_type": "constant_value",
                "constant_name": ";".join(names),
                "constant_value": value,
                "category": category,
                "modules": ";".join(modules),
                "module_count": str(len(modules)),
                "risk": "low",
                "evidence": "same candidate-related constant value appears in multiple modules",
            }
        )

    return sorted(duplicates, key=lambda row: (row["risk"], row["duplicate_type"], row["constant_name"]))


def _status_recommendations(module_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in module_rows:
        recommendation = row["canonical_owner_recommendation"]
        if recommendation == "canonical_contract":
            action = "Treat as the canonical owner for new candidate schema fields."
        elif recommendation == "compatibility_legacy":
            action = "Keep compatibility behavior stable; do not add new schema logic here."
        elif recommendation == "boundary_adapter":
            action = "Keep as boundary adapter; do not make it a candidate contract owner."
        elif recommendation == "generator_orchestrator":
            action = "Use the canonical contract for schema changes."
        elif recommendation == "resolver_consumer":
            action = "Coordinate new candidate metadata with the canonical contract."
        elif recommendation == "experimental_shadow":
            action = "Keep disabled/local-shadow unless separately approved."
        elif recommendation == "support_policy":
            action = "Document support-policy constants and avoid schema ownership drift."
        else:
            action = "Review before refactoring or deleting."
        rows.append(
            {
                "module_path": row["module_path"],
                "canonical_owner_recommendation": recommendation,
                "rationale": row["evidence"],
                "required_action": action,
            }
        )
    return rows


def _risk_findings(module_rows: list[dict[str, str]], duplicate_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for row in module_rows:
        if row["risk"] in {"medium", "high"} or row["has_forbidden_runtime_import"] == "True":
            findings.append(
                {
                    "module_path": row["module_path"],
                    "risk": row["risk"],
                    "finding": (
                        "Candidate ownership role is not canonical"
                        if row["has_forbidden_runtime_import"] == "False"
                        else "Forbidden runtime import detected"
                    ),
                    "required_guardrail": (
                        "Do not change candidate behavior until ownership is reviewed."
                    ),
                }
            )
    for row in duplicate_rows:
        findings.append(
            {
                "module_path": row["modules"],
                "risk": row["risk"],
                "finding": f"Duplicate {row['category']} {row['constant_name']}",
                "required_guardrail": (
                    "Do not consolidate constants without behavior-pinning tests."
                ),
            }
        )
    return sorted(findings, key=lambda row: (row["risk"], row["module_path"]))


def _count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def analyze_candidate_model_ownership(repo_root: Path) -> dict[str, object]:
    sources = _discover_python_sources(repo_root)
    imports = _iter_import_edges(sources)

    symbols: list[dict[str, str]] = []
    shapes: list[dict[str, str]] = []
    for source in sources:
        if not _is_candidate_related_source(source):
            continue
        source_symbols, source_shapes = _collect_symbols(source)
        symbols.extend(source_symbols)
        shapes.extend(source_shapes)

    module_rows = _build_module_rows(sources, imports, symbols, shapes)
    candidate_paths = {row["module_path"] for row in module_rows}
    import_edges = [
        edge.__dict__
        for edge in imports
        if edge.importer_path in candidate_paths
        or edge.imported_path in candidate_paths
        or "candidate" in edge.imported_module.lower()
    ]
    duplicate_rows = _duplicate_constant_rows(symbols)
    status_rows = _status_recommendations(module_rows)
    risk_rows = _risk_findings(module_rows, duplicate_rows)

    return {
        "schema_version": "ratecon_candidate_model_ownership_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "module_count": len(module_rows),
        "import_edge_count": len(import_edges),
        "symbol_count": len(symbols),
        "candidate_shape_finding_count": len(shapes),
        "duplicate_constant_count": len(duplicate_rows),
        "risk_finding_count": len(risk_rows),
        "module_recommendation_counts": _count_by(
            module_rows, "canonical_owner_recommendation"
        ),
        "risk_counts": _count_by(module_rows, "risk"),
        "modules": module_rows,
        "import_edges": import_edges,
        "symbols": sorted(
            symbols, key=lambda row: (row["module_path"], row["symbol_type"], row["symbol_name"])
        ),
        "candidate_shape_findings": sorted(
            shapes, key=lambda row: (row["module_path"], row["shape_owner"])
        ),
        "duplicate_constants": duplicate_rows,
        "status_recommendations": status_rows,
        "risk_findings": risk_rows,
        "safety": {
            "static_ast_only": True,
            "project_modules_imported": False,
            "extraction_executed": False,
            "resolver_executed": False,
            "pdf_processing_attempted": False,
            "ocr_attempted": False,
            "local_outputs_read": False,
            "private_ratecons_read": False,
            "google_called": False,
            "model_or_cloud_called": False,
            "ignored_private_paths": list(IGNORED_RELATIVE_PREFIXES),
        },
        "recommendation": (
            "Use field_candidate_provenance.py as the canonical candidate "
            "contract for new document AI extraction candidates. Keep legacy "
            "RateCon candidate modules as compatibility surfaces until import "
            "graph and behavior-pinning tests support a separate cleanup."
        ),
    }


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
        "# RateCon Candidate Model Ownership Audit",
        "",
        "This report is generated by static AST/text analysis only. It does not import",
        "project modules, execute extraction or resolver code, process PDFs, run OCR,",
        "call Google, or call model/cloud services.",
        "",
        "## Summary",
        "",
        f"- module_count: {summary['module_count']}",
        f"- import_edge_count: {summary['import_edge_count']}",
        f"- symbol_count: {summary['symbol_count']}",
        f"- candidate_shape_finding_count: {summary['candidate_shape_finding_count']}",
        f"- duplicate_constant_count: {summary['duplicate_constant_count']}",
        f"- risk_finding_count: {summary['risk_finding_count']}",
        "",
        "## Module Recommendations",
        "",
    ]
    for row in summary["modules"]:
        lines.append(
            f"- `{row['module_path']}`: {row['canonical_owner_recommendation']} "
            f"({row['risk']} risk; {row['owner_layer']})"
        )
    lines.extend(["", "## Duplicate Candidate Constants", ""])
    if summary["duplicate_constants"]:
        for row in summary["duplicate_constants"]:
            lines.append(
                f"- {row['duplicate_type']} `{row['constant_name']}` "
                f"in {row['module_count']} modules ({row['category']})"
            )
    else:
        lines.append("- none detected")
    lines.extend(["", "## Status Recommendations", ""])
    for row in summary["status_recommendations"]:
        lines.append(
            f"- `{row['module_path']}`: {row['canonical_owner_recommendation']}. "
            f"{row['required_action']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Extraction and resolver code were not executed.",
            "- PDFs were not processed.",
            "- OCR was not executed.",
            "- `.local_outputs/` and `data/private_ratecons/` were not read.",
            "- No Google, AI/model, or cloud calls were made.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(summary: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_json": output_dir / "candidate_model_ownership_summary.json",
        "report_md": output_dir / "candidate_model_ownership_report.md",
        "modules_csv": output_dir / "candidate_modules.csv",
        "import_edges_csv": output_dir / "candidate_import_edges.csv",
        "symbols_csv": output_dir / "candidate_symbols.csv",
        "shape_findings_csv": output_dir / "candidate_shape_findings.csv",
        "duplicate_constants_csv": output_dir / "candidate_duplicate_constants.csv",
        "status_recommendations_csv": output_dir / "candidate_status_recommendations.csv",
        "risk_findings_csv": output_dir / "candidate_risk_findings.csv",
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
            "candidate_classes",
            "candidate_functions",
            "field_constants",
            "confidence_constants",
            "source_constants",
            "candidate_shape_summary",
            "canonical_owner_recommendation",
            "risk",
            "evidence",
            "has_forbidden_runtime_import",
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
        paths["symbols_csv"],
        summary["symbols"],
        ["module_path", "symbol_type", "symbol_name", "category", "value", "line"],
    )
    _write_csv(
        paths["shape_findings_csv"],
        summary["candidate_shape_findings"],
        ["module_path", "shape_owner", "shape_kind", "keys_or_fields", "evidence"],
    )
    _write_csv(
        paths["duplicate_constants_csv"],
        summary["duplicate_constants"],
        [
            "duplicate_type",
            "constant_name",
            "constant_value",
            "category",
            "modules",
            "module_count",
            "risk",
            "evidence",
        ],
    )
    _write_csv(
        paths["status_recommendations_csv"],
        summary["status_recommendations"],
        [
            "module_path",
            "canonical_owner_recommendation",
            "rationale",
            "required_action",
        ],
    )
    _write_csv(
        paths["risk_findings_csv"],
        summary["risk_findings"],
        ["module_path", "risk", "finding", "required_guardrail"],
    )
    return {key: _posix(path) for key, path in paths.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local-only static RateCon candidate model ownership audit."
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
        summary = analyze_candidate_model_ownership(repo_root)
        output_paths = write_outputs(summary, output_dir)
    except CandidateOwnershipAuditError as exc:
        print(f"Candidate ownership audit could not start. Reason: {exc}")
        return 2

    print("RateCon candidate model ownership audit")
    print(f"module_count: {summary['module_count']}")
    print(f"import_edge_count: {summary['import_edge_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
    print(f"candidate_shape_finding_count: {summary['candidate_shape_finding_count']}")
    print(f"duplicate_constant_count: {summary['duplicate_constant_count']}")
    print(f"risk_finding_count: {summary['risk_finding_count']}")
    print(f"recommendation: {summary['recommendation']}")
    print(f"output_dir: {_posix(output_dir)}")
    for label, path in output_paths.items():
        print(f"{label}: {path}")
    print("project_modules_imported: False")
    print("extraction_executed: False")
    print("resolver_executed: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("google_called: False")
    print("model_or_cloud_called: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
