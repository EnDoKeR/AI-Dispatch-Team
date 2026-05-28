RISKY_PAYMENT_TERMS = [
    "cash or zelle",
    "cash/zelle",
    "cashapp",
    "cash app",
    "zelle",
    "venmo",
]


def apply_payment_risk_rules(load, combined_text):
    if not any(term in combined_text for term in RISKY_PAYMENT_TERMS):
        return load

    load.is_blocked = True
    load.block_reasons.append(
        "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
    )

    return load
