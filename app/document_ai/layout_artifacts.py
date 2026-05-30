"""Dependency-free layout artifact contracts for RateCon extraction."""

LAYOUT_ARTIFACT_VERSION = "layout_artifact_v1"

UNIT_POINTS = "points"
UNIT_NORMALIZED = "normalized"
UNIT_PIXELS = "pixels"
BOUNDING_BOX_UNITS = (UNIT_POINTS, UNIT_NORMALIZED, UNIT_PIXELS)

BLOCK_TYPE_TEXT = "text"
BLOCK_TYPE_TABLE = "table"
BLOCK_TYPE_HEADER = "header"
BLOCK_TYPE_FOOTER = "footer"
BLOCK_TYPE_SIGNATURE = "signature"
BLOCK_TYPE_UNKNOWN = "unknown"
BLOCK_TYPES = (
    BLOCK_TYPE_TEXT,
    BLOCK_TYPE_TABLE,
    BLOCK_TYPE_HEADER,
    BLOCK_TYPE_FOOTER,
    BLOCK_TYPE_SIGNATURE,
    BLOCK_TYPE_UNKNOWN,
)

EVIDENCE_LABEL_VALUE = "label_value"
EVIDENCE_TABLE_CELL = "table_cell"
EVIDENCE_SAME_ROW = "same_row"
EVIDENCE_BELOW_LABEL = "below_label"
EVIDENCE_SECTION_CONTEXT = "section_context"
EVIDENCE_HEADER_CONTEXT = "header_context"
EVIDENCE_UNKNOWN = "unknown"
EVIDENCE_TYPES = (
    EVIDENCE_LABEL_VALUE,
    EVIDENCE_TABLE_CELL,
    EVIDENCE_SAME_ROW,
    EVIDENCE_BELOW_LABEL,
    EVIDENCE_SECTION_CONTEXT,
    EVIDENCE_HEADER_CONTEXT,
    EVIDENCE_UNKNOWN,
)


def normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [str(item).strip() for item in values if str(item).strip()]


