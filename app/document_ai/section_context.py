"""Lightweight section-context detection for shadow document diagnostics."""

from collections import Counter


SECTION_PICKUP = "pickup"
SECTION_DELIVERY = "delivery"
SECTION_RATE = "rate"
SECTION_REFERENCE = "reference"
SECTION_LOAD_INFO = "load_info"
SECTION_INSTRUCTIONS = "instructions"
SECTION_STOP = "stop"
SECTION_UNKNOWN = "unknown"


def _text(value):
    return str(value or "").strip()


def classify_line_section_context(text, previous_context=SECTION_UNKNOWN):
    line = _text(text).lower()
    if not line:
        return previous_context or SECTION_UNKNOWN
    if any(token in line for token in ["carrier pay", "total rate", "charges", "rate", "linehaul"]):
        return SECTION_RATE
    if any(token in line for token in ["special instructions", "instructions", "requirements", "notes"]):
        return SECTION_INSTRUCTIONS
    if any(token in line for token in ["load information", "shipment information", "load #", "load no", "load number", "shipment id", "tender id", "order #"]):
        return SECTION_LOAD_INFO
    if any(token in line for token in ["po #", "po number", "bol", "reference", "ref #"]):
        return SECTION_REFERENCE
    if any(token in line for token in ["pickup", "pick up", "origin", "shipper"]):
        return SECTION_PICKUP
    if any(token in line for token in ["delivery", "deliver", "destination", "consignee", "drop"]):
        return SECTION_DELIVERY
    if "stop" in line:
        return SECTION_STOP
    return previous_context or SECTION_UNKNOWN


def artifact_page_lines_with_context(artifact):
    pages = []
    for page in (artifact or {}).get("pages", []) or []:
        page_number = page.get("page_number", len(pages) + 1)
        line_items = []
        for item in page.get("lines", []) or []:
            text = _text(item.get("text") if isinstance(item, dict) else item)
            if text:
                line_items.append(text)
        if not line_items:
            line_items = [
                line.strip()
                for line in str(page.get("text") or "").splitlines()
                if line.strip()
            ]
        context = SECTION_UNKNOWN
        rows = []
        for index, line in enumerate(line_items):
            context = classify_line_section_context(line, previous_context=context)
            rows.append(
                {
                    "page_number": page_number,
                    "line_index": index,
                    "section_context": context,
                    "text": line,
                }
            )
        pages.append((page_number, rows))
    if not pages and _text((artifact or {}).get("full_text")):
        context = SECTION_UNKNOWN
        rows = []
        for index, line in enumerate(
            [
                line.strip()
                for line in str((artifact or {}).get("full_text") or "").splitlines()
                if line.strip()
            ]
        ):
            context = classify_line_section_context(line, previous_context=context)
            rows.append(
                {
                    "page_number": 1,
                    "line_index": index,
                    "section_context": context,
                    "text": line,
                }
            )
        pages.append((1, rows))
    return pages


def line_section_context_lookup(artifact):
    lookup = {}
    for page_number, rows in artifact_page_lines_with_context(artifact):
        for row in rows:
            lookup[(page_number, row["line_index"])] = row["section_context"]
    return lookup


def section_context_summary(artifact):
    counts = Counter()
    total = 0
    for _page_number, rows in artifact_page_lines_with_context(artifact):
        for row in rows:
            total += 1
            counts[row["section_context"]] += 1
    return {
        "lines_with_section_context": total - counts.get(SECTION_UNKNOWN, 0),
        "section_counts": dict(sorted(counts.items())),
        "unknown_section_lines": counts.get(SECTION_UNKNOWN, 0),
    }
