"""Geometry-aware OCR stop assembly for shadow RateCon diagnostics.

This module consumes optional Tesseract TSV line boxes. It is deliberately
profile-gated and falls back to diagnostics instead of changing default stop
extraction when OCR geometry is unavailable.
"""

from __future__ import annotations

from collections import Counter

from app.document_ai.field_candidate_provenance import SOURCE_OCR
from app.document_ai.ocr_stop_block_assembler import (
    ALIGNMENT_MEDIUM,
    ALIGNMENT_STRONG,
    ALIGNMENT_UNSAFE,
    ALIGNMENT_WEAK,
    GENERATOR_OCR_STOP_BLOCK_ASSEMBLER,
    ROLE_DELIVERY,
    ROLE_PICKUP,
    ROLE_UNKNOWN,
    SECTION_FOOTER,
    SECTION_INSTRUCTIONS,
    SECTION_PAYMENT,
    _block_type_from_line,
    _has_date,
    _has_time,
    _line_has_location,
    _role_from_line,
    _section_context,
    _section_should_end_block,
    _stop_index_from_line,
    candidates_from_stop_evidence_blocks,
)


GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER = "ocr_stop_geometry_assembler"

PAIRING_METHOD_OCR_GEOMETRY_BLOCK = "ocr_geometry_block"


def _text(value) -> str:
    return str(value or "").strip()


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
    if not isinstance(value, dict):
        if isinstance(value, (list, tuple)) and len(value) >= 4:
            return {
                "left": _safe_float(value[0]),
                "top": _safe_float(value[1]),
                "right": _safe_float(value[2]),
                "bottom": _safe_float(value[3]),
            }
        return None
    left = _safe_float(value.get("left", value.get("x0")))
    top = _safe_float(value.get("top", value.get("y0")))
    right = _safe_float(value.get("right", value.get("x1", left + _safe_float(value.get("width")))))
    bottom = _safe_float(value.get("bottom", value.get("y1", top + _safe_float(value.get("height")))))
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
    }


def _union_bbox(rows):
    boxes = [_bbox(row.get("bbox")) for row in rows or []]
    boxes = [box for box in boxes if box]
    if not boxes:
        return None
    return {
        "left": min(box["left"] for box in boxes),
        "top": min(box["top"] for box in boxes),
        "right": max(box["right"] for box in boxes),
        "bottom": max(box["bottom"] for box in boxes),
    }


def _row_center_y(row):
    box = _bbox(row.get("bbox")) or {}
    return (_safe_float(box.get("top")) + _safe_float(box.get("bottom"))) / 2.0


def _row_left(row):
    box = _bbox(row.get("bbox")) or {}
    return _safe_float(box.get("left"))


def _line_rows_with_geometry(artifact):
    rows = []
    seen = set()
    for page in (artifact or {}).get("pages", []) or []:
        page_number = _safe_int(page.get("page_number"), 1) or 1
        for ordinal, line in enumerate(page.get("lines", []) or []):
            if not isinstance(line, dict):
                continue
            if _text(line.get("source")) != SOURCE_OCR:
                continue
            text = _text(line.get("text"))
            box = _bbox(line.get("bbox"))
            if not text or not box:
                continue
            key = (page_number, _safe_int(line.get("line_index"), ordinal), text, box["top"], box["left"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "page": page_number,
                    "line_index": _safe_int(line.get("line_index"), ordinal),
                    "ordinal": len(rows),
                    "text": text,
                    "bbox": box,
                    "source": SOURCE_OCR,
                }
            )
    for ocr_page in ((artifact or {}).get("ocr_provider_result") or {}).get("pages", []) or []:
        if not isinstance(ocr_page, dict):
            continue
        page_number = _safe_int(ocr_page.get("page_number"), 1) or 1
        for ordinal, line in enumerate(ocr_page.get("line_boxes", []) or []):
            if not isinstance(line, dict):
                continue
            text = _text(line.get("text"))
            box = _bbox(line.get("bbox") or line)
            if not text or not box:
                continue
            line_index = _safe_int(line.get("line_index"), ordinal)
            key = (page_number, line_index, text, box["top"], box["left"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "page": page_number,
                    "line_index": line_index,
                    "ordinal": len(rows),
                    "text": text,
                    "bbox": box,
                    "source": SOURCE_OCR,
                }
            )
    rows.sort(key=lambda item: (item["page"], _row_center_y(item), _row_left(item)))
    return rows


def _is_boundary_context(context):
    return context in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}


