"""Safe review issue taxonomy and feedback aggregates.

Completed review CSVs may contain private expected values and local notes. This
module records only booleans/counts/categories in returned summaries.
"""

from app.document_ai.ratecon_candidates import normalize_list


REVIEW_ISSUE_TAXONOMY_VERSION = "review_issue_taxonomy_v1"

REVIEW_ISSUE_TYPE_CORRECT = "correct"
REVIEW_ISSUE_TYPE_WRONG_VALUE = "wrong_value"
REVIEW_ISSUE_TYPE_MISSING_VALUE = "missing_value"
REVIEW_ISSUE_TYPE_EXTRA_VALUE = "extra_value"
REVIEW_ISSUE_TYPE_DUPLICATE_STOP = "duplicate_stop"
REVIEW_ISSUE_TYPE_EXTRA_STOP = "extra_stop"
REVIEW_ISSUE_TYPE_MISSING_STOP = "missing_stop"
REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE = "wrong_stop_type"
REVIEW_ISSUE_TYPE_WRONG_PICKUP = "wrong_pickup"
REVIEW_ISSUE_TYPE_WRONG_DELIVERY = "wrong_delivery"
REVIEW_ISSUE_TYPE_WRONG_DATE = "wrong_date"
REVIEW_ISSUE_TYPE_WRONG_TIME = "wrong_time"
REVIEW_ISSUE_TYPE_WRONG_RATE = "wrong_rate"
REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE = "accessorial_confused_as_rate"
REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE = "rate_conflict_true"
REVIEW_ISSUE_TYPE_LOAD_ID_MISSING = "load_id_missing"
REVIEW_ISSUE_TYPE_WRONG_LOAD_ID = "wrong_load_id"
REVIEW_ISSUE_TYPE_BROKER_MISSING = "broker_missing"
REVIEW_ISSUE_TYPE_WRONG_BROKER = "wrong_broker"
REVIEW_ISSUE_TYPE_OCR_NEEDED = "OCR_needed"
REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON = "document_not_ratecon"
REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT = "unclear_document"
REVIEW_ISSUE_TYPE_OTHER = "other"

REVIEW_ISSUE_TYPES = {
    REVIEW_ISSUE_TYPE_CORRECT,
    REVIEW_ISSUE_TYPE_WRONG_VALUE,
    REVIEW_ISSUE_TYPE_MISSING_VALUE,
    REVIEW_ISSUE_TYPE_EXTRA_VALUE,
    REVIEW_ISSUE_TYPE_DUPLICATE_STOP,
    REVIEW_ISSUE_TYPE_EXTRA_STOP,
    REVIEW_ISSUE_TYPE_MISSING_STOP,
    REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE,
    REVIEW_ISSUE_TYPE_WRONG_PICKUP,
    REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
    REVIEW_ISSUE_TYPE_WRONG_DATE,
    REVIEW_ISSUE_TYPE_WRONG_TIME,
    REVIEW_ISSUE_TYPE_WRONG_RATE,
    REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE,
    REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE,
    REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
    REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
    REVIEW_ISSUE_TYPE_BROKER_MISSING,
    REVIEW_ISSUE_TYPE_WRONG_BROKER,
    REVIEW_ISSUE_TYPE_OCR_NEEDED,
    REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON,
    REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT,
    REVIEW_ISSUE_TYPE_OTHER,
}

REVIEW_DECISION_YES = "yes"
REVIEW_DECISION_NO = "no"
REVIEW_DECISION_UNKNOWN = "unknown"
REVIEW_DECISION_NOT_APPLICABLE = "not_applicable"

REVIEW_DECISIONS = {
    REVIEW_DECISION_YES,
    REVIEW_DECISION_NO,
    REVIEW_DECISION_UNKNOWN,
    REVIEW_DECISION_NOT_APPLICABLE,
}

ROW_TYPE_DOCUMENT = "document"
ROW_TYPE_FIELD = "field"
ROW_TYPE_STOP = "stop"
ROW_TYPE_RATE = "rate"
ROW_TYPE_LOAD_IDENTIFIER = "load_identifier"

ROW_TYPES = {
    ROW_TYPE_DOCUMENT,
    ROW_TYPE_FIELD,
    ROW_TYPE_STOP,
    ROW_TYPE_RATE,
    ROW_TYPE_LOAD_IDENTIFIER,
}

