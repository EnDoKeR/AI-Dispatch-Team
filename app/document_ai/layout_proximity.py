"""Label-value proximity helpers for normalized layout artifacts."""

from app.document_ai.layout_artifacts import (
    EVIDENCE_BELOW_LABEL,
    EVIDENCE_LABEL_VALUE,
    EVIDENCE_SAME_ROW,
    EVIDENCE_TABLE_CELL,
    build_layout_evidence_ref,
)
from app.document_ai.layout_index import (
    build_layout_index,
    get_below_label_candidates,
    get_right_of_label_candidates,
    get_tables_by_page,
)

PROXIMITY_SAME_ROW_RIGHT = "same_row_right"
PROXIMITY_BELOW_LABEL = "below_label"
PROXIMITY_TABLE_ROW = "table_row"
PROXIMITY_TABLE_COLUMN = "table_column"
PROXIMITY_SECTION_FOLLOWING = "section_following"
PROXIMITY_UNKNOWN = "unknown"


def _normalize_patterns(label_patterns):
    if isinstance(label_patterns, dict):
        pairs = []
        for field_name, patterns in label_patterns.items():
            if isinstance(patterns, str):
                values = [patterns]
            else:
                values = list(patterns or [])
            for pattern in values:
                clean = str(pattern or "").strip()
                if clean:
                    pairs.append((str(field_name or "").strip(), clean))
        return pairs

    if isinstance(label_patterns, str):
        return [("", label_patterns)]

    normalized = []
    for pattern in label_patterns or []:
        if isinstance(pattern, (list, tuple)) and len(pattern) == 2:
            source_field, label = pattern
            if str(label).strip():
                normalized.append((str(source_field or "").strip(), str(label).strip()))
        elif str(pattern).strip():
            normalized.append(("", str(pattern).strip()))
    return normalized


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return _text(value).lower()


def _bbox_center(bbox):
    return (
        (float(bbox.get("x0", 0)) + float(bbox.get("x1", 0))) / 2.0,
        (float(bbox.get("y0", 0)) + float(bbox.get("y1", 0))) / 2.0,
    )


def _distance(label_bbox, value_bbox):
    lx, ly = _bbox_center(label_bbox)
    vx, vy = _bbox_center(value_bbox)
    return abs(vx - lx) + abs(vy - ly)


def _bucket(score):
    if score >= 0.78:
        return "HIGH"
    if score >= 0.55:
        return "MEDIUM"
    return "LOW"


def _line_text(line):
    return _text(line.get("text_redacted") or line.get("text"))


def _cell_ref(cell):
    return f"r{int(cell.get('row_index') or 0)}c{int(cell.get('col_index') or 0)}"


def _matches(text, pattern):
    return _lower(pattern) in _lower(text)


def _inline_value_after_label(text, pattern):
    lower_text = _lower(text)
    lower_pattern = _lower(pattern)
    index = lower_text.find(lower_pattern)
    if index < 0:
        return ""

    remainder = text[index + len(pattern):].strip()
    if remainder.startswith(":"):
        remainder = remainder[1:].strip()
    return remainder


def build_label_value_candidate(
    label,
    value_text_redacted,
    label_bbox,
    value_bbox,
    page_number,
    proximity_type=PROXIMITY_UNKNOWN,
    distance_score=0.0,
    confidence="LOW",
    reasons=None,
    evidence_ref=None,
    source_field="",
):
    return {
        "label": _text(label),
        "value_text_redacted": _text(value_text_redacted),
        "label_bbox": label_bbox or {},
        "value_bbox": value_bbox or {},
        "page_number": int(page_number or 0),
        "proximity_type": _text(proximity_type) or PROXIMITY_UNKNOWN,
        "distance_score": float(distance_score or 0.0),
        "confidence": _text(confidence) or "LOW",
        "reasons": [str(reason).strip() for reason in (reasons or []) if str(reason).strip()],
        "evidence_ref": evidence_ref or {},
        "source_field": _text(source_field),
    }


def score_label_value_pair(proximity_type, label_bbox, value_bbox, ambiguous=False):
    base_scores = {
        PROXIMITY_SAME_ROW_RIGHT: 0.92,
        PROXIMITY_TABLE_ROW: 0.9,
        PROXIMITY_TABLE_COLUMN: 0.84,
        PROXIMITY_BELOW_LABEL: 0.74,
        PROXIMITY_SECTION_FOLLOWING: 0.62,
    }
    base = base_scores.get(proximity_type, 0.45)
    distance = _distance(label_bbox or {}, value_bbox or {})
    distance_penalty = min(distance / 1000.0, 0.25)
    ambiguity_penalty = 0.18 if ambiguous else 0.0
    score = max(0.0, min(1.0, base - distance_penalty - ambiguity_penalty))

    return {
        "distance_score": round(score, 4),
        "confidence": _bucket(score),
    }


def detect_label_columns_in_table(table, label_patterns):
    patterns = _normalize_patterns(label_patterns)
    label_cells = []

    for cell in table.get("cells", []):
        text = cell.get("text_redacted", "")
        for source_field, pattern in patterns:
            if _matches(text, pattern):
                label_cells.append(
                    {
                        "cell": cell,
                        "label": pattern,
                        "source_field": source_field,
                    }
                )
                break

    return label_cells


def detect_value_cells_for_label(table, label_cell):
    row_index = int(label_cell.get("row_index") or 0)
    col_index = int(label_cell.get("col_index") or 0)
    candidates = [
        cell
        for cell in table.get("cells", [])
        if int(cell.get("row_index") or 0) == row_index
        and int(cell.get("col_index") or 0) > col_index
        and _text(cell.get("text_redacted"))
    ]

    return sorted(candidates, key=lambda cell: int(cell.get("col_index") or 0))


