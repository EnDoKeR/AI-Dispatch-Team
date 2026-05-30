"""Group redacted pattern summaries into safe template family candidates."""

from collections import defaultdict

from app.document_ai.private_template_patterns import build_template_family_candidate


def _text(value):
    return str(value or "").strip()


def _line_values(summary, key):
    return [
        _text(pattern.get("redacted_line", ""))
        for pattern in summary.get(key, [])
        if _text(pattern.get("redacted_line", ""))
    ]


def _unique_sorted(values):
    return sorted({_text(value) for value in values if _text(value)})


def _family_key(summary):
    warnings = set(summary.get("warning_codes", []))
    if "OCR_NEEDED" in warnings or "no_extractable_text" in warnings:
        return ("ocr_needed",)

    markers = tuple(_unique_sorted(summary.get("section_markers", [])))
    rate = tuple(_line_values(summary, "redacted_rate_label_patterns")[:3])
    stops = tuple(_line_values(summary, "redacted_stop_label_patterns")[:3])
    refs = tuple(_line_values(summary, "redacted_reference_label_patterns")[:3])
    page_bucket = "multi_page" if int(summary.get("page_count", 0) or 0) > 1 else "single_page"
    return (page_bucket, markers, rate, stops, refs)


def _common_lines(summaries, key):
    if not summaries:
        return []

    sets = [set(_line_values(summary, key)) for summary in summaries]
    common = set.intersection(*sets) if sets else set()
    if common:
        return _unique_sorted(common)

    combined = []
    for summary in summaries:
        combined.extend(_line_values(summary, key))
    return _unique_sorted(combined)[:5]


def group_redacted_patterns_into_template_families(summaries):
    grouped = defaultdict(list)
    for summary in summaries or []:
        if not isinstance(summary, dict):
            continue
        grouped[_family_key(summary)].append(summary)

    families = []
    for index, key in enumerate(sorted(grouped.keys(), key=lambda item: repr(item)), start=1):
        group = sorted(grouped[key], key=lambda summary: summary.get("document_alias", ""))
        aliases = [summary.get("document_alias", "") for summary in group]
        is_ocr_group = key == ("ocr_needed",)
        confidence = "high" if len(group) >= 3 else "medium" if len(group) == 2 else "low"
        warnings = ["ocr_needed_family_no_text_patterns"] if is_ocr_group else []

        markers = []
        for summary in group:
            markers.extend(summary.get("section_markers", []))

        families.append(
            build_template_family_candidate(
                family_alias=f"TEMPLATE_FAMILY_{index:03d}",
                aliases=aliases,
                common_redacted_markers=_unique_sorted(markers),
                likely_rate_labels_redacted=[] if is_ocr_group else _common_lines(group, "redacted_rate_label_patterns"),
                likely_stop_labels_redacted=[] if is_ocr_group else _common_lines(group, "redacted_stop_label_patterns"),
                likely_reference_labels_redacted=[] if is_ocr_group else _common_lines(group, "redacted_reference_label_patterns"),
                confidence_bucket=confidence,
                warnings=warnings,
            )
        )

    return families
