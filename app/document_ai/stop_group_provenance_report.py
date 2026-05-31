"""Local-only safe reports for stop group provenance diagnostics."""

import json
from collections import Counter
from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    PrivateMeasurementOutputError,
)


STOP_GROUP_PROVENANCE_JSON = "stop_group_provenance.json"
STOP_GROUP_PROVENANCE_MD = "stop_group_provenance_report.md"
DEFAULT_STOP_GROUP_PROVENANCE_JSON = (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR / STOP_GROUP_PROVENANCE_JSON
)
DEFAULT_STOP_GROUP_PROVENANCE_MD = (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR / STOP_GROUP_PROVENANCE_MD
)

ROOT_CAUSE_ONE_GROUP_PER_CELL = "ONE_GROUP_PER_CELL"
ROOT_CAUSE_ONE_GROUP_PER_LINE = "ONE_GROUP_PER_LINE"
ROOT_CAUSE_TABLE_ROW_NOT_MERGED = "TABLE_ROW_NOT_MERGED"
ROOT_CAUSE_SECTION_LINES_NOT_CLUSTERED = "SECTION_LINES_NOT_CLUSTERED"
ROOT_CAUSE_DUPLICATE_HEADERS_NOT_MERGED = "DUPLICATE_HEADERS_NOT_MERGED"
ROOT_CAUSE_TERMS_BILLING_NOISE_NOT_FILTERED = "TERMS_BILLING_NOISE_NOT_FILTERED"
ROOT_CAUSE_DATE_TIME_SPLIT_FROM_LOCATION = "DATE_TIME_SPLIT_FROM_LOCATION"
ROOT_CAUSE_SCOPE_FILTER_MISMATCH = "SCOPE_FILTER_MISMATCH"
ROOT_CAUSE_NORMALIZER_PASSTHROUGH = "NORMALIZER_PASSTHROUGH"

STOP_PROVENANCE_REPORT_VERSION = "stop_group_provenance_report_v1"


def _text(value):
    return str(value or "").strip()


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_mapping(value):
    if not isinstance(value, dict):
        return {}
    return {
        _text(key): item
        for key, item in sorted(value.items(), key=lambda pair: _text(pair[0]))
        if _text(key)
    }


def _normalize_output_dir(output_dir=None, allow_custom_output_dir=False):
    path = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise PrivateMeasurementOutputError(
                "custom output directory requires allow_custom_output_dir=True"
            )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _count_values(report_rows, key):
    counter = Counter()
    for row in report_rows:
        value = row.get(key)
        if isinstance(value, list):
            counter.update(_text(item) for item in value if _text(item))
        elif _text(value):
            counter[_text(value)] += 1
    return dict(sorted(counter.items()))


def _sum_mappings(report_rows, key):
    counter = Counter()
    for row in report_rows:
        mapping = row.get(key, {})
        if not isinstance(mapping, dict):
            continue
        for item, count in mapping.items():
            if _text(item):
                counter[_text(item)] += _int(count)
    return dict(sorted(counter.items()))


