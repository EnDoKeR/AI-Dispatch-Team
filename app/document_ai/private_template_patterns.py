"""Redacted private broker template pattern contracts.

These contracts are JSON-ready summaries for local-only pattern collection. They
must not contain raw private text, filenames, broker values, MC numbers, rates,
addresses, or reference values.
"""


TOKEN_LABEL_LIKE = "LABEL_LIKE"
TOKEN_MONEY = "MONEY"
TOKEN_DATE = "DATE"
TOKEN_TIME = "TIME"
TOKEN_MC_NUMBER = "MC_NUMBER"
TOKEN_REFERENCE = "REFERENCE"
TOKEN_CITY_STATE = "CITY_STATE"
TOKEN_COMPANY_LIKE = "COMPANY_LIKE"
TOKEN_EQUIPMENT = "EQUIPMENT"
TOKEN_WEIGHT = "WEIGHT"
TOKEN_UNKNOWN = "UNKNOWN"

REDACTED_TEMPLATE_PATTERN_VERSION = "redacted_template_pattern_v1"


def _text(value):
    return str(value or "").strip()


def _bool(value, default=False):
    if value is None:
        return default
    return bool(value)


def _normalize_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    return [_text(item) for item in values if _text(item)]


def _safe_redacted_value(value, token_type=TOKEN_UNKNOWN):
    text = _text(value)
    if text.startswith("<") and text.endswith(">"):
        return text

    defaults = {
        TOKEN_MONEY: "<MONEY>",
        TOKEN_DATE: "<DATE>",
        TOKEN_TIME: "<TIME>",
        TOKEN_MC_NUMBER: "<MC>",
        TOKEN_REFERENCE: "<REF>",
        TOKEN_CITY_STATE: "<CITY_STATE>",
        TOKEN_COMPANY_LIKE: "<COMPANY>",
        TOKEN_EQUIPMENT: "<EQUIPMENT>",
        TOKEN_WEIGHT: "<WEIGHT>",
        TOKEN_LABEL_LIKE: "<LABEL>",
    }
    return defaults.get(token_type, "<VALUE>")


def build_redacted_pattern_token(
    token_type=TOKEN_UNKNOWN,
    redacted_value="",
    line_position_bucket="",
    page_number=None,
    source_field="",
    warning_codes=None,
):
    return {
        "token_type": _text(token_type or TOKEN_UNKNOWN),
        "redacted_value": _safe_redacted_value(redacted_value, token_type),
        "line_position_bucket": _text(line_position_bucket),
        "page_number": page_number if page_number is not None else "",
        "source_field": _text(source_field),
        "warning_codes": _normalize_list(warning_codes),
    }


def build_redacted_line_pattern(
    page_number=None,
    line_index_bucket="",
    redacted_line="",
    token_types=None,
    looks_like_header=False,
    looks_like_rate_section=False,
    looks_like_stop_section=False,
    looks_like_terms_section=False,
    warning_codes=None,
):
    return {
        "page_number": page_number if page_number is not None else "",
        "line_index_bucket": _text(line_index_bucket),
        "redacted_line": _text(redacted_line),
        "token_types": _normalize_list(token_types),
        "looks_like_header": _bool(looks_like_header),
        "looks_like_rate_section": _bool(looks_like_rate_section),
        "looks_like_stop_section": _bool(looks_like_stop_section),
        "looks_like_terms_section": _bool(looks_like_terms_section),
        "warning_codes": _normalize_list(warning_codes),
    }


def build_redacted_template_pattern_summary(
    document_alias="",
    page_count=0,
    char_count=0,
    section_markers=None,
    redacted_header_patterns=None,
    redacted_rate_label_patterns=None,
    redacted_stop_label_patterns=None,
    redacted_reference_label_patterns=None,
    redacted_equipment_weight_patterns=None,
    warning_codes=None,
):
    return {
        "document_alias": _text(document_alias),
        "page_count": int(page_count or 0),
        "char_count": int(char_count or 0),
        "section_markers": _normalize_list(section_markers),
        "redacted_header_patterns": [
            item for item in redacted_header_patterns or [] if isinstance(item, dict)
        ],
        "redacted_rate_label_patterns": [
            item for item in redacted_rate_label_patterns or [] if isinstance(item, dict)
        ],
        "redacted_stop_label_patterns": [
            item for item in redacted_stop_label_patterns or [] if isinstance(item, dict)
        ],
        "redacted_reference_label_patterns": [
            item for item in redacted_reference_label_patterns or [] if isinstance(item, dict)
        ],
        "redacted_equipment_weight_patterns": [
            item for item in redacted_equipment_weight_patterns or [] if isinstance(item, dict)
        ],
        "warning_codes": _normalize_list(warning_codes),
        "private_values_redacted": True,
        "raw_text_included": False,
        "pattern_version": REDACTED_TEMPLATE_PATTERN_VERSION,
    }


def build_template_family_candidate(
    family_alias="",
    aliases=None,
    common_redacted_markers=None,
    likely_rate_labels_redacted=None,
    likely_stop_labels_redacted=None,
    likely_reference_labels_redacted=None,
    confidence_bucket="unknown",
    warnings=None,
):
    return {
        "family_alias": _text(family_alias),
        "aliases": _normalize_list(aliases),
        "common_redacted_markers": _normalize_list(common_redacted_markers),
        "likely_rate_labels_redacted": _normalize_list(likely_rate_labels_redacted),
        "likely_stop_labels_redacted": _normalize_list(likely_stop_labels_redacted),
        "likely_reference_labels_redacted": _normalize_list(likely_reference_labels_redacted),
        "confidence_bucket": _text(confidence_bucket or "unknown"),
        "warnings": _normalize_list(warnings),
    }
