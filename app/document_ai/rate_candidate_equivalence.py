"""Rate candidate equivalence helpers.

These helpers may compare candidate money amounts internally, but safe summaries
must expose counts and categories only.
"""

from decimal import Decimal, InvalidOperation
import re

from app.document_ai.rate_candidate_forensics import (
    RATE_CATEGORY_ACCESSORIAL,
    RATE_CATEGORY_AGREED_AMOUNT,
    RATE_CATEGORY_DEDUCTION,
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_LAYOVER,
    RATE_CATEGORY_LINEHAUL,
    RATE_CATEGORY_LUMPER,
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_PENALTY,
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CATEGORY_TOTAL_CHARGE,
    RATE_CATEGORY_TONU,
    RATE_CATEGORY_UNKNOWN_MONEY,
    classify_rate_candidate_category,
)
from app.document_ai.rate_conflict_audit import (
    RATE_EQUIVALENT_DIFFERENT_AMOUNT,
    RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT,
    RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT,
    RATE_EQUIVALENT_SAME_AMOUNT,
    RATE_EQUIVALENT_SAME_LABEL_DUPLICATE,
    RATE_EQUIVALENT_UNKNOWN,
)


_MAIN_RATE_CATEGORIES = {
    RATE_CATEGORY_MAIN_TOTAL_CARRIER_PAY,
    RATE_CATEGORY_AGREED_AMOUNT,
    RATE_CATEGORY_LINEHAUL,
    RATE_CATEGORY_TOTAL_CHARGE,
    RATE_CATEGORY_UNKNOWN_MONEY,
}

_ACCESSORIAL_CATEGORIES = {
    RATE_CATEGORY_ACCESSORIAL,
    RATE_CATEGORY_DETENTION,
    RATE_CATEGORY_LAYOVER,
    RATE_CATEGORY_LUMPER,
}

_PAYMENT_NOISE_CATEGORIES = {
    RATE_CATEGORY_QUICKPAY_DISCOUNT,
    RATE_CATEGORY_DEDUCTION,
    RATE_CATEGORY_PENALTY,
    RATE_CATEGORY_TERMS_AMOUNT,
    RATE_CATEGORY_TONU,
}


def _text(value):
    return str(value or "").strip()


def _token(value):
    return _text(value).lower().replace(" ", "_").replace("-", "_")


def normalize_money_amount_for_comparison(candidate):
    """Return a normalized internal amount key for candidate comparison.

    The returned key is for internal comparison only and must not be written to
    safe audit/report artifacts.
    """

    value = _text(
        (candidate or {}).get("normalized_value")
        or (candidate or {}).get("raw_value")
    )
    if not value:
        return ""
    cleaned = re.sub(r"[^0-9.\-]", "", value)
    if cleaned in {"", "-", ".", "-."}:
        return ""
    try:
        return str(Decimal(cleaned).quantize(Decimal("0.01")))
    except (InvalidOperation, ValueError):
        return ""


def _currency(candidate):
    currency = _token((candidate or {}).get("currency"))
    return currency or "usd"


def _category_family(category):
    if category in _MAIN_RATE_CATEGORIES:
        return "main_rate"
    if category in _ACCESSORIAL_CATEGORIES:
        return "accessorial"
    if category in _PAYMENT_NOISE_CATEGORIES:
        return "payment_noise"
    return "unknown_money"


def build_rate_candidate_fingerprint(candidate):
    category = classify_rate_candidate_category(candidate)
    return {
        "amount_key": normalize_money_amount_for_comparison(candidate),
        "currency": _currency(candidate),
        "category": category,
        "category_family": _category_family(category),
        "label": _token((candidate or {}).get("label"))
        or _token((candidate or {}).get("value_type")),
        "source": _token((candidate or {}).get("source")),
        "section": _token((candidate or {}).get("layout_section_role")),
    }


def group_equivalent_rate_candidates(candidates):
    groups_by_key = {}
    unknown_groups = []
    for index, candidate in enumerate(candidates or []):
        if not isinstance(candidate, dict):
            continue
        fingerprint = build_rate_candidate_fingerprint(candidate)
        amount_key = fingerprint.get("amount_key", "")
        if not amount_key:
            unknown_groups.append(
                {
                    "fingerprint": fingerprint,
                    "candidates": [candidate],
                    "original_indexes": [index],
                }
            )
            continue
        key = (
            amount_key,
            fingerprint.get("currency", ""),
            fingerprint.get("category_family", ""),
        )
        group = groups_by_key.setdefault(
            key,
            {
                "fingerprint": fingerprint,
                "candidates": [],
                "original_indexes": [],
            },
        )
        group["candidates"].append(candidate)
        group["original_indexes"].append(index)
    return list(groups_by_key.values()) + unknown_groups


def classify_rate_candidate_equivalence_group(group):
    candidates = [
        candidate for candidate in (group or {}).get("candidates", []) if isinstance(candidate, dict)
    ]
    if len(candidates) < 2:
        return RATE_EQUIVALENT_UNKNOWN
    fingerprints = [build_rate_candidate_fingerprint(candidate) for candidate in candidates]
    amount_keys = {item.get("amount_key", "") for item in fingerprints if item.get("amount_key", "")}
    if len(amount_keys) > 1:
        return RATE_EQUIVALENT_DIFFERENT_AMOUNT
    labels = {item.get("label", "") for item in fingerprints}
    sources = {item.get("source", "") for item in fingerprints}
    if len(labels) <= 1 and len(sources) <= 1:
        return RATE_EQUIVALENT_SAME_LABEL_DUPLICATE
    if len(labels) > 1:
        return RATE_EQUIVALENT_DIFFERENT_LABEL_SAME_AMOUNT
    if len(sources) > 1:
        return RATE_EQUIVALENT_DIFFERENT_SOURCE_SAME_AMOUNT
    return RATE_EQUIVALENT_SAME_AMOUNT


def summarize_rate_candidate_groups(groups):
    status_counts = {}
    equivalent_group_count = 0
    different_amount_group_count = 0
    main_rate_group_count = 0
    accessorial_group_count = 0

    for group in groups or []:
        status = classify_rate_candidate_equivalence_group(group)
        status_counts[status] = status_counts.get(status, 0) + 1
        fingerprint = (group or {}).get("fingerprint", {}) or {}
        family = fingerprint.get("category_family", "unknown_money")
        if status != RATE_EQUIVALENT_UNKNOWN:
            equivalent_group_count += 1
        if status == RATE_EQUIVALENT_DIFFERENT_AMOUNT:
            different_amount_group_count += 1
        if family == "main_rate":
            main_rate_group_count += 1
        if family == "accessorial":
            accessorial_group_count += 1

    return {
        "group_count": len(groups or []),
        "equivalent_group_count": equivalent_group_count,
        "different_amount_group_count": different_amount_group_count,
        "main_rate_group_count": main_rate_group_count,
        "accessorial_group_count": accessorial_group_count,
        "equivalence_status_counts": dict(sorted(status_counts.items())),
        "private_values_included": False,
        "raw_text_included": False,
        "money_values_included": False,
    }
