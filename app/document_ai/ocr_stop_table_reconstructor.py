"""OCR TSV stop table reconstruction for shadow RateCon diagnostics.

This module uses optional Tesseract word/line boxes to reconstruct
pickup/delivery row bands and simple role/location/date-time columns. It is
profile-gated and does not change default or production extraction.
"""

from __future__ import annotations

from collections import Counter
import re

from app.document_ai.field_candidate_provenance import SOURCE_OCR
from app.document_ai.ocr_stop_block_assembler import (
    ALIGNMENT_MEDIUM,
    ALIGNMENT_STRONG,
    ALIGNMENT_UNSAFE,
    ALIGNMENT_WEAK,
    FIELD_DELIVERY_STOPS,
    FIELD_PICKUP_STOPS,
    GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
    ROLE_DELIVERY,
    ROLE_PICKUP,
    ROLE_UNKNOWN,
    SECTION_FOOTER,
    SECTION_INSTRUCTIONS,
    SECTION_PAYMENT,
    SECTION_STOP,
    _block_type_from_line,
    _has_date,
    _has_time,
    _line_has_location,
    _role_from_line,
    _section_context,
    _stop_index_from_line,
    candidates_from_stop_evidence_blocks,
)


GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR = "ocr_stop_table_reconstructor"
PAIRING_METHOD_OCR_GEOMETRY_COLUMN_ROW = "ocr_geometry_column_row"


_REFERENCE_CONTACT_RE = re.compile(
    r"\b(?:ref|reference|bol|po|phone|tel|contact|fax|email|pu\s*#|pickup\s*#|"
    r"delivery\s*#)\b",
    re.IGNORECASE,
)


def _text(value) -> str:
    return str(value or "").strip()


def _lower(value) -> str:
    return _text(value).lower()


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bbox(value):
    if isinstance(value, dict):
        left = _safe_float(value.get("left", value.get("x0")))
        top = _safe_float(value.get("top", value.get("y0")))
        right = _safe_float(value.get("right", value.get("x1", left + _safe_float(value.get("width")))))
        bottom = _safe_float(value.get("bottom", value.get("y1", top + _safe_float(value.get("height")))))
        return {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": max(0.0, right - left),
            "height": max(0.0, bottom - top),
        }
    if isinstance(value, (list, tuple)) and len(value) >= 4:
        left, top, right, bottom = [_safe_float(item) for item in value[:4]]
        return {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": max(0.0, right - left),
            "height": max(0.0, bottom - top),
        }
    return None


def _union_bbox(items):
    boxes = [_bbox(item.get("bbox") or item) for item in items or []]
    boxes = [box for box in boxes if box]
    if not boxes:
        return None
    return {
        "left": min(box["left"] for box in boxes),
        "top": min(box["top"] for box in boxes),
        "right": max(box["right"] for box in boxes),
        "bottom": max(box["bottom"] for box in boxes),
    }


def _center_y(item):
    box = _bbox(item.get("bbox") or item) or {}
    return (_safe_float(box.get("top")) + _safe_float(box.get("bottom"))) / 2.0


def _center_x(item):
    box = _bbox(item.get("bbox") or item) or {}
    return (_safe_float(box.get("left")) + _safe_float(box.get("right"))) / 2.0


def _word_text(words):
    return " ".join(_text(word.get("text")) for word in words or [] if _text(word.get("text")))


