"""Blocker classification for safe private RateCon measurement."""

from app.document_ai.private_measurement import (
    BLOCKER_CONFLICTING_CRITICAL_FIELD,
    BLOCKER_DIGITAL_TEXT_EXTRACTION_GAP,
    BLOCKER_LAYOUT_EXTRACTION_GAP,
    BLOCKER_LOW_CONFIDENCE_CRITICAL_FIELD,
    BLOCKER_MANUAL_REVIEW_REQUIRED,
    BLOCKER_MISSING_CRITICAL_FIELD,
    BLOCKER_NON_RATECON_DOCUMENT,
    BLOCKER_OCR_NEEDED,
    BLOCKER_PARSED_HIGH_CONFIDENCE_CANDIDATE,
    BLOCKER_RESOLVER_GAP,
    BLOCKER_SUPPLEMENTAL_DOCUMENT_ONLY,
    BLOCKER_TEMPLATE_GAP,
    BLOCKER_UNKNOWN_DOCUMENT_TYPE_REVIEW,
    BLOCKER_UNSUPPORTED_OR_BROKEN_PDF,
    BLOCKER_VALIDATION_GAP,
    EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
    EXTRACTION_STATUS_EMPTY_TEXT,
    EXTRACTION_STATUS_EXTRACTION_FAILED,
    EXTRACTION_STATUS_TEXT_EXTRACTED,
)


CRITICAL_MEASUREMENT_FIELDS = (
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "pickup_date",
    "delivery_location",
    "delivery_date",
    "equipment",
    "weight",
)


def _critical_intersection(fields):
    return set(fields or []).intersection(CRITICAL_MEASUREMENT_FIELDS)


def classify_private_ratecon_measurement_blockers(
    triage_route="",
    extraction_status="",
    template_status="unknown",
    missing_fields=None,
    needs_check_fields=None,
    conflict_fields=None,
    review_required=False,
    candidate_counts_by_field=None,
    broken=False,
    likely_image_based=False,
    ratecon_eligible=True,
    supplemental_only=False,
    classification_status="",
):
    blockers = []
    candidate_counts = candidate_counts_by_field or {}
    critical_missing = _critical_intersection(missing_fields)
    critical_needs_check = _critical_intersection(needs_check_fields)
    critical_conflicts = _critical_intersection(conflict_fields)

    if supplemental_only:
        blockers.append(BLOCKER_SUPPLEMENTAL_DOCUMENT_ONLY)

    if not ratecon_eligible and not supplemental_only:
        blockers.append(BLOCKER_NON_RATECON_DOCUMENT)

    if str(classification_status or "") == "unknown_review_required":
        blockers.append(BLOCKER_UNKNOWN_DOCUMENT_TYPE_REVIEW)

    if broken or extraction_status in [
        EXTRACTION_STATUS_BROKEN_OR_UNSUPPORTED,
        EXTRACTION_STATUS_EXTRACTION_FAILED,
    ]:
        blockers.append(BLOCKER_UNSUPPORTED_OR_BROKEN_PDF)

    if (
        str(triage_route or "").upper() == BLOCKER_OCR_NEEDED
        or extraction_status == EXTRACTION_STATUS_EMPTY_TEXT
        or likely_image_based
    ):
        blockers.append(BLOCKER_OCR_NEEDED)

    if extraction_status == EXTRACTION_STATUS_TEXT_EXTRACTED and ratecon_eligible:
        if critical_missing:
            blockers.extend([BLOCKER_MISSING_CRITICAL_FIELD, BLOCKER_DIGITAL_TEXT_EXTRACTION_GAP])
            if any(candidate_counts.get(field_name, 0) for field_name in critical_missing):
                blockers.append(BLOCKER_RESOLVER_GAP)
            else:
                blockers.append(BLOCKER_LAYOUT_EXTRACTION_GAP)

        if critical_needs_check:
            blockers.extend([BLOCKER_LOW_CONFIDENCE_CRITICAL_FIELD, BLOCKER_RESOLVER_GAP])

        if critical_conflicts:
            blockers.extend(
                [
                    BLOCKER_CONFLICTING_CRITICAL_FIELD,
                    BLOCKER_MANUAL_REVIEW_REQUIRED,
                    BLOCKER_RESOLVER_GAP,
                ]
            )

        if template_status in {"unknown", "conflict", "low_confidence"}:
            blockers.append(BLOCKER_TEMPLATE_GAP)

        if review_required:
            blockers.append(BLOCKER_MANUAL_REVIEW_REQUIRED)
            if not any([critical_missing, critical_needs_check, critical_conflicts]):
                blockers.append(BLOCKER_VALIDATION_GAP)

        if not blockers:
            blockers.append(BLOCKER_PARSED_HIGH_CONFIDENCE_CANDIDATE)

    return sorted(set(blockers))