def _line_candidate(label_line, value_line, pattern, source_field, proximity_type, ambiguous=False):
    label_bbox = label_line.get("bbox", {})
    value_bbox = value_line.get("bbox", {})
    score = score_label_value_pair(proximity_type, label_bbox, value_bbox, ambiguous=ambiguous)
    evidence_type = EVIDENCE_SAME_ROW if proximity_type == PROXIMITY_SAME_ROW_RIGHT else EVIDENCE_BELOW_LABEL

    return build_label_value_candidate(
        label=pattern,
        value_text_redacted=_line_text(value_line),
        label_bbox=label_bbox,
        value_bbox=value_bbox,
        page_number=label_line.get("page_number", 0),
        proximity_type=proximity_type,
        distance_score=score["distance_score"],
        confidence=score["confidence"],
        reasons=[f"{proximity_type}_layout_pair"],
        evidence_ref=build_layout_evidence_ref(
            page_number=label_line.get("page_number", 0),
            bbox=value_bbox,
            line_id=value_line.get("line_id", ""),
            label=pattern,
            evidence_type=evidence_type,
        ),
        source_field=source_field,
    )


def _table_candidate(table, label_info, value_cell, ambiguous=False):
    label_cell = label_info["cell"]
    label_bbox = label_cell.get("bbox", {})
    value_bbox = value_cell.get("bbox", {})
    score = score_label_value_pair(PROXIMITY_TABLE_ROW, label_bbox, value_bbox, ambiguous=ambiguous)

    return build_label_value_candidate(
        label=label_info["label"],
        value_text_redacted=value_cell.get("text_redacted", ""),
        label_bbox=label_bbox,
        value_bbox=value_bbox,
        page_number=table.get("page_number", 0),
        proximity_type=PROXIMITY_TABLE_ROW,
        distance_score=score["distance_score"],
        confidence=score["confidence"],
        reasons=["table_row_layout_pair"],
        evidence_ref=build_layout_evidence_ref(
            page_number=table.get("page_number", 0),
            bbox=value_bbox,
            table_id=table.get("table_id", ""),
            cell_ref=_cell_ref(value_cell),
            label=label_info["label"],
            evidence_type=EVIDENCE_TABLE_CELL,
        ),
        source_field=label_info.get("source_field", ""),
    )


def find_label_value_pairs(layout_artifact, label_patterns, allowed_sections=None):
    index = build_layout_index(layout_artifact)
    patterns = _normalize_patterns(label_patterns)
    allowed = {str(item) for item in (allowed_sections or []) if str(item)}
    candidates = []

    for page_number in sorted(index.get("pages_by_number", {})):
        page = index["pages_by_number"][page_number]
        lines = index["lines_by_page"].get(page_number, [])

        for line in lines:
            section_role = line.get("section_role", "")
            if allowed and section_role not in allowed:
                continue
            text = _line_text(line)
            for source_field, pattern in patterns:
                if not _matches(text, pattern):
                    continue

                inline_value = _inline_value_after_label(text, pattern)
                if inline_value:
                    score = score_label_value_pair(
                        PROXIMITY_SAME_ROW_RIGHT,
                        line.get("bbox", {}),
                        line.get("bbox", {}),
                    )
                    candidates.append(
                        build_label_value_candidate(
                            label=pattern,
                            value_text_redacted=inline_value,
                            label_bbox=line.get("bbox", {}),
                            value_bbox=line.get("bbox", {}),
                            page_number=line.get("page_number", 0),
                            proximity_type=PROXIMITY_SAME_ROW_RIGHT,
                            distance_score=score["distance_score"],
                            confidence=score["confidence"],
                            reasons=["inline_label_value_pair"],
                            evidence_ref=build_layout_evidence_ref(
                                page_number=line.get("page_number", 0),
                                bbox=line.get("bbox", {}),
                                line_id=line.get("line_id", ""),
                                label=pattern,
                                evidence_type=EVIDENCE_LABEL_VALUE,
                            ),
                            source_field=source_field,
                        )
                    )

                right_candidates = get_right_of_label_candidates(index, line)
                ambiguous_right = len(right_candidates) > 1
                for value_line in right_candidates:
                    candidates.append(
                        _line_candidate(
                            line,
                            value_line,
                            pattern,
                            source_field,
                            PROXIMITY_SAME_ROW_RIGHT,
                            ambiguous=ambiguous_right,
                        )
                    )

                below_candidates = get_below_label_candidates(index, line)
                ambiguous_below = len(below_candidates) > 1
                for value_line in below_candidates:
                    proximity_type = (
                        PROXIMITY_BELOW_LABEL
                        if value_line.get("section_role") == section_role
                        else PROXIMITY_SECTION_FOLLOWING
                    )
                    candidates.append(
                        _line_candidate(
                            line,
                            value_line,
                            pattern,
                            source_field,
                            proximity_type,
                            ambiguous=ambiguous_below,
                        )
                    )

        for table in get_tables_by_page(index, page_number):
            label_cells = detect_label_columns_in_table(table, patterns)
            for label_info in label_cells:
                value_cells = detect_value_cells_for_label(table, label_info["cell"])
                ambiguous = len(value_cells) > 1
                for value_cell in value_cells:
                    candidates.append(_table_candidate(table, label_info, value_cell, ambiguous=ambiguous))

    return candidates