def _page_geometry(artifact):
    pages = []
    for ocr_page in ((artifact or {}).get("ocr_provider_result") or {}).get("pages", []) or []:
        if not isinstance(ocr_page, dict):
            continue
        page = _safe_int(ocr_page.get("page_number"), 1) or 1
        words = []
        for ordinal, word in enumerate(ocr_page.get("word_boxes", []) or []):
            if not isinstance(word, dict) or not _text(word.get("text")):
                continue
            box = _bbox(word.get("bbox") or word)
            if not box:
                continue
            words.append(
                {
                    "page": page,
                    "text": _text(word.get("text")),
                    "bbox": box,
                    "confidence": word.get("confidence"),
                    "block_num": _safe_int(word.get("block_num")),
                    "par_num": _safe_int(word.get("par_num")),
                    "line_num": _safe_int(word.get("line_num")),
                    "word_num": _safe_int(word.get("word_num"), ordinal),
                    "line_id": _text(word.get("line_id")),
                }
            )
        line_lookup = {}
        for word in words:
            key = (
                word.get("line_id")
                or f"{word['block_num']}:{word['par_num']}:{word['line_num']}"
            )
            line_lookup.setdefault(key, []).append(word)
        lines = []
        for ordinal, line in enumerate(ocr_page.get("line_boxes", []) or []):
            if not isinstance(line, dict) or not _text(line.get("text")):
                continue
            box = _bbox(line.get("bbox") or line)
            if not box:
                continue
            key = (
                _text(line.get("line_id"))
                or f"{_safe_int(line.get('block_num'))}:"
                f"{_safe_int(line.get('par_num'))}:{_safe_int(line.get('line_num'))}"
            )
            line_words = line_lookup.get(key, [])
            if not line_words:
                line_words = [
                    word
                    for word in words
                    if box["top"] - 3 <= _center_y(word) <= box["bottom"] + 3
                ]
            lines.append(
                {
                    "page": page,
                    "text": _text(line.get("text")),
                    "bbox": box,
                    "words": sorted(line_words, key=lambda item: (_center_x(item), item.get("word_num", 0))),
                    "line_index": _safe_int(line.get("line_index"), ordinal),
                    "block_num": _safe_int(line.get("block_num")),
                    "par_num": _safe_int(line.get("par_num")),
                    "line_num": _safe_int(line.get("line_num")),
                }
            )
        if not lines and words:
            for key, line_words in line_lookup.items():
                line_words = sorted(line_words, key=lambda item: (_center_x(item), item.get("word_num", 0)))
                lines.append(
                    {
                        "page": page,
                        "text": _word_text(line_words),
                        "bbox": _union_bbox(line_words),
                        "words": line_words,
                        "line_index": len(lines),
                        "block_num": line_words[0].get("block_num", 0),
                        "par_num": line_words[0].get("par_num", 0),
                        "line_num": line_words[0].get("line_num", 0),
                    }
                )
        lines.sort(key=lambda item: (_center_y(item), _safe_float((item.get("bbox") or {}).get("left"))))
        pages.append({"page": page, "words": words, "lines": lines})
    return pages


def _is_reference_or_contact(text):
    return bool(_REFERENCE_CONTACT_RE.search(_text(text)))


def _boundary_context(line):
    context = _section_context(line.get("text"))
    if context in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}:
        return context
    return ""


def _row_word_band(words, start_y, end_y):
    return [
        word
        for word in words or []
        if start_y <= _center_y(word) < end_y
    ]


def _row_lines(lines, start_y, end_y):
    return [
        line
        for line in lines or []
        if start_y <= _center_y(line) < end_y
    ]


def _cell_text_from_words(words):
    rows = {}
    for word in words or []:
        rows.setdefault(
            (word.get("block_num"), word.get("par_num"), word.get("line_num")),
            [],
        ).append(word)
    lines = []
    for line_words in rows.values():
        line_words = sorted(line_words, key=lambda item: (_center_x(item), item.get("word_num", 0)))
        text = _word_text(line_words)
        if text:
            lines.append((_center_y(line_words[0]), text))
    return [text for _y, text in sorted(lines)]


def _split_row_columns(row_words, role_line, page_width):
    role_box = _bbox(role_line.get("bbox")) or {}
    role_right = _safe_float(role_box.get("right"))
    date_words = [
        word for word in row_words if _center_x(word) >= max(role_right + 120, page_width * 0.55)
    ]
    role_words = [word for word in row_words if _center_x(word) <= role_right + 24]
    location_words = [
        word
        for word in row_words
        if role_right + 24 < _center_x(word) < max(role_right + 120, page_width * 0.55)
    ]
    if not any(_has_date(word.get("text")) or _has_time(word.get("text")) for word in date_words):
        for word in row_words:
            if _has_date(word.get("text")) or _has_time(word.get("text")):
                date_words.append(word)
    return {
        "role": _cell_text_from_words(role_words),
        "location": _cell_text_from_words(location_words),
        "date_time": _cell_text_from_words(date_words),
        "contact_reference": _cell_text_from_words(
            [word for word in row_words if _is_reference_or_contact(word.get("text"))]
        ),
        "role_bbox": _union_bbox(role_words),
        "location_bbox": _union_bbox(location_words),
        "date_time_bbox": _union_bbox(date_words),
        "contact_reference_bbox": _union_bbox(
            [word for word in row_words if _is_reference_or_contact(word.get("text"))]
        ),
    }


def _location_lines(column_lines):
    lines = []
    for line in column_lines or []:
        if _role_from_line(line) in {ROLE_PICKUP, ROLE_DELIVERY}:
            continue
        if _has_date(line) or _has_time(line):
            continue
        if _is_reference_or_contact(line):
            continue
        if _section_context(line) in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}:
            continue
        if _line_has_location(line) or _text(line):
            lines.append(line)
    return lines[:5]


def _date_time_lines(column_lines):
    return [
        line
        for line in column_lines or []
        if (_has_date(line) or _has_time(line))
        and _section_context(line) not in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}
    ][:3]


