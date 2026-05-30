"""Safe status-only comparison for private template overlay measurements."""

from pathlib import Path


DEFAULT_TEMPLATE_OVERLAY_COMPARISON_PATH = Path(
    ".local_outputs/private_ratecon_measurement/template_overlay_comparison.md"
)


def _count(mapping, key):
    return int((mapping or {}).get(key, 0) or 0)


def _delta(before, after):
    if after < before:
        direction = "improved"
    elif after > before:
        direction = "worsened"
    else:
        direction = "unchanged"
    return {
        "before": int(before or 0),
        "after": int(after or 0),
        "delta": int(after or 0) - int(before or 0),
        "status": direction,
    }


def build_template_overlay_comparison(baseline_aggregate, overlay_aggregate):
    baseline = baseline_aggregate or {}
    overlay = overlay_aggregate or {}
    baseline_blockers = baseline.get("blocker_category_counts", {})
    overlay_blockers = overlay.get("blocker_category_counts", {})

    return {
        "template_unknown": _delta(
            _count(baseline.get("template_status_counts", {}), "unknown"),
            _count(overlay.get("template_status_counts", {}), "unknown"),
        ),
        "template_matched": _delta(
            _count(baseline.get("template_status_counts", {}), "matched"),
            _count(overlay.get("template_status_counts", {}), "matched"),
        ),
        "review_required": _delta(
            baseline.get("review_required_count", 0),
            overlay.get("review_required_count", 0),
        ),
        "missing_critical_fields": {
            field: _delta(
                baseline.get("critical_field_missing_counts", {}).get(field, 0),
                overlay.get("critical_field_missing_counts", {}).get(field, 0),
            )
            for field in sorted(
                set(baseline.get("critical_field_missing_counts", {}))
                | set(overlay.get("critical_field_missing_counts", {}))
            )
        },
        "conflict_critical_fields": {
            field: _delta(
                baseline.get("conflict_counts_by_field", {}).get(field, 0),
                overlay.get("conflict_counts_by_field", {}).get(field, 0),
            )
            for field in sorted(
                set(baseline.get("conflict_counts_by_field", {}))
                | set(overlay.get("conflict_counts_by_field", {}))
            )
        },
        "template_gap": _delta(
            _count(baseline_blockers, "TEMPLATE_GAP"),
            _count(overlay_blockers, "TEMPLATE_GAP"),
        ),
        "resolver_gap": _delta(
            _count(baseline_blockers, "RESOLVER_GAP"),
            _count(overlay_blockers, "RESOLVER_GAP"),
        ),
        "rate_conflict": _delta(
            baseline.get("conflict_counts_by_field", {}).get("rate", 0),
            overlay.get("conflict_counts_by_field", {}).get("rate", 0),
        ),
        "stop_association_conflict": _delta(
            sum(
                baseline.get("conflict_counts_by_field", {}).get(field, 0)
                for field in [
                    "pickup_location",
                    "pickup_date",
                    "delivery_location",
                    "delivery_date",
                ]
            ),
            sum(
                overlay.get("conflict_counts_by_field", {}).get(field, 0)
                for field in [
                    "pickup_location",
                    "pickup_date",
                    "delivery_location",
                    "delivery_date",
                ]
            ),
        ),
        "ocr_needed": _delta(
            _count(baseline_blockers, "OCR_NEEDED"),
            _count(overlay_blockers, "OCR_NEEDED"),
        ),
        "private_values_redacted": True,
        "raw_text_included": False,
    }


def write_template_overlay_comparison_md(comparison, output_path=None):
    path = Path(output_path) if output_path else DEFAULT_TEMPLATE_OVERLAY_COMPARISON_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Safe Private Template Overlay Comparison",
        "",
        "Local-only ignored report. Status deltas only; no private values.",
        "",
    ]
    for key in [
        "template_unknown",
        "template_matched",
        "review_required",
        "template_gap",
        "resolver_gap",
        "rate_conflict",
        "stop_association_conflict",
        "ocr_needed",
    ]:
        value = comparison.get(key, {})
        lines.append(
            f"- {key}: before={value.get('before', 0)}, after={value.get('after', 0)}, "
            f"delta={value.get('delta', 0)}, status={value.get('status', '')}"
        )
    lines.append("")
    lines.append("## Missing Critical Fields")
    for field, value in sorted(comparison.get("missing_critical_fields", {}).items()):
        lines.append(
            f"- {field}: before={value.get('before', 0)}, after={value.get('after', 0)}, "
            f"status={value.get('status', '')}"
        )
    lines.append("")
    lines.append("## Conflict Critical Fields")
    for field, value in sorted(comparison.get("conflict_critical_fields", {}).items()):
        lines.append(
            f"- {field}: before={value.get('before', 0)}, after={value.get('after', 0)}, "
            f"status={value.get('status', '')}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
