"""Local-only normalized stop review packet writers."""

import csv
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.stop_review_pattern_classifier import (
    classify_stop_review_packet_patterns,
)


STOP_REVIEW_PACKET_CSV = "stop_review_packet.csv"
STOP_REVIEW_PACKET_MD = "stop_review_packet.md"
LOCAL_PRIVATE_REVIEW_WARNING = (
    "LOCAL PRIVATE REVIEW ONLY - DO NOT COMMIT - DO NOT PASTE INTO CHAT"
)

SHAREABLE_COLUMNS = [
    "document_alias",
    "stop_id",
    "stop_type",
    "sequence",
    "field_name",
    "status",
    "confidence_bucket",
    "evidence_type",
    "page_number",
    "warning_codes",
]
LOCAL_PRIVATE_COLUMNS = SHAREABLE_COLUMNS + ["selected_value_local_only"]


def _text(value):
    return str(value or "").strip()


def _evidence_type(field):
    refs = field.get("evidence_refs", []) if isinstance(field, dict) else []
    for ref in refs:
        if isinstance(ref, dict) and _text(ref.get("evidence_type")):
            return _text(ref.get("evidence_type"))
    return ""


def _page_number(field):
    refs = field.get("evidence_refs", []) if isinstance(field, dict) else []
    for ref in refs:
        if isinstance(ref, dict) and _text(ref.get("page_number")):
            return _text(ref.get("page_number"))
    return ""


def _selected_value(field):
    return _text((field or {}).get("selected_value") or (field or {}).get("value"))


def stop_review_rows(stop_sets, include_private_values_local_only=False):
    rows = []
    for stop_set in stop_sets or []:
        if not isinstance(stop_set, dict):
            continue
        alias = _text(stop_set.get("document_alias"))
        for stop in stop_set.get("stops", []) or []:
            if not isinstance(stop, dict):
                continue
            for field in stop.get("fields", []) or []:
                if not isinstance(field, dict):
                    continue
                row = {
                    "document_alias": alias,
                    "stop_id": _text(stop.get("stop_id")),
                    "stop_type": _text(stop.get("stop_type")),
                    "sequence": _text(stop.get("sequence")),
                    "field_name": _text(field.get("field_name")),
                    "status": _text(field.get("status")),
                    "confidence_bucket": _text(field.get("confidence")),
                    "evidence_type": _evidence_type(field),
                    "page_number": _page_number(field),
                    "warning_codes": ";".join(field.get("warning_codes", []) or []),
                }
                if include_private_values_local_only:
                    row["selected_value_local_only"] = _selected_value(field)
                rows.append(row)
    return rows


def _field_status_count(rows, field_name, statuses):
    allowed = {str(status) for status in statuses}
    return sum(
        1
        for row in rows or []
        if _text(row.get("field_name")) == field_name
        and _text(row.get("status")) in allowed
    )


def _warning_count(stop_sets, warning_code):
    return sum(
        1
        for stop_set in stop_sets or []
        if isinstance(stop_set, dict)
        for stop in stop_set.get("stops", []) or []
        if isinstance(stop, dict)
        and warning_code in (stop.get("warning_codes", []) or [])
    )


def build_stop_review_packet_summary(stop_sets):
    safe_stop_sets = [stop_set for stop_set in stop_sets or [] if isinstance(stop_set, dict)]
    rows = stop_review_rows(safe_stop_sets)
    patterns = classify_stop_review_packet_patterns(rows)
    attached_statuses = {
        "resolved",
        "low_confidence",
        "conflict",
        "review_required",
    }
    date_generated = _field_status_count(rows, "date", attached_statuses)
    time_generated = _field_status_count(rows, "time", attached_statuses)
    unknown_count = sum(int(stop_set.get("unknown_count", 0) or 0) for stop_set in safe_stop_sets)
    duplicate_removed = sum(
        int(stop_set.get("stop_duplicate_removed_count", 0) or 0)
        for stop_set in safe_stop_sets
    )
    noise_removed = sum(
        int(stop_set.get("stop_noise_removed_count", 0) or 0)
        for stop_set in safe_stop_sets
    )
    pattern_counts = patterns.get("pattern_counts", {})
    return {
        "stop_pattern_counts": pattern_counts,
        "table_row_merge_count": sum(
            int(stop_set.get("table_row_merge_count", 0) or 0)
            for stop_set in safe_stop_sets
        ),
        "section_context_merge_count": sum(
            int(stop_set.get("section_context_merge_count", 0) or 0)
            for stop_set in safe_stop_sets
        ),
        "date_candidate_generated_count": date_generated,
        "date_candidate_attached_count": date_generated,
        "time_candidate_generated_count": time_generated,
        "time_candidate_attached_count": time_generated,
        "overclassified_stop_count": _warning_count(
            safe_stop_sets,
            "stop_type_overclassified_review_required",
        ),
        "ambiguous_stop_count": unknown_count,
        "duplicate_like_stop_count": duplicate_removed
        + int(pattern_counts.get("DUPLICATE_STOP_GROUPS", 0) or 0),
        "noise_removed_count": noise_removed,
        "unresolved_due_to_missing_date": _field_status_count(rows, "date", {"missing"}),
        "unresolved_due_to_ambiguous_type": unknown_count,
        "private_values_included": False,
        "raw_text_included": False,
    }


def _write_csv(path, rows, include_private_values_local_only=False):
    columns = LOCAL_PRIVATE_COLUMNS if include_private_values_local_only else SHAREABLE_COLUMNS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _write_md(path, rows, include_private_values_local_only=False):
    columns = LOCAL_PRIVATE_COLUMNS if include_private_values_local_only else SHAREABLE_COLUMNS
    lines = ["# Normalized Stop Review Packet", ""]
    if include_private_values_local_only:
        lines.extend([LOCAL_PRIVATE_REVIEW_WARNING, ""])
    else:
        lines.extend(["No private values included.", ""])

    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(_text(row.get(column)) for column in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_stop_review_packet(
    stop_sets,
    output_dir=None,
    include_private_values_local_only=False,
):
    output_root = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    output_root.mkdir(parents=True, exist_ok=True)
    rows = stop_review_rows(
        stop_sets,
        include_private_values_local_only=include_private_values_local_only,
    )
    csv_path = output_root / STOP_REVIEW_PACKET_CSV
    md_path = output_root / STOP_REVIEW_PACKET_MD
    _write_csv(
        csv_path,
        rows,
        include_private_values_local_only=include_private_values_local_only,
    )
    _write_md(
        md_path,
        rows,
        include_private_values_local_only=include_private_values_local_only,
    )
    return {
        "csv": csv_path,
        "md": md_path,
        "row_count": len(rows),
        "include_private_values_local_only": bool(include_private_values_local_only),
        "raw_text_included": False,
    }