def normalize_unit(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in BOUNDING_BOX_UNITS else UNIT_POINTS


def normalize_block_type(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in BLOCK_TYPES else BLOCK_TYPE_UNKNOWN


def normalize_evidence_type(value):
    text = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return text if text in EVIDENCE_TYPES else EVIDENCE_UNKNOWN


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def build_bounding_box(
    x0=0,
    y0=0,
    x1=0,
    y1=0,
    unit=UNIT_POINTS,
    page_number=0,
):
    return {
        "x0": _number(x0),
        "y0": _number(y0),
        "x1": _number(x1),
        "y1": _number(y1),
        "unit": normalize_unit(unit),
        "page_number": int(page_number or 0),
    }


def normalize_bbox(value, page_number=0):
    if isinstance(value, dict):
        return build_bounding_box(
            x0=value.get("x0", 0),
            y0=value.get("y0", 0),
            x1=value.get("x1", 0),
            y1=value.get("y1", 0),
            unit=value.get("unit", UNIT_POINTS),
            page_number=value.get("page_number", page_number),
        )

    return build_bounding_box(page_number=page_number)


def build_layout_word(
    text="",
    bbox=None,
    confidence=None,
    source="synthetic_fixture",
    line_id="",
    block_id="",
):
    page_number = (bbox or {}).get("page_number", 0) if isinstance(bbox, dict) else 0

    return {
        "text": str(text or "").strip(),
        "bbox": normalize_bbox(bbox, page_number=page_number),
        "confidence": confidence,
        "source": str(source or "").strip(),
        "line_id": str(line_id or "").strip(),
        "block_id": str(block_id or "").strip(),
    }


def build_layout_line(
    line_id,
    text_redacted="",
    bbox=None,
    word_ids=None,
    page_number=0,
    reading_order_index=0,
    section_role="",
    warning_codes=None,
):
    return {
        "line_id": str(line_id or "").strip(),
        "text_redacted": str(text_redacted or "").strip(),
        "bbox": normalize_bbox(bbox, page_number=page_number),
        "word_ids": normalize_list(word_ids),
        "page_number": int(page_number or 0),
        "reading_order_index": int(reading_order_index or 0),
        "section_role": str(section_role or "").strip(),
        "warning_codes": normalize_list(warning_codes),
    }


def build_layout_block(
    block_id,
    text_redacted="",
    bbox=None,
    line_ids=None,
    page_number=0,
    block_type=BLOCK_TYPE_TEXT,
    section_role="",
    warning_codes=None,
):
    return {
        "block_id": str(block_id or "").strip(),
        "text_redacted": str(text_redacted or "").strip(),
        "bbox": normalize_bbox(bbox, page_number=page_number),
        "line_ids": normalize_list(line_ids),
        "page_number": int(page_number or 0),
        "block_type": normalize_block_type(block_type),
        "section_role": str(section_role or "").strip(),
        "warning_codes": normalize_list(warning_codes),
    }


def build_layout_table_cell(
    row_index=0,
    col_index=0,
    text_redacted="",
    bbox=None,
    row_span=1,
    col_span=1,
    confidence=None,
):
    page_number = (bbox or {}).get("page_number", 0) if isinstance(bbox, dict) else 0

    return {
        "row_index": int(row_index or 0),
        "col_index": int(col_index or 0),
        "text_redacted": str(text_redacted or "").strip(),
        "bbox": normalize_bbox(bbox, page_number=page_number),
        "row_span": int(row_span or 1),
        "col_span": int(col_span or 1),
        "confidence": confidence,
    }


def build_layout_table(
    table_id,
    page_number=0,
    bbox=None,
    cells=None,
    header_rows=None,
    source="synthetic_fixture",
    confidence=None,
    warning_codes=None,
):
    normalized_cells = []
    for cell in cells or []:
        if isinstance(cell, dict):
            normalized_cells.append(
                build_layout_table_cell(
                    row_index=cell.get("row_index", 0),
                    col_index=cell.get("col_index", 0),
                    text_redacted=cell.get("text_redacted", ""),
                    bbox=cell.get("bbox"),
                    row_span=cell.get("row_span", 1),
                    col_span=cell.get("col_span", 1),
                    confidence=cell.get("confidence"),
                )
            )

    return {
        "table_id": str(table_id or "").strip(),
        "page_number": int(page_number or 0),
        "bbox": normalize_bbox(bbox, page_number=page_number),
        "cells": normalized_cells,
        "header_rows": [int(item) for item in (header_rows or [])],
        "source": str(source or "").strip(),
        "confidence": confidence,
        "warning_codes": normalize_list(warning_codes),
    }


def build_reading_order_variant(
    name,
    line_ids=None,
    confidence=None,
    reasons=None,
):
    return {
        "name": str(name or "").strip(),
        "line_ids": normalize_list(line_ids),
        "confidence": confidence,
        "reasons": normalize_list(reasons),
    }


def build_layout_page_artifact(
    page_number=0,
    width=0,
    height=0,
    words=None,
    lines=None,
    blocks=None,
    tables=None,
    page_roles=None,
    section_roles=None,
    warning_codes=None,
):
    return {
        "page_number": int(page_number or 0),
        "width": _number(width),
        "height": _number(height),
        "words": [word for word in (words or []) if isinstance(word, dict)],
        "lines": [line for line in (lines or []) if isinstance(line, dict)],
        "blocks": [block for block in (blocks or []) if isinstance(block, dict)],
        "tables": [table for table in (tables or []) if isinstance(table, dict)],
        "page_roles": normalize_list(page_roles),
        "section_roles": normalize_list(section_roles),
        "warning_codes": normalize_list(warning_codes),
    }


def build_layout_extraction_artifact(
    artifact_id="",
    document_id="",
    source_method="synthetic_fixture",
    provider="synthetic",
    provider_version="",
    layout_version=LAYOUT_ARTIFACT_VERSION,
    pages=None,
    page_count=None,
    warning_codes=None,
    raw_text_included=False,
    private_values_redacted=True,
):
    normalized_pages = [page for page in (pages or []) if isinstance(page, dict)]

    return {
        "artifact_id": str(artifact_id or "").strip(),
        "document_id": str(document_id or "").strip(),
        "source_method": str(source_method or "").strip(),
        "provider": str(provider or "").strip(),
        "provider_version": str(provider_version or "").strip(),
        "layout_version": str(layout_version or LAYOUT_ARTIFACT_VERSION).strip(),
        "pages": normalized_pages,
        "page_count": int(page_count if page_count is not None else len(normalized_pages)),
        "warning_codes": normalize_list(warning_codes),
        "raw_text_included": bool(raw_text_included),
        "private_values_redacted": bool(private_values_redacted),
    }


def build_layout_evidence_ref(
    page_number=0,
    bbox=None,
    line_id="",
    block_id="",
    table_id="",
    cell_ref="",
    label="",
    source_method="synthetic_fixture",
    evidence_type=EVIDENCE_UNKNOWN,
):
    return {
        "page_number": int(page_number or 0),
        "bbox": normalize_bbox(bbox, page_number=page_number) if bbox else None,
        "line_id": str(line_id or "").strip(),
        "block_id": str(block_id or "").strip(),
        "table_id": str(table_id or "").strip(),
        "cell_ref": str(cell_ref or "").strip(),
        "label": str(label or "").strip(),
        "source_method": str(source_method or "").strip(),
        "evidence_type": normalize_evidence_type(evidence_type),
    }
