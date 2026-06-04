"""Static RateCon rate/money safety ownership audit.

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


DEFAULT_OUTPUT_DIR = Path(".local_outputs/ratecon_rate_money_safety_ownership_audit")

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

KNOWN_RATE_MONEY_MODULES = {
    "app/document_ai/ratecon_rate_money_safety.py",
    "app/document_ai/ratecon_candidate_generators.py",
    "app/document_ai/field_candidate_generators.py",
    "app/document_ai/field_candidate_resolver.py",
    "app/document_ai/rate_candidate_forensics.py",
    "app/document_ai/rate_conflict_audit.py",
    "app/document_ai/rate_candidate_equivalence.py",
    "app/document_ai/ratecon_ocr_candidate_policy.py",
    "app/document_ai/ratecon_candidate_context_features.py",
    "scripts/evaluate_ratecon_against_gold.py",
    "scripts/run_private_ratecon_measurement.py",
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


class RateMoneySafetyOwnershipAuditError(ValueError):
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
        raise RateMoneySafetyOwnershipAuditError(f"repo root does not exist: {root}")
    if not root.is_dir():
        raise RateMoneySafetyOwnershipAuditError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise RateMoneySafetyOwnershipAuditError(
            "Output directory must be under .local_outputs."
        )
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


def _is_rate_money_source(source: SourceFile) -> bool:
    lower_path = source.rel_path.lower()
    lower_text = source.text.lower()
    if source.rel_path in KNOWN_RATE_MONEY_MODULES:
        return True
    if source.rel_path.startswith("tests/"):
        return any(
            term in lower_text
            for term in (
                "ratecon_rate_money",
                "rate_candidate_forensics",
                "rate_conflict_audit",
                "money_context",
                "total_carrier_rate",
            )
        )
    if not source.rel_path.startswith(("app/document_ai/", "scripts/")):
        return False
    return any(
        term in lower_text
        for term in (
            "rate_money",
            "money_context",
            "total_carrier_rate",
            "carrier pay",
            "total pay",
            "accessorial",
            "linehaul",
            "quickpay",
            "rate_safety",
            "rate_conflict",
            "rate_forensics",
        )
    )


def _classify_module(path: str) -> tuple[str, str, str, str]:
    if path == "app/document_ai/ratecon_rate_money_safety.py":
        return (
            "document_ai_rate_money_safety",
            "canonical_rate_money_safety",
            "low",
            "Intended canonical owner for money-context safety taxonomy.",
        )
    if path == "app/document_ai/ratecon_candidate_context_features.py":
        return (
            "document_ai_rate_money_context_features",
            "support_context_features",
            "medium",
            "Support context metadata; duplicated labels are compatibility debt.",
        )
    if path == "app/document_ai/field_candidate_generators.py":
        return (
            "document_ai_candidate_generation",
            "generator_consumer",
            "medium",
            "May emit rate candidates but should not own independent safety taxonomy.",
        )
    if path == "app/document_ai/ratecon_candidate_generators.py":
        return (
            "legacy_ratecon_candidate_generation",
            "compatibility",
            "medium",
            "Legacy generator surface with pinned rate/money labels.",
        )
    if path == "app/document_ai/field_candidate_resolver.py":
        return (
            "document_ai_candidate_resolution",
            "resolver_consumer",
            "medium",
            "Consumes rate/money safety metadata and owns ranking policy.",
        )
    if path == "app/document_ai/rate_candidate_forensics.py":
        return (
            "document_ai_rate_money_forensics",
            "forensics_consumer",
            "medium",
            "Reports diagnoses; should not own competing safety taxonomy.",
        )
    if path == "app/document_ai/rate_conflict_audit.py":
        return (
            "document_ai_rate_money_audit",
            "forensics_consumer",
            "medium",
            "Reports audit conflict reasons; should not own competing safety taxonomy.",
        )
    if path == "app/document_ai/rate_candidate_equivalence.py":
        return (
            "document_ai_rate_money_support_policy",
            "support_context_features",
            "medium",
            "Compares money candidates internally for safe summaries.",
        )
    if path == "app/document_ai/ratecon_ocr_candidate_policy.py":
        return (
            "document_ai_shadow_ocr_candidate_policy",
            "experimental_shadow",
            "medium",
            "Shadow OCR rate policy consumer; disabled/local-only context.",
        )
    if path.startswith("scripts/evaluate_ratecon_against_gold.py"):
        return (
            "local_only_evaluator",
            "evaluator_consumer",
            "medium",
            "Evaluator consumer of money context metadata.",
        )
    if path.startswith("scripts/"):
        return ("local_only_script", "manual_review_required", "low", "Local script reference.")
    if path.startswith("tests/"):
        return ("tests", "manual_review_required", "low", "Test reference only.")
    return (
        "rate_money_reference",
        "manual_review_required",
        "medium",
        "Rate/money reference needs manual ownership review.",
    )


def _symbol_category(name: str, value: str = "") -> str:
    upper = name.upper()
    lower_value = value.lower()
    if "MONEY_PATTERN" in upper or ("MONEY" in upper and ("REGEX" in upper or "PATTERN" in upper)):
        return "money_regex_constant"
    if "MONEY_CONTEXT" in upper:
        return "money_context_taxonomy"
    if "RATE_MONEY" in upper or "RATE_SELECTION" in upper or "RATE_SAFETY" in upper:
        return "rate_safety_status"
    if "STRONG_RATE_LABEL" in upper or "TOTAL_PAY" in upper or "CARRIER_PAY" in upper:
        return "strong_total_pay_label"
    if any(token in upper for token in ("ACCESSORIAL", "DETENTION", "LAYOVER", "LUMPER")):
        return "accessorial_label"
    if any(token in upper for token in ("NEGATIVE", "DEDUCTION", "PENALTY", "QUICKPAY", "FUEL_ADVANCE", "COMCHECK")):
        return "negative_label"
    if any(token in upper for token in ("COMPONENT", "LINEHAUL", "LINE_HAUL")):
        return "component_label"
    if any(token in upper for token in ("RANKING", "PENALTY", "PROFILE")):
        return "penalty_or_ranking_constant"
    if any(token in upper for token in ("RATE_CONFLICT", "RATE_CATEGORY", "RATE_SECTION", "RATE_FORENSICS", "RATE_AUDIT", "RATE_EQUIVALENT")):
        return "forensics_diagnosis_constant"
    if upper in {"FIELD_TOTAL_CARRIER_RATE", "FIELD_RATE", "FIELD_ACCESSORIAL_TERM"}:
        return "rate_field_constant"
    if any(
        token in lower_value
        for token in (
            "total_carrier_pay",
            "carrier_freight_pay",
            "linehaul",
            "accessorial",
            "quickpay",
            "money_context",
        )
    ):
        return "rate_money_value_constant"
    return "rate_money_constant"


def _is_rate_money_symbol_name(name: str, value: str = "") -> bool:
    upper = name.upper()
    lower = value.lower()
    name_markers = (
        "RATE",
        "MONEY",
        "TOTAL_PAY",
        "CARRIER_PAY",
        "ACCESSORIAL",
        "DETENTION",
        "LINEHAUL",
        "LINE_HAUL",
        "FUEL_ADVANCE",
        "QUICKPAY",
        "QUICK_PAY",
    )
    value_markers = (
        "money_context",
        "rate_safety",
        "total_carrier_pay",
        "carrier_freight_pay",
        "linehaul",
        "accessorial",
        "detention",
        "quickpay",
        "fuel_advance",
    )
    return any(marker in upper for marker in name_markers) or any(
        marker in lower for marker in value_markers
    )


def _collect_symbols(source: SourceFile) -> list[dict[str, str]]:
    if source.tree is None:
        return []
    rows: list[dict[str, str]] = []
    for node in ast.walk(source.tree):
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = _literal_or_name(node.value)
            for target in targets:
                if target.isupper() and _is_rate_money_symbol_name(target, value):
                    rows.append(
                        {
                            "module_path": source.rel_path,
                            "symbol_type": "constant",
                            "symbol_name": target,
                            "category": _symbol_category(target, value),
                            "value": value,
                            "line": str(getattr(node, "lineno", 0)),
                        }
                    )
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target = node.target.id
            value = _literal_or_name(node.value)
            if target.isupper() and _is_rate_money_symbol_name(target, value):
                rows.append(
                    {
                        "module_path": source.rel_path,
                        "symbol_type": "constant",
                        "symbol_name": target,
                        "category": _symbol_category(target, value),
                        "value": value,
                        "line": str(getattr(node, "lineno", 0)),
                    }
                )
        elif isinstance(node, ast.FunctionDef) and _is_rate_money_symbol_name(node.name):
            rows.append(
                {
                    "module_path": source.rel_path,
                    "symbol_type": "function",
                    "symbol_name": node.name,
                    "category": "rate_money_function",
                    "value": "",
                    "line": str(getattr(node, "lineno", 0)),
                }
            )
    return rows


def _forbidden_import(source: SourceFile, imports: list[ImportEdge]) -> str:
    findings = []
    for edge in imports:
        if edge.importer_path != source.rel_path:
            continue
        for prefix in FORBIDDEN_RUNTIME_IMPORT_PREFIXES:
            if edge.imported_module == prefix or edge.imported_module.startswith(prefix + "."):
                findings.append(f"{edge.imported_module} at line {edge.line}")
    return "; ".join(findings)


def _build_module_rows(
    sources: list[SourceFile],
    imports: list[ImportEdge],
    symbols: list[dict[str, str]],
) -> list[dict[str, str]]:
    rate_money_sources = [source for source in sources if _is_rate_money_source(source)]
    rows: list[dict[str, str]] = []
    for source in rate_money_sources:
        owner_layer, recommendation, risk, evidence = _classify_module(source.rel_path)
        importers = sorted(
            {
                edge.importer_path
                for edge in imports
                if edge.imported_path == source.rel_path
                and edge.importer_path != source.rel_path
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
        forbidden = _forbidden_import(source, imports)
        rows.append(
            {
                "module_path": source.rel_path,
                "module_name": source.module_name,
                "owner_layer": owner_layer,
                "importers": ";".join(importers),
                "imported_dependencies": ";".join(imported_dependencies),
                "money_regex_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "money_regex_constant"
                ),
                "rate_label_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"]
                    in {
                        "strong_total_pay_label",
                        "accessorial_label",
                        "negative_label",
                        "component_label",
                    }
                ),
                "money_context_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "money_context_taxonomy"
                ),
                "rate_safety_status_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "rate_safety_status"
                ),
                "forensics_diagnosis_constants": ";".join(
                    row["symbol_name"]
                    for row in module_symbols
                    if row["category"] == "forensics_diagnosis_constant"
                ),
                "canonical_owner_recommendation": recommendation,
                "risk": "high" if forbidden else risk,
                "evidence": evidence if not forbidden else f"forbidden import: {forbidden}",
                "has_forbidden_runtime_import": str(bool(forbidden)),
            }
        )
    return sorted(rows, key=lambda row: row["module_path"])


def _duplicate_constant_rows(symbols: list[dict[str, str]]) -> list[dict[str, str]]:
    constants = [row for row in symbols if row["symbol_type"] == "constant"]
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
                "evidence": "same rate/money constant name appears in multiple modules",
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
                "evidence": "same rate/money constant value appears in multiple modules",
            }
        )
    return sorted(duplicates, key=lambda row: (row["risk"], row["duplicate_type"], row["constant_name"]))


def _status_recommendations(module_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in module_rows:
        recommendation = row["canonical_owner_recommendation"]
        if recommendation == "canonical_rate_money_safety":
            action = "Treat as the canonical owner for money-context safety taxonomy."
        elif recommendation == "generator_consumer":
            action = "May emit candidates; use canonical/support owners for safety taxonomy changes."
        elif recommendation == "resolver_consumer":
            action = "Consume safety metadata; do not grow independent rate label taxonomy."
        elif recommendation == "forensics_consumer":
            action = "Report diagnoses; do not define competing total-vs-accessorial rules."
        elif recommendation == "support_context_features":
            action = "Keep support constants pinned until a future behavior-preserving consolidation."
        elif recommendation == "evaluator_consumer":
            action = "Use rate/money metadata for evaluation only; do not make runtime policy."
        elif recommendation == "compatibility":
            action = "Keep compatibility behavior stable and pinned."
        elif recommendation == "experimental_shadow":
            action = "Keep shadow/local-only and disabled by default."
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
                    "finding": row["evidence"],
                    "required_guardrail": (
                        "Do not consolidate or change rate/money behavior without behavior-pinning tests."
                    ),
                }
            )
    for row in duplicate_rows:
        findings.append(
            {
                "module_path": row["modules"],
                "risk": row["risk"],
                "finding": f"Duplicate {row['category']} {row['constant_name']}",
                "required_guardrail": "Keep duplicate constants pinned until a narrow consolidation PR.",
            }
        )
    return sorted(findings, key=lambda row: (row["risk"], row["module_path"], row["finding"]))


def _count_by(rows: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(key, "") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def analyze_rate_money_safety_ownership(repo_root: Path) -> dict[str, object]:
    sources = _discover_python_sources(repo_root)
    imports = _iter_import_edges(sources)
    symbols: list[dict[str, str]] = []
    for source in sources:
        if _is_rate_money_source(source):
            symbols.extend(_collect_symbols(source))

    module_rows = _build_module_rows(sources, imports, symbols)
    rate_money_paths = {row["module_path"] for row in module_rows}
    import_edges = [
        edge.__dict__
        for edge in imports
        if edge.importer_path in rate_money_paths
        or edge.imported_path in rate_money_paths
        or "rate_money" in edge.imported_module.lower()
        or "rate_candidate" in edge.imported_module.lower()
        or "rate_conflict" in edge.imported_module.lower()
    ]
    duplicate_rows = _duplicate_constant_rows(symbols)
    status_rows = _status_recommendations(module_rows)
    risk_rows = _risk_findings(module_rows, duplicate_rows)

    return {
        "schema_version": "ratecon_rate_money_safety_ownership_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "module_count": len(module_rows),
        "import_edge_count": len(import_edges),
        "symbol_count": len(symbols),
        "duplicate_constant_count": len(duplicate_rows),
        "risk_finding_count": len(risk_rows),
        "module_recommendation_counts": _count_by(
            module_rows, "canonical_owner_recommendation"
        ),
        "risk_counts": _count_by(module_rows, "risk"),
        "duplicate_category_counts": _count_by(duplicate_rows, "category"),
        "modules": module_rows,
        "import_edges": import_edges,
        "symbols": sorted(
            symbols,
            key=lambda row: (row["module_path"], row["symbol_type"], row["symbol_name"]),
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
            "Treat ratecon_rate_money_safety.py as the intended canonical owner "
            "for money-context safety taxonomy. Keep duplicate labels and "
            "diagnostic constants pinned until a future behavior-preserving "
            "consolidation PR proves selected rate outputs and metrics are unchanged."
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
        "# RateCon Rate/Money Safety Ownership Audit",
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
    lines.extend(["", "## Duplicate Rate/Money Constants", ""])
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
        "summary_json": output_dir / "rate_money_safety_ownership_summary.json",
        "report_md": output_dir / "rate_money_safety_ownership_report.md",
        "modules_csv": output_dir / "rate_money_modules.csv",
        "import_edges_csv": output_dir / "rate_money_import_edges.csv",
        "symbols_csv": output_dir / "rate_money_symbols.csv",
        "duplicate_constants_csv": output_dir / "rate_money_duplicate_constants.csv",
        "status_recommendations_csv": output_dir / "rate_money_status_recommendations.csv",
        "risk_findings_csv": output_dir / "rate_money_risk_findings.csv",
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
            "money_regex_constants",
            "rate_label_constants",
            "money_context_constants",
            "rate_safety_status_constants",
            "forensics_diagnosis_constants",
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
        description="Run a local-only static RateCon rate/money safety ownership audit."
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
        summary = analyze_rate_money_safety_ownership(repo_root)
        output_paths = write_outputs(summary, output_dir)
    except RateMoneySafetyOwnershipAuditError as exc:
        print(f"Rate/money safety ownership audit could not start. Reason: {exc}")
        return 2

    print("RateCon rate/money safety ownership audit")
    print(f"module_count: {summary['module_count']}")
    print(f"import_edge_count: {summary['import_edge_count']}")
    print(f"symbol_count: {summary['symbol_count']}")
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