def reconstruct_ocr_stop_tables(artifact):
    """Return reconstructed stop tables and safe diagnostics."""

    pages = _page_geometry(artifact)
    tables = []
    page_summaries = []
    for page in pages:
        page_number = page["page"]
        lines = page["lines"]
        words = page["words"]
        if not lines or not words:
            page_summaries.append(
                {
                    "page": page_number,
                    "has_tsv": False,
                    "word_count": len(words),
                    "line_count": len(lines),
                    "detected_stop_tables": 0,
                }
            )
            continue
        page_width = max((_safe_float((_bbox(word.get("bbox")) or {}).get("right")) for word in words), default=1.0)
        role_indices = [
            index
            for index, line in enumerate(lines)
            if _role_from_line(line.get("text")) in {ROLE_PICKUP, ROLE_DELIVERY}
        ]
        page_rows = []
        boundary_flags = Counter()
        for ordinal, role_index in enumerate(role_indices):
            role_line = lines[role_index]
            role = _role_from_line(role_line.get("text")) or ROLE_UNKNOWN
            role_y = _center_y(role_line)
            next_role_y = (
                _center_y(lines[role_indices[ordinal + 1]])
                if ordinal + 1 < len(role_indices)
                else None
            )
            boundary_y = next_role_y
            boundary_context = ""
            for next_line in lines[role_index + 1 :]:
                candidate_y = _center_y(next_line)
                if next_role_y is not None and candidate_y >= next_role_y:
                    break
                context = _boundary_context(next_line)
                if context:
                    boundary_y = candidate_y
                    boundary_context = context
                    boundary_flags[context] += 1
                    break
            if boundary_y is None:
                boundary_y = role_y + 150
            row_words = _row_word_band(words, role_y - 10, boundary_y)
            row_lines = _row_lines(lines, role_y - 10, boundary_y)
            columns = _split_row_columns(row_words, role_line, page_width)
            location = _location_lines(columns["location"])
            date_time = _date_time_lines(columns["date_time"])
            warnings = []
            if not columns["role"]:
                warnings.append("missing_role_column")
            if not location:
                warnings.append("missing_location_column")
            if not date_time:
                warnings.append("missing_date_time_column")
            if not any(columns[key] for key in ["role", "location", "date_time"]):
                warnings.append("ambiguous_column_bands")
            if len([line for line in date_time if _has_date(line)]) > 1:
                warnings.append("multiple_dates_in_row")
            if len(location) > 3:
                warnings.append("multiple_locations_in_row")
            if boundary_context == SECTION_PAYMENT:
                warnings.append("payment_overlap")
            elif boundary_context == SECTION_INSTRUCTIONS:
                warnings.append("instructions_overlap")
            elif boundary_context == SECTION_FOOTER:
                warnings.append("footer_overlap")
            if next_role_y is None and not boundary_context:
                warnings.append("row_boundary_unclear")
            confidence = round(
                0.35
                + (0.22 if columns["role"] else 0.0)
                + (0.2 if location else 0.0)
                + (0.2 if date_time else 0.0)
                + (0.03 if not warnings else 0.0),
                3,
            )
            row_bbox = _union_bbox(row_words or row_lines)
            page_rows.append(
                {
                    "role": role,
                    "stop_index": _stop_index_from_line(role_line.get("text"), default=1),
                    "row_bbox": row_bbox,
                    "role_anchor_text_shape": _block_type_from_line(role_line.get("text"), role),
                    "location_cell_present": bool(location),
                    "date_time_cell_present": bool(date_time),
                    "contact_reference_cell_present": bool(columns["contact_reference"]),
                    "row_boundary_confidence": confidence,
                    "column_alignment_confidence": confidence,
                    "warnings": sorted(set(warnings)),
                    "lines": list(columns["role"][:1]) + location + date_time,
                    "source": SOURCE_OCR,
                    "page": page_number,
                    "start_line_index": role_line.get("line_index", role_index),
                    "end_line_index": (
                        row_lines[-1].get("line_index", role_index)
                        if row_lines
                        else role_line.get("line_index", role_index)
                    ),
                    "line_count": len(row_lines),
                    "has_role_label": True,
                    "has_location_like_text": bool(location),
                    "has_date_like_text": any(_has_date(line) for line in date_time),
                    "has_time_like_text": any(_has_time(line) for line in date_time),
                    "has_address_like_text": any(_line_has_location(line) for line in location),
                    "section_context": SECTION_STOP,
                    "column_geometry": {
                        "role_column_bbox": columns["role_bbox"],
                        "location_column_bbox": columns["location_bbox"],
                        "date_time_column_bbox": columns["date_time_bbox"],
                        "contact_reference_column_bbox": columns["contact_reference_bbox"],
                        "row_boundary_confidence": confidence,
                        "column_alignment_confidence": confidence,
                        "warnings": sorted(set(warnings)),
                    },
                    "provenance": {
                        "block_detector": GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
                        "source": SOURCE_OCR,
                        "page": page_number,
                        "start_line_index": role_line.get("line_index", role_index),
                        "end_line_index": (
                            row_lines[-1].get("line_index", role_index)
                            if row_lines
                            else role_line.get("line_index", role_index)
                        ),
                        "block_type": _block_type_from_line(role_line.get("text"), role),
                        "geometry_available": True,
                    },
                }
            )
        if page_rows:
            tables.append(
                {
                    "page": page_number,
                    "bbox": _union_bbox(page_rows),
                    "rows": page_rows,
                    "payment_boundary_y": None,
                    "instructions_boundary_y": None,
                    "footer_boundary_y": None,
                }
            )
        page_summaries.append(
            {
                "page": page_number,
                "has_tsv": True,
                "word_count": len(words),
                "line_count": len(lines),
                "detected_stop_tables": 1 if page_rows else 0,
                "detected_role_column": bool(page_rows),
                "detected_location_column": any(row.get("location_cell_present") for row in page_rows),
                "detected_date_time_column": any(row.get("date_time_cell_present") for row in page_rows),
                "detected_contact_reference_column": any(
                    row.get("contact_reference_cell_present") for row in page_rows
                ),
                "horizontal_stop_bands": len(page_rows),
                "payment_band_detected": bool(boundary_flags.get(SECTION_PAYMENT)),
                "instructions_band_detected": bool(boundary_flags.get(SECTION_INSTRUCTIONS)),
                "footer_band_detected": bool(boundary_flags.get(SECTION_FOOTER)),
            }
        )
    diagnostics = {
        "page_summaries": page_summaries,
        "detected_stop_tables": len(tables),
        "detected_stop_rows": sum(len(table.get("rows", []) or []) for table in tables),
        "row_warning_counts": dict(
            Counter(
                warning
                for table in tables
                for row in table.get("rows", []) or []
                for warning in row.get("warnings", []) or []
            ).most_common()
        ),
        "raw_text_printed": False,
        "private_values_printed": False,
    }
    return tables, diagnostics


