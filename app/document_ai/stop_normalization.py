"""Stop group normalization helpers for layout-backed RateCon extraction."""

from app.document_ai.ratecon_candidates import normalize_list
from app.document_ai.normalized_stops import (
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_NOTES,
    NORMALIZED_STOP_FIELD_REFERENCE,
    NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
    NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE,
    NORMALIZED_STOP_FIELD_STATUS_MISSING,
    NORMALIZED_STOP_FIELD_STATUS_RESOLVED,
    NORMALIZED_STOP_FIELD_TIME,
    build_normalized_stop,
    build_normalized_stop_field,
)
from app.document_ai.stop_association import (
    STOP_ASSOCIATION_SOURCE_TABLE_ROW,
    STOP_FIELD_DATE,
    STOP_FIELD_LOCATION,
    STOP_FIELD_REFERENCE,
    STOP_FIELD_TIME,
    STOP_TYPE_DELIVERY,
    STOP_TYPE_PICKUP,
    STOP_TYPE_STOP,
    STOP_TYPE_UNKNOWN,
)


NOISE_WARNING_SIGNATURE = "stop_group_noise_signature_or_certificate"
NOISE_WARNING_TERMS = "stop_group_noise_terms_or_billing"
NOISE_WARNING_HEADER_FOOTER = "stop_group_noise_header_footer"
DEDUP_WARNING_DUPLICATE = "duplicate_stop_group_removed"
SEQUENCE_WARNING_INFERRED = "stop_sequence_inferred_from_layout_order"
TYPE_WARNING_AMBIGUOUS = "stop_type_ambiguous_review_required"
FIELD_WARNING_CONFLICT = "normalized_stop_field_conflict"
FIELD_WARNING_MISSING = "normalized_stop_field_missing"
FIELD_WARNING_LOW_CONFIDENCE = "normalized_stop_field_low_confidence"

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
_STOP_TO_NORMALIZED_FIELD = {
    STOP_FIELD_LOCATION: NORMALIZED_STOP_FIELD_LOCATION,
    STOP_FIELD_DATE: NORMALIZED_STOP_FIELD_DATE,
    STOP_FIELD_TIME: NORMALIZED_STOP_FIELD_TIME,
    STOP_FIELD_REFERENCE: NORMALIZED_STOP_FIELD_REFERENCE,
}
_REQUIRED_NORMALIZED_FIELDS = (
    NORMALIZED_STOP_FIELD_LOCATION,
    NORMALIZED_STOP_FIELD_DATE,
    NORMALIZED_STOP_FIELD_TIME,
)

_PICKUP_SECTIONS = {"PICKUP_SECTION"}
_DELIVERY_SECTIONS = {"DELIVERY_SECTION"}
_MULTI_STOP_SECTIONS = {"MULTI_STOP_SECTION", "STOP_TABLE"}


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


def _to_int_or_blank(value):
    text = _text(value)
    if not text:
        return ""
    try:
        return int(text)
    except ValueError:
        digits = "".join(char for char in text if char.isdigit())
        return int(digits) if digits else ""


def resolve_stop_type(stop_group):
    """Resolve stop type without forcing ambiguous groups into pickup/delivery."""

    group = stop_group or {}
    current = _text(group.get("stop_type")).lower()
    section = _section(group)
    warnings = []
    reasons = []

    if current in {STOP_TYPE_PICKUP, STOP_TYPE_DELIVERY, STOP_TYPE_STOP}:
        reasons.append("explicit_stop_type")
        return {
            "stop_type": current,
            "confidence": "HIGH",
            "reasons": reasons,
            "warning_codes": warnings,
        }

    if section in _PICKUP_SECTIONS:
        reasons.append("pickup_section_role")
        return {
            "stop_type": STOP_TYPE_PICKUP,
            "confidence": "MEDIUM",
            "reasons": reasons,
            "warning_codes": warnings,
        }

    if section in _DELIVERY_SECTIONS:
        reasons.append("delivery_section_role")
        return {
            "stop_type": STOP_TYPE_DELIVERY,
            "confidence": "MEDIUM",
            "reasons": reasons,
            "warning_codes": warnings,
        }

    if section in _MULTI_STOP_SECTIONS:
        warnings.append(TYPE_WARNING_AMBIGUOUS)
        reasons.append("multi_stop_section_without_type")
        return {
            "stop_type": STOP_TYPE_UNKNOWN,
            "confidence": "LOW",
            "reasons": reasons,
            "warning_codes": warnings,
        }

    warnings.append(TYPE_WARNING_AMBIGUOUS)
    return {
        "stop_type": STOP_TYPE_UNKNOWN,
        "confidence": "LOW",
        "reasons": ["no_stop_type_signal"],
        "warning_codes": warnings,
    }


