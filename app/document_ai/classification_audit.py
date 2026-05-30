"""Safe local-only classification audit reports."""

from pathlib import Path


DEFAULT_CLASSIFICATION_AUDIT_REPORT = Path(
    ".local_outputs/private_ratecon_measurement/classification_audit_report.md"
)
DEFAULT_CLASSIFICATION_REVIEW_TEMPLATE = Path(
    ".local_outputs/private_ratecon_measurement/classification_review_template.csv"
)

CLASSIFICATION_REVIEW_COLUMNS = [
    "document_alias",
    "predicted_document_type",
    "predicted_ratecon_eligible",
    "predicted_supplemental_only",
    "predicted_classification_status",
    "page_role_counts",
    "section_role_counts",
    "warning_codes",
    "user_expected_document_type",
    "user_expected_ratecon_eligible",
    "user_notes_local_only_do_not_share",
]


FORBIDDEN_AUDIT_KEYS = {
    "raw_text",
    "private_text",
    "filename",
    "file_name",
    "path",
    "local_path",
    "selected_candidate_value",
    "broker_name_value",
    "rate_value",
}


def _list_text(values):
    if isinstance(values, dict):
        return ", ".join(f"{key}={values[key]}" for key in sorted(values))
    if isinstance(values, (list, tuple, set)):
        return ", ".join(str(value) for value in values if str(value))
    return str(values or "")


def _safe_row(row):
    return {
        "document_alias": row.get("document_alias", ""),
        "document_type": row.get("document_type", ""),
        "ratecon_eligible": bool(row.get("ratecon_eligible", False)),
        "supplemental_only": bool(row.get("supplemental_only", False)),
        "classification_status": row.get("classification_status", ""),
        "confidence_bucket": row.get("classification_confidence_bucket", row.get("confidence_bucket", "")),
        "page_role_counts": row.get("page_role_counts", {}),
        "section_role_counts": row.get("section_role_counts", {}),
        "extraction_scope_counts": row.get("extraction_scope_counts", {}),
        "warning_codes": row.get("classification_warning_codes", row.get("warning_codes", [])),
        "reason_codes": row.get("classification_reason_codes", row.get("classification_reasons", [])),
        "candidate_extraction_skipped": (
            not row.get("candidate_counts_by_field")
            and not row.get("ratecon_eligible", False)
        ),
        "blocker_categories": row.get("blocker_categories", []),
    }


def build_classification_audit_report(rows):
    safe_rows = [
        _safe_row(row)
        for row in rows or []
        if isinstance(row, dict)
    ]

    eligible = [row for row in safe_rows if row["ratecon_eligible"]]
    supplemental = [row for row in safe_rows if row["supplemental_only"]]
    non_ratecon = [
        row
        for row in safe_rows
        if not row["ratecon_eligible"] and not row["supplemental_only"]
    ]

    lines = [
        "# Safe Classification Audit Report",
        "",
        "Local-only report. No raw text, filenames, paths, or private values included.",
        "",
        f"- documents: {len(safe_rows)}",
        f"- ratecon_eligible: {len(eligible)}",
        f"- supplemental_only: {len(supplemental)}",
        f"- non_ratecon_or_unknown: {len(non_ratecon)}",
        "",
        "## Documents",
    ]

    for row in safe_rows:
        lines.extend(
            [
                "",
                f"### {row['document_alias']}",
                "",
                f"- document_type: {row['document_type']}",
                f"- ratecon_eligible: {row['ratecon_eligible']}",
                f"- supplemental_only: {row['supplemental_only']}",
                f"- classification_status: {row['classification_status']}",
                f"- confidence_bucket: {row['confidence_bucket']}",
                f"- candidate_extraction_skipped: {row['candidate_extraction_skipped']}",
                f"- page_role_counts: {_list_text(row['page_role_counts'])}",
                f"- section_role_counts: {_list_text(row['section_role_counts'])}",
                f"- extraction_scope_counts: {_list_text(row['extraction_scope_counts'])}",
                f"- warning_codes: {_list_text(row['warning_codes'])}",
                f"- reason_codes: {_list_text(row['reason_codes'])}",
                f"- blocker_categories: {_list_text(row['blocker_categories'])}",
            ]
        )

    return "\n".join(lines) + "\n"


def assert_safe_classification_audit_payload(text):
    lowered = str(text or "").lower()
    for key in FORBIDDEN_AUDIT_KEYS:
        if f"{key}:" in lowered:
            raise ValueError(f"unsafe classification audit field detected: {key}")


def write_classification_audit_report(rows, output_path=None):
    path = Path(output_path) if output_path else DEFAULT_CLASSIFICATION_AUDIT_REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    text = build_classification_audit_report(rows)
    assert_safe_classification_audit_payload(text)
    path.write_text(text, encoding="utf-8")
    return path


def _csv_escape(value):
    text = str(value or "")
    if any(char in text for char in [",", '"', "\n", "\r"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def build_classification_review_template_csv(rows):
    lines = [",".join(CLASSIFICATION_REVIEW_COLUMNS)]

    for row in rows or []:
        if not isinstance(row, dict):
            continue
        safe = _safe_row(row)
        record = {
            "document_alias": safe["document_alias"],
            "predicted_document_type": safe["document_type"],
            "predicted_ratecon_eligible": str(safe["ratecon_eligible"]),
            "predicted_supplemental_only": str(safe["supplemental_only"]),
            "predicted_classification_status": safe["classification_status"],
            "page_role_counts": _list_text(safe["page_role_counts"]),
            "section_role_counts": _list_text(safe["section_role_counts"]),
            "warning_codes": _list_text(safe["warning_codes"]),
            "user_expected_document_type": "",
            "user_expected_ratecon_eligible": "",
            "user_notes_local_only_do_not_share": "",
        }
        lines.append(
            ",".join(_csv_escape(record[column]) for column in CLASSIFICATION_REVIEW_COLUMNS)
        )

    return "\n".join(lines) + "\n"


def write_classification_review_template_csv(rows, output_path=None):
    path = Path(output_path) if output_path else DEFAULT_CLASSIFICATION_REVIEW_TEMPLATE
    path.parent.mkdir(parents=True, exist_ok=True)
    text = build_classification_review_template_csv(rows)
    assert_safe_classification_audit_payload(text)
    path.write_text(text, encoding="utf-8")
    return path
