"""Safe provenance contracts for layout stop groups."""

from collections import Counter


STOP_GROUP_SOURCE_TYPE_TABLE_ROW = "table_row"
STOP_GROUP_SOURCE_TYPE_TABLE_CELL = "table_cell"
STOP_GROUP_SOURCE_TYPE_TABLE_HEADER = "table_header"
STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK = "section_block"
STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER = "line_cluster"
STOP_GROUP_SOURCE_TYPE_SINGLE_LINE = "single_line"
STOP_GROUP_SOURCE_TYPE_LABEL_VALUE_PAIR = "label_value_pair"
STOP_GROUP_SOURCE_TYPE_TEXT_REGEX = "text_regex"
STOP_GROUP_SOURCE_TYPE_LAYOUT_SIGNAL = "layout_signal"
STOP_GROUP_SOURCE_TYPE_UNKNOWN = "unknown"

STOP_GROUP_SOURCE_TYPES = {
    STOP_GROUP_SOURCE_TYPE_TABLE_ROW,
    STOP_GROUP_SOURCE_TYPE_TABLE_CELL,
    STOP_GROUP_SOURCE_TYPE_TABLE_HEADER,
    STOP_GROUP_SOURCE_TYPE_SECTION_BLOCK,
    STOP_GROUP_SOURCE_TYPE_LINE_CLUSTER,
    STOP_GROUP_SOURCE_TYPE_SINGLE_LINE,
    STOP_GROUP_SOURCE_TYPE_LABEL_VALUE_PAIR,
    STOP_GROUP_SOURCE_TYPE_TEXT_REGEX,
    STOP_GROUP_SOURCE_TYPE_LAYOUT_SIGNAL,
    STOP_GROUP_SOURCE_TYPE_UNKNOWN,
}

TRIGGER_LABEL_PICKUP = "pickup"
TRIGGER_LABEL_DELIVERY = "delivery"
TRIGGER_LABEL_STOP = "stop"
TRIGGER_LABEL_DATE = "date"
TRIGGER_LABEL_TIME = "time"
TRIGGER_LABEL_LOCATION = "location"
TRIGGER_LABEL_REFERENCE = "reference"
TRIGGER_LABEL_UNKNOWN = "unknown"

TRIGGER_LABEL_CATEGORIES = {
    TRIGGER_LABEL_PICKUP,
    TRIGGER_LABEL_DELIVERY,
    TRIGGER_LABEL_STOP,
    TRIGGER_LABEL_DATE,
    TRIGGER_LABEL_TIME,
    TRIGGER_LABEL_LOCATION,
    TRIGGER_LABEL_REFERENCE,
    TRIGGER_LABEL_UNKNOWN,
}

STOP_GROUP_PROVENANCE_VERSION = "stop_group_provenance_v1"

_NOISE_SECTION_ROLES = {
    "LEGAL_TERMS",
    "PAYMENT_TERMS",
    "BILLING_INSTRUCTIONS",
    "QUICK_PAY",
    "DEDUCTIONS_PENALTIES",
    "SIGNATURE_BLOCK",
    "CERTIFICATE_SIGNATURE_BLOCK",
    "HEADER",
    "FOOTER",
}


def _text(value):
    return str(value or "").strip()


