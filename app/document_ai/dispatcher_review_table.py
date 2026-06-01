"""Dispatcher-style local review table contracts and helpers.

Dispatcher review rows may contain private predicted values when explicitly
written to ignored local files. Feedback rows and aggregates are safe summaries:
they keep only booleans, counts, aliases, field names, and issue types.
"""

from collections import Counter

from app.document_ai.review_issue_taxonomy import (
    REVIEW_ISSUE_TYPE_BROKER_MISSING,
    REVIEW_ISSUE_TYPE_EXTRA_VALUE,
    REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
    REVIEW_ISSUE_TYPE_MISSING_VALUE,
    REVIEW_ISSUE_TYPE_OTHER,
    REVIEW_ISSUE_TYPE_WRONG_BROKER,
    REVIEW_ISSUE_TYPE_WRONG_DATE,
    REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
    REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
    REVIEW_ISSUE_TYPE_WRONG_PICKUP,
    REVIEW_ISSUE_TYPE_WRONG_RATE,
    REVIEW_ISSUE_TYPE_WRONG_VALUE,
    normalize_review_issue_type,
)
from app.document_ai.review_feedback_target_selector import (
    select_repair_target_from_feedback,
)


DISPATCHER_REVIEW_TABLE_VERSION = "dispatcher_review_table_v3"

DISPATCHER_FIELD_BROKER = "broker"
DISPATCHER_FIELD_PICKUP = "pickup"
DISPATCHER_FIELD_PICKUP_DATE = "pickup_date"
DISPATCHER_FIELD_DELIVERY = "delivery"
DISPATCHER_FIELD_DELIVERY_DATE = "delivery_date"
DISPATCHER_FIELD_LOAD_NUMBER = "load_number"
DISPATCHER_FIELD_CARRIER = "carrier"
DISPATCHER_FIELD_TRAILER_TYPE = "trailer_type"
DISPATCHER_FIELD_COMMODITY = "commodity"
DISPATCHER_FIELD_TOTAL_WEIGHT = "total_weight"
DISPATCHER_FIELD_FINAL_RATE = "final_rate"
DISPATCHER_FIELD_SPECIAL_REQUIREMENTS = "special_requirements"

DISPATCHER_EDITABLE_FIELDS = [
    DISPATCHER_FIELD_BROKER,
    DISPATCHER_FIELD_PICKUP,
    DISPATCHER_FIELD_PICKUP_DATE,
    DISPATCHER_FIELD_DELIVERY,
    DISPATCHER_FIELD_DELIVERY_DATE,
    DISPATCHER_FIELD_LOAD_NUMBER,
    DISPATCHER_FIELD_CARRIER,
    DISPATCHER_FIELD_TRAILER_TYPE,
    DISPATCHER_FIELD_COMMODITY,
    DISPATCHER_FIELD_TOTAL_WEIGHT,
    DISPATCHER_FIELD_FINAL_RATE,
    DISPATCHER_FIELD_SPECIAL_REQUIREMENTS,
]

FIELD_TO_REVIEW_COLUMN = {
    DISPATCHER_FIELD_BROKER: "Broker",
    DISPATCHER_FIELD_PICKUP: "Pickup",
    DISPATCHER_FIELD_PICKUP_DATE: "Pickup Date",
    DISPATCHER_FIELD_DELIVERY: "Delivery",
    DISPATCHER_FIELD_DELIVERY_DATE: "Delivery Date",
    DISPATCHER_FIELD_LOAD_NUMBER: "Load No",
    DISPATCHER_FIELD_CARRIER: "Carrier",
    DISPATCHER_FIELD_TRAILER_TYPE: "Trailer Type",
    DISPATCHER_FIELD_COMMODITY: "Commodity",
    DISPATCHER_FIELD_TOTAL_WEIGHT: "Total Weight",
    DISPATCHER_FIELD_FINAL_RATE: "Final Rate",
    DISPATCHER_FIELD_SPECIAL_REQUIREMENTS: "Special Requirements",
}

