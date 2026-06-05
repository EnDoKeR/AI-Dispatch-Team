"""Create local-only RateCon load generated/resolver provenance sidecars.

This script reads existing local audit/sidecar outputs only. It does not run
private measurement, process PDFs, invoke OCR, call Google, call model/cloud
services, or change selected load-number behavior.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.document_ai.load_identifier_generated_resolver_provenance import (  # noqa: E402
    LOAD_FIELD,
    build_load_generated_resolver_provenance_sidecars,
    rows_from_audit_payloads,
    write_load_generated_resolver_provenance_outputs,
)


SERIALIZATION_ROW_FILE = "load_source_line_serialization_rows.csv"

LEGACY_GENERATED_FILES = (
    "load_generated_candidates.csv",
    "ratecon_load_generated_candidates.csv",
    "generated_candidates.csv",
)
LEGACY_ADAPTER_INPUT_FILES = (
    "load_adapter_input_candidates.csv",
    "adapter_input.csv",
)
LEGACY_ADAPTER_OUTPUT_FILES = (
    "load_adapter_output_candidates.csv",
    "adapter_output.csv",
    "load_adapter_roundtrip_rows.csv",
)
LEGACY_DEDUPE_INPUT_FILES = (
    "load_dedupe_input_candidates.csv",
    "dedupe_input.csv",
)
LEGACY_DEDUPE_OUTPUT_FILES = (
    "load_dedupe_output_candidates.csv",
    "dedupe_output.csv",
    "load_dedupe_lineage_rows.csv",
)
LEGACY_RESOLVER_FILES = (
    "load_resolver_visible_candidates.csv",
    "resolver_trace.csv",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local-only RateCon load generated/resolver provenance sidecars."
    )
    parser.add_argument("--audit")
    parser.add_argument("--legacy-output-dir")
    parser.add_argument("--serialization-dir")
    parser.add_argument("--generated-candidates")
    parser.add_argument("--adapter-input")
    parser.add_argument("--adapter-output")
    parser.add_argument("--dedupe-input")
    parser.add_argument("--dedupe-output")
    parser.add_argument("--resolver-trace")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path | None) -> Path | None:
    if not path:
        return None
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    if ".local_outputs" not in path.parts:
        raise ValueError("output-dir must be inside .local_outputs")
    return path


def _text(value: Any) -> str:
    return str(value or "").strip()


def _field_matches(row: dict[str, Any]) -> bool:
    field = _text(row.get("field") or row.get("field_name"))
    return not field or field == LOAD_FIELD


def _csv_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle) if _field_matches(dict(row))]


def _jsonl_payloads(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _find_first(directory: Path | None, names: tuple[str, ...]) -> Path | None:
    if directory is None or not directory.exists():
        return None
    for name in names:
        path = directory / name
        if path.exists():
            return path
    return None


def _merge_rows(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in groups:
        rows.extend(group)
    return rows


def _rows_from_explicit_or_legacy(
    explicit_path: str | Path | None,
    legacy_dir: Path | None,
    legacy_names: tuple[str, ...],
) -> list[dict[str, str]]:
    explicit_rows = _csv_rows(_resolve(explicit_path))
    if explicit_rows:
        return explicit_rows
    return _csv_rows(_find_first(legacy_dir, legacy_names))


def build_sidecars(args: argparse.Namespace) -> dict[str, Any]:
    legacy_dir = _resolve(args.legacy_output_dir)
    serialization_dir = _resolve(args.serialization_dir)
    resolver_from_audit, audit_rows = rows_from_audit_payloads(
        _jsonl_payloads(_resolve(args.audit))
    )
    return build_load_generated_resolver_provenance_sidecars(
        generated_rows=_rows_from_explicit_or_legacy(
            args.generated_candidates, legacy_dir, LEGACY_GENERATED_FILES
        ),
        adapter_input_rows=_rows_from_explicit_or_legacy(
            args.adapter_input, legacy_dir, LEGACY_ADAPTER_INPUT_FILES
        ),
        adapter_output_rows=_rows_from_explicit_or_legacy(
            args.adapter_output, legacy_dir, LEGACY_ADAPTER_OUTPUT_FILES
        ),
        dedupe_input_rows=_rows_from_explicit_or_legacy(
            args.dedupe_input, legacy_dir, LEGACY_DEDUPE_INPUT_FILES
        ),
        dedupe_output_rows=_rows_from_explicit_or_legacy(
            args.dedupe_output, legacy_dir, LEGACY_DEDUPE_OUTPUT_FILES
        ),
        resolver_rows=_merge_rows(
            _rows_from_explicit_or_legacy(
                args.resolver_trace, legacy_dir, LEGACY_RESOLVER_FILES
            ),
            resolver_from_audit,
        ),
        audit_rows=audit_rows,
        serialization_rows=_csv_rows(
            serialization_dir / SERIALIZATION_ROW_FILE
            if serialization_dir is not None
            else None
        ),
        include_private_values=bool(args.include_private_values_local_only),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        raise SystemExit("--confirm-private-local-run is required for this local-only sidecar.")
    output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
    payload = build_sidecars(args)
    write_load_generated_resolver_provenance_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load generated/resolver provenance sidecars")
    print(f"current_artifacts_status: {summary['current_artifacts_status']}")
    print(f"current_artifacts_measurable: {summary['current_artifacts_measurable']}")
    print(f"provenance_candidate_count: {summary['provenance_candidate_count']}")
    print(f"generated_candidate_count: {summary['generated_candidate_count']}")
    print(f"resolver_visible_candidate_count: {summary['resolver_visible_candidate_count']}")
    print(
        "generated_candidate_detail_available_count: "
        f"{summary['generated_candidate_detail_available_count']}"
    )
    print(
        "resolver_visible_detail_available_count: "
        f"{summary['resolver_visible_detail_available_count']}"
    )
    print(f"complete_roundtrip_count: {summary['complete_roundtrip_count']}")
    print(f"private_values_included: {summary['private_values_included']}")
    print(f"values_redacted: {summary['values_redacted']}")
    print(f"pdf_processing_attempted: {summary['pdf_processing_attempted']}")
    print(f"ocr_attempted: {summary['ocr_attempted']}")
    print(f"google_called: {summary['google_called']}")
    print(f"model_or_cloud_called: {summary['model_or_cloud_called']}")
    print(f"output_dir: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
