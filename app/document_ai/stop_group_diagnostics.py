"""Safe diagnostics for raw layout stop group quality."""

from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_SECTION_BLOCK,
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_TIME,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_UNKNOWN,
)


STOP_GROUP_QUALITY_EMPTY = "empty"
STOP_GROUP_QUALITY_NOISY = "noisy"
STOP_GROUP_QUALITY_USEFUL_BUT_UNMERGED = "useful_but_unmerged"
STOP_GROUP_QUALITY_NORMALIZED_READY = "normalized_ready"
STOP_GROUP_QUALITY_AMBIGUOUS_REVIEW = "ambiguous_review"

STOP_GROUP_QUALITY_BUCKETS = {
    STOP_GROUP_QUALITY_EMPTY,
    STOP_GROUP_QUALITY_NOISY,
    STOP_GROUP_QUALITY_USEFUL_BUT_UNMERGED,
    STOP_GROUP_QUALITY_NORMALIZED_READY,
    STOP_GROUP_QUALITY_AMBIGUOUS_REVIEW,
}

STOP_GROUP_DIAGNOSTICS_VERSION = "stop_group_diagnostics_v1"

_SIGNATURE_TOKENS = {"SIGNATURE_BLOCK", "CERTIFICATE_SIGNATURE_BLOCK"}
_TERMS_TOKENS = {
    "LEGAL_TERMS",
    "PAYMENT_TERMS",
    "DEDUCTIONS_PENALTIES",
    "QUICK_PAY",
    "BILLING_INSTRUCTIONS",
}
_HEADER_FOOTER_WARNING_TOKENS = {
    "header",
    "footer",
    "repeated_header",
    "page_footer",
}


def _text(value):
    return str(value or "").strip()


def _field_names(group):
    return {
        _text(candidate.get("field_name"))
        for candidate in (group or {}).get("field_candidates", []) or []
        if isinstance(candidate, dict) and _text(candidate.get("field_name"))
    }


def _group_signature(group):
    fields = ",".join(sorted(_field_names(group)))
    return "|".join(
        [
            _text((group or {}).get("stop_type")),
            _text((group or {}).get("stop_sequence")),
            _text((group or {}).get("page_number")),
            _text((group or {}).get("section_role")),
            _text((group or {}).get("table_id")),
            _text((group or {}).get("row_index")),
            fields,
        ]
    )


def _is_signature_noise(group):
    section = _text((group or {}).get("section_role")).upper()
    warnings = {item.lower() for item in normalize_list((group or {}).get("warning_codes"))}
    reasons = {item.lower() for item in normalize_list((group or {}).get("reasons"))}
    return section in _SIGNATURE_TOKENS or "signature" in warnings or "signature" in reasons


def _is_terms_noise(group):
    section = _text((group or {}).get("section_role")).upper()
    return section in _TERMS_TOKENS


def _is_header_footer_noise(group):
    warnings = {item.lower() for item in normalize_list((group or {}).get("warning_codes"))}
    reasons = {item.lower() for item in normalize_list((group or {}).get("reasons"))}
    tokens = warnings | reasons
    if tokens & _HEADER_FOOTER_WARNING_TOKENS:
        return True
    fields = _field_names(group)
    return not fields and _text((group or {}).get("source")) != STOP_ASSOCIATION_SOURCE_TABLE_ROW


def _quality_bucket(
    raw_group_count,
    duplicate_like_group_count,
    table_group_count,
    pickup_group_count,
    delivery_group_count,
    unknown_type_count,
    groups_missing_location,
    likely_noise_count,
):
    if raw_group_count == 0:
        return STOP_GROUP_QUALITY_EMPTY

    if likely_noise_count >= raw_group_count or (
        duplicate_like_group_count > 0 and duplicate_like_group_count >= raw_group_count // 2
    ):
        return STOP_GROUP_QUALITY_NOISY

    if unknown_type_count > pickup_group_count + delivery_group_count:
        return STOP_GROUP_QUALITY_AMBIGUOUS_REVIEW

    if (
        table_group_count
        and pickup_group_count
        and delivery_group_count
        and groups_missing_location < raw_group_count
    ):
        return STOP_GROUP_QUALITY_NORMALIZED_READY

    return STOP_GROUP_QUALITY_USEFUL_BUT_UNMERGED


def build_stop_group_diagnostics(stop_groups=None, warning_codes=None):
    groups = [group for group in stop_groups or [] if isinstance(group, dict)]
    signatures = {}
    duplicate_like_group_count = 0

    for group in groups:
        signature = _group_signature(group)
        signatures[signature] = signatures.get(signature, 0) + 1
        if signatures[signature] > 1:
            duplicate_like_group_count += 1

    table_group_count = sum(
        1 for group in groups if group.get("source") == STOP_ASSOCIATION_SOURCE_TABLE_ROW
    )
    section_group_count = sum(
        1 for group in groups if group.get("source") == STOP_ASSOCIATION_SOURCE_SECTION_BLOCK
    )
    unknown_type_count = sum(1 for group in groups if group.get("stop_type") == STOP_TYPE_UNKNOWN)
    pickup_group_count = sum(1 for group in groups if group.get("stop_type") == STOP_TYPE_PICKUP)
    delivery_group_count = sum(
        1 for group in groups if group.get("stop_type") == STOP_TYPE_DELIVERY
    )

    groups_missing_location = sum(
        1 for group in groups if STOP_FIELD_LOCATION not in _field_names(group)
    )
    groups_missing_date = sum(
        1 for group in groups if STOP_FIELD_DATE not in _field_names(group)
    )
    groups_missing_time = sum(
        1 for group in groups if STOP_FIELD_TIME not in _field_names(group)
    )
    groups_with_reference = sum(
        1 for group in groups if STOP_FIELD_REFERENCE in _field_names(group)
    )
    likely_header_footer_noise_count = sum(
        1 for group in groups if _is_header_footer_noise(group)
    )
    likely_signature_noise_count = sum(1 for group in groups if _is_signature_noise(group))
    likely_terms_noise_count = sum(1 for group in groups if _is_terms_noise(group))
    likely_noise_count = (
        likely_header_footer_noise_count
        + likely_signature_noise_count
        + likely_terms_noise_count
    )

    return {
        "raw_group_count": len(groups),
        "duplicate_like_group_count": duplicate_like_group_count,
        "table_group_count": table_group_count,
        "section_group_count": section_group_count,
        "unknown_type_count": unknown_type_count,
        "pickup_group_count": pickup_group_count,
        "delivery_group_count": delivery_group_count,
        "groups_missing_location": groups_missing_location,
        "groups_missing_date": groups_missing_date,
        "groups_missing_time": groups_missing_time,
        "groups_with_reference": groups_with_reference,
        "likely_header_footer_noise_count": likely_header_footer_noise_count,
        "likely_signature_noise_count": likely_signature_noise_count,
        "likely_terms_noise_count": likely_terms_noise_count,
        "warning_codes": normalize_list(warning_codes),
        "quality_bucket": _quality_bucket(
            len(groups),
            duplicate_like_group_count,
            table_group_count,
            pickup_group_count,
            delivery_group_count,
            unknown_type_count,
            groups_missing_location,
            likely_noise_count,
        ),
        "diagnostics_version": STOP_GROUP_DIAGNOSTICS_VERSION,
        "raw_text_included": False,
        "private_values_redacted": True,
    }