FIELD_TO_CORRECTION_COLUMN = {
    field_name: f"User Corrected {column_name}"
    for field_name, column_name in FIELD_TO_REVIEW_COLUMN.items()
}

FIELD_TO_DEFAULT_ISSUE = {
    DISPATCHER_FIELD_BROKER: REVIEW_ISSUE_TYPE_WRONG_BROKER,
    DISPATCHER_FIELD_PICKUP: REVIEW_ISSUE_TYPE_WRONG_PICKUP,
    DISPATCHER_FIELD_PICKUP_DATE: REVIEW_ISSUE_TYPE_WRONG_DATE,
    DISPATCHER_FIELD_DELIVERY: REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
    DISPATCHER_FIELD_DELIVERY_DATE: REVIEW_ISSUE_TYPE_WRONG_DATE,
    DISPATCHER_FIELD_LOAD_NUMBER: REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
    DISPATCHER_FIELD_FINAL_RATE: REVIEW_ISSUE_TYPE_WRONG_RATE,
}

FIELD_TO_MISSING_ISSUE = {
    DISPATCHER_FIELD_BROKER: REVIEW_ISSUE_TYPE_BROKER_MISSING,
    DISPATCHER_FIELD_LOAD_NUMBER: REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
    DISPATCHER_FIELD_FINAL_RATE: REVIEW_ISSUE_TYPE_WRONG_RATE,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def _bool_text(value):
    return "yes" if bool(value) else "no"


def _normalize_compare(value):
    return " ".join(_text(value).split()).casefold()


def build_dispatcher_review_row(
    folder_order="",
    local_document_name_or_file_stem="",
    measurement_alias="",
    document_type="",
    ocr_needed=False,
    extraction_relevant=True,
    readiness_level="",
    review_priority="",
    source="local_review_outputs",
    broker="",
    pickup="",
    pickup_date="",
    delivery="",
    delivery_date="",
    load_number="",
    carrier="",
    trailer_type="",
    commodity="",
    total_weight="",
    final_rate="",
    special_requirements="",
    top_blockers="",
    predicted_status_summary="",
    user_review_status="",
    user_notes_local_only="",
):
    return {
        "Folder Order": folder_order,
        "Local Document Name / File Stem": _text(local_document_name_or_file_stem),
        "Measurement Alias": _text(measurement_alias),
        "Document Type": _text(document_type),
        "OCR Needed": _bool_text(ocr_needed),
        "Extraction Relevant": _bool_text(extraction_relevant),
        "Readiness Level": _text(readiness_level),
        "Review Priority": _text(review_priority),
        "Source": _text(source),
        "Broker": _text(broker),
        "Pickup": _text(pickup),
        "Pickup Date": _text(pickup_date),
        "Delivery": _text(delivery),
        "Delivery Date": _text(delivery_date),
        "Load No": _text(load_number),
        "Carrier": _text(carrier),
        "Trailer Type": _text(trailer_type),
        "Commodity": _text(commodity),
        "Total Weight": _text(total_weight),
        "Final Rate": _text(final_rate),
        "Special Requirements": _text(special_requirements),
        "Top Blockers": _text(top_blockers),
        "Predicted Status Summary": _text(predicted_status_summary),
        "User Review Status": _text(user_review_status),
        "User Notes Local Only": _text(user_notes_local_only),
        "User Corrected Broker": "",
        "User Corrected Pickup": "",
        "User Corrected Pickup Date": "",
        "User Corrected Delivery": "",
        "User Corrected Delivery Date": "",
        "User Corrected Load No": "",
        "User Corrected Final Rate": "",
    }


def build_dispatcher_audit_row(
    measurement_alias="",
    field_name="",
    predicted_value_local_only="",
    predicted_status="",
    candidate_count="",
    conflict_reason="",
    gap_reason="",
    source_sheet="",
    source_field="",
    blocker_type="",
    warning_codes=None,
):
    return {
        "Measurement Alias": _text(measurement_alias),
        "Field Name": _token(field_name),
        "Predicted Value LOCAL ONLY": _text(predicted_value_local_only),
        "Predicted Status": _text(predicted_status),
        "Candidate Count": _text(candidate_count),
        "Conflict Reason": _text(conflict_reason),
        "Gap Reason": _text(gap_reason),
        "Source Sheet": _text(source_sheet),
        "Source Field": _text(source_field),
        "Blocker Type": _text(blocker_type),
        "Warning Codes": ";".join(_token(code) for code in warning_codes or [] if _token(code)),
    }


def infer_dispatcher_issue_type(field_name, original_value, corrected_value):
    field = _token(field_name)
    original_present = bool(_text(original_value))
    corrected_present = bool(_text(corrected_value))
    if not original_present and corrected_present:
        return FIELD_TO_MISSING_ISSUE.get(field, REVIEW_ISSUE_TYPE_MISSING_VALUE)
    if original_present and not corrected_present:
        return REVIEW_ISSUE_TYPE_EXTRA_VALUE
    if original_present and corrected_present:
        return FIELD_TO_DEFAULT_ISSUE.get(field, REVIEW_ISSUE_TYPE_WRONG_VALUE)
    return REVIEW_ISSUE_TYPE_OTHER


def build_dispatcher_feedback_row(
    measurement_alias="",
    field_name="",
    original_predicted_value="",
    user_corrected_value="",
    user_issue_type="",
    user_review_status="",
    user_notes_local_only="",
    warning_codes=None,
):
    original_present = bool(_text(original_predicted_value))
    corrected_present = bool(_text(user_corrected_value))
    changed = _normalize_compare(original_predicted_value) != _normalize_compare(
        user_corrected_value
    )
    issue_type = normalize_review_issue_type(user_issue_type)
    if changed and not issue_type:
        issue_type = infer_dispatcher_issue_type(
            field_name,
            original_predicted_value,
            user_corrected_value,
        )
    return {
        "measurement_alias": _text(measurement_alias),
        "field_name": _token(field_name),
        "original_predicted_present": original_present,
        "user_corrected_present": corrected_present,
        "changed": changed,
        "inferred_issue_type": issue_type,
        "user_review_status": _token(user_review_status),
        "user_notes_present": bool(_text(user_notes_local_only)),
        "warning_codes": [_token(code) for code in warning_codes or [] if _token(code)],
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def _top_counts(counts):
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def aggregate_dispatcher_feedback(feedback_rows):
    safe_rows = [row for row in feedback_rows or [] if isinstance(row, dict)]
    changed_rows = [row for row in safe_rows if row.get("changed")]
    issue_counts = Counter(
        row.get("inferred_issue_type") or REVIEW_ISSUE_TYPE_OTHER
        for row in changed_rows
    )
    field_counts = Counter(row.get("field_name") or "unknown" for row in changed_rows)
    changed_aliases = sorted(
        {
            row.get("measurement_alias")
            for row in changed_rows
            if row.get("measurement_alias")
        }
    )
    feedback_like_aggregate = {
        "reviewed_count": len(safe_rows),
        "incorrect_count": len(changed_rows),
        "issue_type_counts": dict(issue_counts),
    }
    decision = select_repair_target_from_feedback(feedback_like_aggregate)
    return {
        "rows_loaded": len(safe_rows),
        "documents_reviewed": len(
            {
                row.get("measurement_alias")
                for row in safe_rows
                if row.get("measurement_alias")
            }
        ),
        "changed_field_count": len(changed_rows),
        "issue_type_counts": _top_counts(issue_counts),
        "changed_fields_by_name": _top_counts(field_counts),
        "changed_aliases": changed_aliases,
        "recommended_next_repair_target": decision.get("selected_target"),
        "analysis_version": DISPATCHER_REVIEW_TABLE_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }
