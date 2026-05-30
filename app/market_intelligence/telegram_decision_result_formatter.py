"""Output-only Telegram formatting for decision result summaries."""

REVIEW_REQUIRED = "REVIEW_REQUIRED"
MAX_ITEM_LENGTH = 160


def value_from(source, key, default=""):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def safe_text(value):
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()

    if len(text) > MAX_ITEM_LENGTH:
        return text[:MAX_ITEM_LENGTH].rstrip() + "..."

    return text


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    cleaned = []

    for item in values:
        text = safe_text(item)

        if text and text not in cleaned:
            cleaned.append(text)

    return cleaned


def result_recommendation(decision_result):
    return safe_text(
        value_from(
            decision_result,
            "recommendation",
            value_from(decision_result, "decision", REVIEW_REQUIRED),
        )
    ) or REVIEW_REQUIRED


def add_list_section(lines, title, values, empty_text="None reported"):
    lines.append(f"{title}:")
    items = safe_list(values)

    if not items:
        lines.append(f"- {empty_text}")
        return

    for item in items:
        lines.append(f"- {item}")


def format_decision_result_message(decision_result, heading="Dispatch Decision"):
    recommendation = result_recommendation(decision_result)
    confidence = safe_text(value_from(decision_result, "confidence", "UNKNOWN")) or "UNKNOWN"
    approval_required = bool(value_from(decision_result, "approval_required", False))
    missing_fields = safe_list(value_from(decision_result, "missing_fields", []))
    needs_check_fields = safe_list(value_from(decision_result, "needs_check_fields", []))
    low_confidence_fields = safe_list(
        value_from(decision_result, "low_confidence_fields", needs_check_fields)
    )

    lines = [
        safe_text(heading) or "Dispatch Decision",
        "",
        f"Recommendation: {recommendation}",
        f"Confidence: {confidence}",
        f"Approval required: {'yes' if approval_required else 'no'}",
        "",
    ]

    add_list_section(lines, "Missing critical fields", missing_fields)
    add_list_section(lines, "Low-confidence fields", low_confidence_fields)
    add_list_section(lines, "Needs-check fields", needs_check_fields)
    add_list_section(lines, "Risk flags", value_from(decision_result, "risk_flags", []))
    add_list_section(lines, "Rules fired", value_from(decision_result, "rules_fired", []))
    add_list_section(lines, "Reasons", value_from(decision_result, "reasons", []))

    if recommendation == REVIEW_REQUIRED or approval_required:
        lines.extend(
            [
                "",
                "Next human action:",
                "- Review missing and low-confidence fields before dispatch action.",
            ]
        )

    return "\n".join(lines).strip()