_ISSUE_TYPE_ALIASES = {
    "ocr_needed": REVIEW_ISSUE_TYPE_OCR_NEEDED,
    "ocr": REVIEW_ISSUE_TYPE_OCR_NEEDED,
    "accessorial_confused_as_main_rate": REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE,
    "wrong_load_number": REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
    "load_number_missing": REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
}

_DECISION_ALIASES = {
    "y": REVIEW_DECISION_YES,
    "true": REVIEW_DECISION_YES,
    "correct": REVIEW_DECISION_YES,
    "n": REVIEW_DECISION_NO,
    "false": REVIEW_DECISION_NO,
    "incorrect": REVIEW_DECISION_NO,
    "unk": REVIEW_DECISION_UNKNOWN,
    "unsure": REVIEW_DECISION_UNKNOWN,
    "na": REVIEW_DECISION_NOT_APPLICABLE,
    "n/a": REVIEW_DECISION_NOT_APPLICABLE,
    "not_applicable": REVIEW_DECISION_NOT_APPLICABLE,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def normalize_review_decision(value):
    token = _token(value)
    if token in REVIEW_DECISIONS:
        return token
    return _DECISION_ALIASES.get(token, REVIEW_DECISION_UNKNOWN if token else "")


def normalize_review_issue_type(value):
    raw = _text(value)
    if raw == REVIEW_ISSUE_TYPE_OCR_NEEDED:
        return REVIEW_ISSUE_TYPE_OCR_NEEDED
    token = _token(value)
    if token in _ISSUE_TYPE_ALIASES:
        return _ISSUE_TYPE_ALIASES[token]
    if token in {_token(issue_type) for issue_type in REVIEW_ISSUE_TYPES}:
        for issue_type in REVIEW_ISSUE_TYPES:
            if _token(issue_type) == token:
                return issue_type
    return REVIEW_ISSUE_TYPE_OTHER if token else ""


def _normalize_row_type(value):
    token = _token(value)
    return token if token in ROW_TYPES else ROW_TYPE_FIELD


def _value_present(row, keys):
    for key in keys:
        if _text((row or {}).get(key)):
            return True
    return False


def build_review_feedback_row(
    measurement_alias="",
    sheet_name="",
    row_type=ROW_TYPE_FIELD,
    field_name="",
    stop_id="",
    predicted_status="",
    review_decision="",
    issue_type="",
    user_expected_value_present=False,
    private_note_present=False,
    warning_codes=None,
):
    decision = normalize_review_decision(review_decision)
    normalized_issue = normalize_review_issue_type(issue_type)
    if decision == REVIEW_DECISION_YES and not normalized_issue:
        normalized_issue = REVIEW_ISSUE_TYPE_CORRECT
    return {
        "measurement_alias": _text(measurement_alias),
        "sheet_name": _text(sheet_name),
        "row_type": _normalize_row_type(row_type),
        "field_name": _token(field_name),
        "stop_id": _text(stop_id),
        "predicted_status": _token(predicted_status),
        "review_decision": decision,
        "issue_type": normalized_issue,
        "user_expected_value_present": bool(user_expected_value_present),
        "private_note_present": bool(private_note_present),
        "warning_codes": normalize_list(warning_codes),
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def review_feedback_row_from_csv(row, sheet_name="", row_type=ROW_TYPE_FIELD):
    safe_row = row or {}
    return build_review_feedback_row(
        measurement_alias=safe_row.get("Measurement Alias")
        or safe_row.get("Alias")
        or safe_row.get("measurement_alias"),
        sheet_name=sheet_name,
        row_type=safe_row.get("Row Type") or row_type,
        field_name=safe_row.get("Field Name")
        or safe_row.get("Rate Field Type")
        or safe_row.get("Identifier Type")
        or safe_row.get("field_name"),
        stop_id=safe_row.get("Stop ID") or safe_row.get("stop_id"),
        predicted_status=safe_row.get("Status")
        or safe_row.get("Predicted Status")
        or safe_row.get("predicted_status"),
        review_decision=safe_row.get("User Correct? yes/no/unknown")
        or safe_row.get("User Correct?")
        or safe_row.get("review_decision"),
        issue_type=safe_row.get("User Issue Type") or safe_row.get("issue_type"),
        user_expected_value_present=_value_present(
            safe_row,
            [
                "User Expected Value LOCAL ONLY",
                "Expected Value LOCAL ONLY",
                "user_expected_value",
            ],
        ),
        private_note_present=_value_present(
            safe_row,
            ["User Notes Local Only", "User Notes LOCAL ONLY", "private_note"],
        ),
    )


def _increment_nested(counts, outer_key, inner_key):
    outer = outer_key or "unknown"
    inner = inner_key or REVIEW_ISSUE_TYPE_OTHER
    counts.setdefault(outer, {})
    counts[outer][inner] = counts[outer].get(inner, 0) + 1


def _top_counts(counts, limit=10):
    return [
        {"name": key, "count": value}
        for key, value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[
            :limit
        ]
    ]


def _top_nested_incorrect(nested_counts, limit=10):
    totals = {
        key: sum(inner.values())
        for key, inner in nested_counts.items()
        if isinstance(inner, dict)
    }
    return _top_counts(totals, limit=limit)


def recommend_repair_target(issue_type_counts):
    counts = issue_type_counts or {}
    if not counts:
        return "human_review_continue"
    target_scores = {
        "rate_resolution": counts.get(REVIEW_ISSUE_TYPE_WRONG_RATE, 0)
        + counts.get(REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE, 0)
        + counts.get(REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE, 0),
        "stop_date_extraction": counts.get(REVIEW_ISSUE_TYPE_WRONG_DATE, 0)
        + counts.get(REVIEW_ISSUE_TYPE_MISSING_VALUE, 0),
        "stop_span_boundary": counts.get(REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE, 0)
        + counts.get(REVIEW_ISSUE_TYPE_EXTRA_STOP, 0)
        + counts.get(REVIEW_ISSUE_TYPE_DUPLICATE_STOP, 0)
        + counts.get(REVIEW_ISSUE_TYPE_MISSING_STOP, 0),
        "load_identifier_extraction": counts.get(REVIEW_ISSUE_TYPE_LOAD_ID_MISSING, 0)
        + counts.get(REVIEW_ISSUE_TYPE_WRONG_LOAD_ID, 0),
        "broker_identity_extraction": counts.get(REVIEW_ISSUE_TYPE_BROKER_MISSING, 0)
        + counts.get(REVIEW_ISSUE_TYPE_WRONG_BROKER, 0),
        "OCR_design": counts.get(REVIEW_ISSUE_TYPE_OCR_NEEDED, 0),
        "document_classification": counts.get(REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON, 0)
        + counts.get(REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT, 0),
    }
    selected, score = max(target_scores.items(), key=lambda item: (item[1], item[0]))
    return selected if score else "human_review_continue"


def build_review_feedback_aggregate(records):
    safe_records = [record for record in records or [] if isinstance(record, dict)]
    reviewed_count = 0
    correct_count = 0
    incorrect_count = 0
    unknown_count = 0
    not_applicable_count = 0
    issue_type_counts = {}
    issue_type_by_field = {}
    issue_type_by_alias = {}

    for record in safe_records:
        decision = normalize_review_decision(record.get("review_decision"))
        issue_type = normalize_review_issue_type(record.get("issue_type"))
        if not decision:
            continue
        reviewed_count += 1
        if decision == REVIEW_DECISION_YES:
            correct_count += 1
            continue
        if decision == REVIEW_DECISION_NO:
            incorrect_count += 1
        elif decision == REVIEW_DECISION_NOT_APPLICABLE:
            not_applicable_count += 1
        else:
            unknown_count += 1

        if not issue_type:
            issue_type = REVIEW_ISSUE_TYPE_OTHER
        issue_type_counts[issue_type] = issue_type_counts.get(issue_type, 0) + 1
        _increment_nested(issue_type_by_field, _token(record.get("field_name")), issue_type)
        _increment_nested(
            issue_type_by_alias,
            _text(record.get("measurement_alias")) or "UNKNOWN_ALIAS",
            issue_type,
        )

    return {
        "rows_loaded": len(safe_records),
        "reviewed_count": reviewed_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unknown_count": unknown_count,
        "not_applicable_count": not_applicable_count,
        "issue_type_counts": dict(sorted(issue_type_counts.items())),
        "issue_type_by_field": {
            key: dict(sorted(value.items()))
            for key, value in sorted(issue_type_by_field.items())
        },
        "issue_type_by_alias": {
            key: dict(sorted(value.items()))
            for key, value in sorted(issue_type_by_alias.items())
        },
        "top_issue_types": _top_counts(issue_type_counts),
        "top_fields_by_incorrect": _top_nested_incorrect(issue_type_by_field),
        "recommended_next_repair_target": recommend_repair_target(issue_type_counts),
        "analysis_version": REVIEW_ISSUE_TAXONOMY_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }


def summarize_review_feedback_records(records):
    return build_review_feedback_aggregate(records)
