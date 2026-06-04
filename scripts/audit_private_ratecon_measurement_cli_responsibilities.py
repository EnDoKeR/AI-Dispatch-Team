"""Static responsibility audit for the private RateCon measurement CLI.

This tool is intentionally local-only. It parses Python source with ``ast`` and
never imports project modules, executes measurement code, processes PDFs, calls
OCR, calls Google, or calls model/cloud services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_TARGET_SCRIPT = Path("scripts/run_private_ratecon_measurement.py")
DEFAULT_OUTPUT_DIR = Path(
    ".local_outputs/private_ratecon_measurement_cli_responsibility_audit"
)

DELEGATED_MODULES = {
    "args/config/safety": (
        "app.document_ai.measurement_cli.ratecon_private_args",
        "app.document_ai.measurement_cli.ratecon_private_config",
        "app.document_ai.measurement_cli.ratecon_private_safety",
    ),
    "output paths": (
        "app.document_ai.measurement_cli.ratecon_private_output_paths",
    ),
    "report writers": (
        "app.document_ai.measurement_cli.ratecon_private_report_writers",
    ),
    "review exports": (
        "app.document_ai.measurement_cli.ratecon_private_review_exports",
    ),
    "audit orchestration": (
        "app.document_ai.measurement_cli.ratecon_private_audit_orchestration",
    ),
    "review workbook": (
        "app.document_ai.measurement_cli.ratecon_private_review_workbook",
    ),
    "Google sync": (
        "app.document_ai.measurement_cli.ratecon_private_google_sync",
    ),
}

DIRECT_CALL_CATEGORIES = {
    "discover_private_pdfs": "PDF discovery / input selection",
    "build_safe_aliases": "PDF discovery / input selection",
    "measure_private_ratecon_pdf": "private measurement call",
    "build_private_ratecon_measurement_aggregate": "measurement aggregation",
    "build_safe_measurement_output_policy": "safe output policy construction",
    "BrokerTemplateRegistry.from_directory": "template registry loading",
    "BrokerTemplateRegistry.from_directories": "template registry loading",
    "compare_pdfplumber_table_profiles": "layout/table profile comparison hook",
    "write_ratecon_review_export": "remaining direct review/export call",
    "write_private_ratecon_safe_outputs": "delegated report writer call",
    "write_private_ratecon_review_packet_exports": "delegated review export call",
    "write_private_ratecon_review_workbook_if_enabled": "delegated review workbook call",
    "run_private_ratecon_audit_exports": "delegated audit orchestration call",
    "run_private_ratecon_google_sync_if_enabled": "delegated Google sync call",
    "build_private_ratecon_output_paths": "delegated output path call",
    "parse_private_ratecon_measurement_args": "delegated args call",
    "build_private_ratecon_measurement_config": "delegated config call",
    "validate_private_ratecon_measurement_config": "delegated safety call",
    "Path": "private/local path construction",
    "print": "console summary formatting",
}

RESPONSIBILITY_PATTERNS = {
    "measurement pipeline sequencing": (
        "build_private_ratecon_measurement_report",
        "measure_private_ratecon_pdf",
    ),
    "PDF discovery / input selection": (
        "discover_private_pdfs",
        "build_safe_aliases",
    ),
    "private measurement call": (
        "measure_private_ratecon_pdf",
    ),
    "template registry loading": (
        "_load_registry",
        "BrokerTemplateRegistry",
    ),
    "layout/table profile comparison hook": (
        "compare_pdfplumber_table_profiles",
        "PDFPLUMBER_TABLE_SETTING_PROFILES",
    ),
    "console summary formatting": (
        "format_private_measurement_report",
        "SAFETY_BANNER",
        "print(",
    ),
    "top-level sequencing/error handling": (
        "def main",
        "try:",
        "except ",
        "return 2",
    ),
    "remaining output/report logic if any": (
        "write_ratecon_review_export",
        "write_private_ratecon_safe_outputs",
    ),
    "remaining audit logic if any": (
        "run_private_ratecon_audit_exports",
    ),
    "remaining Google/workbook logic if any": (
        "run_private_ratecon_google_sync_if_enabled",
        "write_private_ratecon_review_workbook_if_enabled",
    ),
    "remaining private path construction": (
        "REPO_ROOT",
        "Path(",
        "output_dir",
    ),
}

FUNCTION_CATEGORY_BY_NAME = {
    "_safe_output_file_labels": "output label helper",
    "_print_expected_error": "top-level error handling",
    "_print_expected_config_error": "top-level error handling",
    "_load_registry": "template registry loading",
    "build_private_ratecon_measurement_report": "measurement pipeline sequencing",
    "format_private_measurement_report": "console summary formatting",
    "main": "top-level sequencing/error handling",
}

HIGH_LEVEL_IMPORT_PREFIXES = (
    "app.document_ai.",
    "app.integrations.",
)

IGNORED_PREFIXES = (
    ".local_outputs",
    "data/private_ratecons",
)


class ResponsibilityAuditError(ValueError):
    """Raised for safe user-facing audit failures."""


@dataclass(frozen=True)
class ImportRecord:
    line: int
    module: str
    name: str
    category: str


@dataclass(frozen=True)
class CallRecord:
    line: int
    call_name: str
    category: str


@dataclass(frozen=True)
class SectionRecord:
    name: str
    category: str
    start_line: int
    end_line: int
    line_count: int


def _posix(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _is_within(path: Path, parent: Path) -> bool:
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def _resolve_repo_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.exists():
        raise ResponsibilityAuditError(f"repo root does not exist: {root}")
    if not root.is_dir():
        raise ResponsibilityAuditError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise ResponsibilityAuditError("Output directory must be under .local_outputs.")
    return output_dir


def _read_target_script(repo_root: Path, target_script: Path = DEFAULT_TARGET_SCRIPT) -> tuple[Path, str]:
    path = (repo_root / target_script).resolve()
    if not _is_within(path, repo_root):
        raise ResponsibilityAuditError("Target script must be inside the repository root.")
    rel = _posix(path.relative_to(repo_root))
    if any(rel == prefix or rel.startswith(prefix + "/") for prefix in IGNORED_PREFIXES):
        raise ResponsibilityAuditError("Target script cannot be under ignored private/local paths.")
    if not path.exists():
        raise ResponsibilityAuditError(f"target script not found: {target_script}")
    if not path.is_file():
        raise ResponsibilityAuditError(f"target script is not a file: {target_script}")
    return path, path.read_text(encoding="utf-8-sig")


def _import_records(tree: ast.AST) -> list[ImportRecord]:
    records: list[ImportRecord] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                records.append(
                    ImportRecord(
                        line=node.lineno,
                        module=module,
                        name=alias.asname or alias.name,
                        category=_import_category(module),
                    )
                )
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            for alias in node.names:
                records.append(
                    ImportRecord(
                        line=node.lineno,
                        module=module,
                        name=alias.name,
                        category=_import_category(module),
                    )
                )
    return sorted(records, key=lambda record: (record.line, record.module, record.name))


def _import_category(module: str) -> str:
    if module.startswith("app.document_ai.measurement_cli."):
        return "delegated measurement_cli"
    if any(module.startswith(prefix) for prefix in HIGH_LEVEL_IMPORT_PREFIXES):
        return "direct high-level import"
    if module in {"sys", "pathlib"}:
        return "standard library"
    return "other"


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _short_call_name(name: str) -> str:
    if name in DIRECT_CALL_CATEGORIES:
        return name
    tail = name.rsplit(".", 1)[-1]
    if tail in DIRECT_CALL_CATEGORIES:
        return tail
    return name


def _call_records(tree: ast.AST) -> list[CallRecord]:
    records: list[CallRecord] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        full_name = _call_name(node.func)
        if not full_name:
            continue
        name = _short_call_name(full_name)
        category = DIRECT_CALL_CATEGORIES.get(name)
        if not category and full_name in DIRECT_CALL_CATEGORIES:
            name = full_name
            category = DIRECT_CALL_CATEGORIES[full_name]
        if category:
            records.append(CallRecord(line=node.lineno, call_name=name, category=category))
    return sorted(records, key=lambda record: (record.line, record.call_name))


def _section_records(tree: ast.Module) -> list[SectionRecord]:
    sections: list[SectionRecord] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno)
            sections.append(
                SectionRecord(
                    name=node.name,
                    category=FUNCTION_CATEGORY_BY_NAME.get(node.name, "uncategorized helper"),
                    start_line=node.lineno,
                    end_line=end_line,
                    line_count=max(1, end_line - node.lineno + 1),
                )
            )
    return sections


def _delegated_modules(imports: list[ImportRecord]) -> list[dict[str, str]]:
    modules_by_layer = []
    imported_modules = {record.module for record in imports}
    for layer, modules in DELEGATED_MODULES.items():
        present = [module for module in modules if module in imported_modules]
        modules_by_layer.append(
            {
                "layer": layer,
                "status": "present" if present else "missing",
                "modules": ", ".join(present),
            }
        )
    return modules_by_layer


def _todo_fixme_count(lines: list[str]) -> int:
    pattern = re.compile(r"\b(TODO|FIXME)\b", re.IGNORECASE)
    return sum(1 for line in lines if pattern.search(line))


def _cli_entrypoint_present(tree: ast.Module) -> bool:
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        left = getattr(node.test, "left", None)
        comparators = getattr(node.test, "comparators", [])
        if isinstance(left, ast.Name) and left.id == "__name__":
            if any(isinstance(comp, ast.Constant) and comp.value == "__main__" for comp in comparators):
                return True
    return False


def _responsibility_rows(text: str, calls: list[CallRecord]) -> list[dict[str, object]]:
    rows = []
    for category, patterns in RESPONSIBILITY_PATTERNS.items():
        matched_patterns = [pattern for pattern in patterns if pattern in text]
        call_count = sum(1 for call in calls if call.category == category)
        rows.append(
            {
                "category": category,
                "status": "present" if matched_patterns or call_count else "not_detected",
                "evidence_count": len(matched_patterns) + call_count,
                "patterns": ", ".join(matched_patterns),
            }
        )
    return rows


def _recommendations(responsibilities: list[dict[str, object]]) -> list[dict[str, str]]:
    present = {
        str(row["category"])
        for row in responsibilities
        if row.get("status") == "present"
    }
    rows = [
        {
            "priority": "1",
            "recommendation": "Pause behavior splits until the audit is reviewed.",
            "rationale": "The CLI already delegates several helper layers; further movement should be justified by measured remaining responsibility.",
            "next_step": "Review this report before opening another split PR.",
        }
    ]
    if "PDF discovery / input selection" in present:
        rows.append(
            {
                "priority": "2",
                "recommendation": "Consider a separate PDF discovery/input-selection split only if ownership remains unclear.",
                "rationale": "Input selection is still visible in the public CLI orchestration path.",
                "next_step": "Keep behavior unchanged and add fixture-only tests before moving it.",
            }
        )
    if "console summary formatting" in present:
        rows.append(
            {
                "priority": "3",
                "recommendation": "Consider splitting console summary formatting before splitting measurement sequencing.",
                "rationale": "Formatting is easier to isolate than core measurement orchestration and can preserve output text with focused tests.",
                "next_step": "Snapshot existing safe console output before any formatting move.",
            }
        )
    rows.append(
        {
            "priority": "4",
            "recommendation": "Leave measurement sequencing in the public CLI wrapper unless a stronger boundary is proven.",
            "rationale": "Measurement sequencing coordinates private PDF discovery, registry loading, policy construction, and existing measurement calls.",
            "next_step": "Treat sequencing movement as a separate reviewed PR, not a cleanup default.",
        }
    )
    return rows


def analyze_responsibilities(repo_root: Path) -> dict[str, object]:
    target_path, text = _read_target_script(repo_root)
    lines = text.splitlines()
    tree = ast.parse(text, filename=str(target_path))
    imports = _import_records(tree)
    calls = _call_records(tree)
    sections = _section_records(tree)
    delegated = _delegated_modules(imports)
    responsibilities = _responsibility_rows(text, calls)
    high_level_imports = [
        record for record in imports if record.category == "direct high-level import"
    ]
    remaining_calls = [
        call for call in calls if not call.category.startswith("delegated ")
    ]
    remaining_categories = sorted({call.category for call in remaining_calls})
    main_present = any(section.name == "main" for section in sections)
    recommendations = _recommendations(responsibilities)

    return {
        "schema_version": "private_ratecon_measurement_cli_responsibility_audit_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_script": _posix(target_path.relative_to(repo_root)),
        "line_count": len(lines),
        "function_count": len(sections),
        "top_level_statement_count": len(tree.body),
        "import_count": len(imports),
        "cli_entrypoint_present": _cli_entrypoint_present(tree),
        "main_function_present": main_present,
        "todo_fixme_count": _todo_fixme_count(lines),
        "direct_high_level_import_count": len(high_level_imports),
        "remaining_direct_call_count": len(remaining_calls),
        "remaining_direct_call_categories": remaining_categories,
        "delegated_modules": delegated,
        "remaining_responsibilities": responsibilities,
        "sections": [section.__dict__ for section in sections],
        "remaining_imports": [record.__dict__ for record in imports],
        "remaining_direct_calls": [record.__dict__ for record in calls],
        "recommendations": recommendations,
        "safety": {
            "static_ast_only": True,
            "project_modules_imported": False,
            "measurement_executed": False,
            "pdf_processing_attempted": False,
            "ocr_attempted": False,
            "google_called": False,
            "model_or_cloud_called": False,
            "ignored_private_paths": list(IGNORED_PREFIXES),
        },
        "recommendation": recommendations[0]["recommendation"],
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
    delegated = summary["delegated_modules"]
    responsibilities = summary["remaining_responsibilities"]
    direct_categories = summary["remaining_direct_call_categories"]
    recommendations = summary["recommendations"]
    lines = [
        "# Private RateCon Measurement CLI Responsibility Audit",
        "",
        "This report is generated by static AST/text analysis only. It does not import",
        "project modules, run measurement, process PDFs, call OCR, call Google, or call",
        "model/cloud services.",
        "",
        "## Summary",
        "",
        f"- target_script: `{summary['target_script']}`",
        f"- line_count: {summary['line_count']}",
        f"- function_count: {summary['function_count']}",
        f"- top_level_statement_count: {summary['top_level_statement_count']}",
        f"- import_count: {summary['import_count']}",
        f"- cli_entrypoint_present: {summary['cli_entrypoint_present']}",
        f"- todo_fixme_count: {summary['todo_fixme_count']}",
        f"- direct_high_level_import_count: {summary['direct_high_level_import_count']}",
        f"- remaining_direct_call_count: {summary['remaining_direct_call_count']}",
        "",
        "## Delegated Modules",
        "",
    ]
    for row in delegated:
        lines.append(f"- {row['layer']}: {row['status']} {row['modules']}".rstrip())
    lines.extend(["", "## Remaining Responsibility Signals", ""])
    for row in responsibilities:
        lines.append(
            f"- {row['category']}: {row['status']} "
            f"(evidence_count={row['evidence_count']})"
        )
    lines.extend(["", "## Remaining Direct Call Categories", ""])
    if direct_categories:
        lines.extend(f"- {category}" for category in direct_categories)
    else:
        lines.append("- none detected")
    lines.extend(["", "## Recommendations", ""])
    for row in recommendations:
        lines.append(
            f"- P{row['priority']} {row['recommendation']} "
            f"Next: {row['next_step']}"
        )
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- No private PDF, raw text, gold label, local output, Google credential,",
            "  token, model output, OCR artifact, or benchmark output is read or written",
            "  by this audit except for the generated local-only report files.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(summary: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "summary_json": output_dir / "measurement_cli_responsibility_summary.json",
        "report_md": output_dir / "measurement_cli_responsibility_report.md",
        "sections_csv": output_dir / "measurement_cli_responsibility_sections.csv",
        "imports_csv": output_dir / "measurement_cli_remaining_imports.csv",
        "direct_calls_csv": output_dir / "measurement_cli_remaining_direct_calls.csv",
        "recommendations_csv": output_dir / "measurement_cli_recommendations.csv",
    }
    _write_json(paths["summary_json"], summary)
    _write_report(paths["report_md"], summary)
    _write_csv(
        paths["sections_csv"],
        summary["sections"],
        ["name", "category", "start_line", "end_line", "line_count"],
    )
    _write_csv(
        paths["imports_csv"],
        summary["remaining_imports"],
        ["line", "module", "name", "category"],
    )
    _write_csv(
        paths["direct_calls_csv"],
        summary["remaining_direct_calls"],
        ["line", "call_name", "category"],
    )
    _write_csv(
        paths["recommendations_csv"],
        summary["recommendations"],
        ["priority", "recommendation", "rationale", "next_step"],
    )
    return {key: _posix(path) for key, path in paths.items()}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a local-only static responsibility audit for "
            "scripts/run_private_ratecon_measurement.py."
        )
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
        summary = analyze_responsibilities(repo_root)
        output_paths = write_outputs(summary, output_dir)
    except ResponsibilityAuditError as exc:
        print(f"Responsibility audit could not start. Reason: {exc}")
        return 2

    print("Private RateCon measurement CLI responsibility audit")
    print(f"target_script: {summary['target_script']}")
    print(f"line_count: {summary['line_count']}")
    print(f"import_count: {summary['import_count']}")
    print(
        "delegated_modules: "
        + ", ".join(
            row["layer"] for row in summary["delegated_modules"] if row["status"] == "present"
        )
    )
    print(
        "remaining_direct_call_categories: "
        + ", ".join(summary["remaining_direct_call_categories"])
    )
    print(f"recommendation: {summary['recommendation']}")
    print(f"output_dir: {_posix(output_dir)}")
    for label, path in output_paths.items():
        print(f"{label}: {path}")
    print("no_private_values_read_or_written: True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