def _row_to_block(row):
    return {
        "role": row.get("role") or ROLE_UNKNOWN,
        "stop_index": row.get("stop_index") or 1,
        "source": SOURCE_OCR,
        "page": row.get("page") or 1,
        "start_line_index": row.get("start_line_index", 0),
        "end_line_index": row.get("end_line_index", 0),
        "line_count": row.get("line_count", 0),
        "has_role_label": True,
        "has_location_like_text": bool(row.get("location_cell_present")),
        "has_date_like_text": bool(row.get("has_date_like_text")),
        "has_time_like_text": bool(row.get("has_time_like_text")),
        "has_address_like_text": bool(row.get("has_address_like_text")),
        "section_context": SECTION_STOP,
        "lines": list(row.get("lines") or []),
        "provenance": row.get("provenance") or {},
        "column_geometry": row.get("column_geometry") or {},
        "raw_text_included": False,
    }


def _component_alignment(row, stop):
    geometry = row.get("column_geometry") or {}
    return {
        "facility": "location_column" if stop.get("facility") else "missing",
        "address": "location_column" if stop.get("address") else "missing",
        "city_state_zip": "location_column" if stop.get("city") or stop.get("state") else "missing",
        "date": "date_time_column" if stop.get("date") else "missing",
        "time": "date_time_column" if stop.get("time") else "missing",
        "appointment_window": "date_time_column" if stop.get("appointment_window") else "missing",
        "contact_reference": "separate_column" if geometry.get("contact_reference_column_bbox") else "missing",
    }


def _column_status(row, stop):
    warnings = set(row.get("warnings") or [])
    has_location = bool(
        _text(stop.get("facility"))
        or _text(stop.get("address"))
        or _text(stop.get("city"))
        or _text(stop.get("state"))
        or _text(stop.get("zip"))
    )
    has_datetime = bool(_text(stop.get("date")) or _text(stop.get("time")) or _text(stop.get("appointment_window")))
    unsafe = {
        "payment_overlap",
        "instructions_overlap",
        "footer_overlap",
        "date_time_outside_row",
        "location_outside_row",
    }
    if warnings.intersection(unsafe):
        return ALIGNMENT_UNSAFE, 0.16
    if row.get("role") not in {ROLE_PICKUP, ROLE_DELIVERY}:
        return ALIGNMENT_UNSAFE, 0.0
    if has_location and has_datetime and not warnings:
        return ALIGNMENT_STRONG, 0.92
    if has_location and has_datetime:
        return ALIGNMENT_MEDIUM, 0.7
    if has_location or has_datetime:
        return ALIGNMENT_MEDIUM, 0.6
    return ALIGNMENT_WEAK, 0.28


