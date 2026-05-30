"""Safe CSV export for RateCon dry-run summary rows."""

import csv
from pathlib import Path


DEFAULT_CSV_OUTPUT_PATH = Path(
    "data/private_ratecons/dry_run_results/ratecon_dry_run_summary.csv"
)

CSV_COLUMNS = [
    "anonymized_label",
    "extraction_status",
    "page_count",
    "char_count",
    "intake_status",
    "result_category",
    "broker_name_status",
    "broker_mc_status",
    "rate_status",
    "pickup_status",
    "delivery_status",
    "pickup_date_status",
    "delivery_date_status",
    "commodity_status",
    "weight_status",
    "reference_id_status",
    "equipment_status",
    "missing_fields",
    "needs_check_fields",
    "low_confidence_fields",
    "suspected_parser_gap_fields",
    "link_candidate_action",
    "approval_required",
    "generic_warnings",
]

FIELD_STATUS_COLUMNS = {
    "broker_name": "broker_name_status",
    "broker_mc": "broker_mc_status",
    "rate": "rate_status",
    "pickup_location": "pickup_status",
    "delivery_location": "delivery_status",
    "pickup_date": "pickup_date_status",
    "delivery_date": "delivery_date_status",
    "commodity": "commodity_status",
    "weight": "weight_status",
    "reference_id": "reference_id_status",
    "equipment": "equipment_status",
}


def _as_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]

    return [str(value).strip()]


def _join(values):
    return "; ".join(_as_list(values))


def _bool_text(value):
    return "yes" if bool(value) else "no"


def _field_status(field_name, missing_fields, needs_check_fields, low_confidence_fields):
    if field_name in missing_fields:
        return "missing"

    if field_name in needs_check_fields:
        return "needs_check"

    if field_name in low_confidence_fields:
        return "low_confidence"

    return "present_or_not_flagged"


def build_ratecon_dry_run_csv_row(summary):
    safe_summary = dict(summary or {})
    missing_field_list = _as_list(safe_summary.get("missing_fields", []))
    needs_check_field_list = _as_list(safe_summary.get("needs_check_fields", []))
    low_confidence_field_list = _as_list(
        safe_summary.get("low_confidence_fields", [])
    )
    missing_fields = set(missing_field_list)
    needs_check_fields = set(needs_check_field_list)
    low_confidence_fields = set(low_confidence_field_list)
    row = {
        "anonymized_label": str(
            safe_summary.get("anonymized_label")
            or safe_summary.get("label")
            or ""
        ),
        "extraction_status": str(safe_summary.get("extraction_status", "")),
        "page_count": safe_summary.get("page_count", 0),
        "char_count": safe_summary.get("char_count", 0),
        "intake_status": str(safe_summary.get("intake_status", "")),
        "result_category": str(safe_summary.get("result_category", "")),
        "missing_fields": _join(missing_field_list),
        "needs_check_fields": _join(needs_check_field_list),
        "low_confidence_fields": _join(low_confidence_field_list),
        "suspected_parser_gap_fields": _join(
            safe_summary.get("suspected_parser_gap_fields", [])
        ),
        "link_candidate_action": str(safe_summary.get("link_candidate_action", "")),
        "approval_required": _bool_text(safe_summary.get("approval_required", False)),
        "generic_warnings": _join(
            safe_summary.get("generic_warnings", safe_summary.get("warnings", []))
        ),
    }

    for field_name, column_name in FIELD_STATUS_COLUMNS.items():
        row[column_name] = _field_status(
            field_name,
            missing_fields,
            needs_check_fields,
            low_confidence_fields,
        )

    return {column: row.get(column, "") for column in CSV_COLUMNS}


def build_ratecon_dry_run_csv_rows(summaries=None):
    return [build_ratecon_dry_run_csv_row(summary) for summary in summaries or []]


def export_ratecon_dry_run_csv(summaries=None, output_path=DEFAULT_CSV_OUTPUT_PATH):
    rows = build_ratecon_dry_run_csv_rows(summaries)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "output_path": str(path),
        "rows_written": len(rows),
        "columns": list(CSV_COLUMNS),
        "raw_text_saved": False,
        "private_text_saved": False,
        "google_sheets_used": False,
    }
