"""pdfplumber-backed layout provider for local digital-text PDFs."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pdfplumber

from app.document_ai.layout_artifacts import (
    BLOCK_TYPE_TABLE,
    BLOCK_TYPE_TEXT,
    BLOCK_TYPE_UNKNOWN,
    build_bounding_box,
    build_layout_block,
    build_layout_extraction_artifact,
    build_layout_line,
    build_layout_page_artifact,
    build_layout_table,
    build_layout_table_cell,
    build_layout_word,
)
from app.document_ai.layout_provider import (
    PROVIDER_PDFPLUMBER,
    STATUS_EMPTY_TEXT,
    STATUS_EXTRACTION_FAILED,
    STATUS_SUCCESS,
    STATUS_UNSUPPORTED_PDF,
    build_layout_provider_result,
)


PDFPLUMBER_SOURCE_METHOD = "pdfplumber_layout_v1"
LINE_Y_TOLERANCE = 3.0
TABLE_PROFILE_DEFAULT = "default"
TABLE_PROFILE_LINES = "lines"
TABLE_PROFILE_TEXT = "text"
TABLE_PROFILE_LINES_STRICT = "lines_strict"
TABLE_PROFILE_TEXT_STRICT = "text_strict"
PDFPLUMBER_TABLE_SETTING_PROFILES = (
    TABLE_PROFILE_DEFAULT,
    TABLE_PROFILE_LINES,
    TABLE_PROFILE_TEXT,
    TABLE_PROFILE_LINES_STRICT,
    TABLE_PROFILE_TEXT_STRICT,
)


def normalize_pdfplumber_table_profile(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in PDFPLUMBER_TABLE_SETTING_PROFILES else TABLE_PROFILE_DEFAULT


def get_pdfplumber_table_settings(profile_name=TABLE_PROFILE_DEFAULT):
    profile = normalize_pdfplumber_table_profile(profile_name)
    if profile == TABLE_PROFILE_DEFAULT:
        return None
    if profile == TABLE_PROFILE_LINES:
        return {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }
    if profile == TABLE_PROFILE_TEXT:
        return {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        }
    if profile == TABLE_PROFILE_LINES_STRICT:
        return {
            "vertical_strategy": "lines_strict",
            "horizontal_strategy": "lines_strict",
            "snap_tolerance": 2,
            "join_tolerance": 2,
            "intersection_tolerance": 2,
        }
    if profile == TABLE_PROFILE_TEXT_STRICT:
        return {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "text_x_tolerance": 1,
            "text_y_tolerance": 1,
            "snap_tolerance": 1,
            "join_tolerance": 1,
            "intersection_tolerance": 1,
        }
    return None


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _bbox_from_pdfplumber(value, page_number):
    if isinstance(value, dict):
        return build_bounding_box(
            x0=value.get("x0", 0),
            y0=value.get("top", value.get("y0", 0)),
            x1=value.get("x1", 0),
            y1=value.get("bottom", value.get("y1", 0)),
            page_number=page_number,
        )

    if isinstance(value, (list, tuple)) and len(value) >= 4:
        return build_bounding_box(
            x0=value[0],
            y0=value[1],
            x1=value[2],
            y1=value[3],
            page_number=page_number,
        )

    return build_bounding_box(page_number=page_number)


def _merge_bboxes(boxes, page_number):
    filtered = [box for box in boxes if isinstance(box, dict)]
    if not filtered:
        return build_bounding_box(page_number=page_number)

    return build_bounding_box(
        x0=min(_number(box.get("x0")) for box in filtered),
        y0=min(_number(box.get("y0")) for box in filtered),
        x1=max(_number(box.get("x1")) for box in filtered),
        y1=max(_number(box.get("y1")) for box in filtered),
        page_number=page_number,
    )


def _extract_words(page, page_number, warnings):
    try:
        words = page.extract_words(
            x_tolerance=1,
            y_tolerance=LINE_Y_TOLERANCE,
            keep_blank_chars=False,
            use_text_flow=False,
        )
    except Exception as exc:  # pragma: no cover - provider-specific failure
        warnings.append(f"pdfplumber_words_failed:{exc.__class__.__name__}")
        return []

    normalized = []
    for index, word in enumerate(words or [], start=1):
        text = str(word.get("text") or "").strip()
        if not text:
            continue
        bbox = _bbox_from_pdfplumber(word, page_number)
        item = build_layout_word(
            text=text,
            bbox=bbox,
            confidence=None,
            source=PROVIDER_PDFPLUMBER,
        )
        item["word_id"] = f"P{page_number}_W{index}"
        item["_sort_top"] = _number(word.get("top", bbox.get("y0", 0)))
        item["_sort_x0"] = _number(word.get("x0", bbox.get("x0", 0)))
        normalized.append(item)

    return normalized


def _group_words_into_lines(words, page_number):
    sorted_words = sorted(
        words,
        key=lambda word: (_number(word.get("_sort_top")), _number(word.get("_sort_x0"))),
    )
    groups = []
    current_group = []
    current_top = None

    for word in sorted_words:
        top = _number(word.get("_sort_top"))
        if current_top is None or abs(top - current_top) <= LINE_Y_TOLERANCE:
            current_group.append(word)
            current_top = top if current_top is None else min(current_top, top)
            continue

        groups.append(current_group)
        current_group = [word]
        current_top = top

    if current_group:
        groups.append(current_group)

    lines = []
    cleaned_words = []
    for index, group in enumerate(groups, start=1):
        ordered_group = sorted(group, key=lambda word: _number(word.get("_sort_x0")))
        line_id = f"P{page_number}_L{index}"
        text = " ".join(str(word.get("text") or "").strip() for word in ordered_group).strip()
        bbox = _merge_bboxes([word.get("bbox", {}) for word in ordered_group], page_number)
        word_ids = []

        for word in ordered_group:
            word["line_id"] = line_id
            word.pop("_sort_top", None)
            word.pop("_sort_x0", None)
            word_ids.append(word.get("word_id", ""))
            cleaned_words.append(word)

        lines.append(
            build_layout_line(
                line_id=line_id,
                text_redacted=text,
                bbox=bbox,
                word_ids=word_ids,
                page_number=page_number,
                reading_order_index=index,
            )
        )

    return cleaned_words, lines


def _page_text_block(lines, page_number):
    if not lines:
        return []

    block_id = f"P{page_number}_B_TEXT"
    return [
        build_layout_block(
            block_id=block_id,
            text_redacted="",
            bbox=_merge_bboxes([line.get("bbox", {}) for line in lines], page_number),
            line_ids=[line.get("line_id", "") for line in lines],
            page_number=page_number,
            block_type=BLOCK_TYPE_TEXT,
        )
    ]


def _cell_bbox(table_bbox, row_index, col_index, row_count, col_count, page_number):
    x0 = _number(table_bbox.get("x0"))
    y0 = _number(table_bbox.get("y0"))
    x1 = _number(table_bbox.get("x1"))
    y1 = _number(table_bbox.get("y1"))
    row_count = max(int(row_count or 1), 1)
    col_count = max(int(col_count or 1), 1)
    cell_width = (x1 - x0) / col_count if col_count else 0
    cell_height = (y1 - y0) / row_count if row_count else 0

    return build_bounding_box(
        x0=x0 + (cell_width * col_index),
        y0=y0 + (cell_height * row_index),
        x1=x0 + (cell_width * (col_index + 1)),
        y1=y0 + (cell_height * (row_index + 1)),
        page_number=page_number,
    )


def _extract_tables(page, page_number, warnings, table_settings_profile=TABLE_PROFILE_DEFAULT):
    table_settings = get_pdfplumber_table_settings(table_settings_profile)
    try:
        if table_settings is None:
            tables = page.find_tables() or []
        else:
            tables = page.find_tables(table_settings=table_settings) or []
    except Exception as exc:  # pragma: no cover - provider-specific failure
        warnings.append(f"pdfplumber_tables_failed:{exc.__class__.__name__}")
        return []

    normalized_tables = []
    for table_index, table in enumerate(tables, start=1):
        table_id = f"P{page_number}_T{table_index}"
        table_bbox = _bbox_from_pdfplumber(getattr(table, "bbox", None), page_number)
        try:
            rows = table.extract() or []
        except Exception as exc:  # pragma: no cover - provider-specific failure
            warnings.append(f"pdfplumber_table_extract_failed:{exc.__class__.__name__}")
            continue

        row_count = len(rows)
        col_count = max((len(row or []) for row in rows), default=0)
        cells = []
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row or []):
                text = str(value or "").strip()
                cells.append(
                    build_layout_table_cell(
                        row_index=row_index,
                        col_index=col_index,
                        text_redacted=text,
                        bbox=_cell_bbox(table_bbox, row_index, col_index, row_count, col_count, page_number),
                        confidence="MEDIUM",
                    )
                )

        normalized_tables.append(
            build_layout_table(
                table_id=table_id,
                page_number=page_number,
                bbox=table_bbox,
                cells=cells,
                header_rows=[0] if cells else [],
                source=PROVIDER_PDFPLUMBER,
                confidence="MEDIUM",
            )
        )

    return normalized_tables


def _rect_blocks(page, page_number, warnings):
    blocks = []
    try:
        rects = getattr(page, "rects", []) or []
    except Exception as exc:  # pragma: no cover - provider-specific failure
        warnings.append(f"pdfplumber_rects_failed:{exc.__class__.__name__}")
        return blocks

    for index, rect in enumerate(rects, start=1):
        blocks.append(
            build_layout_block(
                block_id=f"P{page_number}_B_RECT{index}",
                text_redacted="",
                bbox=_bbox_from_pdfplumber(rect, page_number),
                line_ids=[],
                page_number=page_number,
                block_type=BLOCK_TYPE_UNKNOWN,
            )
        )
    return blocks


def _table_blocks(tables, page_number):
    blocks = []
    for table in tables or []:
        if not isinstance(table, dict):
            continue
        blocks.append(
            build_layout_block(
                block_id=f"{table.get('table_id', '')}_BLOCK",
                text_redacted="",
                bbox=table.get("bbox"),
                line_ids=[],
                page_number=page_number,
                block_type=BLOCK_TYPE_TABLE,
            )
        )
    return blocks


def _page_has_extractable_text(page_artifact):
    if page_artifact.get("words"):
        return True
    for line in page_artifact.get("lines", []):
        if str(line.get("text_redacted") or "").strip():
            return True
    for table in page_artifact.get("tables", []):
        for cell in table.get("cells", []):
            if str(cell.get("text_redacted") or "").strip():
                return True
    return False


def extract_pdfplumber_layout(
    path,
    document_id=None,
    table_settings_profile=TABLE_PROFILE_DEFAULT,
):
    file_path = Path(path or "")
    requested_profile = str(table_settings_profile or "").strip()
    normalized_table_profile = normalize_pdfplumber_table_profile(requested_profile)

    if not file_path.exists():
        return build_layout_provider_result(
            provider_name=PROVIDER_PDFPLUMBER,
            status=STATUS_EXTRACTION_FAILED,
            warning_codes=["layout_input_missing"],
            error_code="layout_input_missing",
            safe_message="Layout input file does not exist.",
            provider_version=pdfplumber.__version__,
            table_settings_profile=normalized_table_profile,
        )

    if file_path.suffix.lower() != ".pdf":
        return build_layout_provider_result(
            provider_name=PROVIDER_PDFPLUMBER,
            status=STATUS_UNSUPPORTED_PDF,
            warning_codes=["unsupported_file_type"],
            error_code="unsupported_file_type",
            safe_message="Layout provider only accepts PDF inputs.",
            provider_version=pdfplumber.__version__,
            table_settings_profile=normalized_table_profile,
        )

    warnings = []
    if requested_profile and requested_profile != normalized_table_profile:
        warnings.append("unsupported_pdfplumber_table_profile_defaulted")
    pages = []

    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()), pdfplumber.open(str(file_path)) as pdf:
            for page_index, page in enumerate(pdf.pages or [], start=1):
                page_warnings = []
                raw_words = _extract_words(page, page_index, page_warnings)
                words, lines = _group_words_into_lines(raw_words, page_index)
                tables = _extract_tables(
                    page,
                    page_index,
                    page_warnings,
                    table_settings_profile=normalized_table_profile,
                )
                blocks = (
                    _page_text_block(lines, page_index)
                    + _table_blocks(tables, page_index)
                    + _rect_blocks(page, page_index, page_warnings)
                )

                page_artifact = build_layout_page_artifact(
                    page_number=page_index,
                    width=getattr(page, "width", 0) or 0,
                    height=getattr(page, "height", 0) or 0,
                    words=words,
                    lines=lines,
                    blocks=blocks,
                    tables=tables,
                    warning_codes=page_warnings,
                )
                warnings.extend(f"page_{page_index}:{warning}" for warning in page_warnings)
                pages.append(page_artifact)
    except Exception as exc:
        return build_layout_provider_result(
            provider_name=PROVIDER_PDFPLUMBER,
            status=STATUS_EXTRACTION_FAILED,
            warning_codes=[f"pdfplumber_open_failed:{exc.__class__.__name__}"],
            error_code="pdfplumber_open_failed",
            safe_message="Layout provider could not read the PDF.",
            provider_version=pdfplumber.__version__,
            table_settings_profile=normalized_table_profile,
        )

    page_count = len(pages)
    if page_count == 0:
        warnings.append("no_pages")

    has_text = any(_page_has_extractable_text(page) for page in pages)
    status = STATUS_SUCCESS if has_text else STATUS_EMPTY_TEXT
    if not has_text:
        warnings.append("no_extractable_layout_text")

    artifact = build_layout_extraction_artifact(
        artifact_id=f"LAYOUT-{document_id}" if document_id else "",
        document_id=document_id or "",
        source_method=PDFPLUMBER_SOURCE_METHOD,
        provider=PROVIDER_PDFPLUMBER,
        provider_version=pdfplumber.__version__,
        pages=pages,
        page_count=page_count,
        warning_codes=warnings,
        raw_text_included=False,
        private_values_redacted=True,
    )

    return build_layout_provider_result(
        provider_name=PROVIDER_PDFPLUMBER,
        status=status,
        artifact=artifact,
        page_count=page_count,
        warning_codes=warnings,
        safe_message="Layout extraction completed." if has_text else "No extractable layout text found.",
        provider_version=pdfplumber.__version__,
        table_settings_profile=normalized_table_profile,
    )
