"""Stop group normalization helpers for layout-backed RateCon extraction."""

from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_TIME,
)


NOISE_WARNING_SIGNATURE = "stop_group_noise_signature_or_certificate"
NOISE_WARNING_TERMS = "stop_group_noise_terms_or_billing"
NOISE_WARNING_HEADER_FOOTER = "stop_group_noise_header_footer"
DEDUP_WARNING_DUPLICATE = "duplicate_stop_group_removed"

_SIGNATURE_SECTIONS = {"SIGNATURE_BLOCK", "CERTIFICATE_SIGNATURE_BLOCK"}
_TERMS_SECTIONS = {
    "LEGAL_TERMS",
    "PAYMENT_TERMS",
    "BILLING_INSTRUCTIONS",
    "QUICK_PAY",
    "DEDUCTIONS_PENALTIES",
}
_HEADER_FOOTER_TOKENS = {"header", "footer", "repeated_header", "page_footer"}
_MEANINGFUL_STOP_FIELDS = {
    STOP_FIELD_LOCATION,
    STOP_FIELD_DATE,
    STOP_FIELD_TIME,
    STOP_FIELD_REFERENCE,
}


def _text(value):
    return str(value or "").strip()


def _section(group):
    return _text((group or {}).get("section_role")).upper()


def _warning_tokens(group):
    return {
        item.lower()
        for item in normalize_list((group or {}).get("warning_codes"))
        + normalize_list((group or {}).get("reasons"))
    }


def _field_names(group):
    return {
        _text(candidate.get("field_name"))
        for candidate in (group or {}).get("field_candidates", []) or []
        if isinstance(candidate, dict) and _text(candidate.get("field_name"))
    }


def _has_meaningful_stop_fields(group):
    return bool(_field_names(group) & _MEANINGFUL_STOP_FIELDS)


def _has_strong_location_date_evidence(group):
    fields = _field_names(group)
    return STOP_FIELD_LOCATION in fields and bool(
        fields & {STOP_FIELD_DATE, STOP_FIELD_TIME, STOP_FIELD_REFERENCE}
    )


def compute_stop_group_signature(stop_group):
    """Return a conservative duplicate signature without private values."""

    group = stop_group or {}
    field_names = ",".join(sorted(_field_names(group)))
    return "|".join(
        [
            _text(group.get("stop_sequence")),
            _text(group.get("stop_type")),
            _text(group.get("section_role")).upper(),
            _text(group.get("table_id")),
            _text(group.get("row_index")),
            field_names,
        ]
    )


def is_likely_stop_noise(stop_group):
    """Return True when a raw group is likely non-core stop noise."""

    section = _section(stop_group)
    tokens = _warning_tokens(stop_group)

    if section in _SIGNATURE_SECTIONS or "signature" in tokens:
        return True

    if section in _TERMS_SECTIONS and not _has_strong_location_date_evidence(stop_group):
        return True

    if tokens & _HEADER_FOOTER_TOKENS and not _has_meaningful_stop_fields(stop_group):
        return True

    if not _has_meaningful_stop_fields(stop_group):
        return _text((stop_group or {}).get("source")) != STOP_ASSOCIATION_SOURCE_TABLE_ROW

    return False


def _noise_warning(stop_group):
    section = _section(stop_group)
    tokens = _warning_tokens(stop_group)
    if section in _SIGNATURE_SECTIONS or "signature" in tokens:
        return NOISE_WARNING_SIGNATURE
    if section in _TERMS_SECTIONS:
        return NOISE_WARNING_TERMS
    return NOISE_WARNING_HEADER_FOOTER


def filter_stop_group_noise(stop_groups):
    kept = []
    removed = []
    warnings = []

    for group in stop_groups or []:
        if not isinstance(group, dict):
            continue
        if is_likely_stop_noise(group):
            removed_group = dict(group)
            removed_group["warning_codes"] = sorted(
                set(normalize_list(removed_group.get("warning_codes")) + [_noise_warning(group)])
            )
            removed.append(removed_group)
            warnings.append(_noise_warning(group))
            continue
        kept.append(group)

    return {
        "kept_groups": kept,
        "removed_groups": removed,
        "removed_count": len(removed),
        "warning_codes": sorted(set(warnings)),
    }


def is_likely_duplicate_stop_group(first, second):
    if not isinstance(first, dict) or not isinstance(second, dict):
        return False

    if (
        _text(first.get("table_id"))
        and first.get("table_id") == second.get("table_id")
        and first.get("row_index") == second.get("row_index")
    ):
        return True

    if compute_stop_group_signature(first) != compute_stop_group_signature(second):
        return False

    if _warning_tokens(first) & {"repeated_header", "header", "footer", "page_footer"}:
        return True
    if _warning_tokens(second) & {"repeated_header", "header", "footer", "page_footer"}:
        return True

    return (
        _text(first.get("stop_sequence")) != ""
        and _text(first.get("stop_type")) != "unknown"
        and _field_names(first) == _field_names(second)
    )


def dedupe_stop_groups(stop_groups):
    kept = []
    removed = []
    warnings = []

    for group in stop_groups or []:
        if not isinstance(group, dict):
            continue
        duplicate = any(is_likely_duplicate_stop_group(existing, group) for existing in kept)
        if duplicate:
            removed_group = dict(group)
            removed_group["warning_codes"] = sorted(
                set(normalize_list(removed_group.get("warning_codes")) + [DEDUP_WARNING_DUPLICATE])
            )
            removed.append(removed_group)
            warnings.append(DEDUP_WARNING_DUPLICATE)
            continue
        kept.append(group)

    return {
        "kept_groups": kept,
        "removed_groups": removed,
        "removed_count": len(removed),
        "warning_codes": sorted(set(warnings)),
    }
