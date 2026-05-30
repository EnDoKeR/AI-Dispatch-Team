"""Safe diagnostics contracts for layout provider output quality."""

from pathlib import Path

from app.document_ai.private_measurement_outputs import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
    PrivateMeasurementOutputError,
)


QUALITY_EMPTY = "empty"
QUALITY_WEAK = "weak"
QUALITY_TEXT_ONLY = "text_only"
QUALITY_TABLE_LIKE = "table_like"
QUALITY_RICH_LAYOUT = "rich_layout"
QUALITY_UNKNOWN = "unknown"

LAYOUT_QUALITY_BUCKETS = {
    QUALITY_EMPTY,
    QUALITY_WEAK,
    QUALITY_TEXT_ONLY,
    QUALITY_TABLE_LIKE,
    QUALITY_RICH_LAYOUT,
    QUALITY_UNKNOWN,
}

LAYOUT_PROVIDER_DIAGNOSTICS_VERSION = "layout_provider_diagnostics_v1"
LAYOUT_PROVIDER_DIAGNOSTICS_MD = "layout_provider_diagnostics.md"

ISSUE_PROVIDER_NO_TABLES = "provider_no_tables"
ISSUE_PROVIDER_NO_WORDS = "provider_no_words"
ISSUE_PROVIDER_HAS_TABLES_BUT_NO_STOP_GROUPS = "provider_has_tables_but_no_stop_groups"
ISSUE_PROVIDER_HAS_STOP_LABELS_BUT_NO_GROUPS = "provider_has_stop_labels_but_no_groups"
ISSUE_SCOPE_FILTER_EXCLUDED_PAGES = "scope_filter_excluded_pages"
ISSUE_ASSOCIATION_LOGIC_GAP = "association_logic_gap"
ISSUE_CANDIDATE_FUSION_REGRESSION = "candidate_fusion_regression"
ISSUE_NO_DIAGNOSTIC_ISSUE = "no_diagnostic_issue"

FORBIDDEN_DIAGNOSTIC_KEYS = {
    "raw_text",
    "extracted_text",
    "filename",
    "file_path",
    "local_path",
    "broker_name",
    "broker_mc",
    "rate_value",
    "address",
    "reference_value",
    "private_note",
}

_PICKUP_LABELS = ("pickup", "pick up", "pu", "shipper", "origin")
_DELIVERY_LABELS = (
    "delivery",
    "deliver",
    "drop",
    "del",
    "consignee",
    "receiver",
    "destination",
    "so",
)
_STOP_LABELS = ("stop", "route", "appointment", "appt")
_DATE_LABELS = ("date", "pickup date", "delivery date", "pu date", "del date", "<date>")
_TIME_LABELS = ("time", "appt", "appointment", "window", "<time>")
_RATE_LABELS = ("rate", "pay", "total", "agreed amount", "carrier pay")

STOP_SIGNAL_KEYS = (
    "pickup_label_hits",
    "delivery_label_hits",
    "stop_label_hits",
    "date_label_hits",
    "time_label_hits",
    "table_stop_like_rows",
)


def _text(value):
    return str(value or "").strip()


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _bool(value):
    return bool(value)


def _list(value):
    if not value:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    return [_text(item) for item in values if _text(item)]


def _mapping(value):
    if not isinstance(value, dict):
        return {}
    return {_text(key): item for key, item in value.items() if _text(key)}


def _contains_any(text, labels):
    normalized = f" {_text(text).lower().replace('#', ' ')} "
    return any(f" {label} " in normalized for label in labels)


def _char_count_bucket(char_count):
    count = _int(char_count)
    if count <= 0:
        return "zero"
    if count < 250:
        return "very_low"
    if count < 1500:
        return "low"
    if count < 5000:
        return "medium"
    return "high"


def normalize_layout_quality_bucket(value):
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    return text if text in LAYOUT_QUALITY_BUCKETS else QUALITY_UNKNOWN


def build_stop_evidence_signals(
    pickup_label_hits=0,
    delivery_label_hits=0,
    stop_label_hits=0,
    date_label_hits=0,
    time_label_hits=0,
    table_stop_like_rows=0,
):
    return {
        "pickup_label_hits": _int(pickup_label_hits),
        "delivery_label_hits": _int(delivery_label_hits),
        "stop_label_hits": _int(stop_label_hits),
        "date_label_hits": _int(date_label_hits),
        "time_label_hits": _int(time_label_hits),
        "table_stop_like_rows": _int(table_stop_like_rows),
    }


