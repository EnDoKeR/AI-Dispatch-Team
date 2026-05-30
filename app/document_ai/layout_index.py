"""Pure helpers for indexing normalized layout artifacts."""


def _bbox(item):
    if isinstance(item, dict):
        return item.get("bbox") or {}
    return {}


def _page_number(item):
    if isinstance(item, dict):
        return int(item.get("page_number") or (_bbox(item).get("page_number") or 0))
    return 0


def _center_y(bbox):
    return (float(bbox.get("y0", 0)) + float(bbox.get("y1", 0))) / 2.0


def _vertical_overlap(a, b):
    top = max(float(a.get("y0", 0)), float(b.get("y0", 0)))
    bottom = min(float(a.get("y1", 0)), float(b.get("y1", 0)))
    return max(0.0, bottom - top)


def _height(bbox):
    return max(0.0, float(bbox.get("y1", 0)) - float(bbox.get("y0", 0)))


def build_layout_index(artifact):
    pages = [page for page in artifact.get("pages", []) if isinstance(page, dict)]
    index = {
        "artifact": artifact,
        "pages_by_number": {},
        "lines_by_id": {},
        "blocks_by_id": {},
        "tables_by_id": {},
        "lines_by_page": {},
        "blocks_by_section_role": {},
        "tables_by_page": {},
        "words_by_page": {},
    }

    for page in pages:
        page_number = int(page.get("page_number") or 0)
        index["pages_by_number"][page_number] = page
        index["lines_by_page"].setdefault(page_number, [])
        index["tables_by_page"].setdefault(page_number, [])
        index["words_by_page"].setdefault(page_number, [])

        for word in page.get("words", []):
            if isinstance(word, dict):
                index["words_by_page"][page_number].append(word)

        for line in page.get("lines", []):
            if isinstance(line, dict):
                line_id = line.get("line_id", "")
                if line_id:
                    index["lines_by_id"][line_id] = line
                index["lines_by_page"][page_number].append(line)

        for block in page.get("blocks", []):
            if isinstance(block, dict):
                block_id = block.get("block_id", "")
                section_role = block.get("section_role", "")
                if block_id:
                    index["blocks_by_id"][block_id] = block
                if section_role:
                    index["blocks_by_section_role"].setdefault(section_role, []).append(block)

        for table in page.get("tables", []):
            if isinstance(table, dict):
                table_id = table.get("table_id", "")
                if table_id:
                    index["tables_by_id"][table_id] = table
                index["tables_by_page"][page_number].append(table)

    for page_number, lines in index["lines_by_page"].items():
        index["lines_by_page"][page_number] = sort_lines_reading_order(lines)

    return index


def get_lines_by_page(index, page_number):
    return list(index.get("lines_by_page", {}).get(int(page_number or 0), []))


def get_blocks_by_section_role(index, section_role):
    return list(index.get("blocks_by_section_role", {}).get(str(section_role or ""), []))


def get_tables_by_page(index, page_number):
    return list(index.get("tables_by_page", {}).get(int(page_number or 0), []))


def find_words_in_bbox(index, bbox, page_number=None):
    target_page = int(page_number or bbox.get("page_number") or 0)
    words = index.get("words_by_page", {}).get(target_page, [])
    x0 = float(bbox.get("x0", 0))
    y0 = float(bbox.get("y0", 0))
    x1 = float(bbox.get("x1", 0))
    y1 = float(bbox.get("y1", 0))

    matches = []
    for word in words:
        word_box = _bbox(word)
        if (
            float(word_box.get("x0", 0)) >= x0
            and float(word_box.get("x1", 0)) <= x1
            and float(word_box.get("y0", 0)) >= y0
            and float(word_box.get("y1", 0)) <= y1
        ):
            matches.append(word)
    return matches


def find_lines_near_bbox(index, bbox, page_number=None, max_distance=30):
    target_page = int(page_number or bbox.get("page_number") or 0)
    target_center = _center_y(bbox)
    matches = []

    for line in get_lines_by_page(index, target_page):
        line_box = _bbox(line)
        distance = abs(_center_y(line_box) - target_center)
        if distance <= max_distance:
            matches.append(line)

    return sort_lines_reading_order(matches)


def sort_lines_reading_order(lines):
    return sorted(
        [line for line in lines or [] if isinstance(line, dict)],
        key=lambda line: (
            _page_number(line),
            int(line.get("reading_order_index") or 0),
            float(_bbox(line).get("y0", 0)),
            float(_bbox(line).get("x0", 0)),
        ),
    )


def group_lines_by_vertical_gap(lines, gap_threshold=20):
    sorted_lines = sort_lines_reading_order(lines)
    groups = []
    current = []
    previous_box = None

    for line in sorted_lines:
        line_box = _bbox(line)
        if previous_box is not None:
            gap = float(line_box.get("y0", 0)) - float(previous_box.get("y1", 0))
            if gap > gap_threshold:
                groups.append(current)
                current = []
        current.append(line)
        previous_box = line_box

    if current:
        groups.append(current)

    return groups


def get_same_row_candidates(index, label_line, min_overlap_ratio=0.35):
    label_box = _bbox(label_line)
    label_height = _height(label_box) or 1.0
    page_number = _page_number(label_line)
    candidates = []

    for line in get_lines_by_page(index, page_number):
        if line is label_line or line.get("line_id") == label_line.get("line_id"):
            continue
        line_box = _bbox(line)
        overlap = _vertical_overlap(label_box, line_box)
        if overlap / label_height >= min_overlap_ratio:
            candidates.append(line)

    return sort_lines_reading_order(candidates)


def get_right_of_label_candidates(index, label_line, max_horizontal_gap=240):
    label_box = _bbox(label_line)
    candidates = []

    for line in get_same_row_candidates(index, label_line):
        line_box = _bbox(line)
        horizontal_gap = float(line_box.get("x0", 0)) - float(label_box.get("x1", 0))
        if 0 <= horizontal_gap <= max_horizontal_gap:
            candidates.append(line)

    return sort_lines_reading_order(candidates)


def get_below_label_candidates(index, label_line, max_vertical_gap=80):
    label_box = _bbox(label_line)
    page_number = _page_number(label_line)
    candidates = []

    for line in get_lines_by_page(index, page_number):
        if line is label_line or line.get("line_id") == label_line.get("line_id"):
            continue
        line_box = _bbox(line)
        gap = float(line_box.get("y0", 0)) - float(label_box.get("y1", 0))
        horizontal_overlap = _vertical_overlap(
            {"y0": label_box.get("x0", 0), "y1": label_box.get("x1", 0)},
            {"y0": line_box.get("x0", 0), "y1": line_box.get("x1", 0)},
        )
        if 0 <= gap <= max_vertical_gap and horizontal_overlap > 0:
            candidates.append(line)

    return sort_lines_reading_order(candidates)