def _component_rows(rows):
    location_rows = [
        row
        for row in rows or []
        if _line_has_location(row.get("text")) and _section_context(row.get("text")) not in {
            SECTION_PAYMENT,
            SECTION_INSTRUCTIONS,
            SECTION_FOOTER,
        }
    ]
    date_time_rows = [
        row
        for row in rows or []
        if (_has_date(row.get("text")) or _has_time(row.get("text")))
        and _section_context(row.get("text")) not in {
            SECTION_PAYMENT,
            SECTION_INSTRUCTIONS,
            SECTION_FOOTER,
        }
    ]
    return location_rows, date_time_rows


def _geometry_warnings(role, rows, role_row, next_role_y=None, boundary_context=""):
    warnings = []
    if not rows:
        return ["no_clear_role_boundary"]
    other_role = ROLE_DELIVERY if role == ROLE_PICKUP else ROLE_PICKUP
    for row in rows[1:]:
        if _role_from_line(row.get("text")) == other_role:
            warnings.append("pickup_delivery_overlap")
        context = _section_context(row.get("text"))
        if context == SECTION_PAYMENT:
            warnings.append("component_from_payment_section")
        elif context == SECTION_INSTRUCTIONS:
            warnings.append("component_from_instructions")
        elif context == SECTION_FOOTER:
            warnings.append("component_from_footer")
    if boundary_context in {SECTION_PAYMENT, SECTION_INSTRUCTIONS, SECTION_FOOTER}:
        warnings.append(f"block_bounded_by_{boundary_context}")
    if next_role_y is None and len(rows) >= 8:
        warnings.append("no_clear_block_end")
    role_y = _row_center_y(role_row)
    for row in rows:
        if _has_date(row.get("text")) and abs(_row_center_y(row) - role_y) > 260:
            warnings.append("date_far_from_role")
        if _line_has_location(row.get("text")) and abs(_row_center_y(row) - role_y) > 320:
            warnings.append("location_far_from_role")
        if next_role_y is not None and _row_center_y(row) >= next_role_y:
            warnings.append("component_from_neighbor_block")
    if role == ROLE_DELIVERY and not any(_has_date(row.get("text")) for row in rows):
        warnings.append("delivery_date_missing")
    if sum(1 for row in rows if _has_date(row.get("text"))) > 1:
        warnings.append("multiple_dates_unpaired")
    if sum(1 for row in rows if _line_has_location(row.get("text"))) > 3:
        warnings.append("multiple_locations_unpaired")
    return sorted(set(warnings))


def _alignment_status(role, rows, warnings):
    has_location = any(_line_has_location(row.get("text")) for row in rows or [])
    has_datetime = any(_has_date(row.get("text")) or _has_time(row.get("text")) for row in rows or [])
    unsafe_warnings = {
        "component_from_payment_section",
        "component_from_instructions",
        "component_from_footer",
        "component_from_neighbor_block",
        "pickup_delivery_overlap",
    }
    if role not in {ROLE_PICKUP, ROLE_DELIVERY}:
        return ALIGNMENT_UNSAFE, 0.0
    if set(warnings).intersection(unsafe_warnings):
        return ALIGNMENT_UNSAFE, 0.14
    if has_location and has_datetime:
        return ALIGNMENT_STRONG, 0.88
    if has_location or has_datetime:
        return ALIGNMENT_MEDIUM, 0.62
    return ALIGNMENT_WEAK, 0.25


def _component_alignment(rows, role_row):
    role_box = _bbox(role_row.get("bbox")) or {}
    role_right = _safe_float(role_box.get("right"))
    location_rows, date_time_rows = _component_rows(rows)
    alignment = {
        "facility": "missing",
        "address": "missing",
        "city_state_zip": "missing",
        "date": "missing",
        "time": "missing",
    }
    if location_rows:
        alignment["facility"] = "same_block"
        alignment["address"] = "same_block"
        alignment["city_state_zip"] = "same_block"
    for row in date_time_rows:
        row_left = _row_left(row)
        if _has_date(row.get("text")):
            alignment["date"] = "same_block_right_column" if row_left >= role_right else "same_row"
        if _has_time(row.get("text")):
            alignment["time"] = "same_block_right_column" if row_left >= role_right else "same_row"
    return alignment