def _normalize_source_type(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in STOP_GROUP_SOURCE_TYPES else STOP_GROUP_SOURCE_TYPE_UNKNOWN


def _normalize_trigger_label(value):
    text = _text(value).lower().replace(" ", "_").replace("-", "_")
    return text if text in TRIGGER_LABEL_CATEGORIES else TRIGGER_LABEL_UNKNOWN


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


def _bool(value):
    return bool(value)


def _row_key(page_number="", table_id="", row_index=""):
    if not _text(table_id) or _text(row_index) == "":
        return ""
    return "|".join([_text(page_number), _text(table_id), _text(row_index)])


def _section_key(page_number="", section_role="", block_id="", line_id=""):
    if not _text(page_number) or not _text(section_role):
        return ""
    return "|".join(
        item
        for item in [
            _text(page_number),
            _text(section_role).upper(),
            _text(block_id),
            _text(line_id),
        ]
        if item
    )


def build_stop_group_provenance(
    source_type=STOP_GROUP_SOURCE_TYPE_UNKNOWN,
    source_generator="",
    page_number="",
    table_id="",
    row_index="",
    col_index="",
    cell_ref="",
    line_id="",
    block_id="",
    section_role="",
    page_role="",
    trigger_label_category=TRIGGER_LABEL_UNKNOWN,
    candidate_field_names=None,
    grouping_key="",
    warning_codes=None,
):
    fields = sorted(set(_normalize_list(candidate_field_names)))
    normalized_source_type = _normalize_source_type(source_type)
    normalized_trigger = _normalize_trigger_label(trigger_label_category)
    resolved_grouping_key = _text(grouping_key)
    if not resolved_grouping_key:
        resolved_grouping_key = _row_key(page_number, table_id, row_index)
    if not resolved_grouping_key:
        resolved_grouping_key = _section_key(page_number, section_role, block_id, line_id)

    return {
        "source_type": normalized_source_type,
        "source_generator": _text(source_generator),
        "page_number": page_number if page_number not in [None, ""] else "",
        "table_id": _text(table_id),
        "row_index": row_index if row_index not in [None, ""] else "",
        "col_index": col_index if col_index not in [None, ""] else "",
        "cell_ref": _text(cell_ref),
        "line_id": _text(line_id),
        "block_id": _text(block_id),
        "section_role": _text(section_role),
        "page_role": _text(page_role),
        "trigger_label_category": normalized_trigger,
        "candidate_field_names": fields,
        "field_count": len(fields),
        "has_location_candidate": "location" in fields,
        "has_date_candidate": "date" in fields,
        "has_time_candidate": "time" in fields,
        "has_reference_candidate": "reference" in fields,
        "grouping_key": resolved_grouping_key,
        "raw_text_included": False,
        "private_values_redacted": True,
        "warning_codes": _normalize_list(warning_codes),
        "provenance_version": STOP_GROUP_PROVENANCE_VERSION,
    }


def _provenance_from_stop_group(stop_group):
    if not isinstance(stop_group, dict):
        return None
    provenance = stop_group.get("provenance")
    if isinstance(provenance, dict):
        return provenance
    return None


def _count_by(provenances, key):
    counter = Counter()
    for provenance in provenances:
        value = _text(provenance.get(key))
        if value:
            counter[value] += 1
    return dict(sorted(counter.items()))


def _merge_candidate_count(counts):
    return sum(count - 1 for count in counts.values() if count > 1)


def _noise_candidate_count(provenances):
    return sum(
        1
        for provenance in provenances
        if _text(provenance.get("section_role")).upper() in _NOISE_SECTION_ROLES
    )


def build_stop_group_provenance_summary(
    document_alias="",
    provenances=None,
    stop_groups=None,
    warning_codes=None,
):
    safe_provenances = [
        item for item in provenances or [] if isinstance(item, dict)
    ]
    safe_provenances.extend(
        item
        for item in (_provenance_from_stop_group(group) for group in stop_groups or [])
        if isinstance(item, dict)
    )

    row_keys = _count_by(safe_provenances, "grouping_key")
    table_row_keys = {
        key: count
        for key, count in row_keys.items()
        if key.count("|") >= 2
    }
    section_cluster_keys = {
        key: count
        for key, count in row_keys.items()
        if key.count("|") in {1, 2} and key not in table_row_keys
    }
    summary_warnings = set(_normalize_list(warning_codes))
    for provenance in safe_provenances:
        summary_warnings.update(_normalize_list(provenance.get("warning_codes")))

    return {
        "document_alias": _text(document_alias),
        "raw_group_count": len(safe_provenances),
        "groups_by_source_type": _count_by(safe_provenances, "source_type"),
        "groups_by_page": _count_by(safe_provenances, "page_number"),
        "groups_by_table": _count_by(safe_provenances, "table_id"),
        "groups_by_row_key": row_keys,
        "groups_by_section_role": _count_by(safe_provenances, "section_role"),
        "groups_by_trigger_label": _count_by(safe_provenances, "trigger_label_category"),
        "one_group_per_cell_suspected_count": sum(
            1
            for provenance in safe_provenances
            if provenance.get("source_type") == STOP_GROUP_SOURCE_TYPE_TABLE_CELL
        ),
        "one_group_per_line_suspected_count": sum(
            1
            for provenance in safe_provenances
            if provenance.get("source_type") == STOP_GROUP_SOURCE_TYPE_SINGLE_LINE
        ),
        "table_row_merge_candidate_count": _merge_candidate_count(table_row_keys),
        "section_cluster_merge_candidate_count": _merge_candidate_count(section_cluster_keys),
        "duplicate_candidate_count": _merge_candidate_count(row_keys),
        "noise_candidate_count": _noise_candidate_count(safe_provenances),
        "warning_codes": sorted(summary_warnings),
        "raw_text_included": False,
        "private_values_redacted": True,
        "provenance_version": STOP_GROUP_PROVENANCE_VERSION,
    }
