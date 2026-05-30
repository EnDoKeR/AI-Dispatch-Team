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