def detect_geometry_stop_blocks_from_artifact(artifact):
    rows = _line_rows_with_geometry(artifact)
    if not rows:
        return [], {
            "geometry_available": False,
            "ocr_line_box_count": 0,
            "detected_geometry_block_count": 0,
        }

    blocks = []
    by_page = {}
    for row in rows:
        by_page.setdefault(row["page"], []).append(row)

    for page, page_rows in sorted(by_page.items()):
        ordered = sorted(page_rows, key=lambda item: (_row_center_y(item), _row_left(item)))
        role_indices = [
            index
            for index, row in enumerate(ordered)
            if _role_from_line(row.get("text")) in {ROLE_PICKUP, ROLE_DELIVERY}
        ]
        for ordinal, role_index in enumerate(role_indices):
            role_row = ordered[role_index]
            role = _role_from_line(role_row.get("text")) or ROLE_UNKNOWN
            role_y = _row_center_y(role_row)
            next_role_y = (
                _row_center_y(ordered[role_indices[ordinal + 1]])
                if ordinal + 1 < len(role_indices)
                else None
            )
            boundary_y = next_role_y
            boundary_context = ""
            for candidate in ordered[role_index + 1:]:
                candidate_y = _row_center_y(candidate)
                if next_role_y is not None and candidate_y >= next_role_y:
                    break
                context = _section_context(candidate.get("text"))
                if _is_boundary_context(context) or _section_should_end_block(context):
                    boundary_y = candidate_y
                    boundary_context = context
                    break
            collected = []
            for row in ordered[role_index:]:
                y = _row_center_y(row)
                if y < role_y - 16:
                    continue
                if boundary_y is not None and y >= boundary_y and row is not role_row:
                    break
                collected.append(row)
            warnings = _geometry_warnings(
                role,
                collected,
                role_row,
                next_role_y=next_role_y,
                boundary_context=boundary_context,
            )
            status, score = _alignment_status(role, collected, warnings)
            location_rows, date_time_rows = _component_rows(collected)
            block_bbox = _union_bbox(collected)
            role_bbox = _union_bbox([role_row])
            location_bbox = _union_bbox(location_rows)
            date_time_bbox = _union_bbox(date_time_rows)
            has_boundary = bool(next_role_y is not None or boundary_context)
            boundary_confidence = round(
                (0.4 if role in {ROLE_PICKUP, ROLE_DELIVERY} else 0.0)
                + (0.25 if has_boundary else 0.0)
                + (0.2 if location_rows else 0.0)
                + (0.15 if date_time_rows else 0.0),
                3,
            )
            block = {
                "role": role,
                "stop_index": _stop_index_from_line(role_row.get("text"), default=1),
                "source": SOURCE_OCR,
                "page": page,
                "start_line_index": collected[0]["line_index"] if collected else role_row["line_index"],
                "end_line_index": collected[-1]["line_index"] if collected else role_row["line_index"],
                "line_count": len(collected),
                "has_role_label": True,
                "has_location_like_text": bool(location_rows),
                "has_date_like_text": any(_has_date(row.get("text")) for row in collected),
                "has_time_like_text": any(_has_time(row.get("text")) for row in collected),
                "has_address_like_text": bool(location_rows),
                "section_context": "stop_section",
                "lines": [row["text"] for row in collected],
                "geometry": {
                    "role": role,
                    "stop_index": _stop_index_from_line(role_row.get("text"), default=1),
                    "page": page,
                    "bbox": block_bbox,
                    "role_bbox": role_bbox,
                    "location_bbox": location_bbox,
                    "date_time_bbox": date_time_bbox,
                    "boundary_confidence": boundary_confidence,
                    "has_clear_horizontal_boundary": has_boundary,
                    "has_clear_role_anchor": role in {ROLE_PICKUP, ROLE_DELIVERY},
                    "has_date_time_column": bool(date_time_rows),
                    "has_location_column": bool(location_rows),
                    "alignment_status": status,
                    "alignment_score": score,
                    "warnings": warnings,
                    "component_alignment": _component_alignment(collected, role_row),
                },
                "provenance": {
                    "block_detector": GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER,
                    "source": SOURCE_OCR,
                    "page": page,
                    "start_line_index": collected[0]["line_index"] if collected else role_row["line_index"],
                    "end_line_index": collected[-1]["line_index"] if collected else role_row["line_index"],
                    "block_type": _block_type_from_line(role_row.get("text"), role),
                    "geometry_available": True,
                },
            }
            blocks.append(block)
    diagnostics = {
        "geometry_available": True,
        "ocr_line_box_count": len(rows),
        "detected_geometry_block_count": len(blocks),
        "geometry_blocks_by_role": dict(
            Counter(block.get("role") for block in blocks).most_common()
        ),
        "geometry_alignment_status_counts": dict(
            Counter((block.get("geometry") or {}).get("alignment_status") for block in blocks).most_common()
        ),
        "geometry_warning_counts": dict(
            Counter(
                warning
                for block in blocks
                for warning in (block.get("geometry") or {}).get("warnings", []) or []
            ).most_common()
        ),
        "raw_text_printed": False,
        "private_values_printed": False,
    }
    return blocks, diagnostics