def compute_layout_quality_bucket(
    total_word_count=0,
    total_line_count=0,
    total_table_count=0,
    total_table_cell_count=0,
    page_count=0,
):
    words = _int(total_word_count)
    lines = _int(total_line_count)
    tables = _int(total_table_count)
    cells = _int(total_table_cell_count)
    pages = _int(page_count)

    if words <= 0 and lines <= 0 and tables <= 0 and cells <= 0:
        return QUALITY_EMPTY
    if tables > 0 and cells >= 12 and (words > 0 or lines > 0):
        return QUALITY_RICH_LAYOUT
    if tables > 0 or cells > 0:
        return QUALITY_TABLE_LIKE
    if words >= max(20, pages * 10) or lines >= max(5, pages * 3):
        return QUALITY_TEXT_ONLY
    return QUALITY_WEAK


def build_provider_page_diagnostics(
    page_number=0,
    word_count=0,
    line_count=0,
    block_count=0,
    table_count=0,
    table_cell_count=0,
    rect_count=0,
    curve_count=0,
    image_count=0,
    char_count=0,
    warning_codes=None,
):
    words = _int(word_count)
    lines = _int(line_count)
    tables = _int(table_count)
    cells = _int(table_cell_count)

    return {
        "page_number": _int(page_number),
        "word_count": words,
        "line_count": lines,
        "block_count": _int(block_count),
        "table_count": tables,
        "table_cell_count": cells,
        "rect_count": _int(rect_count),
        "curve_count": _int(curve_count),
        "image_count": _int(image_count),
        "char_count_bucket": _char_count_bucket(char_count),
        "has_tables": tables > 0 or cells > 0,
        "has_words": words > 0,
        "has_lines": lines > 0,
        "warning_codes": _list(warning_codes),
    }


def build_provider_document_diagnostics(
    document_alias="",
    provider_name="",
    provider_status="",
    page_count=0,
    pages=None,
    table_settings_profile="",
    extraction_scope_counts=None,
    layout_quality_bucket="",
    stop_evidence_signals=None,
    warning_codes=None,
):
    normalized_pages = [
        build_provider_page_diagnostics(
            page_number=page.get("page_number", 0),
            word_count=page.get("word_count", 0),
            line_count=page.get("line_count", 0),
            block_count=page.get("block_count", 0),
            table_count=page.get("table_count", 0),
            table_cell_count=page.get("table_cell_count", 0),
            rect_count=page.get("rect_count", 0),
            curve_count=page.get("curve_count", 0),
            image_count=page.get("image_count", 0),
            char_count=page.get("char_count", 0),
            warning_codes=page.get("warning_codes"),
        )
        for page in (pages or [])
        if isinstance(page, dict)
    ]
    total_word_count = sum(page["word_count"] for page in normalized_pages)
    total_line_count = sum(page["line_count"] for page in normalized_pages)
    total_table_count = sum(page["table_count"] for page in normalized_pages)
    total_table_cell_count = sum(page["table_cell_count"] for page in normalized_pages)
    normalized_page_count = _int(page_count) or len(normalized_pages)
    quality = normalize_layout_quality_bucket(layout_quality_bucket)
    if quality == QUALITY_UNKNOWN and normalized_pages:
        quality = compute_layout_quality_bucket(
            total_word_count=total_word_count,
            total_line_count=total_line_count,
            total_table_count=total_table_count,
            total_table_cell_count=total_table_cell_count,
            page_count=normalized_page_count,
        )

    signals = build_stop_evidence_signals(**_mapping(stop_evidence_signals))

    return {
        "document_alias": _text(document_alias),
        "provider_name": _text(provider_name),
        "provider_status": _text(provider_status),
        "page_count": normalized_page_count,
        "pages": normalized_pages,
        "total_word_count": total_word_count,
        "total_line_count": total_line_count,
        "total_table_count": total_table_count,
        "total_table_cell_count": total_table_cell_count,
        "table_settings_profile": _text(table_settings_profile),
        "extraction_scope_counts": _mapping(extraction_scope_counts),
        "layout_quality_bucket": quality,
        "stop_evidence_signals": signals,
        "warning_codes": _list(warning_codes),
        "raw_text_included": False,
        "private_values_redacted": True,
        "diagnostics_version": LAYOUT_PROVIDER_DIAGNOSTICS_VERSION,
    }