def _suspected_root_causes(row, summary):
    causes = set()
    raw_group_count = _int(summary.get("raw_group_count"))
    normalized_stop_count = _int(row.get("normalized_stop_count"))

    if raw_group_count and normalized_stop_count == raw_group_count:
        causes.add(ROOT_CAUSE_NORMALIZER_PASSTHROUGH)
    if _int(summary.get("one_group_per_cell_suspected_count")):
        causes.add(ROOT_CAUSE_ONE_GROUP_PER_CELL)
    if _int(summary.get("one_group_per_line_suspected_count")):
        causes.add(ROOT_CAUSE_ONE_GROUP_PER_LINE)
    if _int(summary.get("table_row_merge_candidate_count")):
        causes.add(ROOT_CAUSE_TABLE_ROW_NOT_MERGED)
    if _int(summary.get("section_cluster_merge_candidate_count")):
        causes.add(ROOT_CAUSE_SECTION_LINES_NOT_CLUSTERED)
    if _int(summary.get("duplicate_candidate_count")) and not _int(
        row.get("stop_duplicate_removed_count")
    ):
        causes.add(ROOT_CAUSE_DUPLICATE_HEADERS_NOT_MERGED)
    if _int(summary.get("noise_candidate_count")) and not _int(
        row.get("stop_noise_removed_count")
    ):
        causes.add(ROOT_CAUSE_TERMS_BILLING_NOISE_NOT_FILTERED)
    if _int(row.get("date_candidate_generated_count")) and _int(
        row.get("unresolved_due_to_missing_date")
    ):
        causes.add(ROOT_CAUSE_DATE_TIME_SPLIT_FROM_LOCATION)

    warnings = " ".join(str(item) for item in row.get("warning_codes", []) or [])
    if "scope" in warnings.lower():
        causes.add(ROOT_CAUSE_SCOPE_FILTER_MISMATCH)

    return sorted(causes)


def build_stop_group_provenance_report_rows(rows):
    report_rows = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        summary = row.get("stop_group_provenance_summary", {})
        if not isinstance(summary, dict):
            summary = {}
        if not summary and not row.get("stop_group_count"):
            continue

        report_row = {
            "alias": _text(summary.get("document_alias")) or _text(row.get("document_alias")),
            "raw_group_count": _int(summary.get("raw_group_count")),
            "normalized_stop_count": _int(row.get("normalized_stop_count")),
            "groups_by_source_type": _safe_mapping(summary.get("groups_by_source_type")),
            "groups_by_page": _safe_mapping(summary.get("groups_by_page")),
            "groups_by_table": _safe_mapping(summary.get("groups_by_table")),
            "groups_by_row_key": _safe_mapping(summary.get("groups_by_row_key")),
            "groups_by_section_role": _safe_mapping(summary.get("groups_by_section_role")),
            "groups_by_trigger_label": _safe_mapping(summary.get("groups_by_trigger_label")),
            "table_row_merge_candidate_count": _int(
                summary.get("table_row_merge_candidate_count")
            ),
            "section_cluster_merge_candidate_count": _int(
                summary.get("section_cluster_merge_candidate_count")
            ),
            "duplicate_candidate_count": _int(summary.get("duplicate_candidate_count")),
            "noise_candidate_count": _int(summary.get("noise_candidate_count")),
            "warning_codes": sorted(
                _text(item)
                for item in (summary.get("warning_codes", []) or [])
                if _text(item)
            ),
            "raw_text_included": False,
            "private_values_redacted": True,
        }
        report_row["suspected_root_causes"] = _suspected_root_causes(row, summary)
        report_rows.append(report_row)
    return report_rows


def build_stop_group_provenance_report_payload(rows):
    report_rows = build_stop_group_provenance_report_rows(rows)
    return {
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
        "report_version": STOP_PROVENANCE_REPORT_VERSION,
        "rows": report_rows,
        "aggregate": {
            "document_count": len(report_rows),
            "raw_group_count_total": sum(row["raw_group_count"] for row in report_rows),
            "normalized_stop_count_total": sum(
                row["normalized_stop_count"] for row in report_rows
            ),
            "groups_by_source_type": _sum_mappings(report_rows, "groups_by_source_type"),
            "groups_by_trigger_label": _sum_mappings(report_rows, "groups_by_trigger_label"),
            "suspected_root_cause_counts": _count_values(
                report_rows, "suspected_root_causes"
            ),
            "table_row_merge_candidate_count_total": sum(
                row["table_row_merge_candidate_count"] for row in report_rows
            ),
            "section_cluster_merge_candidate_count_total": sum(
                row["section_cluster_merge_candidate_count"] for row in report_rows
            ),
            "duplicate_candidate_count_total": sum(
                row["duplicate_candidate_count"] for row in report_rows
            ),
            "noise_candidate_count_total": sum(
                row["noise_candidate_count"] for row in report_rows
            ),
        },
    }


