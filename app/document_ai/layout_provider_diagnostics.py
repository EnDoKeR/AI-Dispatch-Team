"""Safe diagnostics contracts for layout provider output quality."""


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
