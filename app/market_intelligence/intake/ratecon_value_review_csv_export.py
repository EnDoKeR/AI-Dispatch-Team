"""Local-only CSV export for private RateCon value review."""

import csv
from pathlib import Path

from app.market_intelligence.intake.ratecon_core_fields import (
    DEFERRED_GOOGLE_MAPS,
    NOT_FROM_RATECON,
)


DEFAULT_VALUE_REVIEW_CSV_PATH = Path(
    "data/private_ratecons/dry_run_results/ratecon_value_review.csv"
)

VALUE_REVIEW_COLUMNS = [
    "anonymized_label",
    "customer_name",
    "load_label",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "load_number",
    "loaded_miles",
    "miles_status",
    "miles_source",
    "rate",
    "commodity",
    "weight",
    "missing_core_fields",
    "optional_missing_fields",
    "deferred_fields",
    "needs_check_fields",
    "low_confidence_fields",
    "result_category",
    "generic_warnings",
]


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


def _low_confidence_fields(parser_output):
    field_confidence = parser_output.get("field_confidence", {})

    if not isinstance(field_confidence, dict):
        return []

    return sorted(
        field_name
        for field_name, confidence in field_confidence.items()
        if str(confidence or "").strip().upper() == "LOW"
    )


def build_ratecon_value_review_csv_row(summary):
    safe_summary = dict(summary or {})
    parser_output = dict(safe_summary.get("parser_output") or {})
    core_summary = dict(safe_summary.get("ratecon_core_summary") or {})
    intake_summary = dict(safe_summary.get("intake_summary") or {})

    row = {
        "anonymized_label": str(
            safe_summary.get("anonymized_label")
            or safe_summary.get("label")
            or ""
        ),
        "customer_name": str(
            parser_output.get("customer_name")
            or parser_output.get("broker_name")
            or ""
        ),
        "load_label": str(parser_output.get("load_label", "")),
        "pickup_location": str(parser_output.get("pickup_location", "")),
        "pickup_date": str(parser_output.get("pickup_date", "")),
        "delivery_location": str(parser_output.get("delivery_location", "")),
        "delivery_date": str(parser_output.get("delivery_date", "")),
        "load_number": str(
            parser_output.get("load_number")
            or parser_output.get("reference_id")
            or ""
        ),
        "loaded_miles": str(core_summary.get("loaded_miles", "")),
        "miles_status": str(
            core_summary.get("miles_status") or DEFERRED_GOOGLE_MAPS
        ),
        "miles_source": str(
            core_summary.get("miles_source") or NOT_FROM_RATECON
        ),
        "rate": parser_output.get("rate", ""),
        "commodity": str(parser_output.get("commodity", "")),
        "weight": parser_output.get("weight", ""),
        "missing_core_fields": _join(core_summary.get("missing_core_fields", [])),
        "optional_missing_fields": _join(
            core_summary.get("optional_missing_fields", [])
        ),
        "deferred_fields": _join(core_summary.get("deferred_fields", [])),
        "needs_check_fields": _join(intake_summary.get("needs_check_fields", [])),
        "low_confidence_fields": _join(_low_confidence_fields(parser_output)),
        "result_category": str(safe_summary.get("result_category", "")),
        "generic_warnings": _join(safe_summary.get("warnings", [])),
    }

    return {column: row.get(column, "") for column in VALUE_REVIEW_COLUMNS}


def build_ratecon_value_review_csv_rows(summaries=None):
    return [
        build_ratecon_value_review_csv_row(summary)
        for summary in summaries or []
    ]


def export_ratecon_value_review_csv(
    summaries=None,
    output_path=DEFAULT_VALUE_REVIEW_CSV_PATH,
):
    rows = build_ratecon_value_review_csv_rows(summaries)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=VALUE_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "output_path": str(path),
        "rows_written": len(rows),
        "columns": list(VALUE_REVIEW_COLUMNS),
        "raw_text_saved": False,
        "private_text_saved": False,
        "google_sheets_used": False,
    }
