"""Conservative redaction helpers for private template pattern collection."""

import re


MONEY_RE = re.compile(r"(?i)(?:USD\s*)?\$?\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b")
DATE_RE = re.compile(
    r"(?i)\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})\b"
)
TIME_RE = re.compile(r"(?i)\b\d{1,2}:\d{2}\s*(?:AM|PM)?(?:\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM)?)?\b")
MC_RE = re.compile(r"(?i)\bMC\s*#?\s*\d{4,8}\b")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
WEIGHT_RE = re.compile(r"(?i)\b\d{2,6}\s*(?:lbs?|pounds)\b")

REFERENCE_LABELS = (
    "load #",
    "load no",
    "load number",
    "order #",
    "order number",
    "shipment #",
    "po number",
    "po #",
    "bol number",
    "bol #",
    "pickup #",
    "delivery #",
    "appointment #",
    "customer ref",
    "reference",
)

COMPANY_LABELS = (
    "broker",
    "carrier",
    "carrier name",
    "logistics company",
    "rate confirmation from",
    "dispatch contact",
)

LOCATION_LABELS = (
    "pickup",
    "delivery",
    "shipper",
    "consignee",
    "origin",
    "destination",
    "address",
)


def _replace_after_label(text, labels, placeholder, stop_at_comma=True):
    result = str(text or "")
    terminator = r"\n|;,"
    if not stop_at_comma:
        terminator = r"\n|;"

    for label in sorted(labels, key=len, reverse=True):
        separator = r"\s*[:#-]?\s*" if label.strip().endswith("#") else r"\s*[:#-]\s*"
        pattern = re.compile(rf"(?i)\b({re.escape(label)}){separator}([^{terminator}]+)")

        def repl(match):
            return f"{match.group(1)}: {placeholder}"

        result = pattern.sub(repl, result)
    return result


def redact_phone_email(text):
    redacted = EMAIL_RE.sub("<CONTACT>", str(text or ""))
    return PHONE_RE.sub("<CONTACT>", redacted)


def redact_mc_numbers(text):
    return MC_RE.sub("<MC>", str(text or ""))


def redact_money(text):
    value = str(text or "")
    value = re.sub(r"(?i)(?<=rate: )USD\s*\$?\s*[\d,]+(?:\.\d{2})?", "<MONEY>", value)
    value = re.sub(r"(?i)(?<=pay: )USD\s*\$?\s*[\d,]+(?:\.\d{2})?", "<MONEY>", value)
    value = re.sub(r"\$\s*[\d,]+(?:\.\d{2})?", "<MONEY>", value)
    return value


def redact_dates(text):
    return DATE_RE.sub("<DATE>", str(text or ""))


def redact_times(text):
    return TIME_RE.sub("<TIME>", str(text or ""))


def redact_reference_like_values(text):
    return _replace_after_label(text, REFERENCE_LABELS, "<REF>")


def redact_company_like_fragments(text):
    return _replace_after_label(text, COMPANY_LABELS, "<COMPANY>")


def redact_city_state_like_fragments(text):
    return _replace_after_label(
        text,
        LOCATION_LABELS,
        "<CITY_STATE_OR_LOCATION>",
        stop_at_comma=False,
    )


def redact_weight(text):
    return WEIGHT_RE.sub("<WEIGHT>", str(text or ""))


def redact_line_for_pattern_collection(text):
    """Redact a line while preserving safe generic labels."""
    redacted = str(text or "")
    redacted = redact_phone_email(redacted)
    redacted = redact_mc_numbers(redacted)
    redacted = redact_reference_like_values(redacted)
    redacted = redact_company_like_fragments(redacted)
    redacted = redact_city_state_like_fragments(redacted)
    redacted = redact_money(redacted)
    redacted = redact_dates(redacted)
    redacted = redact_times(redacted)
    redacted = redact_weight(redacted)
    return redacted.strip()
