"""Create local-only RateCon load source-line serialization sidecars.

This script reads existing generated candidate, resolver trace, audit, and
evaluator artifacts. It does not run extraction, resolve candidates, process
PDFs, invoke OCR, call Google, call model/cloud services, or run private
measurement.
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

from app.document_ai.load_identifier_source_line_serialization import (  # noqa: E402
    LOAD_FIELD,
    build_load_source_line_serialization_sidecar,
)


SELECTED_ROW_FILES = (
    "private_selected_load_selected_rows.csv",
    "ratecon_selected_load_comparison_rows.csv",
    "selected_load_comparison_rows.csv",
    "ratecon_gold_selected_load_rows.csv",
    "selected_load_rows.csv",
)
GENERATED_RESOLVER_SUMMARY_FILE = "load_generated_resolver_provenance_summary.json"
GENERATED_RESOLVER_LOSS_FILE = "load_provenance_loss_by_stage.csv"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local-only RateCon load source-line serialization sidecars."
    )
    parser.add_argument("--generated-candidates")
    parser.add_argument("--resolver-trace")
    parser.add_argument("--audit")
    parser.add_argument("--eval-dir")
    parser.add_argument("--generated-resolver-provenance-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confirm-private-local-run", action="store_true")
    parser.add_argument("--include-private-values-local-only", action="store_true")
    return parser.parse_args(argv)


def _resolve(path: str | Path | None) -> Path | None:
    if path is None:
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


def _jsonl_rows(path: Path | None) -> list[dict[str, Any]]:
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


def _find_selected_rows(eval_dir: Path | None) -> Path | None:
    if eval_dir is None or not eval_dir.exists():
        return None
    for name in SELECTED_ROW_FILES:
        path = eval_dir / name
        if path.exists():
            return path
    return None


def _read_audit_rows(path: Path | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for payload in _jsonl_rows(path):
        details = payload.get("candidate_details")
        if isinstance(details, list):
            for index, detail in enumerate(details, start=1):
                if not isinstance(detail, dict):
                    continue
                row = dict(detail)
                row.setdefault("document_id", payload.get("document_id"))
                row.setdefault("field", LOAD_FIELD)
                row.setdefault("selected_source", payload.get("selected_source"))
                row.setdefault("selected_value", payload.get("selected_value"))
                row.setdefault("selected", row.get("selected") or index == 1)
                rows.append(row)
        else:
            row = {
                "document_id": payload.get("document_id"),
                "field": LOAD_FIELD,
                "candidate_id": payload.get("candidate_id") or payload.get("selected_candidate_id"),
                "candidate_value": payload.get("selected_value"),
                "selected": True,
                "source": payload.get("selected_source"),
                "pairing_method": payload.get("pairing_method")
                or payload.get("selected_pairing_method"),
                "page_number": payload.get("selected_page_index") or payload.get("selected_page"),
                "line_index": payload.get("selected_line_index"),
                "source_line": payload.get("selected_source_line"),
            }
            rows.append(row)
    return [row for row in rows if _field_matches(row)]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# RateCon Load Source-Line Serialization Sidecar",
        "",
        "Local-only serialization sidecar over existing generated/resolver/audit/evaluator artifacts.",
        "",
        f"- document_count: {summary['document_count']}",
        f"- candidate_serialization_row_count: {summary['candidate_serialization_row_count']}",
        f"- complete_detail_serialized_count: {summary['complete_detail_serialized_count']}",
        f"- missing_at_generation_count: {summary['missing_at_generation_count']}",
        f"- lost_after_generation_count: {summary['lost_after_generation_count']}",
        f"- adapter_detail_preserved_count: {summary['adapter_detail_preserved_count']}",
        f"- adapter_detail_lost_count: {summary['adapter_detail_lost_count']}",
        f"- private_values_included: {summary['private_values_included']}",
        f"- values_redacted: {summary['values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Serialization Loss Buckets",
    ]
    for bucket, count in summary["serialization_loss_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    lines.extend(["", "## Adapter Roundtrip Statuses"])
    for status, count in summary["adapter_roundtrip_status_counts"].items():
        lines.append(f"- {status}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "load_source_line_serialization_summary.json", payload)
    _write_report(output_dir / "load_source_line_serialization_report.md", payload)
    _write_csv(
        output_dir / "load_source_line_serialization_rows.csv",
        payload["serialization_rows"],
        [
            "document_id",
            "field",
            "candidate_id",
            "source",
            "source_family",
            "parser_name",
            "pairing_method",
            "page_number",
            "line_index",
            "bbox_available",
            "selected",
            "candidate_rank",
            "resolver_seen",
            "resolver_eligible",
            "resolver_selected",
            "audit_serialized",
            "evaluator_serialized",
            "serialization_loss_bucket",
            "detail_loss_bucket",
            "detail_loss_stage",
            "detail_loss_reason",
            "adapter_input_candidate_id_available",
            "adapter_output_candidate_id_available",
            "adapter_input_page_line_available",
            "adapter_output_page_line_available",
            "adapter_input_source_available",
            "adapter_output_source_available",
            "adapter_input_pairing_method_available",
            "adapter_output_pairing_method_available",
            "adapter_roundtrip_status",
            "adapter_loss_reason",
            "private_values_redacted",
            "value_preview",
            "generated_resolver_roundtrip_status",
            "generated_resolver_loss_stage",
            "generated_resolver_loss_reason",
        ],
    )


def _merge_generated_resolver_sidecar(payload: dict[str, Any], sidecar_dir: Path | None) -> dict[str, Any]:
    summary = payload["summary"]
    sidecar_payload = _read_json(
        sidecar_dir / GENERATED_RESOLVER_SUMMARY_FILE
        if sidecar_dir is not None
        else None
    )
    sidecar_summary = dict(sidecar_payload.get("summary") or {}) if sidecar_payload else {}
    loss_rows = _csv_rows(
        sidecar_dir / GENERATED_RESOLVER_LOSS_FILE
        if sidecar_dir is not None and sidecar_dir.exists()
        else None
    )
    loss_by_key = {
        (
            _text(row.get("document_id")),
            _text(row.get("candidate_id")),
        ): row
        for row in loss_rows
    }
    for row in payload["serialization_rows"]:
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
    summary["generated_resolver_loss_bucket_counts"] = dict(
        sidecar_summary.get("stage_loss_bucket_counts") or {}
    )
    return payload


def build_sidecar(args: argparse.Namespace) -> dict[str, Any]:
    eval_dir = _resolve(args.eval_dir)
    payload = build_load_source_line_serialization_sidecar(
        generated_rows=_csv_rows(_resolve(args.generated_candidates)),
        resolver_rows=_csv_rows(_resolve(args.resolver_trace)),
        audit_rows=_read_audit_rows(_resolve(args.audit)),
        evaluator_rows=_csv_rows(_find_selected_rows(eval_dir)),
        include_private_values=bool(args.include_private_values_local_only),
    )
    sidecar_dir = (
        _resolve(args.generated_resolver_provenance_dir)
        if args.generated_resolver_provenance_dir
        else None
    )
    return _merge_generated_resolver_sidecar(payload, sidecar_dir)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        raise SystemExit("--confirm-private-local-run is required for this local-only sidecar.")
    output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
    payload = build_sidecar(args)
    write_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load source-line serialization sidecar")
    print(f"document_count: {summary['document_count']}")
    print(f"candidate_serialization_row_count: {summary['candidate_serialization_row_count']}")
    print(f"complete_detail_serialized_count: {summary['complete_detail_serialized_count']}")
    print(f"missing_at_generation_count: {summary['missing_at_generation_count']}")
    print(f"lost_after_generation_count: {summary['lost_after_generation_count']}")
    print(f"adapter_detail_preserved_count: {summary['adapter_detail_preserved_count']}")
    print(f"adapter_detail_lost_count: {summary['adapter_detail_lost_count']}")
    print(f"generated_resolver_sidecar_status: {summary['generated_resolver_sidecar_status']}")
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
