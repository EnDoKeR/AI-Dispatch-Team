"""Static module inventory and import graph analyzer.

This tool is intentionally local-only. It parses Python source with ``ast`` and
never imports project modules, executes app code, processes PDFs, calls OCR, or
uses network/model services.
"""

from __future__ import annotations

import argparse
import ast
import csv
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path


ALLOWED_STATUSES = {
    "active",
    "local_only",
    "test_only",
    "compatibility",
    "deprecated",
    "experimental",
}

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

EXCLUDED_RELATIVE_PREFIXES = (
    ".local_outputs",
    ".local_private",
    "data/private_ratecons",
    "data/ratecons",
)

DEFAULT_OUTPUT_DIR = Path(".local_outputs/module_graph")


class ModuleGraphError(ValueError):
    """Raised for safe, user-facing analyzer failures."""


@dataclass(frozen=True)
class ModuleMapEntry:
    module_path: str
    package_area: str
    owner_layer: str
    status: str
    entrypoints: str
    imported_by_summary: str
    imports_summary: str
    remove_after: str
    notes: str

    @property
    def is_pattern(self) -> bool:
        return any(char in self.module_path for char in "*?[")


@dataclass(frozen=True)
class ModuleRecord:
    module_path: str
    module_name: str
    package_area: str
    status: str
    entrypoint: bool
    parse_error: str = ""


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


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _is_within(path: Path, parent: Path) -> bool:
    path = path.resolve()
    parent = parent.resolve()
    return path == parent or parent in path.parents


def _resolve_repo_root(value: str) -> Path:
    root = Path(value).resolve()
    if not root.exists():
        raise ModuleGraphError(f"repo root does not exist: {root}")
    if not root.is_dir():
        raise ModuleGraphError(f"repo root is not a directory: {root}")
    return root


def _resolve_output_dir(repo_root: Path, value: str | None) -> Path:
    raw = Path(value) if value else DEFAULT_OUTPUT_DIR
    output_dir = raw if raw.is_absolute() else repo_root / raw
    output_dir = output_dir.resolve()
    local_outputs = (repo_root / ".local_outputs").resolve()
    if not _is_within(output_dir, local_outputs):
        raise ModuleGraphError("Output directory must be under .local_outputs.")
    return output_dir


def _should_skip_path(repo_root: Path, path: Path, include_tests: bool, include_docs: bool) -> bool:
    rel = _posix(path.relative_to(repo_root))
    rel_parts = Path(rel).parts
    if any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
        return True
    if any(rel == prefix or rel.startswith(prefix + "/") for prefix in EXCLUDED_RELATIVE_PREFIXES):
        return True
    if not include_tests and (rel == "tests" or rel.startswith("tests/")):
        return True
    if not include_docs and (rel == "docs" or rel.startswith("docs/")):
        return True
    return False


