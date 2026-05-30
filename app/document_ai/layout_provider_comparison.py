"""Safe local-only comparison report for layout provider measurement."""

from collections import Counter
from pathlib import Path

from app.document_ai.private_measurement_outputs import DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR


LAYOUT_PROVIDER_COMPARISON_MD = "layout_provider_comparison.md"


def _count_by_key(rows, key):
    counter = Counter()
    for row in rows or []:
        value = str(row.get(key) or "").strip()
        if value:
            counter[value] += 1
    return dict(sorted(counter.items()))


def _sum_deltas(rows):
    deltas = Counter()
    for row in rows or []:
        text_counts = row.get("candidate_counts_by_field", {}) or {}
        layout_counts = row.get("layout_candidate_counts_by_field", {}) or {}
        fields = set(text_counts).union(layout_counts)
        for field_name in fields:
            deltas[field_name] += int(layout_counts.get(field_name, 0) or 0) - int(
                text_counts.get(field_name, 0) or 0
            )
    return dict(sorted(deltas.items()))


def _alias_field_map(rows, key):
    result = {}
    for row in rows or []:
        alias = str(row.get("document_alias") or "").strip()
        if not alias:
            continue
        fields = [
            str(field or "").strip()
            for field in row.get(key, []) or []
            if str(field or "").strip()
        ]
        if fields:
            result[alias] = sorted(fields)
    return dict(sorted(result.items()))


def _layout_attempted(status):
    text = str(status or "").strip()
    return bool(text and not text.startswith("skipped"))


def build_layout_provider_comparison(rows):
    safe_rows = [row for row in rows or [] if isinstance(row, dict)]
    status_counts = _count_by_key(safe_rows, "layout_provider_status")

    return {
        "total_docs": len(safe_rows),
        "layout_provider_attempted_count": sum(
            1 for row in safe_rows if _layout_attempted(row.get("layout_provider_status"))
        ),
        "layout_provider_status_counts": status_counts,
        "layout_provider_success_count": status_counts.get("success", 0),
        "layout_provider_failure_count": sum(
            count
            for status, count in status_counts.items()
            if status and status != "success" and not status.startswith("skipped")
        ),
        "layout_provider_skipped_count": sum(
            count
            for status, count in status_counts.items()
            if str(status).startswith("skipped")
        ),
        "candidate_count_deltas_by_field": _sum_deltas(safe_rows),
        "layout_improved_fields_by_alias": _alias_field_map(safe_rows, "layout_improved_fields"),
        "layout_worsened_fields_by_alias": _alias_field_map(safe_rows, "layout_worsened_fields"),
        "layout_unchanged_fields_by_alias": _alias_field_map(safe_rows, "layout_unchanged_fields"),
        "blocker_category_counts": _count_list_values(safe_rows, "blocker_categories"),
        "status_delta_mode": "candidate_coverage_only_no_resolution_delta",
        "raw_text_saved": False,
        "private_values_redacted": True,
    }


def _count_list_values(rows, key):
    counter = Counter()
    for row in rows or []:
        counter.update(
            str(item or "").strip()
            for item in row.get(key, []) or []
            if str(item or "").strip()
        )
    return dict(sorted(counter.items()))


def _normalize_output_dir(output_dir=None, allow_custom_output_dir=False):
    path = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise ValueError("custom layout comparison output directory requires explicit allow flag")
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_layout_provider_comparison_report(
    rows,
    output_dir=None,
    allow_custom_output_dir=False,
):
    comparison = build_layout_provider_comparison(rows)
    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / LAYOUT_PROVIDER_COMPARISON_MD
    lines = [
        "# Safe Layout Provider Comparison",
        "",
        "Local-only status report. No raw text, filenames, paths, or private values included.",
        "",
        f"- total_docs: {comparison['total_docs']}",
        f"- layout_provider_attempted_count: {comparison['layout_provider_attempted_count']}",
        f"- layout_provider_success_count: {comparison['layout_provider_success_count']}",
        f"- layout_provider_failure_count: {comparison['layout_provider_failure_count']}",
        f"- layout_provider_skipped_count: {comparison['layout_provider_skipped_count']}",
        f"- layout_provider_status_counts: {comparison['layout_provider_status_counts']}",
        f"- candidate_count_deltas_by_field: {comparison['candidate_count_deltas_by_field']}",
        f"- layout_improved_fields_by_alias: {comparison['layout_improved_fields_by_alias']}",
        f"- layout_worsened_fields_by_alias: {comparison['layout_worsened_fields_by_alias']}",
        f"- layout_unchanged_fields_by_alias: {comparison['layout_unchanged_fields_by_alias']}",
        f"- blocker_category_counts: {comparison['blocker_category_counts']}",
        f"- status_delta_mode: {comparison['status_delta_mode']}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
