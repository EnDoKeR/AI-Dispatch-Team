"""Create local-only RateCon load source-line detail inventory sidecars.

This script reads existing local evaluation, audit, and diagnostics artifacts.
It does not run measurement, process PDFs, invoke OCR, call Google, or call
model/cloud services. Default outputs redact selected, gold, and candidate
values.
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

from app.document_ai.load_identifier_source_line_detail import (
    LOAD_FIELD,
    build_load_source_line_detail_inventory,
)


SUMMARY_FILE = "ratecon_gold_evaluation_summary.json"
ERROR_CASE_FILES = (
    "ratecon_gold_evaluation_error_cases.csv",
    "ratecon_gold_error_cases.csv",
)
SELECTED_ROW_FILES = (
    "private_selected_load_selected_rows.csv",
    "ratecon_selected_load_comparison_rows.csv",
    "selected_load_comparison_rows.csv",
    "ratecon_gold_selected_load_rows.csv",
    "selected_load_rows.csv",
)
DIAGNOSTICS_SUMMARY_FILE = "load_source_line_diagnostics_summary.json"
DIAGNOSTIC_ROW_FILE = "load_source_line_error_cases.csv"
SERIALIZATION_ROW_FILE = "load_source_line_serialization_rows.csv"
GENERATED_RESOLVER_SUMMARY_FILE = "load_generated_resolver_provenance_summary.json"
GENERATED_RESOLVER_LOSS_FILE = "load_provenance_loss_by_stage.csv"
BOUNDARY_SUMMARY_FILE = "load_generated_provenance_boundary_summary.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local-only RateCon load source-line detail inventory."
    )
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--diagnostics-dir", required=True)
    parser.add_argument("--serialization-dir")
    parser.add_argument("--generated-resolver-provenance-dir")
    parser.add_argument("--boundary-compare-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _require_output_under_local_outputs(path: Path) -> Path:
    if ".local_outputs" not in path.parts:
        raise ValueError("output-dir must be inside .local_outputs")
    return path


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _find_first(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = directory / name
        if path.exists():
            return path
    return None


def _csv_rows(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _field_matches(row: dict[str, Any]) -> bool:
    field = _text(row.get("field") or row.get("field_name"))
    return not field or field == LOAD_FIELD


def _document_id(row: dict[str, Any], fallback: str = "") -> str:
    return _text(
        row.get("document_id")
        or row.get("case_id")
        or row.get("measurement_alias")
        or row.get("file_hash")
        or fallback
    )


def _rows_by_doc(rows: list[dict[str, Any]], fallback_prefix: str) -> dict[str, dict[str, Any]]:
    by_doc: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        if not _field_matches(row):
            continue
        by_doc[_document_id(row, f"{fallback_prefix}_{index}")] = row
    return by_doc


def _read_selected_rows(eval_dir: Path) -> dict[str, dict[str, Any]]:
    return _rows_by_doc(
        _csv_rows(_find_first(eval_dir, SELECTED_ROW_FILES)),
        "selected_row",
    )


def _read_error_rows(eval_dir: Path) -> dict[str, dict[str, Any]]:
    return _rows_by_doc(
        _csv_rows(_find_first(eval_dir, ERROR_CASE_FILES)),
        "error_row",
    )


def _read_diagnostic_rows(diagnostics_dir: Path) -> dict[str, dict[str, Any]]:
    return _rows_by_doc(
        _csv_rows(diagnostics_dir / DIAGNOSTIC_ROW_FILE),
        "diagnostic_row",
    )


def _read_audit_rows(path: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return rows
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            continue
        rows[_document_id(payload, f"audit_row_{index}")] = payload
    return rows


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# RateCon Load Source-Line Detail Inventory",
        "",
        "Local-only detail inventory over existing evaluation/audit/diagnostic artifacts.",
        "Private selected, gold, and candidate values are redacted unless explicitly included locally.",
        "",
        f"- detail_input_status: {summary['detail_input_status']}",
        f"- document_count: {summary['document_count']}",
        f"- candidate_detail_row_count: {summary['candidate_detail_row_count']}",
        f"- complete_source_detail_count: {summary['complete_source_detail_count']}",
        f"- missing_page_line_count: {summary['missing_page_line_count']}",
        f"- missing_source_count: {summary['missing_source_count']}",
        f"- dropped_detail_count: {summary['dropped_detail_count']}",
        f"- unknown_caused_by_missing_detail_count: {summary['unknown_caused_by_missing_detail_count']}",
        f"- private_values_included: {summary['private_values_included']}",
        f"- values_redacted: {summary['values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Detail Loss Buckets",
    ]
    for bucket, count in summary["detail_loss_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(
        [
            "",
            "## Serialization Sidecar",
            f"- serialization_sidecar_status: {summary['serialization_sidecar_status']}",
            f"- serialization_complete_detail_count: {summary['serialization_complete_detail_count']}",
            f"- adapter_detail_preserved_count: {summary['adapter_detail_preserved_count']}",
            f"- adapter_detail_lost_count: {summary['adapter_detail_lost_count']}",
        ]
    )
    for bucket, count in summary["serialization_loss_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Adapter Roundtrip Statuses"])
    for status, count in summary["adapter_roundtrip_status_counts"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Generated/Resolver Provenance Sidecar",
            f"- generated_resolver_sidecar_status: {summary['generated_resolver_sidecar_status']}",
            f"- generated_resolver_current_artifacts_status: {summary['generated_resolver_current_artifacts_status']}",
            f"- generated_candidate_detail_available_count: {summary['generated_candidate_detail_available_count']}",
            f"- resolver_visible_detail_available_count: {summary['resolver_visible_detail_available_count']}",
            f"- boundary_compare_status: {summary.get('boundary_compare_status', 'skipped_not_requested')}",
            f"- boundary_first_loss_boundary: {summary.get('boundary_first_loss_boundary', '')}",
            f"- boundary_complete_roundtrip_count: {summary.get('boundary_complete_roundtrip_count', 0)}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "load_source_line_detail_inventory_summary.json", payload)
    _write_report(output_dir / "load_source_line_detail_inventory_report.md", payload)
    _write_csv(
        output_dir / "load_source_line_detail_rows.csv",
        payload["detail_rows"],
        [
            "document_id",
            "file_name_redacted_or_alias",
            "field",
            "candidate_id",
            "selected",
            "candidate_rank",
            "source",
            "source_family",
            "parser_name",
            "pairing_method",
            "page_number",
            "line_index",
            "bbox_available",
            "source_line_status",
            "candidate_value_status",
            "label_text_status",
            "value_text_status",
            "neighbor_context_status",
            "detail_loss_bucket",
            "detail_loss_stage",
            "detail_loss_reason",
            "serialization_loss_stage",
            "serialization_loss_reason",
            "source_detail_roundtrip_status",
            "adapter_roundtrip_status",
            "adapter_loss_reason",
            "generated_resolver_roundtrip_status",
            "generated_resolver_loss_stage",
            "generated_resolver_loss_reason",
            "diagnostic_bucket",
            "known_debt",
            "private_values_redacted",
            "value_preview",
            "gold_value_preview",
        ],
    )
    _write_csv(
        output_dir / "load_source_line_detail_loss.csv",
        payload["detail_loss_rows"],
        [
            "document_id",
            "candidate_id",
            "detail_loss_bucket",
            "detail_loss_stage",
            "detail_loss_reason",
            "serialization_loss_stage",
            "serialization_loss_reason",
            "source_detail_roundtrip_status",
                "adapter_roundtrip_status",
                "adapter_loss_reason",
                "generated_resolver_roundtrip_status",
                "generated_resolver_loss_stage",
                "generated_resolver_loss_reason",
                "diagnostic_bucket",
            ],
    )
    _write_csv(
        output_dir / "load_source_line_candidate_detail_coverage.csv",
        payload["coverage_rows"],
        ["coverage_metric", "count", "detail"],
    )
    _write_csv(
        output_dir / "load_source_line_detail_review_items.csv",
        payload["review_rows"],
        [
            "document_id",
            "detail_loss_bucket",
            "diagnostic_bucket",
            "recommended_action",
            "behavior_change_allowed",
        ],
    )


def build_inventory(args: argparse.Namespace) -> dict[str, Any]:
    eval_dir = _resolve(args.eval_dir)
    diagnostics_dir = _resolve(args.diagnostics_dir)
    serialization_dir = _resolve(args.serialization_dir) if args.serialization_dir else None
    diagnostics_payload = _read_json(diagnostics_dir / DIAGNOSTICS_SUMMARY_FILE)
    serialization_rows = (
        _csv_rows(serialization_dir / SERIALIZATION_ROW_FILE)
        if serialization_dir and serialization_dir.exists()
        else []
    )
    payload = build_load_source_line_detail_inventory(
        selected_rows=_read_selected_rows(eval_dir),
        error_rows=_read_error_rows(eval_dir),
        audit_rows=_read_audit_rows(_resolve(args.audit)),
        diagnostic_rows=_read_diagnostic_rows(diagnostics_dir),
        diagnostics_summary=diagnostics_payload.get("summary") or {},
        serialization_rows=serialization_rows,
        include_private_values=bool(args.include_private_values_local_only),
    )
    generated_resolver_dir = (
        _resolve(args.generated_resolver_provenance_dir)
        if args.generated_resolver_provenance_dir
        else None
    )
    payload = _merge_generated_resolver_sidecar(payload, generated_resolver_dir)
    return _merge_boundary_compare_summary(
        payload,
        _resolve(args.boundary_compare_dir) if args.boundary_compare_dir else None,
        bool(args.boundary_compare_dir),
    )


def _merge_generated_resolver_sidecar(payload: dict[str, Any], sidecar_dir: Path | None) -> dict[str, Any]:
    sidecar_payload = _read_json(
        sidecar_dir / GENERATED_RESOLVER_SUMMARY_FILE
        if sidecar_dir is not None and sidecar_dir.exists()
        else Path("__missing__")
    )
    sidecar_summary = dict(sidecar_payload.get("summary") or {}) if sidecar_payload else {}
    loss_rows = _csv_rows(
        sidecar_dir / GENERATED_RESOLVER_LOSS_FILE
        if sidecar_dir is not None and sidecar_dir.exists()
        else None
    )
    loss_by_key = {
        (_text(row.get("document_id")), _text(row.get("candidate_id"))): row
        for row in loss_rows
    }
    for row in payload["detail_rows"]:
        loss = loss_by_key.get((_text(row.get("document_id")), _text(row.get("candidate_id"))), {})
        row["generated_resolver_roundtrip_status"] = _text(
            loss.get("generated_resolver_roundtrip_status")
        )
        row["generated_resolver_loss_stage"] = _text(
            loss.get("generated_resolver_loss_stage")
        )
        row["generated_resolver_loss_reason"] = _text(
            loss.get("generated_resolver_loss_reason")
        )
    for row in payload["detail_loss_rows"]:
        loss = loss_by_key.get((_text(row.get("document_id")), _text(row.get("candidate_id"))), {})
        row["generated_resolver_roundtrip_status"] = _text(
            loss.get("generated_resolver_roundtrip_status")
        )
        row["generated_resolver_loss_stage"] = _text(
            loss.get("generated_resolver_loss_stage")
        )
        row["generated_resolver_loss_reason"] = _text(
            loss.get("generated_resolver_loss_reason")
        )
    summary = payload["summary"]
    summary["generated_resolver_sidecar_status"] = (
        "present" if sidecar_summary else "skipped_missing_optional_dir"
    )
    summary["generated_resolver_current_artifacts_status"] = sidecar_summary.get(
        "current_artifacts_status",
        "skipped",
    )
    summary["generated_candidate_detail_available_count"] = int(
        sidecar_summary.get("generated_candidate_detail_available_count") or 0
    )
    summary["resolver_visible_detail_available_count"] = int(
        sidecar_summary.get("resolver_visible_detail_available_count") or 0
    )
    summary["generated_resolver_stage_loss_bucket_counts"] = dict(
        sidecar_summary.get("stage_loss_bucket_counts") or {}
    )
    summary["generated_resolver_complete_roundtrip_count"] = int(
        sidecar_summary.get("complete_roundtrip_count") or 0
    )
    return payload


def _merge_boundary_compare_summary(
    payload: dict[str, Any],
    boundary_dir: Path | None,
    requested: bool,
) -> dict[str, Any]:
    boundary_payload = _read_json(
        boundary_dir / BOUNDARY_SUMMARY_FILE
        if boundary_dir is not None and boundary_dir.exists()
        else Path("__missing__")
    )
    boundary_summary = dict(boundary_payload.get("summary") or {}) if boundary_payload else {}
    summary = payload["summary"]
    summary["boundary_compare_status"] = "present" if boundary_summary else (
        "skipped_missing_optional_dir" if requested else "skipped_not_requested"
    )
    summary["boundary_first_loss_boundary"] = boundary_summary.get("first_loss_boundary", "")
    summary["boundary_complete_roundtrip_count"] = int(
        boundary_summary.get("complete_roundtrip_count") or 0
    )
    summary["boundary_loss_boundary_counts"] = dict(
        boundary_summary.get("loss_boundary_counts") or {}
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        raise SystemExit("--confirm-private-local-run is required for this local-only detail inventory.")
    output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
    payload = build_inventory(args)
    write_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load source-line detail inventory")
    print(f"detail_input_status: {summary['detail_input_status']}")
    print(f"document_count: {summary['document_count']}")
    print(f"candidate_detail_row_count: {summary['candidate_detail_row_count']}")
    print(f"complete_source_detail_count: {summary['complete_source_detail_count']}")
    print(f"missing_page_line_count: {summary['missing_page_line_count']}")
    print(f"missing_source_count: {summary['missing_source_count']}")
    print(f"dropped_detail_count: {summary['dropped_detail_count']}")
    print(
        "unknown_caused_by_missing_detail_count: "
        f"{summary['unknown_caused_by_missing_detail_count']}"
    )
    print(f"serialization_sidecar_status: {summary['serialization_sidecar_status']}")
    print(
        "serialization_complete_detail_count: "
        f"{summary['serialization_complete_detail_count']}"
    )
    print(f"adapter_detail_preserved_count: {summary['adapter_detail_preserved_count']}")
    print(f"adapter_detail_lost_count: {summary['adapter_detail_lost_count']}")
    print(f"generated_resolver_sidecar_status: {summary['generated_resolver_sidecar_status']}")
    print(f"boundary_compare_status: {summary['boundary_compare_status']}")
    print(f"boundary_first_loss_boundary: {summary['boundary_first_loss_boundary']}")
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
