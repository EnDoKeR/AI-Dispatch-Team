"""Safe load-identity label-hit forensics for shadow diagnostics."""

from collections import Counter
import re

from app.document_ai.section_context import (
    SECTION_LOAD_INFO,
    SECTION_RATE,
    artifact_page_lines_with_context,
)


_IDENTIFIER_LABEL_CORE = (
    r"rate\s+confirmation|load|shipment|order|tender|confirmation|trip|dispatch|"
    r"reference|ref|po|bol|pickup|delivery"
)
LOAD_IDENTIFIER_LINE_PATTERN = re.compile(
    r"^\s*(?P<label>(?:"
    + _IDENTIFIER_LABEL_CORE
    + r")(?:\s*(?:#|no\.?|number|id))?)"
    r"(?:\s*[:#-]\s*|\s{2,}|\s+)"
    r"(?P<value>[A-Za-z0-9][A-Za-z0-9_./ -]{1,})\s*$",
    re.IGNORECASE,
)
LOAD_IDENTIFIER_LABEL_ONLY_PATTERN = re.compile(
    r"^\s*(?P<label>(?:"
    + _IDENTIFIER_LABEL_CORE
    + r")(?:\s*(?:#|no\.?|number|id))?)\s*[:#-]?\s*$",
    re.IGNORECASE,
)


def _text(value):
    return str(value or "").strip()


