RISKY_PAYMENT_TERMS = [
    "cash or zelle",
    "zelle or cash",
    "cash/zelle",
    "cashapp",
    "cash app",
    "zelle",
    "venmo",
    "cash on delivery",
]

QUICKPAY_REVIEW_TERMS = [
    "quickpay",
    "quick pay",
]


def apply_payment_risk_rules(load, combined_text):
    if any(term in combined_text for term in RISKY_PAYMENT_TERMS):
        load.is_blocked = True
        load.block_reasons.append(
            "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
        )
        return load

    if any(term in combined_text for term in QUICKPAY_REVIEW_TERMS):
        load.is_review_once = True
        load.review_reasons.append(
            "QuickPay payment language detected; check broker MC before buying."
        )

    return load
