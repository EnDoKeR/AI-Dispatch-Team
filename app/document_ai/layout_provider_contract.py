"""Dependency-light layout provider contract for shadow document diagnostics."""

PROVIDER_NATIVE_TEXT = "native_text"
PROVIDER_AUTO = "auto"
PROVIDER_PDFPLUMBER = "pdfplumber"
PROVIDER_UNAVAILABLE = "unavailable"

STATUS_SUCCESS = "success"
STATUS_UNAVAILABLE = "unavailable"
STATUS_FAILED = "failed"
STATUS_PARTIAL = "partial"
STATUS_NATIVE_TEXT = "native_text"

SHADOW_LAYOUT_PROVIDER_CHOICES = (
    PROVIDER_NATIVE_TEXT,
    PROVIDER_AUTO,
    PROVIDER_PDFPLUMBER,
)


def _text(value):
    return str(value or "").strip()


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_bool(value):
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


def normalize_shadow_layout_provider(value):
    provider = _text(value).lower().replace("-", "_").replace(" ", "_")
    return provider if provider in SHADOW_LAYOUT_PROVIDER_CHOICES else PROVIDER_NATIVE_TEXT


def build_layout_provider_summary(
    provider_requested=PROVIDER_NATIVE_TEXT,
    provider_used=PROVIDER_NATIVE_TEXT,
    available=True,
    status=STATUS_NATIVE_TEXT,
    pages=None,
    warnings=None,
    errors=None,
    table_settings_profile="",
):
    normalized_pages = [page for page in pages or [] if isinstance(page, dict)]
    pages_with_words = 0
    pages_with_lines = 0
    pages_with_tables = 0
    word_count = 0
    line_count = 0
    table_count = 0
    table_cell_count = 0

    for page in normalized_pages:
        words = [item for item in page.get("words", []) or [] if isinstance(item, dict)]
        lines = [item for item in page.get("lines", []) or [] if isinstance(item, dict)]
        tables = [item for item in page.get("tables", []) or [] if isinstance(item, dict)]
        word_count += len(words)
        line_count += len(lines)
        table_count += len(tables)
        if words:
            pages_with_words += 1
        if lines:
            pages_with_lines += 1
        if tables:
            pages_with_tables += 1
        for table in tables:
            for row in table.get("rows", []) or []:
                if isinstance(row, dict):
                    table_cell_count += len(
                        [cell for cell in row.get("cells", []) or [] if isinstance(cell, dict)]
                    )
            if not table.get("rows") and table.get("cells"):
                table_cell_count += len(
                    [cell for cell in table.get("cells", []) or [] if isinstance(cell, dict)]
                )

    return {
        "provider_requested": normalize_shadow_layout_provider(provider_requested),
        "provider_used": _text(provider_used) or PROVIDER_UNAVAILABLE,
        "available": _safe_bool(available),
        "status": _text(status) or STATUS_UNAVAILABLE,
        "pages_with_words": pages_with_words,
        "pages_with_lines": pages_with_lines,
        "pages_with_tables": pages_with_tables,
        "word_count": word_count,
        "line_count": line_count,
        "table_count": table_count,
        "table_cell_count": table_cell_count,
        "warnings": _list(warnings),
        "errors": _list(errors),
        "table_settings_profile": _text(table_settings_profile),
    }


def empty_layout_provider_summary(provider_requested=PROVIDER_NATIVE_TEXT):
    return build_layout_provider_summary(
        provider_requested=provider_requested,
        provider_used=PROVIDER_NATIVE_TEXT,
        available=True,
        status=STATUS_NATIVE_TEXT,
        pages=[],
    )