def _block_key_from_block(block):
    return (
        _text(block.get("role")),
        _safe_int(block.get("page")),
        _safe_int(block.get("start_line_index")),
        _safe_int(block.get("end_line_index")),
    )


def _block_key_from_metadata(metadata):
    line_span = metadata.get("proximity_cluster_line_span") or metadata.get("line_span") or []
    if isinstance(line_span, dict):
        start = line_span.get("start")
        end = line_span.get("end")
    else:
        start = line_span[0] if len(line_span) > 0 else 0
        end = line_span[1] if len(line_span) > 1 else start
    page_span = metadata.get("page_span") or []
    page = page_span[0] if isinstance(page_span, list) and page_span else 0
    return (
        _text(metadata.get("stop_role") or metadata.get("role")),
        _safe_int(page),
        _safe_int(start),
        _safe_int(end),
    )


def _geometry_metadata(block):
    geometry = block.get("geometry") or {}
    warnings = list(geometry.get("warnings") or [])
    status = _text(geometry.get("alignment_status")) or ALIGNMENT_WEAK
    score = _safe_float(geometry.get("alignment_score"))
    return {
        "generator_name": GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER,
        "source_generator_name": GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER,
        "assembled_from_geometry_block": True,
        "geometry_available": True,
        "component_bboxes_available": bool(
            geometry.get("location_bbox") or geometry.get("date_time_bbox")
        ),
        "pairing_method": PAIRING_METHOD_OCR_GEOMETRY_BLOCK,
        "block_boundary_confidence": geometry.get("boundary_confidence", 0.0),
        "has_clear_horizontal_boundary": bool(geometry.get("has_clear_horizontal_boundary")),
        "has_clear_role_anchor": bool(geometry.get("has_clear_role_anchor")),
        "has_date_time_column": bool(geometry.get("has_date_time_column")),
        "has_location_column": bool(geometry.get("has_location_column")),
        "component_alignment": dict(geometry.get("component_alignment") or {}),
        "stop_alignment_status": status,
        "stop_alignment_score": round(score, 3),
        "stop_alignment_warnings": sorted(set(warnings)),
        "stop_geometry_status": status,
        "stop_geometry_score": round(score, 3),
        "stop_geometry_warnings": sorted(set(warnings)),
        "geometry_block_type": _text((block.get("provenance") or {}).get("block_type")) or "unknown",
        "raw_text_included": False,
    }


def candidates_from_geometry_stop_blocks(blocks):
    candidates, diagnostics = candidates_from_stop_evidence_blocks(blocks)
    block_lookup = {_block_key_from_block(block): block for block in blocks or []}
    adjusted = []
    for candidate in candidates:
        item = dict(candidate)
        metadata = dict(item.get("metadata") or {})
        block = block_lookup.get(_block_key_from_metadata(metadata), {})
        metadata.update(_geometry_metadata(block))
        if metadata.get("stop_block_component_candidate"):
            metadata["structured_stop_candidate"] = False
        item["metadata"] = metadata
        item["parser_name"] = GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER
        item["source"] = SOURCE_OCR
        if item.get("label"):
            item["label"] = str(item["label"]).replace("stop_block", "geometry_stop_block")
        adjusted.append(item)
    structured = [
        item
        for item in adjusted
        if (item.get("metadata") or {}).get("structured_stop_candidate")
    ]
    diagnostics = dict(diagnostics or {})
    diagnostics.update(
        {
            "generator_name": GENERATOR_OCR_STOP_GEOMETRY_ASSEMBLER,
            "geometry_structured_stop_candidates": len(structured),
            "geometry_candidate_count": len(adjusted),
            "geometry_candidate_fields": dict(
                Counter(_text(item.get("field")) for item in adjusted).most_common()
            ),
            "raw_text_printed": False,
            "private_values_printed": False,
        }
    )
    return adjusted, diagnostics


def generate_ocr_stop_geometry_candidates(artifact):
    blocks, diagnostics = detect_geometry_stop_blocks_from_artifact(artifact)
    if not diagnostics.get("geometry_available"):
        return [], {
            **diagnostics,
            "warnings": ["ocr_geometry_unavailable"],
            "fallback_profile": "ocr_block_assembly_v1",
            "fallback_used_for_candidates": False,
        }
    candidates, candidate_diagnostics = candidates_from_geometry_stop_blocks(blocks)
    merged = {**diagnostics, **candidate_diagnostics}
    return candidates, merged