def _markdown_mapping(mapping):
    return json.dumps(mapping or {}, sort_keys=True)


def build_stop_group_provenance_markdown(rows):
    payload = build_stop_group_provenance_report_payload(rows)
    aggregate = payload["aggregate"]
    lines = [
        "# Stop Group Provenance Report",
        "",
        "Local-only report. No raw text, private values, filenames, or paths included.",
        "",
        f"- document_count: {aggregate.get('document_count', 0)}",
        f"- raw_group_count_total: {aggregate.get('raw_group_count_total', 0)}",
        f"- normalized_stop_count_total: {aggregate.get('normalized_stop_count_total', 0)}",
        f"- groups_by_source_type: {_markdown_mapping(aggregate.get('groups_by_source_type'))}",
        f"- groups_by_trigger_label: {_markdown_mapping(aggregate.get('groups_by_trigger_label'))}",
        f"- suspected_root_cause_counts: {_markdown_mapping(aggregate.get('suspected_root_cause_counts'))}",
        f"- table_row_merge_candidate_count_total: {aggregate.get('table_row_merge_candidate_count_total', 0)}",
        f"- section_cluster_merge_candidate_count_total: {aggregate.get('section_cluster_merge_candidate_count_total', 0)}",
        f"- duplicate_candidate_count_total: {aggregate.get('duplicate_candidate_count_total', 0)}",
        f"- noise_candidate_count_total: {aggregate.get('noise_candidate_count_total', 0)}",
    ]
    for row in payload["rows"]:
        lines.extend(
            [
                "",
                f"## {row.get('alias', '')}",
                f"- raw_group_count: {row.get('raw_group_count', 0)}",
                f"- normalized_stop_count: {row.get('normalized_stop_count', 0)}",
                f"- groups_by_source_type: {_markdown_mapping(row.get('groups_by_source_type'))}",
                f"- groups_by_page: {_markdown_mapping(row.get('groups_by_page'))}",
                f"- groups_by_table: {_markdown_mapping(row.get('groups_by_table'))}",
                f"- groups_by_row_key: {_markdown_mapping(row.get('groups_by_row_key'))}",
                f"- groups_by_section_role: {_markdown_mapping(row.get('groups_by_section_role'))}",
                f"- groups_by_trigger_label: {_markdown_mapping(row.get('groups_by_trigger_label'))}",
                f"- table_row_merge_candidate_count: {row.get('table_row_merge_candidate_count', 0)}",
                f"- section_cluster_merge_candidate_count: {row.get('section_cluster_merge_candidate_count', 0)}",
                f"- duplicate_candidate_count: {row.get('duplicate_candidate_count', 0)}",
                f"- noise_candidate_count: {row.get('noise_candidate_count', 0)}",
                f"- suspected_root_causes: {row.get('suspected_root_causes', [])}",
                f"- warning_codes: {row.get('warning_codes', [])}",
            ]
        )
    lines.extend(
        [
            "",
            "SAFE TO SHARE: aliases, counts, source types, grouping keys, root-cause labels.",
            "DO NOT SHARE: raw text, filenames, broker names, MCs, rates, addresses, dates/times, references, local paths.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_stop_group_provenance_report(
    rows,
    output_dir=None,
    allow_custom_output_dir=False,
):
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    json_path = directory / STOP_GROUP_PROVENANCE_JSON
    md_path = directory / STOP_GROUP_PROVENANCE_MD
    payload = build_stop_group_provenance_report_payload(rows)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(build_stop_group_provenance_markdown(rows), encoding="utf-8")
    return {
        "json": str(json_path),
        "md": str(md_path),
        "row_count": len(payload["rows"]),
        "local_only": True,
        "private_values_redacted": True,
        "raw_text_saved": False,
    }
