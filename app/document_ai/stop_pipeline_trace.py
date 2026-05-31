"""Safe stop pipeline stage trace contracts."""

from app.document_ai.ratecon_candidates import normalize_list


STOP_PIPELINE_TRACE_VERSION = "stop_pipeline_trace_v1"

STOP_STAGE_RAW_SIGNALS = "raw_signals"
STOP_STAGE_PREMERGE_GROUPS = "premerge_groups"
STOP_STAGE_POST_SINGLE_LINE_CLUSTER = "post_single_line_cluster"
STOP_STAGE_POST_TABLE_ROW_MERGE = "post_table_row_merge"
STOP_STAGE_POST_SECTION_CLUSTER = "post_section_cluster"
STOP_STAGE_POST_NOISE_FILTER = "post_noise_filter"
STOP_STAGE_POST_STRUCTURAL_DEDUPE = "post_structural_dedupe"
STOP_STAGE_POST_DATE_TIME_ATTACHMENT = "post_date_time_attachment"
STOP_STAGE_NORMALIZED_STOPS = "normalized_stops"

STOP_PIPELINE_STAGE_NAMES = {
    STOP_STAGE_RAW_SIGNALS,
    STOP_STAGE_PREMERGE_GROUPS,
    STOP_STAGE_POST_SINGLE_LINE_CLUSTER,
    STOP_STAGE_POST_TABLE_ROW_MERGE,
    STOP_STAGE_POST_SECTION_CLUSTER,
    STOP_STAGE_POST_NOISE_FILTER,
    STOP_STAGE_POST_STRUCTURAL_DEDUPE,
    STOP_STAGE_POST_DATE_TIME_ATTACHMENT,
    STOP_STAGE_NORMALIZED_STOPS,
}


def _text(value):
    return str(value or "").strip()


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def normalize_stop_pipeline_stage_name(value):
    token = _text(value)
    return token if token in STOP_PIPELINE_STAGE_NAMES else STOP_STAGE_PREMERGE_GROUPS


def build_stop_pipeline_stage_stats(
    stage_name,
    input_count=0,
    output_count=0,
    changed_count=0,
    merge_count=0,
    removed_count=0,
    warning_codes=None,
):
    """Build a serializable safe stage stats record."""

    return {
        "stage_name": normalize_stop_pipeline_stage_name(stage_name),
        "input_count": _int(input_count),
        "output_count": _int(output_count),
        "changed_count": _int(changed_count),
        "merge_count": _int(merge_count),
        "removed_count": _int(removed_count),
        "warning_codes": normalize_list(warning_codes),
    }


def _stage_changed(stage):
    if not isinstance(stage, dict):
        return False
    if _int(stage.get("input_count")) != _int(stage.get("output_count")):
        return True
    return any(
        _int(stage.get(field)) > 0
        for field in ("changed_count", "merge_count", "removed_count")
    )


def first_changed_stage_name(stages):
    for stage in stages or []:
        if _stage_changed(stage):
            return _text(stage.get("stage_name"))
    return ""


def build_stop_pipeline_trace(
    document_alias="",
    stages=None,
    no_change_reason="",
    warning_codes=None,
):
    """Build a safe trace for stop grouping pipeline stage counts."""

    normalized_stages = [stage for stage in stages or [] if isinstance(stage, dict)]
    first_changed = first_changed_stage_name(normalized_stages)
    passthrough_detected = not bool(first_changed) and bool(normalized_stages)

    return {
        "document_alias": _text(document_alias),
        "stages": normalized_stages,
        "passthrough_detected": passthrough_detected,
        "first_stage_that_changed": first_changed,
        "no_change_reason": _text(no_change_reason) if passthrough_detected else "",
        "warning_codes": normalize_list(warning_codes),
        "trace_version": STOP_PIPELINE_TRACE_VERSION,
    }