def _module_name_from_path(rel_path: str) -> str:
    path = Path(rel_path)
    without_suffix = path.with_suffix("")
    parts = list(without_suffix.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _module_package(module_name: str, rel_path: str) -> str:
    if rel_path.endswith("__init__.py"):
        return module_name
    parts = module_name.split(".")
    return ".".join(parts[:-1])


def discover_python_modules(
    repo_root: Path,
    include_tests: bool = False,
    include_docs: bool = False,
) -> list[tuple[str, str, Path]]:
    modules = []
    for path in sorted(repo_root.rglob("*.py")):
        if _should_skip_path(repo_root, path, include_tests=include_tests, include_docs=include_docs):
            continue
        rel_path = _posix(path.relative_to(repo_root))
        module_name = _module_name_from_path(rel_path)
        if module_name:
            modules.append((rel_path, module_name, path))
    return modules


def _split_markdown_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [cell.strip().strip("`") for cell in line.split("|")]


def load_module_map(repo_root: Path) -> tuple[list[ModuleMapEntry], list[str]]:
    path = repo_root / "docs" / "MODULE_MAP.md"
    if not path.exists():
        return [], ["docs/MODULE_MAP.md not found"]

    lines = _read_text(path).splitlines()
    header = None
    entries: list[ModuleMapEntry] = []
    warnings: list[str] = []
    required = [
        "module_path",
        "package_area",
        "owner_layer",
        "status",
        "entrypoints",
        "imported_by_summary",
        "imports_summary",
        "remove_after",
        "notes",
    ]
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = _split_markdown_row(line)
        normalized = [cell.lower().replace(" ", "_") for cell in cells]
        if header is None and "module_path" in normalized and "status" in normalized:
            header = normalized
            continue
        if header is None:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        row = dict(zip(header, cells))
        if not row.get("module_path"):
            continue
        missing = [key for key in required if key not in row]
        if missing:
            warnings.append(f"MODULE_MAP row missing columns {missing}: {row.get('module_path')}")
            continue
        status = row.get("status", "").strip()
        if status not in ALLOWED_STATUSES:
            warnings.append(f"MODULE_MAP row has invalid status {status!r}: {row.get('module_path')}")
        entries.append(
            ModuleMapEntry(
                module_path=row["module_path"].strip(),
                package_area=row["package_area"].strip(),
                owner_layer=row["owner_layer"].strip(),
                status=status,
                entrypoints=row["entrypoints"].strip(),
                imported_by_summary=row["imported_by_summary"].strip(),
                imports_summary=row["imports_summary"].strip(),
                remove_after=row["remove_after"].strip(),
                notes=row["notes"].strip(),
            )
        )
    return entries, warnings


def _matching_entry(path: str, entries: list[ModuleMapEntry]) -> ModuleMapEntry | None:
    for entry in entries:
        if not entry.is_pattern and entry.module_path == path:
            return entry
    for entry in entries:
        if entry.is_pattern and fnmatch.fnmatch(path, entry.module_path):
            return entry
    return None


def _package_area(rel_path: str) -> str:
    if rel_path == "main.py":
        return "root"
    if rel_path.startswith("app/document_ai/"):
        return "document_ai"
    if rel_path.startswith("app/market_intelligence/"):
        return "market_intelligence"
    if rel_path.startswith("app/integrations/"):
        return "integrations"
    if rel_path.startswith("scripts/"):
        return "scripts"
    if rel_path.startswith("tests/"):
        return "tests"
    return rel_path.split("/", 1)[0]


def _has_main_guard(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not isinstance(test, ast.Compare):
            continue
        left = test.left
        if not (
            isinstance(left, ast.Name)
            and left.id == "__name__"
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
        ):
            continue
        comparator = test.comparators[0]
        if isinstance(comparator, ast.Constant) and comparator.value == "__main__":
            return True
    return False


def parse_module_tree(path: Path) -> tuple[ast.AST | None, str]:
    try:
        return ast.parse(_read_text(path), filename=str(path)), ""
    except SyntaxError as exc:
        return None, f"{exc.__class__.__name__}: {exc.msg}"


def build_module_records(
    discovered: list[tuple[str, str, Path]],
    module_map_entries: list[ModuleMapEntry],
) -> tuple[list[ModuleRecord], dict[str, ast.AST], dict[str, str]]:
    records: list[ModuleRecord] = []
    trees: dict[str, ast.AST] = {}
    parse_errors: dict[str, str] = {}
    for rel_path, module_name, path in discovered:
        tree, parse_error = parse_module_tree(path)
        entry = _matching_entry(rel_path, module_map_entries)
        status = entry.status if entry else ""
        package_area = entry.package_area if entry else _package_area(rel_path)
        entrypoint = rel_path == "main.py" or bool(tree and _has_main_guard(tree))
        records.append(
            ModuleRecord(
                module_path=rel_path,
                module_name=module_name,
                package_area=package_area,
                status=status,
                entrypoint=entrypoint,
                parse_error=parse_error,
            )
        )
        if tree is not None:
            trees[rel_path] = tree
        if parse_error:
            parse_errors[rel_path] = parse_error
    return records, trees, parse_errors


def _resolve_absolute_import(base: str, alias: str, known_modules: set[str]) -> str:
    if alias == "*":
        return base
    child = f"{base}.{alias}" if base else alias
    if child in known_modules:
        return child
    if base in known_modules:
        return base
    return child


def _resolve_relative_base(module_name: str, rel_path: str, level: int, module: str | None) -> str:
    package = _module_package(module_name, rel_path)
    parts = package.split(".") if package else []
    if level > 1:
        parts = parts[: -(level - 1)] if level - 1 <= len(parts) else []
    if module:
        parts.extend(module.split("."))
    return ".".join(part for part in parts if part)


def extract_import_edges(
    records: list[ModuleRecord],
    trees: dict[str, ast.AST],
) -> list[ImportEdge]:
    by_path = {record.module_path: record for record in records}
    known_modules = {record.module_name for record in records}
    module_to_path = {record.module_name: record.module_path for record in records}
    edges: list[ImportEdge] = []

    for rel_path, tree in trees.items():
        record = by_path[rel_path]
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported = alias.name
                    imported_path = module_to_path.get(imported, "")
                    edges.append(
                        ImportEdge(
                            importer_path=rel_path,
                            importer_module=record.module_name,
                            imported_module=imported,
                            imported_path=imported_path,
                            is_internal=bool(imported_path),
                            line=node.lineno,
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = _resolve_relative_base(
                        record.module_name,
                        rel_path,
                        node.level,
                        node.module,
                    )
                else:
                    base = node.module or ""
                for alias in node.names:
                    imported = _resolve_absolute_import(base, alias.name, known_modules)
                    imported_path = module_to_path.get(imported, "")
                    edges.append(
                        ImportEdge(
                            importer_path=rel_path,
                            importer_module=record.module_name,
                            imported_module=imported,
                            imported_path=imported_path,
                            is_internal=bool(imported_path),
                            line=node.lineno,
                        )
                    )
    return edges


def _index_edges(edges: list[ImportEdge]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    imports: dict[str, set[str]] = {}
    imported_by: dict[str, set[str]] = {}
    for edge in edges:
        if not edge.is_internal:
            continue
        imports.setdefault(edge.importer_path, set()).add(edge.imported_path)
        imported_by.setdefault(edge.imported_path, set()).add(edge.importer_path)
    return imports, imported_by


def _is_test_path(path: str) -> bool:
    return path.startswith("tests/")


def _is_script_path(path: str) -> bool:
    return path.startswith("scripts/")


def _orphan_candidates(records, imports_by_path, imported_by_path):
    rows = []
    for record in records:
        if record.entrypoint or _is_test_path(record.module_path) or record.module_path.endswith("__init__.py"):
            continue
        if not imported_by_path.get(record.module_path) and not imports_by_path.get(record.module_path):
            rows.append(record)
    return rows


def _script_only_modules(records, imported_by_path):
    rows = []
    for record in records:
        if not _is_script_path(record.module_path):
            continue
        importers = imported_by_path.get(record.module_path, set())
        non_script_importers = [path for path in importers if not _is_script_path(path)]
        if not non_script_importers:
            rows.append(record)
    return rows


def _test_only_modules(records, imported_by_path):
    rows = []
    for record in records:
        importers = imported_by_path.get(record.module_path, set())
        if _is_test_path(record.module_path) or (importers and all(_is_test_path(path) for path in importers)):
            rows.append(record)
    return rows


def _strongly_connected_components(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack = []
    indices = {}
    lowlinks = {}
    on_stack = set()
    components = []

    def strongconnect(node):
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1 or node in graph.get(node, set()):
                components.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            strongconnect(node)
    return components


def _reachable_from(starts: set[str], graph: dict[str, set[str]]) -> set[str]:
    seen = set()
    pending = list(starts)
    while pending:
        node = pending.pop()
        for neighbor in graph.get(node, set()):
            if neighbor in seen:
                continue
            seen.add(neighbor)
            pending.append(neighbor)
    return seen


def build_findings(
    records: list[ModuleRecord],
    entries: list[ModuleMapEntry],
    edges: list[ImportEdge],
):
    by_path = {record.module_path: record for record in records}
    imports_by_path, imported_by_path = _index_edges(edges)
    internal_graph = {record.module_path: set() for record in records}
    for importer, imports in imports_by_path.items():
        internal_graph.setdefault(importer, set()).update(imports)

    unclassified = [record for record in records if not record.status]
    listed_missing = []
    for entry in entries:
        if entry.is_pattern:
            if not any(fnmatch.fnmatch(record.module_path, entry.module_path) for record in records):
                listed_missing.append(entry.module_path)
        elif entry.module_path not in by_path:
            listed_missing.append(entry.module_path)

    deprecated_references = []
    for edge in edges:
        imported = by_path.get(edge.imported_path)
        if not edge.is_internal or not imported or imported.status != "deprecated":
            continue
        if not _is_test_path(edge.importer_path):
            deprecated_references.append(edge)

    production_entrypoints = {
        record.module_path
        for record in records
        if record.entrypoint and record.status in {"active", "compatibility"} and not _is_test_path(record.module_path)
    }
    reachable = _reachable_from(production_entrypoints, internal_graph)
    experimental_reachable = [
        by_path[path] for path in sorted(reachable) if by_path[path].status == "experimental"
    ]
    local_only_reachable = [
        by_path[path] for path in sorted(reachable) if by_path[path].status == "local_only"
    ]
    compatibility_imports_experimental = [
        edge
        for edge in edges
        if edge.is_internal
        and by_path.get(edge.importer_path)
        and by_path.get(edge.imported_path)
        and by_path[edge.importer_path].status == "compatibility"
        and by_path[edge.imported_path].status == "experimental"
    ]
    cycles = _strongly_connected_components(internal_graph)
    orphan_candidates = _orphan_candidates(records, imports_by_path, imported_by_path)
    script_only = _script_only_modules(records, imported_by_path)
    test_only = _test_only_modules(records, imported_by_path)

    return {
        "imports_by_path": imports_by_path,
        "imported_by_path": imported_by_path,
        "unclassified": unclassified,
        "listed_missing": listed_missing,
        "deprecated_references": deprecated_references,
        "experimental_reachable": experimental_reachable,
        "local_only_reachable": local_only_reachable,
        "compatibility_imports_experimental": compatibility_imports_experimental,
        "cycles": cycles,
        "orphan_candidates": orphan_candidates,
        "script_only": script_only,
        "test_only": test_only,
        "production_entrypoints": sorted(production_entrypoints),
    }


def _limited(rows, max_rows):
    return list(rows)[:max_rows]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _record_row(record, findings):
    imports = findings["imports_by_path"].get(record.module_path, set())
    imported_by = findings["imported_by_path"].get(record.module_path, set())
    return {
        "module_path": record.module_path,
        "module_name": record.module_name,
        "package_area": record.package_area,
        "status": record.status,
        "entrypoint": str(bool(record.entrypoint)).lower(),
        "imported_by_count": len(imported_by),
        "imports_count": len(imports),
        "parse_error": record.parse_error,
    }


def _edge_row(edge):
    return {
        "importer_path": edge.importer_path,
        "importer_module": edge.importer_module,
        "imported_module": edge.imported_module,
        "imported_path": edge.imported_path,
        "is_internal": str(bool(edge.is_internal)).lower(),
        "line": edge.line,
    }


def _risk_findings(findings):
    rows = []
    for edge in findings["deprecated_references"]:
        rows.append(
            {
                "finding_type": "deprecated_non_test_import",
                "module_path": edge.imported_path,
                "importer_path": edge.importer_path,
                "details": f"line {edge.line}",
            }
        )
    for record in findings["experimental_reachable"]:
        rows.append(
            {
                "finding_type": "experimental_reachable_from_production_entrypoint",
                "module_path": record.module_path,
                "importer_path": "",
                "details": "reachable from active/compatibility entrypoint",
            }
        )
    for record in findings["local_only_reachable"]:
        rows.append(
            {
                "finding_type": "local_only_reachable_from_production_entrypoint",
                "module_path": record.module_path,
                "importer_path": "",
                "details": "reachable from active/compatibility entrypoint",
            }
        )
    for edge in findings["compatibility_imports_experimental"]:
        rows.append(
            {
                "finding_type": "compatibility_imports_experimental",
                "module_path": edge.imported_path,
                "importer_path": edge.importer_path,
                "details": f"line {edge.line}",
            }
        )
    return rows


def write_outputs(
    output_dir: Path,
    records: list[ModuleRecord],
    entries: list[ModuleMapEntry],
    map_warnings: list[str],
    edges: list[ImportEdge],
    findings,
    max_rows: int,
):
    output_dir.mkdir(parents=True, exist_ok=True)
    records = sorted(records, key=lambda item: item.module_path)
    edges = sorted(edges, key=lambda item: (item.importer_path, item.line, item.imported_module))
    risk_findings = _risk_findings(findings)
    entrypoints = [record for record in records if record.entrypoint]

    summary = {
        "schema_version": "module_graph_summary_v1",
        "total_modules": len(records),
        "total_import_edges": len(edges),
        "internal_import_edges": sum(1 for edge in edges if edge.is_internal),
        "entrypoint_count": len(entrypoints),
        "orphan_candidate_count": len(findings["orphan_candidates"]),
        "script_only_count": len(findings["script_only"]),
        "test_only_count": len(findings["test_only"]),
        "import_cycle_count": len(findings["cycles"]),
        "unclassified_module_count": len(findings["unclassified"]),
        "deprecated_reference_count": len(findings["deprecated_references"]),
        "experimental_reachable_from_production_count": len(findings["experimental_reachable"]),
        "local_only_reachable_from_production_count": len(findings["local_only_reachable"]),
        "compatibility_imports_experimental_count": len(
            findings["compatibility_imports_experimental"]
        ),
        "module_map_entries": len(entries),
        "module_map_warnings": map_warnings,
        "module_map_listed_missing": findings["listed_missing"],
        "production_entrypoints": findings["production_entrypoints"],
        "top_risk_findings": _limited(risk_findings, 10),
        "local_only": True,
        "static_ast_only": True,
        "project_modules_imported": False,
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "network_or_model_calls_attempted": False,
    }
    (output_dir / "module_graph_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    inventory_rows = [_record_row(record, findings) for record in records]
    _write_csv(
        output_dir / "module_inventory.csv",
        [
            "module_path",
            "module_name",
            "package_area",
            "status",
            "entrypoint",
            "imported_by_count",
            "imports_count",
            "parse_error",
        ],
        _limited(inventory_rows, max_rows),
    )
    _write_csv(
        output_dir / "import_edges.csv",
        ["importer_path", "importer_module", "imported_module", "imported_path", "is_internal", "line"],
        _limited([_edge_row(edge) for edge in edges], max_rows),
    )
    _write_csv(
        output_dir / "entrypoints.csv",
        ["module_path", "module_name", "package_area", "status", "entrypoint"],
        _limited(
            [
                {
                    "module_path": record.module_path,
                    "module_name": record.module_name,
                    "package_area": record.package_area,
                    "status": record.status,
                    "entrypoint": "true",
                }
                for record in entrypoints
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "orphan_module_candidates.csv",
        ["module_path", "module_name", "package_area", "status"],
        _limited(
            [
                {
                    "module_path": record.module_path,
                    "module_name": record.module_name,
                    "package_area": record.package_area,
                    "status": record.status,
                }
                for record in findings["orphan_candidates"]
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "script_only_modules.csv",
        ["module_path", "module_name", "status", "entrypoint"],
        _limited(
            [
                {
                    "module_path": record.module_path,
                    "module_name": record.module_name,
                    "status": record.status,
                    "entrypoint": str(bool(record.entrypoint)).lower(),
                }
                for record in findings["script_only"]
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "test_only_modules.csv",
        ["module_path", "module_name", "status"],
        _limited(
            [
                {
                    "module_path": record.module_path,
                    "module_name": record.module_name,
                    "status": record.status,
                }
                for record in findings["test_only"]
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "deprecated_references.csv",
        ["importer_path", "deprecated_module_path", "deprecated_module", "line"],
        _limited(
            [
                {
                    "importer_path": edge.importer_path,
                    "deprecated_module_path": edge.imported_path,
                    "deprecated_module": edge.imported_module,
                    "line": edge.line,
                }
                for edge in findings["deprecated_references"]
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "import_cycles.csv",
        ["cycle_id", "module_count", "modules"],
        _limited(
            [
                {
                    "cycle_id": index + 1,
                    "module_count": len(component),
                    "modules": ";".join(component),
                }
                for index, component in enumerate(findings["cycles"])
            ],
            max_rows,
        ),
    )
    _write_csv(
        output_dir / "unclassified_modules.csv",
        ["module_path", "module_name", "package_area"],
        _limited(
            [
                {
                    "module_path": record.module_path,
                    "module_name": record.module_name,
                    "package_area": record.package_area,
                }
                for record in findings["unclassified"]
            ],
            max_rows,
        ),
    )

    report_lines = [
        "# Module Graph Report",
        "",
        "This report was generated by static AST parsing only. It does not import project modules, execute app code, process PDFs, run OCR, or call network/model/cloud services.",
        "",
        "## Summary",
        "",
        f"- Total modules: {summary['total_modules']}",
        f"- Total import edges: {summary['total_import_edges']}",
        f"- Entrypoints: {summary['entrypoint_count']}",
        f"- Orphan candidates: {summary['orphan_candidate_count']}",
        f"- Script-only modules: {summary['script_only_count']}",
        f"- Test-only modules: {summary['test_only_count']}",
        f"- Import cycles: {summary['import_cycle_count']}",
        f"- Unclassified modules: {summary['unclassified_module_count']}",
        f"- Deprecated non-test references: {summary['deprecated_reference_count']}",
        "",
        "## Top Risk Findings",
        "",
    ]
    if risk_findings:
        for row in _limited(risk_findings, 10):
            report_lines.append(
                f"- {row['finding_type']}: {row['module_path']} imported/reached by {row['importer_path'] or 'production reachability'}"
            )
    else:
        report_lines.append("- None found by the configured MODULE_MAP coverage.")
    if findings["listed_missing"]:
        report_lines.extend(["", "## MODULE_MAP Entries Not Found", ""])
        for item in findings["listed_missing"][:10]:
            report_lines.append(f"- {item}")
    (output_dir / "module_graph_report.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )
    return summary


def analyze(repo_root: Path, output_dir: Path, include_tests=False, include_docs=False, max_rows=1000):
    entries, map_warnings = load_module_map(repo_root)
    discovered = discover_python_modules(
        repo_root,
        include_tests=include_tests,
        include_docs=include_docs,
    )
    records, trees, parse_errors = build_module_records(discovered, entries)
    edges = extract_import_edges(records, trees)
    findings = build_findings(records, entries, edges)
    if parse_errors:
        map_warnings.extend(
            f"Could not parse {path}: {error}" for path, error in sorted(parse_errors.items())
        )
    return write_outputs(output_dir, records, entries, map_warnings, edges, findings, max_rows)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Build a local-only static module inventory and import graph."
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--confirm-local-audit-run", action="store_true")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--include-docs", action="store_true")
    parser.add_argument("--max-rows", type=int, default=1000)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.confirm_local_audit_run:
        print("Refusing to run without --confirm-local-audit-run.")
        return 2
    try:
        repo_root = _resolve_repo_root(args.repo_root)
        output_dir = _resolve_output_dir(repo_root, args.output_dir)
        max_rows = max(1, int(args.max_rows or 1000))
        summary = analyze(
            repo_root,
            output_dir,
            include_tests=bool(args.include_tests),
            include_docs=bool(args.include_docs),
            max_rows=max_rows,
        )
    except ModuleGraphError as exc:
        print(str(exc))
        return 2

    print("Module graph local audit complete")
    print(f"output_dir: {output_dir}")
    print(f"total_modules: {summary['total_modules']}")
    print(f"total_import_edges: {summary['total_import_edges']}")
    print(f"entrypoint_count: {summary['entrypoint_count']}")
    print(f"orphan_candidate_count: {summary['orphan_candidate_count']}")
    print(f"script_only_count: {summary['script_only_count']}")
    print(f"test_only_count: {summary['test_only_count']}")
    print(f"import_cycle_count: {summary['import_cycle_count']}")
    print(f"unclassified_module_count: {summary['unclassified_module_count']}")
    print(f"deprecated_reference_count: {summary['deprecated_reference_count']}")
    print("project_modules_imported: False")
    print("pdf_processing_attempted: False")
    print("ocr_attempted: False")
    print("network_or_model_calls_attempted: False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