def _looks_like_phone(text):
    return bool(re.search(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", _text(text)))


def _looks_like_address(text):
    value = _text(text).lower()
    return bool(
        re.match(r"^\d+\s+\S+", value)
        and any(
            token in value
            for token in [
                " st",
                " street",
                " ave",
                " avenue",
                " rd",
                " road",
                " dr",
                " drive",
                " lane",
                " blvd",
                " hwy",
                " highway",
            ]
        )
    )


def candidate_value_shape(value):
    text = _text(value)
    lower = text.lower()
    return {
        "length": len(text),
        "has_digits": any(char.isdigit() for char in text),
        "has_letters": any(char.isalpha() for char in text),
        "has_dash": "-" in text,
        "has_slash": "/" in text,
        "looks_like_date": bool(re.fullmatch(r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?", text)),
        "looks_like_money": "$" in text
        or bool(re.fullmatch(r"\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?", text)),
        "looks_like_phone": _looks_like_phone(text),
        "looks_like_address": _looks_like_address(text),
        "token_count": len(text.split()) if text else 0,
    }


def line_shape(value):
    shape = candidate_value_shape(value)
    return {
        "length": shape["length"],
        "has_digits": shape["has_digits"],
        "has_letters": shape["has_letters"],
        "has_dash": shape["has_dash"],
        "has_slash": shape["has_slash"],
        "looks_like_date": shape["looks_like_date"],
        "looks_like_money": shape["looks_like_money"],
        "looks_like_phone": shape["looks_like_phone"],
        "looks_like_address": shape["looks_like_address"],
        "token_count": shape["token_count"],
    }


def normalized_label(label):
    token = _text(label).lower().replace(".", "")
    if "rate confirmation" in token:
        return "confirmation_number"
    if "load" in token:
        return "load_number"
    if "shipment" in token:
        return "shipment_number"
    if "order" in token:
        return "order_number"
    if "tender" in token:
        return "tender_number"
    if "confirmation" in token:
        return "confirmation_number"
    if "dispatch" in token:
        return "dispatch_number"
    if "trip" in token:
        return "trip_number"
    if "po" in token or "bol" in token or "pickup" in token or "delivery" in token:
        return "reference_number"
    if "reference" in token or token.startswith("ref"):
        return "reference_number"
    return "unknown"


def identifier_value_rejection_reason(value):
    text = _text(value)
    lower = text.lower()
    shape = candidate_value_shape(text)
    if not text:
        return "no_value"
    if len(text) < 4:
        return "candidate_too_short"
    if len(text) > 40:
        return "candidate_too_long"
    if not shape["has_digits"]:
        return "candidate_has_no_digits"
    if lower in {"confirmation", "number", "id", "load", "shipment", "order"}:
        return "candidate_generic_label_word"
    if re.fullmatch(r"[\W_]+", text):
        return "candidate_only_punctuation"
    if shape["looks_like_money"]:
        return "candidate_looks_like_money"
    if shape["looks_like_date"]:
        return "candidate_looks_like_date"
    if shape["looks_like_phone"]:
        return "candidate_looks_like_phone"
    if shape["looks_like_address"]:
        return "candidate_looks_like_address"
    if shape["token_count"] > 4:
        return "candidate_line_too_noisy"
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_./ -]{2,}$", text):
        return "candidate_failed_charset_shape"
    return ""


def _label_match(line):
    same_line = LOAD_IDENTIFIER_LINE_PATTERN.match(_text(line))
    if same_line:
        return same_line, None
    return None, LOAD_IDENTIFIER_LABEL_ONLY_PATTERN.match(_text(line))


def _next_value(rows, index):
    for position in range(index + 1, min(len(rows), index + 4)):
        value = _text(rows[position]["text"])
        if value:
            return value
    return ""


def _previous_value(rows, index):
    for position in range(index - 1, max(-1, index - 4), -1):
        value = _text(rows[position]["text"])
        if value:
            return value
    return ""


def _window_attempts(rows, index, same_line_value=""):
    attempts = []
    if same_line_value:
        attempts.append(("same_line", same_line_value))
    next_value = _next_value(rows, index)
    previous_value = _previous_value(rows, index)
    attempts.append(("adjacent_next", next_value))
    attempts.append(("adjacent_previous", previous_value))
    for position in range(max(0, index - 2), min(len(rows), index + 3)):
        if position == index:
            continue
        method = "line_window_previous" if position < index else "line_window_next"
        attempts.append((method, _text(rows[position]["text"])))
    return attempts


def _full_text_window_value(artifact, label):
    full_text = _text((artifact or {}).get("full_text"))
    label_text = _text(label)
    if not full_text or not label_text:
        return ""
    pattern = re.compile(
        re.escape(label_text) + r"[^A-Za-z0-9]{0,50}([A-Za-z0-9][A-Za-z0-9_./-]{2,})",
        re.IGNORECASE,
    )
    match = pattern.search(full_text)
    return match.group(1).strip() if match else ""


def _line_window_shape(rows, index):
    def row_shape(offset):
        position = index + offset
        if position < 0 or position >= len(rows):
            return line_shape("")
        return line_shape(rows[position]["text"])

    return {
        "previous_line_shape": row_shape(-1),
        "same_line_shape": row_shape(0),
        "next_line_shape": row_shape(1),
        "next_2_line_shape": row_shape(2),
    }


def _hit_type(method, accepted, label, section_context, rejection_reason, attempts):
    label_type = normalized_label(label)
    if label_type == "reference_number":
        return "po_bol_reference_only"
    if accepted:
        if method == "same_line":
            return "same_line_value_present"
        if method == "adjacent_next":
            return "adjacent_next_value_present"
        if method == "adjacent_previous":
            return "adjacent_previous_value_present"
        if method in {"line_window_next", "line_window_previous"}:
            return "line_window_value_present"
        if method == "full_text_window":
            return "full_text_window_value_present"
    if section_context == SECTION_RATE:
        return "false_positive_label"
    if any(int(attempt.get("candidate_value_shape", {}).get("length") or 0) > 0 for attempt in attempts):
        if rejection_reason in {"candidate_has_no_digits", "candidate_too_long", "candidate_failed_charset_shape"}:
            return "unsafe_identifier_shape"
        return "columnar_value_possible"
    return "label_only_no_value_nearby"


def analyze_load_identity_label_hits(artifact):
    records = []
    for page_number, rows in artifact_page_lines_with_context(artifact):
        for index, row in enumerate(rows):
            line = row["text"]
            same_line_match, label_only_match = _label_match(line)
            if not same_line_match and not label_only_match:
                continue
            label = (
                same_line_match.group("label").strip()
                if same_line_match
                else label_only_match.group("label").strip()
            )
            same_line_value = same_line_match.group("value").strip() if same_line_match else ""
            attempts = []
            accepted_method = ""
            accepted_value = ""
            first_rejection = ""
            raw_attempts = _window_attempts(rows, index, same_line_value=same_line_value)
            raw_attempts.append(("full_text_window", _full_text_window_value(artifact, label)))
            for method, value in raw_attempts:
                reason = identifier_value_rejection_reason(value)
                accepted = not reason
                attempts.append(
                    {
                        "method": method,
                        "candidate_value_shape": candidate_value_shape(value),
                        "accepted": accepted,
                        "rejection_reason": reason,
                    }
                )
                if accepted and not accepted_method:
                    accepted_method = method
                    accepted_value = value
                if reason and not first_rejection:
                    first_rejection = reason
            hit_type = _hit_type(
                accepted_method,
                bool(accepted_method),
                label,
                row["section_context"],
                first_rejection,
                attempts,
            )
            records.append(
                {
                    "page_number": page_number,
                    "line_index": index,
                    "label_text_shape": {
                        "normalized_label": normalized_label(label),
                        "raw_label_length": len(label),
                    },
                    "section_context": row["section_context"],
                    "line_window": _line_window_shape(rows, index),
                    "candidate_extraction_attempts": attempts,
                    "final_outcome": "emitted_candidate"
                    if accepted_method
                    else ("rejected_no_value" if not first_rejection else "rejected_shape"),
                    "hit_type": hit_type,
                    "accepted_method": accepted_method,
                    "_accepted_value": accepted_value,
                    "_label": label,
                    "_rejection_reason": first_rejection,
                }
            )
    return records


def summarize_load_identity_forensics(records, emitted_candidates=0):
    hit_types = Counter()
    rejections = Counter()
    method_attempts = Counter()
    method_successes = Counter()
    value_shapes = Counter()
    for record in records or []:
        hit_types[record.get("hit_type", "unknown")] += 1
        if record.get("_rejection_reason"):
            rejections[record["_rejection_reason"]] += 1
        for attempt in record.get("candidate_extraction_attempts", []) or []:
            method = attempt.get("method", "unknown")
            method_attempts[method] += 1
            if attempt.get("accepted"):
                method_successes[method] += 1
            shape = attempt.get("candidate_value_shape", {}) or {}
            if shape.get("has_digits"):
                value_shapes["has_digits"] += 1
            if shape.get("has_letters"):
                value_shapes["has_letters"] += 1
            if shape.get("looks_like_date"):
                value_shapes["looks_like_date"] += 1
            if shape.get("looks_like_money"):
                value_shapes["looks_like_money"] += 1
            if shape.get("looks_like_phone"):
                value_shapes["looks_like_phone"] += 1
            if shape.get("looks_like_address"):
                value_shapes["looks_like_address"] += 1
    return {
        "label_hits": len(records or []),
        "emitted_candidates": int(emitted_candidates or 0),
        "hit_type_counts": dict(hit_types.most_common()),
        "rejection_reason_counts": dict(rejections.most_common()),
        "method_attempt_counts": dict(method_attempts.most_common()),
        "method_success_counts": dict(method_successes.most_common()),
        "value_shape_counts": dict(value_shapes.most_common()),
        "docs_with_label_hits": 1 if records else 0,
        "docs_with_emitted_load_candidates": 1 if int(emitted_candidates or 0) > 0 else 0,
        "label_hit_records": [
            {key: value for key, value in record.items() if not key.startswith("_")}
            for record in records or []
        ],
    }
