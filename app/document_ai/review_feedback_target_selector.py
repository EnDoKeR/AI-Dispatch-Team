"""Select the next repair target from completed local review feedback."""

from app.document_ai.review_issue_taxonomy import (
    REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE,
    REVIEW_ISSUE_TYPE_BROKER_MISSING,
    REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON,
    REVIEW_ISSUE_TYPE_DUPLICATE_STOP,
    REVIEW_ISSUE_TYPE_EXTRA_STOP,
    REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
    REVIEW_ISSUE_TYPE_MISSING_STOP,
    REVIEW_ISSUE_TYPE_OCR_NEEDED,
    REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE,
    REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT,
    REVIEW_ISSUE_TYPE_WRONG_BROKER,
    REVIEW_ISSUE_TYPE_WRONG_DATE,
    REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
    REVIEW_ISSUE_TYPE_WRONG_RATE,
    REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
    REVIEW_ISSUE_TYPE_WRONG_PICKUP,
    REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE,
    REVIEW_ISSUE_TYPE_WRONG_TIME,
)
from app.document_ai.target_disposition import (
    is_target_selectable,
    skipped_targets_for_registry,
)


REVIEW_TARGET_STOP_LOCATION_EXTRACTION = "stop_location_extraction"
REVIEW_TARGET_STOP_DATE_EXTRACTION = "stop_date_extraction"
REVIEW_TARGET_STOP_TIME_EXTRACTION = "stop_time_extraction"
REVIEW_TARGET_STOP_SPAN_BOUNDARY = "stop_span_boundary"
REVIEW_TARGET_RATE_RESOLUTION = "rate_resolution"
REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION = "load_identifier_extraction"
REVIEW_TARGET_BROKER_IDENTITY_EXTRACTION = "broker_identity_extraction"
REVIEW_TARGET_DOCUMENT_CLASSIFICATION = "document_classification"
REVIEW_TARGET_OCR_DESIGN = "OCR_design"
REVIEW_TARGET_HUMAN_REVIEW_CONTINUE = "human_review_continue"
REVIEW_TARGET_NO_ACTION = "no_action"

REVIEW_FEEDBACK_TARGET_SELECTOR_VERSION = "review_feedback_target_selector_v1"

_DEFERRED_TARGET_ALIASES = {
    REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION: "load_identifier_candidate_generation",
    REVIEW_TARGET_RATE_RESOLUTION: "rate_conflict_review_routing",
    REVIEW_TARGET_STOP_DATE_EXTRACTION: "generic_stop_datetime_mapping",
    REVIEW_TARGET_STOP_TIME_EXTRACTION: "generic_stop_datetime_mapping",
    REVIEW_TARGET_STOP_SPAN_BOUNDARY: "generic_stop_span_mapping",
}


def _count(issue_type_counts, *issue_types):
    counts = issue_type_counts or {}
    return sum(int(counts.get(issue_type, 0) or 0) for issue_type in issue_types)


def _score_targets(issue_type_counts):
    return {
        REVIEW_TARGET_RATE_RESOLUTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_WRONG_RATE,
            REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE,
            REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE,
        ),
        REVIEW_TARGET_STOP_DATE_EXTRACTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_WRONG_DATE,
        ),
        REVIEW_TARGET_STOP_TIME_EXTRACTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_WRONG_TIME,
        ),
        REVIEW_TARGET_STOP_LOCATION_EXTRACTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_WRONG_PICKUP,
            REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
        ),
        REVIEW_TARGET_STOP_SPAN_BOUNDARY: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE,
            REVIEW_ISSUE_TYPE_EXTRA_STOP,
            REVIEW_ISSUE_TYPE_DUPLICATE_STOP,
            REVIEW_ISSUE_TYPE_MISSING_STOP,
        ),
        REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
            REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
        ),
        REVIEW_TARGET_BROKER_IDENTITY_EXTRACTION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_BROKER_MISSING,
            REVIEW_ISSUE_TYPE_WRONG_BROKER,
        ),
        REVIEW_TARGET_DOCUMENT_CLASSIFICATION: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON,
            REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT,
        ),
        REVIEW_TARGET_OCR_DESIGN: _count(
            issue_type_counts,
            REVIEW_ISSUE_TYPE_OCR_NEEDED,
        ),
    }