def infer_stop_sequence(stop_group, surrounding_groups=None):
    """Infer a sequence using explicit sequence, table row, then layout order."""

    group = stop_group or {}
    explicit = _to_int_or_blank(group.get("stop_sequence"))
    if explicit != "":
        return {
            "sequence": explicit,
            "confidence": "HIGH",
            "reasons": ["explicit_stop_sequence"],
            "warning_codes": [],
        }

    row_index = _to_int_or_blank(group.get("row_index"))
    if row_index != "":
        return {
            "sequence": row_index,
            "confidence": "MEDIUM",
            "reasons": ["table_row_order"],
            "warning_codes": [],
        }

    groups = [item for item in surrounding_groups or [] if isinstance(item, dict)]
    ordered = _sort_groups_by_layout_order(groups)
    for index, candidate in enumerate(ordered, start=1):
        if candidate is group or candidate.get("stop_group_id") == group.get("stop_group_id"):
            return {
                "sequence": index,
                "confidence": "LOW",
                "reasons": ["page_order_fallback"],
                "warning_codes": [SEQUENCE_WARNING_INFERRED],
            }

    return {
        "sequence": "",
        "confidence": "LOW",
        "reasons": ["sequence_not_found"],
        "warning_codes": [SEQUENCE_WARNING_INFERRED],
    }


def _sort_groups_by_layout_order(stop_groups):
    return sorted(
        [group for group in stop_groups or [] if isinstance(group, dict)],
        key=lambda group: (
            _to_int_or_blank(group.get("page_number")) or 999999,
            _text(group.get("table_id")),
            _to_int_or_blank(group.get("row_index")) or 999999,
            _to_int_or_blank(group.get("stop_sequence")) or 999999,
            _text(group.get("stop_group_id")),
        ),
    )


def assign_stop_sequence_order(stop_groups):
    groups = _sort_groups_by_layout_order(stop_groups)
    sequenced = []

    for index, group in enumerate(groups, start=1):
        sequence_result = infer_stop_sequence(group, groups)
        resolved_type = resolve_stop_type(group)
        safe_group = dict(group)
        safe_group["stop_sequence"] = sequence_result["sequence"] or index
        safe_group["stop_type"] = resolved_type["stop_type"]
        safe_group["warning_codes"] = sorted(
            set(
                normalize_list(safe_group.get("warning_codes"))
                + sequence_result["warning_codes"]
                + resolved_type["warning_codes"]
            )
        )
        safe_group["reasons"] = sorted(
            set(
                normalize_list(safe_group.get("reasons"))
                + sequence_result["reasons"]
                + resolved_type["reasons"]
            )
        )
        sequenced.append(safe_group)

    return sequenced