def summarize_layout_tables(layout_artifact):
    table_count = 0
    table_cell_count = 0
    table_stop_like_rows = 0

    for page in (layout_artifact or {}).get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        for table in page.get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            table_count += 1
            rows = {}
            for cell in table.get("cells", []) or []:
                if not isinstance(cell, dict):
                    continue
                table_cell_count += 1
                row_index = _int(cell.get("row_index"))
                rows.setdefault(row_index, []).append(_text(cell.get("text_redacted")))
            for row_texts in rows.values():
                row_text = " ".join(row_texts)
                has_stop_label = (
                    _contains_any(row_text, _PICKUP_LABELS)
                    or _contains_any(row_text, _DELIVERY_LABELS)
                    or _contains_any(row_text, _STOP_LABELS)
                )
                has_date_or_time = _contains_any(row_text, _DATE_LABELS) or _contains_any(
                    row_text,
                    _TIME_LABELS,
                )
                if has_stop_label and has_date_or_time:
                    table_stop_like_rows += 1

    return {
        "table_count": table_count,
        "table_cell_count": table_cell_count,
        "table_stop_like_rows": table_stop_like_rows,
    }


def summarize_stop_label_signals(layout_artifact, classification_result=None):
    pickup_hits = 0
    delivery_hits = 0
    stop_hits = 0
    date_hits = 0
    time_hits = 0

    texts = []
    for page in (layout_artifact or {}).get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        for collection_name in ("lines", "blocks"):
            for item in page.get(collection_name, []) or []:
                if isinstance(item, dict):
                    texts.append(_text(item.get("text_redacted")))
        for table in page.get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            for cell in table.get("cells", []) or []:
                if isinstance(cell, dict):
                    texts.append(_text(cell.get("text_redacted")))

    for text in texts:
        pickup_hits += 1 if _contains_any(text, _PICKUP_LABELS) else 0
        delivery_hits += 1 if _contains_any(text, _DELIVERY_LABELS) else 0
        stop_hits += 1 if _contains_any(text, _STOP_LABELS) else 0
        date_hits += 1 if _contains_any(text, _DATE_LABELS) else 0
        time_hits += 1 if _contains_any(text, _TIME_LABELS) else 0

    table_summary = summarize_layout_tables(layout_artifact)
    signals = build_stop_evidence_signals(
        pickup_label_hits=pickup_hits,
        delivery_label_hits=delivery_hits,
        stop_label_hits=stop_hits,
        date_label_hits=date_hits,
        time_label_hits=time_hits,
        table_stop_like_rows=table_summary["table_stop_like_rows"],
    )

    if classification_result:
        return signals
    return signals