def _supporting_issue_types(selected_target, issue_type_counts):
    issue_type_counts = issue_type_counts or {}
    target_issue_types = {
        REVIEW_TARGET_RATE_RESOLUTION: {
            REVIEW_ISSUE_TYPE_WRONG_RATE,
            REVIEW_ISSUE_TYPE_ACCESSORIAL_CONFUSED_AS_RATE,
            REVIEW_ISSUE_TYPE_RATE_CONFLICT_TRUE,
        },
        REVIEW_TARGET_STOP_DATE_EXTRACTION: {REVIEW_ISSUE_TYPE_WRONG_DATE},
        REVIEW_TARGET_STOP_TIME_EXTRACTION: {REVIEW_ISSUE_TYPE_WRONG_TIME},
        REVIEW_TARGET_STOP_LOCATION_EXTRACTION: {
            REVIEW_ISSUE_TYPE_WRONG_PICKUP,
            REVIEW_ISSUE_TYPE_WRONG_DELIVERY,
        },
        REVIEW_TARGET_STOP_SPAN_BOUNDARY: {
            REVIEW_ISSUE_TYPE_WRONG_STOP_TYPE,
            REVIEW_ISSUE_TYPE_EXTRA_STOP,
            REVIEW_ISSUE_TYPE_DUPLICATE_STOP,
            REVIEW_ISSUE_TYPE_MISSING_STOP,
        },
        REVIEW_TARGET_LOAD_IDENTIFIER_EXTRACTION: {
            REVIEW_ISSUE_TYPE_LOAD_ID_MISSING,
            REVIEW_ISSUE_TYPE_WRONG_LOAD_ID,
        },
        REVIEW_TARGET_BROKER_IDENTITY_EXTRACTION: {
            REVIEW_ISSUE_TYPE_BROKER_MISSING,
            REVIEW_ISSUE_TYPE_WRONG_BROKER,
        },
        REVIEW_TARGET_DOCUMENT_CLASSIFICATION: {
            REVIEW_ISSUE_TYPE_DOCUMENT_NOT_RATECON,
            REVIEW_ISSUE_TYPE_UNCLEAR_DOCUMENT,
        },
        REVIEW_TARGET_OCR_DESIGN: {REVIEW_ISSUE_TYPE_OCR_NEEDED},
    }
    return {
        issue_type: issue_type_counts.get(issue_type, 0)
        for issue_type in sorted(target_issue_types.get(selected_target, set()))
        if issue_type_counts.get(issue_type, 0)
    }


def select_repair_target_from_feedback(
    feedback_aggregate,
    target_disposition_registry=None,
):
    aggregate = feedback_aggregate or {}
    issue_type_counts = aggregate.get("issue_type_counts", {}) or {}
    reviewed_count = int(aggregate.get("reviewed_count", 0) or 0)
    incorrect_count = int(aggregate.get("incorrect_count", 0) or 0)
    skipped = skipped_targets_for_registry(target_disposition_registry or {})
    if not reviewed_count:
        return {
            "selected_target": REVIEW_TARGET_HUMAN_REVIEW_CONTINUE,
            "supporting_issue_types": {},
            "supporting_count": 0,
            "feedback_proven": False,
            "skipped_deferred_targets": skipped,
            "warning_codes": ["no_completed_feedback"],
            "analysis_version": REVIEW_FEEDBACK_TARGET_SELECTOR_VERSION,
            "private_values_included": False,
            "raw_text_included": False,
        }
    if reviewed_count and not incorrect_count:
        return {
            "selected_target": REVIEW_TARGET_NO_ACTION,
            "supporting_issue_types": {},
            "supporting_count": 0,
            "feedback_proven": True,
            "skipped_deferred_targets": skipped,
            "warning_codes": [],
            "analysis_version": REVIEW_FEEDBACK_TARGET_SELECTOR_VERSION,
            "private_values_included": False,
            "raw_text_included": False,
        }

    scores = _score_targets(issue_type_counts)
    selected_target, selected_score = max(
        scores.items(),
        key=lambda item: (item[1], item[0]),
    )
    warning_codes = []
    disposition_target = _DEFERRED_TARGET_ALIASES.get(selected_target)
    if disposition_target and not is_target_selectable(
        disposition_target,
        target_disposition_registry or {},
    ):
        if selected_score:
            warning_codes.append("deferred_target_reopened_by_feedback")
        else:
            selected_target = REVIEW_TARGET_HUMAN_REVIEW_CONTINUE
            warning_codes.append("deferred_target_without_feedback")

    supporting = _supporting_issue_types(selected_target, issue_type_counts)
    return {
        "selected_target": selected_target if selected_score else REVIEW_TARGET_HUMAN_REVIEW_CONTINUE,
        "supporting_issue_types": supporting,
        "supporting_count": sum(supporting.values()),
        "feedback_proven": bool(selected_score),
        "skipped_deferred_targets": skipped,
        "warning_codes": warning_codes,
        "analysis_version": REVIEW_FEEDBACK_TARGET_SELECTOR_VERSION,
        "private_values_included": False,
        "raw_text_included": False,
    }


def select_repair_target_from_dispatcher_feedback(
    dispatcher_feedback_aggregate,
    target_disposition_registry=None,
):
    aggregate = dispatcher_feedback_aggregate or {}
    feedback_like = {
        "reviewed_count": aggregate.get("rows_loaded", 0),
        "incorrect_count": aggregate.get("changed_field_count", 0),
        "issue_type_counts": aggregate.get("issue_type_counts", {}) or {},
    }
    decision = select_repair_target_from_feedback(
        feedback_like,
        target_disposition_registry=target_disposition_registry,
    )
    decision["dispatcher_feedback_rows_loaded"] = int(
        aggregate.get("rows_loaded", 0) or 0
    )
    decision["dispatcher_changed_field_count"] = int(
        aggregate.get("changed_field_count", 0) or 0
    )
    return decision