def _confidence_value(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        text = _text(value).upper()
        if text == "HIGH":
            return 0.9
        if text == "MEDIUM":
            return 0.65
        if text == "LOW":
            return 0.35
        return 0.0


def _confidence_bucket(value):
    numeric = _confidence_value(value)
    if numeric >= 0.8:
        return "HIGH"
    if numeric >= 0.5:
        return "MEDIUM"
    if numeric > 0:
        return "LOW"
    return "UNKNOWN"


def _candidate_evidence(candidate):
    evidence = candidate.get("evidence_ref") if isinstance(candidate, dict) else {}
    return evidence if isinstance(evidence, dict) else {}


def associate_stop_fields(stop_group):
    fields = {}
    for candidate in (stop_group or {}).get("field_candidates", []) or []:
        if not isinstance(candidate, dict):
            continue
        field_name = _STOP_TO_NORMALIZED_FIELD.get(
            _text(candidate.get("field_name")),
            NORMALIZED_STOP_FIELD_NOTES,
        )
        fields.setdefault(field_name, []).append(candidate)
    return fields


def resolve_stop_field(field_name, candidates):
    safe_candidates = [candidate for candidate in candidates or [] if isinstance(candidate, dict)]
    if not safe_candidates:
        return build_normalized_stop_field(
            field_name=field_name,
            status=NORMALIZED_STOP_FIELD_STATUS_MISSING,
            warning_codes=[FIELD_WARNING_MISSING],
        )

    candidate_ids = {
        _text(candidate.get("candidate_id"))
        for candidate in safe_candidates
        if _text(candidate.get("candidate_id"))
    }
    if len(candidate_ids) > 1:
        return build_normalized_stop_field(
            field_name=field_name,
            status=NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
            confidence="LOW",
            evidence_refs=[_candidate_evidence(candidate) for candidate in safe_candidates],
            reasons=["multiple_candidates_for_stop_field"],
            warning_codes=[FIELD_WARNING_CONFLICT],
        )

    selected = max(safe_candidates, key=lambda candidate: _confidence_value(candidate.get("confidence")))
    confidence = _confidence_bucket(selected.get("confidence"))
    status = (
        NORMALIZED_STOP_FIELD_STATUS_RESOLVED
        if confidence in {"HIGH", "MEDIUM"}
        else NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE
    )
    warnings = [] if status == NORMALIZED_STOP_FIELD_STATUS_RESOLVED else [FIELD_WARNING_LOW_CONFIDENCE]
    return build_normalized_stop_field(
        field_name=field_name,
        status=status,
        selected_candidate_id=selected.get("candidate_id", ""),
        confidence=confidence,
        evidence_refs=[_candidate_evidence(selected)],
        reasons=["same_group_stop_field_candidate"],
        warning_codes=warnings,
    )


def mark_missing_stop_fields(fields, required_fields=None):
    required = required_fields or _REQUIRED_NORMALIZED_FIELDS
    by_name = {field.get("field_name"): field for field in fields or [] if isinstance(field, dict)}
    for field_name in required:
        if field_name not in by_name:
            by_name[field_name] = build_normalized_stop_field(
                field_name=field_name,
                status=NORMALIZED_STOP_FIELD_STATUS_MISSING,
                warning_codes=[FIELD_WARNING_MISSING],
            )
    ordered = []
    for field_name in list(required) + sorted(
        name for name in by_name if name not in set(required)
    ):
        ordered.append(by_name[field_name])
    return ordered


def compute_stop_completeness(normalized_stop):
    fields = {
        field.get("field_name"): field
        for field in (normalized_stop or {}).get("fields", []) or []
        if isinstance(field, dict)
    }
    required_count = len(_REQUIRED_NORMALIZED_FIELDS)
    resolved_count = sum(
        1
        for field_name in _REQUIRED_NORMALIZED_FIELDS
        if fields.get(field_name, {}).get("status") == NORMALIZED_STOP_FIELD_STATUS_RESOLVED
    )
    return {
        "required_field_count": required_count,
        "resolved_required_field_count": resolved_count,
        "missing_required_fields": [
            field_name
            for field_name in _REQUIRED_NORMALIZED_FIELDS
            if fields.get(field_name, {}).get("status") == NORMALIZED_STOP_FIELD_STATUS_MISSING
        ],
        "complete": resolved_count == required_count,
    }


def build_normalized_stop_from_group(stop_group):
    type_result = resolve_stop_type(stop_group)
    sequence_result = infer_stop_sequence(stop_group, [stop_group])
    associated_fields = associate_stop_fields(stop_group)
    fields = [
        resolve_stop_field(field_name, candidates)
        for field_name, candidates in associated_fields.items()
    ]
    fields = mark_missing_stop_fields(fields)
    review_required = any(
        field.get("status")
        in {
            NORMALIZED_STOP_FIELD_STATUS_CONFLICT,
            NORMALIZED_STOP_FIELD_STATUS_LOW_CONFIDENCE,
            NORMALIZED_STOP_FIELD_STATUS_MISSING,
        }
        for field in fields
    ) or type_result["stop_type"] == STOP_TYPE_UNKNOWN

    return build_normalized_stop(
        stop_id=_text((stop_group or {}).get("stop_group_id")),
        sequence=sequence_result["sequence"],
        stop_type=type_result["stop_type"],
        source_group_ids=[(stop_group or {}).get("stop_group_id", "")],
        page_numbers=[(stop_group or {}).get("page_number", "")]
        if (stop_group or {}).get("page_number") not in [None, ""]
        else [],
        section_roles=[(stop_group or {}).get("section_role", "")],
        table_ids=[(stop_group or {}).get("table_id", "")],
        row_indices=[(stop_group or {}).get("row_index", "")]
        if (stop_group or {}).get("row_index") not in [None, ""]
        else [],
        fields=fields,
        confidence=type_result["confidence"],
        reasons=type_result["reasons"] + sequence_result["reasons"],
        warning_codes=sorted(
            set(
                normalize_list((stop_group or {}).get("warning_codes"))
                + type_result["warning_codes"]
                + sequence_result["warning_codes"]
            )
        ),
        review_required=review_required,
    )