def generate_ocr_stop_column_candidates(artifact):
    tables, table_diagnostics = reconstruct_ocr_stop_tables(artifact)
    rows = [row for table in tables for row in table.get("rows", []) or []]
    if not rows:
        return [], {
            **table_diagnostics,
            "generator_name": GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
            "ocr_geometry_column_candidates": 0,
            "raw_text_printed": False,
            "private_values_printed": False,
        }
    blocks = [_row_to_block(row) for row in rows]
    candidates, block_diagnostics = candidates_from_stop_evidence_blocks(blocks)
    row_lookup = {
        (
            _text(row.get("role")),
            _safe_int(row.get("page")),
            _safe_int(row.get("start_line_index")),
            _safe_int(row.get("end_line_index")),
        ): row
        for row in rows
    }
    adjusted = []
    structured_count = 0
    dispatch_usable_count = 0
    by_field = Counter()
    warning_counts = Counter()
    for candidate in candidates:
        item = dict(candidate)
        metadata = dict(item.get("metadata") or {})
        key = (
            _text(metadata.get("stop_role") or metadata.get("role")),
            _safe_int((metadata.get("page_span") or [0])[0] if metadata.get("page_span") else 0),
            _safe_int((metadata.get("proximity_cluster_line_span") or [0, 0])[0]),
            _safe_int((metadata.get("proximity_cluster_line_span") or [0, 0])[1]),
        )
        row = row_lookup.get(key, {})
        geometry = row.get("column_geometry") or {}
        value = item.get("value")
        stop = value[0] if isinstance(value, list) and value and isinstance(value[0], dict) else {}
        status, score = _column_status(row, stop)
        warnings = sorted(set(row.get("warnings") or []))
        warning_counts.update(warnings)
        dispatch_usable = bool(
            metadata.get("structured_stop_candidate")
            and status in {ALIGNMENT_STRONG, ALIGNMENT_MEDIUM}
            and metadata.get("has_location")
            and metadata.get("has_date")
        )
        if metadata.get("structured_stop_candidate"):
            structured_count += 1
            if dispatch_usable:
                dispatch_usable_count += 1
        metadata.update(
            {
                "generator_name": GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
                "source_generator_name": GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
                "assembled_from_column_geometry": True,
                "geometry_available": True,
                "component_bboxes_available": bool(
                    geometry.get("location_column_bbox")
                    or geometry.get("date_time_column_bbox")
                ),
                "pairing_method": PAIRING_METHOD_OCR_GEOMETRY_COLUMN_ROW,
                "row_boundary_confidence": row.get("row_boundary_confidence", 0.0),
                "column_alignment_confidence": row.get("column_alignment_confidence", 0.0),
                "component_alignment": _component_alignment(row, stop),
                "stop_alignment_status": status,
                "stop_alignment_score": score,
                "stop_alignment_warnings": warnings,
                "stop_geometry_status": status,
                "stop_geometry_score": score,
                "stop_geometry_warnings": warnings,
                "stop_column_status": status,
                "stop_column_score": score,
                "stop_column_warnings": warnings,
                "dispatch_usable": dispatch_usable,
                "review_required": True,
                "raw_text_included": False,
            }
        )
        if metadata.get("stop_block_component_candidate"):
            metadata["structured_stop_candidate"] = False
        item["metadata"] = metadata
        item["parser_name"] = GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR
        item["source"] = SOURCE_OCR
        if item.get("label"):
            item["label"] = str(item["label"]).replace("stop_block", "column_stop_row")
        adjusted.append(item)
        by_field[_text(item.get("field"))] += 1
    diagnostics = {
        **table_diagnostics,
        **(block_diagnostics or {}),
        "generator_name": GENERATOR_OCR_STOP_TABLE_RECONSTRUCTOR,
        "ocr_geometry_column_candidates": len(adjusted),
        "ocr_geometry_column_structured_stop_candidates": structured_count,
        "ocr_geometry_column_dispatch_usable_candidates": dispatch_usable_count,
        "ocr_geometry_column_candidate_fields": dict(by_field.most_common()),
        "column_warning_counts": dict(warning_counts.most_common()),
        "raw_text_printed": False,
        "private_values_printed": False,
    }
    return adjusted, diagnostics
