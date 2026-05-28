from app.market_intelligence.broker_memory_rules import get_broker_memory_status


INVALID_BROKER_MC_VALUES = [
    "NEEDS CHECK",
    "NO MC",
    "UNKNOWN",
    "NONE",
]


def apply_broker_memory(load):
    broker_mc = str(getattr(load, "broker_mc", "") or "").strip()

    if not broker_mc:
        return load

    if broker_mc.upper() in INVALID_BROKER_MC_VALUES:
        return load

    broker_memory_status = get_broker_memory_status(broker_mc)
    broker_memory_name = broker_memory_status.get("status", "UNKNOWN")
    broker_memory_risk = broker_memory_status.get("risk_level", "UNKNOWN")
    broker_memory_reasons = broker_memory_status.get("reasons", [])

    if broker_memory_name == "BAD_BROKER_REVIEW":
        load.is_review_once = True

        reason_text = "Broker memory requires review"

        if broker_memory_reasons:
            reason_text += f": {'; '.join(broker_memory_reasons)}"

        load.review_reasons.append(
            f"{reason_text}. Risk: {broker_memory_risk}."
        )

    elif broker_memory_name == "RATE_NEGOTIATION_REQUIRED":
        load.is_review_once = True

        reason_text = "Broker memory shows rate negotiation risk"

        if broker_memory_reasons:
            reason_text += f": {'; '.join(broker_memory_reasons)}"

        load.review_reasons.append(
            f"{reason_text}. Risk: {broker_memory_risk}."
        )

    elif broker_memory_name == "WATCHLIST":
        load.is_review_once = True

        reason_text = "Broker memory watchlist"

        if broker_memory_reasons:
            reason_text += f": {'; '.join(broker_memory_reasons)}"

        load.review_reasons.append(
            f"{reason_text}. Risk: {broker_memory_risk}."
        )

    elif broker_memory_name == "GOOD":
        if broker_memory_reasons:
            load.match_reasons.append(
                f"Broker memory positive signal: {'; '.join(broker_memory_reasons)}."
            )

    return load
