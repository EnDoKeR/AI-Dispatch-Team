"""Local-only RateCon review workbook row contracts and writers.

The workbook rows are designed for ignored local review artifacts. Console and
shareable summaries should only use the count metadata returned by this module.
"""

import csv
from pathlib import Path

from app.document_ai.extraction_readiness import assess_extraction_readiness
from app.document_ai.measurement_integrity import (
    check_measurement_row_integrity,
    summarize_integrity_issues,
)
from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    _normalize_output_dir,
)
from app.document_ai.ratecon_candidates import normalize_list


REVIEW_WORKBOOK_XLSX = "ratecon_review_workbook.xlsx"
REVIEW_DOCUMENT_SUMMARY_CSV = "ratecon_review_document_summary.csv"
REVIEW_STOP_REVIEW_CSV = "ratecon_review_stop_review.csv"
REVIEW_FIELD_REVIEW_CSV = "ratecon_review_field_review.csv"
REVIEW_RATE_REVIEW_CSV = "ratecon_review_rate_review.csv"

SHEET_DOCUMENT_SUMMARY = "Document_Summary"
SHEET_STOP_REVIEW = "Stop_Review"
SHEET_FIELD_REVIEW = "Field_Review"
SHEET_RATE_REVIEW = "Rate_Review"
SHEET_INSTRUCTIONS = "Instructions"

DOCUMENT_SUMMARY_COLUMNS = [
    "Folder Order",
    "Local Document Name / File Stem",
    "Measurement Alias",
    "Document Type",
    "Classification Status",
    "Extraction Relevant",
    "Normal Load Movement",
    "TONU",
    "OCR Needed",
    "Layout Attempted",
    "Provider Status",
    "Old Raw Stop Groups",
    "Old Normalized Stops",
    "Span Anchors",
    "Stop Spans",
    "Span Normalized Stops",
    "Pickup Count",
    "Delivery Count",
    "Unknown Count",
    "Date Resolved",
    "Date Missing",
    "Time Resolved",
    "Time Missing",
    "Review Required Stops",
    "Readiness Level",
    "Top Blocker",
    "Integrity Issues",
    "Recommended Review Priority",
    "User Review Status",
    "User Notes Local Only",
]

STOP_REVIEW_COLUMNS = [
    "Folder Order",
    "Local Document Name / File Stem",
    "Measurement Alias",
    "Stop ID",
    "Stop Sequence",
    "Stop Type",
    "Field Name",
    "Predicted Value LOCAL ONLY",
    "Status",
    "Confidence Bucket",
    "Evidence Type",
    "Page Number",
    "Source",
    "Needs Review",
    "Integrity Issue",
    "User Correct? yes/no/unknown",
    "User Expected Value LOCAL ONLY",
    "User Issue Type",
    "User Notes Local Only",
]

FIELD_REVIEW_COLUMNS = [
    "Folder Order",
    "Local Document Name / File Stem",
    "Measurement Alias",
    "Field Name",
    "Predicted Value LOCAL ONLY",
    "Status",
    "Confidence Bucket",
    "Evidence Type",
    "Needs Review",
    "User Correct? yes/no/unknown",
    "User Expected Value LOCAL ONLY",
    "User Issue Type",
    "User Notes Local Only",
]

RATE_REVIEW_COLUMNS = [
    "Measurement Alias",
    "Rate Field Type",
    "Predicted Value LOCAL ONLY",
    "Status",
    "Evidence Type",
    "Main Rate? yes/no/unknown",
    "User Correct? yes/no/unknown",
]

INSTRUCTIONS_COLUMNS = ["Section", "Instruction"]

REVIEW_WORKBOOK_COLUMNS_BY_SHEET = {
    SHEET_DOCUMENT_SUMMARY: DOCUMENT_SUMMARY_COLUMNS,
    SHEET_STOP_REVIEW: STOP_REVIEW_COLUMNS,
    SHEET_FIELD_REVIEW: FIELD_REVIEW_COLUMNS,
    SHEET_RATE_REVIEW: RATE_REVIEW_COLUMNS,
    SHEET_INSTRUCTIONS: INSTRUCTIONS_COLUMNS,
}

LOCAL_PRIVATE_REVIEW_WARNING = (
    "LOCAL PRIVATE REVIEW ONLY - DO NOT COMMIT - DO NOT PASTE INTO CHAT"
)

