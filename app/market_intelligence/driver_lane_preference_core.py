POSITIVE_FEEDBACK = {
    "booked",
    "ratecon_received",
    "sent_to_driver",
}

RATE_FEEDBACK = {
    "rate_too_low",
}

BROKER_FEEDBACK = {
    "bad_broker",
    "called_broker",
}

MARKET_FEEDBACK = {
    "covered",
}

NEGATIVE_OR_UNCLEAR_FEEDBACK = {
    "skipped",
    "driver_rejected",
    "not_interested",
    "other",
}


def normalize_text(value):
    return str(value or "").strip()


def normalize_location(value):
    return normalize_text(value).lower()


def is_valid_driver_name(driver_name):
    driver_name = normalize_text(driver_name)

    if not driver_name:
        return False

    if driver_name.upper() in ["UNKNOWN", "NEEDS CHECK", "NONE"]:
        return False

    return True


def get_sample_quality(sample_size):
    sample_size = int(sample_size or 0)

    if sample_size >= 50:
        return {
            "sample_quality": "RELIABLE_PATTERN",
            "sample_note": "50+ lane feedback signals available",
            "can_affect_decision": True,
        }

    if sample_size >= 25:
        return {
            "sample_quality": "DEVELOPING_PATTERN",
            "sample_note": "25-49 lane feedback signals available",
            "can_affect_decision": False,
        }

    if sample_size >= 10:
        return {
            "sample_quality": "EARLY_SIGNAL",
            "sample_note": "10-24 lane feedback signals available",
            "can_affect_decision": False,
        }

    return {
        "sample_quality": "INSUFFICIENT_SAMPLE",
        "sample_note": "Less than 10 lane feedback signals available",
        "can_affect_decision": False,
    }


def lane_sample_size(feedback_counts):
    return sum(int(value or 0) for value in feedback_counts.values())


def average(values):
    if not values:
        return 0

    return sum(values) / len(values)


def classify_lane_signal(feedback_counts):
    positive_count = sum(feedback_counts.get(item, 0) for item in POSITIVE_FEEDBACK)
    rate_count = sum(feedback_counts.get(item, 0) for item in RATE_FEEDBACK)
    broker_count = sum(feedback_counts.get(item, 0) for item in BROKER_FEEDBACK)
    market_count = sum(feedback_counts.get(item, 0) for item in MARKET_FEEDBACK)
    negative_count = sum(
        feedback_counts.get(item, 0)
        for item in NEGATIVE_OR_UNCLEAR_FEEDBACK
    )

    sample_size = lane_sample_size(feedback_counts)
    sample_quality = get_sample_quality(sample_size)

    reasons = []

    base_result = {
        "sample_size": sample_size,
        "sample_quality": sample_quality["sample_quality"],
        "sample_note": sample_quality["sample_note"],
        "can_affect_decision": sample_quality["can_affect_decision"],
    }

    if positive_count >= 2 and rate_count >= 1:
        reasons.append(f"positive feedback {positive_count}x")
        reasons.append(f"rate feedback {rate_count}x")

        return {
            **base_result,
            "status": "POSITIVE_LANE_WITH_RATE_SENSITIVITY",
            "confidence": "MEDIUM" if sample_size < 50 else "HIGH",
            "reasons": reasons,
        }

    if positive_count >= 2:
        reasons.append(f"positive feedback {positive_count}x")

        return {
            **base_result,
            "status": "POSITIVE_LANE",
            "confidence": "MEDIUM" if sample_size < 50 else "HIGH",
            "reasons": reasons,
        }

    if broker_count >= 2:
        reasons.append(f"broker/workflow feedback {broker_count}x")

        return {
            **base_result,
            "status": "BROKER_ISSUE_NOT_DRIVER_PREFERENCE",
            "confidence": "MEDIUM",
            "reasons": reasons,
        }

    if rate_count >= 2:
        reasons.append(f"rate feedback {rate_count}x")

        return {
            **base_result,
            "status": "RATE_SENSITIVE_LANE",
            "confidence": "LOW" if sample_size < 50 else "MEDIUM",
            "reasons": reasons,
        }

    if market_count >= 1 and positive_count == 0:
        reasons.append(f"market timing feedback {market_count}x")

        return {
            **base_result,
            "status": "MARKET_TIMING_SIGNAL",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if negative_count >= 2:
        reasons.append(f"negative/unclear feedback {negative_count}x")

        return {
            **base_result,
            "status": "NEEDS_DRIVER_OR_DISPATCH_REVIEW",
            "confidence": "LOW",
            "reasons": reasons,
        }

    return {
        **base_result,
        "status": "INSUFFICIENT_LANE_DATA",
        "confidence": "LOW",
        "reasons": [],
    }


def format_lane_preference_status(classification):
    status = classification.get("status", "UNKNOWN")
    confidence = classification.get("confidence", "UNKNOWN")
    sample_quality = classification.get("sample_quality", "UNKNOWN")
    sample_size = classification.get("sample_size", 0)
    reasons = classification.get("reasons", [])

    base_text = f"{status} / {confidence} / {sample_quality} ({sample_size} signals)"

    if reasons:
        return f"{base_text} — {'; '.join(reasons)}"

    return base_text


def format_driver_lane_preference_status(preference_status):
    status = preference_status.get("status", "UNKNOWN")
    confidence = preference_status.get("confidence", "UNKNOWN")
    sample_quality = preference_status.get("sample_quality", "UNKNOWN")
    sample_size = preference_status.get("sample_size", 0)
    reasons = preference_status.get("reasons", [])

    base_text = f"{status} / {confidence} / {sample_quality} ({sample_size} signals)"

    if reasons:
        return f"{base_text} — {'; '.join(reasons)}"

    return base_text