def detect_stop_like_tables(layout_artifact):
    summary = summarize_layout_tables(layout_artifact)
    warnings = []
    if summary["table_count"] > 0 and summary["table_stop_like_rows"] <= 0:
        warnings.append("tables_found_but_no_stop_headers")
    if summary["table_stop_like_rows"] > 0:
        warnings.append("stop_headers_found")
    return {
        "table_count": summary["table_count"],
        "table_cell_count": summary["table_cell_count"],
        "stop_like_table_count": 1 if summary["table_stop_like_rows"] > 0 else 0,
        "stop_like_row_count": summary["table_stop_like_rows"],
        "warning_codes": warnings,
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def detect_pickup_delivery_label_lines(layout_artifact):
    refs = []
    counts = {
        "pickup_line_count": 0,
        "delivery_line_count": 0,
        "stop_line_count": 0,
        "date_time_line_count": 0,
    }
    for page in (layout_artifact or {}).get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        for line in page.get("lines", []) or []:
            if not isinstance(line, dict):
                continue
            text = _text(line.get("text_redacted"))
            signal_type = ""
            if _contains_any(text, _PICKUP_LABELS):
                counts["pickup_line_count"] += 1
                signal_type = "pickup"
            elif _contains_any(text, _DELIVERY_LABELS):
                counts["delivery_line_count"] += 1
                signal_type = "delivery"
            elif _contains_any(text, _STOP_LABELS):
                counts["stop_line_count"] += 1
                signal_type = "stop"
            if _contains_any(text, _DATE_LABELS) or _contains_any(text, _TIME_LABELS):
                counts["date_time_line_count"] += 1
                signal_type = signal_type or "date_time"
            if signal_type:
                refs.append(
                    {
                        "page_number": _int(line.get("page_number")),
                        "line_id": _text(line.get("line_id")),
                        "signal_type": signal_type,
                    }
                )
    return {
        **counts,
        "line_refs": refs,
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def detect_stop_like_sections(layout_artifact):
    section_counts = {}
    for page in (layout_artifact or {}).get("pages", []) or []:
        if not isinstance(page, dict):
            continue
        for collection_name in ("lines", "blocks"):
            for item in page.get(collection_name, []) or []:
                if not isinstance(item, dict):
                    continue
                role = _text(item.get("section_role")).upper()
                if role in {
                    "PICKUP_SECTION",
                    "DELIVERY_SECTION",
                    "MULTI_STOP_SECTION",
                    "STOP_TABLE",
                }:
                    section_counts[role] = section_counts.get(role, 0) + 1
    return {
        "section_role_counts": section_counts,
        "stop_section_count": sum(section_counts.values()),
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def detect_stop_signals_from_layout(layout_artifact, classification_result=None):
    signals = summarize_stop_label_signals(layout_artifact, classification_result)
    tables = detect_stop_like_tables(layout_artifact)
    lines = detect_pickup_delivery_label_lines(layout_artifact)
    sections = detect_stop_like_sections(layout_artifact)
    warnings = list(tables["warning_codes"])

    label_count = (
        signals["pickup_label_hits"]
        + signals["delivery_label_hits"]
        + signals["stop_label_hits"]
    )
    if label_count > 0 and tables["stop_like_row_count"] <= 0:
        warnings.append("stop_labels_found_but_no_groups")
    if sections["stop_section_count"] > 0:
        warnings.append("stop_sections_found")

    return {
        "stop_evidence_signals": signals,
        "table_signal_summary": tables,
        "line_signal_summary": lines,
        "section_signal_summary": sections,
        "warning_codes": sorted(set(warnings)),
        "raw_text_included": False,
        "private_values_redacted": True,
    }


def _page_char_count(page):
    total = 0
    for collection_name in ("lines", "blocks"):
        for item in page.get(collection_name, []) or []:
            if isinstance(item, dict):
                total += len(_text(item.get("text_redacted")))
    if total:
        return total
    for word in page.get("words", []) or []:
        if isinstance(word, dict):
            total += len(_text(word.get("text")))
    return total


def _page_diagnostics_from_artifact_page(page):
    tables = [table for table in page.get("tables", []) or [] if isinstance(table, dict)]
    table_cell_count = sum(
        len([cell for cell in table.get("cells", []) or [] if isinstance(cell, dict)])
        for table in tables
    )
    return build_provider_page_diagnostics(
        page_number=page.get("page_number", 0),
        word_count=len([word for word in page.get("words", []) or [] if isinstance(word, dict)]),
        line_count=len([line for line in page.get("lines", []) or [] if isinstance(line, dict)]),
        block_count=len([block for block in page.get("blocks", []) or [] if isinstance(block, dict)]),
        table_count=len(tables),
        table_cell_count=table_cell_count,
        char_count=_page_char_count(page),
        warning_codes=page.get("warning_codes"),
    )


def _classification_scope_counts(classification_result):
    if not isinstance(classification_result, dict):
        return {}
    if isinstance(classification_result.get("extraction_scope_counts"), dict):
        return classification_result["extraction_scope_counts"]
    counts = {}
    for page in classification_result.get("page_results", []) or []:
        if not isinstance(page, dict):
            continue
        for section in page.get("section_summaries", []) or []:
            if not isinstance(section, dict):
                continue
            for scope in section.get("extraction_scopes", []) or []:
                key = _text(scope)
                if key:
                    counts[key] = counts.get(key, 0) + 1
    return counts


def build_layout_provider_diagnostics(provider_result, classification_result=None):
    result = provider_result if isinstance(provider_result, dict) else {}
    artifact = result.get("artifact") if isinstance(result.get("artifact"), dict) else {}
    pages = [
        _page_diagnostics_from_artifact_page(page)
        for page in artifact.get("pages", []) or []
        if isinstance(page, dict)
    ]
    table_summary = summarize_layout_tables(artifact)
    stop_signals = summarize_stop_label_signals(artifact, classification_result)
    warnings = list(result.get("warning_codes", []) or [])
    warnings.extend(artifact.get("warning_codes", []) or [])
    if table_summary["table_count"] and not table_summary["table_stop_like_rows"]:
        warnings.append("tables_found_but_no_stop_headers")
    if (
        stop_signals["pickup_label_hits"]
        or stop_signals["delivery_label_hits"]
        or stop_signals["stop_label_hits"]
    ) and not table_summary["table_stop_like_rows"]:
        warnings.append("stop_labels_found_without_stop_like_rows")

    return build_provider_document_diagnostics(
        document_alias=result.get("document_alias", ""),
        provider_name=result.get("provider_name") or artifact.get("provider", ""),
        provider_status=result.get("status", ""),
        page_count=result.get("page_count") or artifact.get("page_count", len(pages)),
        pages=pages,
        table_settings_profile=result.get("table_settings_profile", ""),
        extraction_scope_counts=_classification_scope_counts(classification_result),
        stop_evidence_signals=stop_signals,
        warning_codes=warnings,
    )


def classify_layout_provider_diagnostic_issue(diagnostics, stop_group_count=0):
    signals = _mapping((diagnostics or {}).get("stop_evidence_signals"))
    warnings = set(_list((diagnostics or {}).get("warning_codes")))
    word_count = _int((diagnostics or {}).get("total_word_count"))
    table_count = _int((diagnostics or {}).get("total_table_count"))
    stop_groups = _int(stop_group_count)
    stop_signal_count = sum(_int(signals.get(key)) for key in STOP_SIGNAL_KEYS)

    if word_count <= 0:
        return ISSUE_PROVIDER_NO_WORDS
    if "scope_filter_excluded_pages" in warnings:
        return ISSUE_SCOPE_FILTER_EXCLUDED_PAGES
    if "candidate_fusion_regression" in warnings:
        return ISSUE_CANDIDATE_FUSION_REGRESSION
    if table_count <= 0:
        return ISSUE_PROVIDER_NO_TABLES
    if table_count > 0 and stop_groups <= 0 and stop_signal_count > 0:
        return ISSUE_PROVIDER_HAS_STOP_LABELS_BUT_NO_GROUPS
    if table_count > 0 and stop_groups <= 0:
        return ISSUE_PROVIDER_HAS_TABLES_BUT_NO_STOP_GROUPS
    if stop_signal_count > 0 and stop_groups <= 0:
        return ISSUE_ASSOCIATION_LOGIC_GAP
    return ISSUE_NO_DIAGNOSTIC_ISSUE


def _reject_unsafe_diagnostics(diagnostics):
    unsafe_keys = FORBIDDEN_DIAGNOSTIC_KEYS & set(diagnostics or {})
    if unsafe_keys:
        raise PrivateMeasurementOutputError(
            "unsafe layout provider diagnostics field detected: "
            + ", ".join(sorted(unsafe_keys))
        )
    if (diagnostics or {}).get("raw_text_included"):
        raise PrivateMeasurementOutputError(
            "layout provider diagnostics cannot include raw text"
        )


def _normalize_output_dir(output_dir=None, allow_custom_output_dir=False):
    path = Path(output_dir) if output_dir else DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR
    if output_dir and not allow_custom_output_dir:
        default_parts = DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR.parts
        if path.parts[: len(default_parts)] != default_parts:
            raise PrivateMeasurementOutputError(
                "custom layout provider diagnostics output directory requires explicit allow flag"
            )
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_layout_provider_diagnostics_report(
    diagnostics_items,
    output_dir=None,
    allow_custom_output_dir=False,
):
    items = diagnostics_items if isinstance(diagnostics_items, list) else [diagnostics_items]
    safe_items = [item for item in items if isinstance(item, dict)]
    for item in safe_items:
        _reject_unsafe_diagnostics(item)

    directory = _normalize_output_dir(output_dir, allow_custom_output_dir)
    path = directory / LAYOUT_PROVIDER_DIAGNOSTICS_MD
    lines = [
        "# Safe Layout Provider Diagnostics",
        "",
        "Local-only report. No raw text, line text, filenames, paths, or private values included.",
        "",
        "| alias | provider_status | page_count | words | lines | tables | cells | quality | stop_signals | table_profile | likely_issue_bucket | warning_codes |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]

    for item in safe_items:
        signals = _mapping(item.get("stop_evidence_signals"))
        stop_signal_summary = ";".join(
            f"{key}={_int(signals.get(key))}" for key in STOP_SIGNAL_KEYS
        )
        lines.append(
            "| {alias} | {status} | {pages} | {words} | {lines_count} | {tables} | {cells} | {quality} | {signals} | {profile} | {issue} | {warnings} |".format(
                alias=_text(item.get("document_alias")),
                status=_text(item.get("provider_status")),
                pages=_int(item.get("page_count")),
                words=_int(item.get("total_word_count")),
                lines_count=_int(item.get("total_line_count")),
                tables=_int(item.get("total_table_count")),
                cells=_int(item.get("total_table_cell_count")),
                quality=_text(item.get("layout_quality_bucket")),
                signals=stop_signal_summary,
                profile=_text(item.get("table_settings_profile")),
                issue=classify_layout_provider_diagnostic_issue(item),
                warnings=";".join(_list(item.get("warning_codes"))),
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _profile_summary_from_result(profile_name, provider_result, document_alias=""):
    result = provider_result if isinstance(provider_result, dict) else {}
    safe_result = dict(result)
    safe_result["document_alias"] = _text(document_alias)
    diagnostics = build_layout_provider_diagnostics(safe_result)
    stop_signals = diagnostics["stop_evidence_signals"]
    stop_signal_count = sum(_int(stop_signals.get(key)) for key in STOP_SIGNAL_KEYS)

    return {
        "profile_name": _text(profile_name),
        "provider_status": _text(result.get("status")),
        "table_count": diagnostics["total_table_count"],
        "table_cell_count": diagnostics["total_table_cell_count"],
        "word_count": diagnostics["total_word_count"],
        "line_count": diagnostics["total_line_count"],
        "stop_signal_count": stop_signal_count,
        "warning_codes": _list(result.get("warning_codes")),
    }


def compare_pdfplumber_table_profiles(pdf_path, profiles=None, document_alias=""):
    from app.document_ai.pdfplumber_layout_provider import (
        PDFPLUMBER_TABLE_SETTING_PROFILES,
        extract_pdfplumber_layout,
        normalize_pdfplumber_table_profile,
    )

    requested = profiles or PDFPLUMBER_TABLE_SETTING_PROFILES
    normalized_profiles = []
    for profile in requested:
        normalized = normalize_pdfplumber_table_profile(profile)
        if normalized not in normalized_profiles:
            normalized_profiles.append(normalized)

    summaries = []
    warnings = []
    for profile in normalized_profiles:
        result = extract_pdfplumber_layout(
            pdf_path,
            document_id=_text(document_alias),
            table_settings_profile=profile,
        )
        summaries.append(
            _profile_summary_from_result(profile, result, document_alias=document_alias)
        )
        warnings.extend(_list(result.get("warning_codes")))

    best_by_tables = max(
        summaries,
        key=lambda item: (item["table_count"], item["table_cell_count"], item["word_count"]),
        default={},
    )
    best_by_stop_signals = max(
        summaries,
        key=lambda item: (item["stop_signal_count"], item["table_count"], item["word_count"]),
        default={},
    )

    return {
        "document_alias": _text(document_alias),
        "profiles": summaries,
        "best_profile_by_table_count": _text(best_by_tables.get("profile_name")),
        "best_profile_by_stop_signal_count": _text(best_by_stop_signals.get("profile_name")),
        "warning_codes": sorted(set(warnings)),
        "raw_text_included": False,
        "private_values_redacted": True,
    }