RATE_REVIEW_FIELD_NAMES = {
    "rate",
    "payment_amount",
    "linehaul",
    "fuel_surcharge",
    "accessorial",
    "detention",
    "tonu_payment",
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool_text(value):
    return "yes" if bool(value) else "no"


def _join(values):
    return ";".join(normalize_list(values))


def _selected_value(item, include_private_values=False):
    if not include_private_values or not isinstance(item, dict):
        return ""
    for key in (
        "selected_value",
        "predicted_value",
        "value",
        "extracted_value",
        "value_text",
    ):
        value = _text(item.get(key))
        if value:
            return value
    return ""


def _first_evidence_ref(field):
    refs = (field or {}).get("evidence_refs", []) if isinstance(field, dict) else []
    for ref in refs:
        if isinstance(ref, dict):
            return ref
    return {}


def _evidence_type(item):
    if not isinstance(item, dict):
        return ""
    if _text(item.get("evidence_type")):
        return _text(item.get("evidence_type"))
    ref = _first_evidence_ref(item)
    return _text(ref.get("evidence_type"))


def _page_number(item):
    if not isinstance(item, dict):
        return ""
    if _text(item.get("page_number")):
        return _text(item.get("page_number"))
    ref = _first_evidence_ref(item)
    return _text(ref.get("page_number"))


def _field_status(row, field_name):
    for field_status in (row or {}).get("field_statuses", []) or []:
        if isinstance(field_status, dict) and _token(field_status.get("field_name")) == field_name:
            return _text(field_status.get("status"))
    return ""


def _top_blocker(row):
    blockers = normalize_list((row or {}).get("blocker_categories", []))
    return blockers[0] if blockers else ""


def _layout_attempted(row):
    status = _text((row or {}).get("layout_provider_status"))
    return bool(status) and not status.startswith("skipped")


def _review_priority(row, integrity_issues, readiness):
    if integrity_issues:
        return "integrity_check"
    if readiness.get("readiness_level") == "not_ready":
        return "high"
    if _int((row or {}).get("span_review_required_count")):
        return "stop_review"
    if _int((row or {}).get("old_normalized_stops")) > _int(
        (row or {}).get("span_normalized_stop_count")
    ):
        return "value_review"
    return "normal"


def _stop_set_for_review(row):
    span_stop_set = (row or {}).get("span_normalized_stop_set", {}) or {}
    if span_stop_set.get("stops"):
        return span_stop_set, "span_normalized_stop_set"
    return (row or {}).get("normalized_stop_set", {}) or {}, "normalized_stop_set"


def _stop_needs_review(stop, field):
    return bool((stop or {}).get("review_required")) or _text((field or {}).get("status")) in {
        "missing",
        "low_confidence",
        "conflict",
        "review_required",
        "needs_review",
    }


def _integrity_issue_codes(row):
    return [issue.get("issue_code", "") for issue in check_measurement_row_integrity(row)]


def _field_review_rows(row, folder_order, local_name, include_private_values=False):
    rows = []
    alias = _text((row or {}).get("document_alias"))
    seen = set()
    for field in (row or {}).get("field_statuses", []) or []:
        if not isinstance(field, dict):
            continue
        field_name = _token(field.get("field_name"))
        if not field_name:
            continue
        seen.add(field_name)
        status = _text(field.get("status"))
        rows.append(
            {
                "Folder Order": folder_order,
                "Local Document Name / File Stem": local_name,
                "Measurement Alias": alias,
                "Field Name": field_name,
                "Predicted Value LOCAL ONLY": _selected_value(
                    field,
                    include_private_values=include_private_values,
                ),
                "Status": status,
                "Confidence Bucket": _text(field.get("confidence")),
                "Evidence Type": _evidence_type(field),
                "Needs Review": _bool_text(
                    status
                    in {"missing", "low_confidence", "conflict", "needs_review"}
                ),
                "User Correct? yes/no/unknown": "",
                "User Expected Value LOCAL ONLY": "",
                "User Issue Type": "",
                "User Notes Local Only": "",
            }
        )

    for field_name in normalize_list((row or {}).get("missing_fields", [])):
        token = _token(field_name)
        if token and token not in seen:
            rows.append(
                {
                    "Folder Order": folder_order,
                    "Local Document Name / File Stem": local_name,
                    "Measurement Alias": alias,
                    "Field Name": token,
                    "Predicted Value LOCAL ONLY": "",
                    "Status": "missing",
                    "Confidence Bucket": "",
                    "Evidence Type": "",
                    "Needs Review": "yes",
                    "User Correct? yes/no/unknown": "",
                    "User Expected Value LOCAL ONLY": "",
                    "User Issue Type": "",
                    "User Notes Local Only": "",
                }
            )
    return rows


def _rate_review_rows(field_rows):
    rows = []
    for field_row in field_rows or []:
        if _token(field_row.get("Field Name")) not in RATE_REVIEW_FIELD_NAMES:
            continue
        rows.append(
            {
                "Measurement Alias": field_row.get("Measurement Alias", ""),
                "Rate Field Type": field_row.get("Field Name", ""),
                "Predicted Value LOCAL ONLY": field_row.get(
                    "Predicted Value LOCAL ONLY",
                    "",
                ),
                "Status": field_row.get("Status", ""),
                "Evidence Type": field_row.get("Evidence Type", ""),
                "Main Rate? yes/no/unknown": "",
                "User Correct? yes/no/unknown": "",
            }
        )
    return rows


def _stop_review_rows(row, folder_order, local_name, include_private_values=False):
    stop_set, source = _stop_set_for_review(row)
    alias = _text((row or {}).get("document_alias"))
    integrity_codes = _join(_integrity_issue_codes(row))
    rows = []
    for stop in stop_set.get("stops", []) or []:
        if not isinstance(stop, dict):
            continue
        for field in stop.get("fields", []) or []:
            if not isinstance(field, dict):
                continue
            rows.append(
                {
                    "Folder Order": folder_order,
                    "Local Document Name / File Stem": local_name,
                    "Measurement Alias": alias,
                    "Stop ID": _text(stop.get("stop_id")),
                    "Stop Sequence": _text(stop.get("sequence")),
                    "Stop Type": _text(stop.get("stop_type")),
                    "Field Name": _text(field.get("field_name")),
                    "Predicted Value LOCAL ONLY": _selected_value(
                        field,
                        include_private_values=include_private_values,
                    ),
                    "Status": _text(field.get("status")),
                    "Confidence Bucket": _text(field.get("confidence")),
                    "Evidence Type": _evidence_type(field),
                    "Page Number": _page_number(field),
                    "Source": source,
                    "Needs Review": _bool_text(_stop_needs_review(stop, field)),
                    "Integrity Issue": integrity_codes,
                    "User Correct? yes/no/unknown": "",
                    "User Expected Value LOCAL ONLY": "",
                    "User Issue Type": "",
                    "User Notes Local Only": "",
                }
            )
    return rows


def _document_summary_row(row, folder_order, local_name):
    readiness = assess_extraction_readiness(row)
    issues = check_measurement_row_integrity(row)
    issue_codes = [issue.get("issue_code", "") for issue in issues]
    return {
        "Folder Order": folder_order,
        "Local Document Name / File Stem": local_name,
        "Measurement Alias": _text((row or {}).get("document_alias")),
        "Document Type": _text((row or {}).get("document_type")),
        "Classification Status": _text((row or {}).get("classification_status")),
        "Extraction Relevant": _bool_text((row or {}).get("extraction_relevant")),
        "Normal Load Movement": _bool_text((row or {}).get("normal_load_movement")),
        "TONU": _bool_text(_text((row or {}).get("document_type")).upper() == "TRUCK_ORDER_NOT_USED"),
        "OCR Needed": _bool_text((row or {}).get("extraction_status") == "EMPTY_TEXT"),
        "Layout Attempted": _bool_text(_layout_attempted(row)),
        "Provider Status": _text((row or {}).get("layout_provider_status")),
        "Old Raw Stop Groups": _int((row or {}).get("old_raw_stop_groups", (row or {}).get("raw_stop_group_count"))),
        "Old Normalized Stops": _int((row or {}).get("old_normalized_stops", (row or {}).get("normalized_stop_count"))),
        "Span Anchors": _int((row or {}).get("span_anchor_count")),
        "Stop Spans": _int((row or {}).get("stop_span_count")),
        "Span Normalized Stops": _int((row or {}).get("span_normalized_stop_count")),
        "Pickup Count": _int((row or {}).get("span_pickup_count", (row or {}).get("pickup_count"))),
        "Delivery Count": _int((row or {}).get("span_delivery_count", (row or {}).get("delivery_count"))),
        "Unknown Count": _int((row or {}).get("span_unknown_count", (row or {}).get("unknown_stop_count"))),
        "Date Resolved": _int((row or {}).get("span_date_resolved_count")),
        "Date Missing": _int((row or {}).get("span_date_missing_count")),
        "Time Resolved": _int((row or {}).get("span_time_resolved_count")),
        "Time Missing": _int((row or {}).get("span_time_missing_count")),
        "Review Required Stops": _int((row or {}).get("span_review_required_count")),
        "Readiness Level": readiness.get("readiness_level", "not_ready"),
        "Top Blocker": _top_blocker(row),
        "Integrity Issues": _join(issue_codes),
        "Recommended Review Priority": _review_priority(row, issues, readiness),
        "User Review Status": "",
        "User Notes Local Only": "",
    }


def _instruction_rows(include_private_values=False):
    rows = [
        {
            "Section": "Local-only warning",
            "Instruction": LOCAL_PRIVATE_REVIEW_WARNING,
        },
        {
            "Section": "Review order",
            "Instruction": "Review Document_Summary first, then Stop_Review, Field_Review, and Rate_Review.",
        },
        {
            "Section": "Safe sharing",
            "Instruction": "Share aliases, counts, statuses, issue types, and field names only.",
        },
        {
            "Section": "Do not share",
            "Instruction": "Do not share private values, raw text, local paths, broker names, rates, addresses, or references.",
        },
    ]
    if include_private_values:
        rows.append(
            {
                "Section": "Private values",
                "Instruction": "Predicted values are included only for local review. Do not paste workbook rows into chat.",
            }
        )
    else:
        rows.append(
            {
                "Section": "Private values",
                "Instruction": "Predicted value columns are intentionally blank in redacted mode.",
            }
        )
    return rows


def build_ratecon_review_rows(
    measurement_rows,
    local_document_names_by_alias=None,
    include_private_values=False,
):
    local_names = local_document_names_by_alias or {}
    document_rows = []
    stop_rows = []
    field_rows = []
    rate_rows = []

    for folder_order, row in enumerate(measurement_rows or [], start=1):
        if not isinstance(row, dict):
            continue
        alias = _text(row.get("document_alias"))
        local_name = _text(local_names.get(alias))
        document_rows.append(_document_summary_row(row, folder_order, local_name))
        row_stop_rows = _stop_review_rows(
            row,
            folder_order,
            local_name,
            include_private_values=include_private_values,
        )
        row_field_rows = _field_review_rows(
            row,
            folder_order,
            local_name,
            include_private_values=include_private_values,
        )
        stop_rows.extend(row_stop_rows)
        field_rows.extend(row_field_rows)
        rate_rows.extend(_rate_review_rows(row_field_rows))

    return {
        SHEET_DOCUMENT_SUMMARY: document_rows,
        SHEET_STOP_REVIEW: stop_rows,
        SHEET_FIELD_REVIEW: field_rows,
        SHEET_RATE_REVIEW: rate_rows,
        SHEET_INSTRUCTIONS: _instruction_rows(
            include_private_values=include_private_values
        ),
    }


def summarize_ratecon_review_workbook_rows(rows_by_sheet):
    document_rows = (rows_by_sheet or {}).get(SHEET_DOCUMENT_SUMMARY, []) or []
    readiness_counts = {}
    for row in document_rows:
        level = _text(row.get("Readiness Level"))
        if level:
            readiness_counts[level] = readiness_counts.get(level, 0) + 1

    issue_codes = []
    for row in document_rows:
        issue_codes.extend(normalize_list(row.get("Integrity Issues", "").split(";")))
    integrity_summary = summarize_integrity_issues(
        [{"issue_code": code, "severity": "warning"} for code in issue_codes if code]
    )
    return {
        "document_rows": len(document_rows),
        "stop_review_rows": len((rows_by_sheet or {}).get(SHEET_STOP_REVIEW, []) or []),
        "field_review_rows": len((rows_by_sheet or {}).get(SHEET_FIELD_REVIEW, []) or []),
        "rate_review_rows": len((rows_by_sheet or {}).get(SHEET_RATE_REVIEW, []) or []),
        "readiness_level_counts": dict(sorted(readiness_counts.items())),
        "integrity_issue_counts": integrity_summary.get("issue_counts", {}),
        "raw_text_included": False,
        "private_values_printed": False,
    }


def _write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows or []:
            writer.writerow({column: row.get(column, "") for column in columns})


def write_ratecon_review_csvs(
    measurement_rows,
    output_dir=None,
    local_document_names_by_alias=None,
    include_private_values=False,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    rows_by_sheet = build_ratecon_review_rows(
        measurement_rows,
        local_document_names_by_alias=local_document_names_by_alias,
        include_private_values=include_private_values,
    )
    csv_specs = {
        "document_summary_csv": (
            REVIEW_DOCUMENT_SUMMARY_CSV,
            SHEET_DOCUMENT_SUMMARY,
            DOCUMENT_SUMMARY_COLUMNS,
        ),
        "stop_review_csv": (
            REVIEW_STOP_REVIEW_CSV,
            SHEET_STOP_REVIEW,
            STOP_REVIEW_COLUMNS,
        ),
        "field_review_csv": (
            REVIEW_FIELD_REVIEW_CSV,
            SHEET_FIELD_REVIEW,
            FIELD_REVIEW_COLUMNS,
        ),
        "rate_review_csv": (
            REVIEW_RATE_REVIEW_CSV,
            SHEET_RATE_REVIEW,
            RATE_REVIEW_COLUMNS,
        ),
    }
    paths = {}
    for key, (filename, sheet_name, columns) in csv_specs.items():
        path = output_root / filename
        _write_csv(path, rows_by_sheet.get(sheet_name, []), columns)
        paths[key] = path

    return {
        "paths": paths,
        "rows_by_sheet": rows_by_sheet,
        "summary": summarize_ratecon_review_workbook_rows(rows_by_sheet),
        "include_private_values_local_only": bool(include_private_values),
        "local_only": True,
        "raw_text_included": False,
        "private_values_printed": False,
    }


def _write_xlsx_if_available(path, rows_by_sheet):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill
        from openpyxl.utils import get_column_letter
    except Exception:
        return False

    workbook = Workbook()
    default_sheet = workbook.active
    workbook.remove(default_sheet)
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    warning_fill = PatternFill("solid", fgColor="FDE68A")

    for sheet_name, columns in REVIEW_WORKBOOK_COLUMNS_BY_SHEET.items():
        sheet = workbook.create_sheet(title=sheet_name)
        sheet.append(columns)
        for row in rows_by_sheet.get(sheet_name, []) or []:
            sheet.append([row.get(column, "") for column in columns])

        for cell in sheet[1]:
            cell.font = Font(bold=True)
            cell.fill = header_fill
        if sheet_name == SHEET_INSTRUCTIONS:
            for cell in sheet[2]:
                cell.fill = warning_fill
                cell.font = Font(bold=True)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for index, column in enumerate(columns, start=1):
            width = min(max(len(column) + 2, 12), 42)
            sheet.column_dimensions[get_column_letter(index)].width = width

    workbook.save(path)
    return True


def write_ratecon_review_workbook(
    measurement_rows,
    output_dir=None,
    local_document_names_by_alias=None,
    include_private_values=False,
    allow_custom_output_dir=False,
):
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    rows_by_sheet = build_ratecon_review_rows(
        measurement_rows,
        local_document_names_by_alias=local_document_names_by_alias,
        include_private_values=include_private_values,
    )
    xlsx_path = output_root / REVIEW_WORKBOOK_XLSX
    xlsx_written = _write_xlsx_if_available(xlsx_path, rows_by_sheet)
    return {
        "xlsx": xlsx_path if xlsx_written else None,
        "rows_by_sheet": rows_by_sheet,
        "summary": summarize_ratecon_review_workbook_rows(rows_by_sheet),
        "include_private_values_local_only": bool(include_private_values),
        "local_only": True,
        "raw_text_included": False,
        "private_values_printed": False,
    }


def write_ratecon_review_artifacts(
    measurement_rows,
    output_dir=None,
    local_document_names_by_alias=None,
    include_private_values=False,
    write_workbook=True,
    write_csvs=True,
    allow_custom_output_dir=False,
):
    rows_by_sheet = build_ratecon_review_rows(
        measurement_rows,
        local_document_names_by_alias=local_document_names_by_alias,
        include_private_values=include_private_values,
    )
    output_root = _normalize_output_dir(
        output_dir or DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
        allow_custom_output_dir=allow_custom_output_dir,
    )
    paths = {}
    csv_result = None
    if write_csvs:
        csv_result = write_ratecon_review_csvs(
            measurement_rows,
            output_dir=output_root,
            local_document_names_by_alias=local_document_names_by_alias,
            include_private_values=include_private_values,
            allow_custom_output_dir=True,
        )
        paths.update(csv_result["paths"])
    workbook_result = None
    if write_workbook:
        workbook_result = write_ratecon_review_workbook(
            measurement_rows,
            output_dir=output_root,
            local_document_names_by_alias=local_document_names_by_alias,
            include_private_values=include_private_values,
            allow_custom_output_dir=True,
        )
        if workbook_result.get("xlsx"):
            paths["review_workbook_xlsx"] = workbook_result["xlsx"]

    return {
        "paths": paths,
        "rows_by_sheet": rows_by_sheet,
        "summary": summarize_ratecon_review_workbook_rows(rows_by_sheet),
        "xlsx_written": bool(workbook_result and workbook_result.get("xlsx")),
        "csvs_written": bool(csv_result),
        "include_private_values_local_only": bool(include_private_values),
        "local_only": True,
        "raw_text_included": False,
        "private_values_printed": False,
    }
