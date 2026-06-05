"""Create local-only RateCon load source-line/evidence diagnostics.

This script reads existing local evaluation/audit artifacts only. It does not
run measurement, process PDFs, invoke OCR, call Google, or call model/cloud
services. Default outputs redact selected and gold values.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


LOAD_FIELD = "load_number"
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
REDACTED = "[redacted]"

DIAGNOSTIC_BUCKETS = (
    "selected_table_neighbor_wrong_cell",
    "selected_nearby_row_wrong_pair",
    "selected_footer_or_barcode_noise",
    "selected_reference_number_noise",
    "selected_po_number_noise",
    "selected_pro_number_noise",
    "selected_bol_number_noise",
    "gold_not_in_candidates",
    "gold_in_candidates_not_selected",
    "candidate_source_line_unavailable",
    "candidate_page_line_unavailable",
    "ambiguous_multiple_load_ids",
    "duplicate_same_value_candidates",
    "layout_ordering_ambiguous",
    "text_extraction_ordering_ambiguous",
    "evaluator_detail_unavailable",
    "gold_uncertain_or_review_required",
    "unknown",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create local-only RateCon load source-line/evidence diagnostics."
    )
    parser.add_argument("--eval-dir", required=True)
    parser.add_argument("--audit", required=True)
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


def _find_first(eval_dir: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        path = eval_dir / name
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


def _token(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _value_for_output(value: Any, include_private_values: bool) -> str:
    text = _text(value)
    if include_private_values:
        return text
    return REDACTED if text else ""


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


def _read_error_rows(eval_dir: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for index, row in enumerate(_csv_rows(_find_first(eval_dir, ERROR_CASE_FILES)), start=1):
        if not _field_matches(row):
            continue
        doc_id = _document_id(row, f"error_row_{index}")
        rows[doc_id] = row
    return rows


def _read_selected_rows(eval_dir: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for index, row in enumerate(_csv_rows(_find_first(eval_dir, SELECTED_ROW_FILES)), start=1):
        if not _field_matches(row):
            continue
        doc_id = _document_id(row, f"selected_row_{index}")
        rows[doc_id] = row
    return rows


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
        doc_id = _document_id(payload, f"audit_row_{index}")
        rows[doc_id] = payload
    return rows


def _summary_counts(summary: dict[str, Any]) -> dict[str, int]:
    metric = (
        ((summary.get("field_metrics") or {}).get("shadow") or {}).get(LOAD_FIELD)
        or (summary.get("field_metrics") or {}).get(LOAD_FIELD)
        or {}
    )
    error_analysis = (
        summary.get("load_number_error_analysis")
        or summary.get("load_identifier_error_analysis")
        or {}
    )
    diagnoses = error_analysis.get("diagnosis_counts") or {}

    def number(*keys: str) -> int:
        for key in keys:
            if key in metric:
                try:
                    return int(round(float(metric.get(key) or 0)))
                except (TypeError, ValueError):
                    return 0
        return 0

    return {
        "evaluated_document_count": int(summary.get("labels_evaluated") or summary.get("evaluated_document_count") or 0),
        "correct_count": number("correct_count", "correct"),
        "wrong_count": number("wrong_count", "wrong_value_count", "wrong"),
        "missing_count": number("missing_count", "missing"),
        "high_confidence_wrong_count": number(
            "high_confidence_wrong_count",
            "high_confidence_but_wrong_count",
            "high_conf_wrong_count",
        ),
        "diagnosis_count_total": sum(int(value or 0) for value in diagnoses.values()),
    }


def _candidate_values(row: dict[str, Any]) -> list[str]:
    value = row.get("candidate_values") or row.get("candidate_value_fingerprints")
    if isinstance(value, list):
        return [_text(item) for item in value if _text(item)]
    if isinstance(value, str):
        return [_text(item) for item in value.replace("|", ",").split(",") if _text(item)]
    return []


def _hints(row: dict[str, Any]) -> set[str]:
    value = row.get("diagnostic_hints") or row.get("diagnostic_hint") or []
    if isinstance(value, list):
        return {_token(item) for item in value if _text(item)}
    if isinstance(value, str):
        return {_token(item) for item in value.replace("|", ",").split(",") if _text(item)}
    return set()


def _known_bucket(value: Any) -> str:
    token = _token(value)
    return token if token in DIAGNOSTIC_BUCKETS else ""


def classify_diagnostic(
    *,
    error_row: dict[str, Any],
    selected_row: dict[str, Any],
    audit_row: dict[str, Any],
) -> tuple[str, str]:
    for value in (
        error_row.get("error_reason"),
        error_row.get("reason"),
        error_row.get("diagnosis"),
        selected_row.get("diagnostic_bucket"),
        audit_row.get("diagnostic_bucket"),
    ):
        bucket = _known_bucket(value)
        if bucket:
            return bucket, "explicit_status"

    hints = _hints(audit_row) | _hints(selected_row) | _hints(error_row)
    for bucket in DIAGNOSTIC_BUCKETS:
        if bucket in hints:
            return bucket, "explicit_hint"

    selected_source = _token(
        selected_row.get("selected_source")
        or selected_row.get("source")
        or audit_row.get("selected_source")
    )
    selected_label = _token(selected_row.get("selected_label") or audit_row.get("selected_label"))
    selected_value = _token(selected_row.get("selected_value") or audit_row.get("selected_value"))
    gold_value = _token(selected_row.get("gold_value") or audit_row.get("gold_value"))
    candidate_values = {_token(value) for value in _candidate_values(audit_row)}

    if "table" in selected_source and "neighbor" in selected_source:
        return "selected_table_neighbor_wrong_cell", "selected_source"
    if "nearby" in selected_source or "nearby_row" in selected_source:
        return "selected_nearby_row_wrong_pair", "selected_source"
    if any(marker in selected_label or marker in selected_source or marker in selected_value for marker in ("footer", "barcode")):
        return "selected_footer_or_barcode_noise", "selected_noise_shape"
    if "po" in selected_label or selected_value.startswith("po"):
        return "selected_po_number_noise", "selected_label"
    if "pro" in selected_label or selected_value.startswith("pro"):
        return "selected_pro_number_noise", "selected_label"
    if "bol" in selected_label or selected_value.startswith("bol"):
        return "selected_bol_number_noise", "selected_label"
    if "ref" in selected_label or selected_value.startswith("ref"):
        return "selected_reference_number_noise", "selected_label"
    if audit_row and not _text(audit_row.get("selected_source_line")) and not _text(audit_row.get("selected_line_index")):
        return "candidate_source_line_unavailable", "missing_source_line"
    if audit_row and not _text(audit_row.get("selected_page")) and not _text(audit_row.get("selected_page_index")):
        return "candidate_page_line_unavailable", "missing_page_line"
    if gold_value and candidate_values and gold_value not in candidate_values:
        return "gold_not_in_candidates", "candidate_presence"
    if gold_value and candidate_values and gold_value in candidate_values and gold_value != selected_value:
        return "gold_in_candidates_not_selected", "candidate_presence"
    if len(candidate_values) > 1 and any(value.startswith("load") for value in candidate_values):
        return "ambiguous_multiple_load_ids", "candidate_presence"
    if audit_row.get("duplicate_same_value_candidates"):
        return "duplicate_same_value_candidates", "candidate_presence"
    if not error_row and not selected_row and not audit_row:
        return "evaluator_detail_unavailable", "detail_unavailable"
    return "unknown", "fallback"


def build_diagnostics(args: argparse.Namespace) -> dict[str, Any]:
    eval_dir = _resolve(args.eval_dir)
    audit_path = _resolve(args.audit)
    summary = _read_json(eval_dir / SUMMARY_FILE)
    error_rows = _read_error_rows(eval_dir)
    selected_rows = _read_selected_rows(eval_dir)
    audit_rows = _read_audit_rows(audit_path)
    document_ids = sorted(set(error_rows) | set(selected_rows) | set(audit_rows))

    detail_status = "available" if document_ids else "detail_unavailable"
    if not document_ids:
        document_ids = ["detail_unavailable"]

    diagnostic_rows: list[dict[str, Any]] = []
    pairing_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    bucket_counts: Counter[str] = Counter()

    for doc_id in document_ids:
        error_row = error_rows.get(doc_id, {})
        selected_row = selected_rows.get(doc_id, {})
        audit_row = audit_rows.get(doc_id, {})
        bucket, evidence = classify_diagnostic(
            error_row=error_row,
            selected_row=selected_row,
            audit_row=audit_row,
        )
        bucket_counts[bucket] += 1
        selected_value = selected_row.get("selected_value") or audit_row.get("selected_value")
        gold_value = selected_row.get("gold_value") or audit_row.get("gold_value")
        candidate_values = _candidate_values(audit_row)
        diagnostic = {
            "document_id": doc_id,
            "diagnostic_bucket": bucket,
            "evidence_source": evidence,
            "selected_source": selected_row.get("selected_source") or audit_row.get("selected_source") or "",
            "selected_label": selected_row.get("selected_label") or audit_row.get("selected_label") or "",
            "selected_line_index": selected_row.get("selected_line_index") or audit_row.get("selected_line_index") or "",
            "selected_page_index": selected_row.get("selected_page_index") or audit_row.get("selected_page_index") or "",
            "gold_in_candidates": bool(_token(gold_value) and _token(gold_value) in {_token(value) for value in candidate_values}),
            "candidate_count": len(candidate_values),
            "selected_value": _value_for_output(selected_value, args.include_private_values_local_only),
            "gold_value": _value_for_output(gold_value, args.include_private_values_local_only),
            "private_values_included": bool(args.include_private_values_local_only),
        }
        diagnostic_rows.append(diagnostic)
        pairing_rows.append(
            {
                "document_id": doc_id,
                "diagnostic_bucket": bucket,
                "selected_source": diagnostic["selected_source"],
                "selected_line_index": diagnostic["selected_line_index"],
                "selected_page_index": diagnostic["selected_page_index"],
                "gold_line_index": selected_row.get("gold_line_index") or audit_row.get("gold_line_index") or "",
                "gold_page_index": selected_row.get("gold_page_index") or audit_row.get("gold_page_index") or "",
                "layout_ordering_note": audit_row.get("layout_ordering_note") or "",
            }
        )
        candidate_rows.append(
            {
                "document_id": doc_id,
                "diagnostic_bucket": bucket,
                "candidate_count": len(candidate_values),
                "gold_in_candidates": diagnostic["gold_in_candidates"],
                "candidate_source_line_available": bool(
                    audit_row.get("selected_source_line") or audit_row.get("selected_line_index")
                ),
                "candidate_page_line_available": bool(
                    audit_row.get("selected_page") or audit_row.get("selected_page_index")
                ),
            }
        )
        if bucket not in {"unknown", "duplicate_same_value_candidates"}:
            review_rows.append(
                {
                    "document_id": doc_id,
                    "diagnostic_bucket": bucket,
                    "recommended_action": "review_evidence_quality_only",
                    "behavior_change_allowed": False,
                }
            )

    side_effects = {
        "pdf_processing_attempted": False,
        "ocr_attempted": False,
        "google_called": False,
        "model_or_cloud_called": False,
        "private_measurement_run": False,
    }
    return {
        "summary": {
            **_summary_counts(summary),
            "detail_status": detail_status,
            "document_count": len(document_ids),
            "diagnostic_bucket_counts": dict(sorted(bucket_counts.items())),
            "private_values_included": bool(args.include_private_values_local_only),
            "values_redacted": not bool(args.include_private_values_local_only),
            **side_effects,
        },
        "diagnostic_rows": diagnostic_rows,
        "pairing_rows": pairing_rows,
        "candidate_rows": candidate_rows,
        "review_rows": review_rows,
    }


def _write_json(path: Path, payload: Any) -> None:
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
        "# RateCon Load Source-Line Diagnostics",
        "",
        "Local-only diagnostics over existing evaluation/audit artifacts.",
        "Private selected and gold values are redacted unless explicitly included locally.",
        "",
        f"- detail_status: {summary['detail_status']}",
        f"- document_count: {summary['document_count']}",
        f"- private_values_included: {summary['private_values_included']}",
        f"- values_redacted: {summary['values_redacted']}",
        f"- pdf_processing_attempted: {summary['pdf_processing_attempted']}",
        f"- ocr_attempted: {summary['ocr_attempted']}",
        f"- google_called: {summary['google_called']}",
        f"- model_or_cloud_called: {summary['model_or_cloud_called']}",
        "",
        "## Diagnostic Buckets",
    ]
    for bucket, count in summary["diagnostic_bucket_counts"].items():
        lines.append(f"- {bucket}: {count}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(output_dir: Path, payload: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "load_source_line_diagnostics_summary.json", payload)
    _write_report(output_dir / "load_source_line_diagnostics_report.md", payload)
    _write_csv(
        output_dir / "load_source_line_error_cases.csv",
        payload["diagnostic_rows"],
        [
            "document_id",
            "diagnostic_bucket",
            "evidence_source",
            "selected_source",
            "selected_label",
            "selected_line_index",
            "selected_page_index",
            "gold_in_candidates",
            "candidate_count",
            "selected_value",
            "gold_value",
            "private_values_included",
        ],
    )
    _write_csv(
        output_dir / "load_source_line_pairing_diagnostics.csv",
        payload["pairing_rows"],
        [
            "document_id",
            "diagnostic_bucket",
            "selected_source",
            "selected_line_index",
            "selected_page_index",
            "gold_line_index",
            "gold_page_index",
            "layout_ordering_note",
        ],
    )
    _write_csv(
        output_dir / "load_source_line_candidate_presence.csv",
        payload["candidate_rows"],
        [
            "document_id",
            "diagnostic_bucket",
            "candidate_count",
            "gold_in_candidates",
            "candidate_source_line_available",
            "candidate_page_line_available",
        ],
    )
    _write_csv(
        output_dir / "load_source_line_review_items.csv",
        payload["review_rows"],
        ["document_id", "diagnostic_bucket", "recommended_action", "behavior_change_allowed"],
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.confirm_private_local_run:
        raise SystemExit("--confirm-private-local-run is required for this local-only diagnostic.")
    output_dir = _require_output_under_local_outputs(_resolve(args.output_dir))
    payload = build_diagnostics(args)
    write_outputs(output_dir, payload)
    summary = payload["summary"]
    print("RateCon load source-line diagnostics")
    print(f"detail_status: {summary['detail_status']}")
    print(f"document_count: {summary['document_count']}")
    print(f"diagnostic_bucket_counts: {summary['diagnostic_bucket_counts']}")
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
