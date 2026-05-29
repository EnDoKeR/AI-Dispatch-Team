def normalize_driver_name(driver_name):
    return str(driver_name or "").strip()


def is_valid_driver_name(driver_name):
    driver_name = normalize_driver_name(driver_name)

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
            "sample_note": "50+ feedback/case signals available",
            "can_affect_decision": True,
        }

    if sample_size >= 25:
        return {
            "sample_quality": "DEVELOPING_PATTERN",
            "sample_note": "25-49 feedback/case signals available",
            "can_affect_decision": False,
        }

    if sample_size >= 10:
        return {
            "sample_quality": "EARLY_SIGNAL",
            "sample_note": "10-24 feedback/case signals available",
            "can_affect_decision": False,
        }

    return {
        "sample_quality": "INSUFFICIENT_SAMPLE",
        "sample_note": "Less than 10 feedback/case signals available",
        "can_affect_decision": False,
    }


def feedback_sample_size(feedback_counts):
    return sum(int(value or 0) for value in feedback_counts.values())


def classify_driver_from_counts(feedback_counts, case_counts):
    booked = feedback_counts.get("booked", 0)
    ratecon_received = feedback_counts.get("ratecon_received", 0)
    sent_to_driver = feedback_counts.get("sent_to_driver", 0)
    driver_rejected = feedback_counts.get("driver_rejected", 0)
    skipped = feedback_counts.get("skipped", 0)
    rate_too_low = feedback_counts.get("rate_too_low", 0)
    bad_broker = feedback_counts.get("bad_broker", 0)

    feedback_items = case_counts.get("feedback_items", 0)
    telegram_alerts = case_counts.get("telegram_alerts", 0)
    load_opportunity_cases = case_counts.get("load_opportunity_cases", 0)
    rate_check_cases = case_counts.get("rate_check_cases", 0)

    sample_size = max(
        feedback_sample_size(feedback_counts),
        int(feedback_items or 0),
    )
    sample_quality = get_sample_quality(sample_size)

    reasons = []

    base_result = {
        "sample_size": sample_size,
        "sample_quality": sample_quality["sample_quality"],
        "sample_note": sample_quality["sample_note"],
        "can_affect_decision": sample_quality["can_affect_decision"],
    }

    if booked >= 1 or ratecon_received >= 1:
        if booked:
            reasons.append(f"booked feedback {booked}x")

        if ratecon_received:
            reasons.append(f"ratecon_received feedback {ratecon_received}x")

        return {
            **base_result,
            "status": "STRONG_POSITIVE",
            "confidence": "MEDIUM" if sample_size < 50 else "HIGH",
            "reasons": reasons,
        }

    if sent_to_driver >= 2 and driver_rejected == 0:
        reasons.append(f"sent_to_driver feedback {sent_to_driver}x")

        return {
            **base_result,
            "status": "WEAK_POSITIVE",
            "confidence": "LOW" if sample_size < 50 else "MEDIUM",
            "reasons": reasons,
        }

    if driver_rejected >= 2:
        reasons.append(f"driver_rejected feedback {driver_rejected}x")

        return {
            **base_result,
            "status": "NEEDS_REVIEW",
            "confidence": "LOW" if sample_size < 50 else "MEDIUM",
            "reasons": reasons,
        }

    if skipped >= 2:
        reasons.append(f"skipped feedback {skipped}x")

        return {
            **base_result,
            "status": "NEEDS_REVIEW",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if rate_too_low >= 2:
        reasons.append(f"rate_too_low feedback {rate_too_low}x")

        return {
            **base_result,
            "status": "RATE_SENSITIVE",
            "confidence": "LOW" if sample_size < 50 else "MEDIUM",
            "reasons": reasons,
        }

    if bad_broker >= 1:
        reasons.append(f"bad_broker feedback {bad_broker}x, should stay broker-side")

        return {
            **base_result,
            "status": "INSUFFICIENT_DRIVER_DATA",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if telegram_alerts >= 5 and feedback_items == 0:
        reasons.append(f"{telegram_alerts} Telegram alerts but no feedback")

        return {
            **base_result,
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if load_opportunity_cases >= 3 and feedback_items == 0:
        reasons.append(f"{load_opportunity_cases} load opportunities but no feedback")

        return {
            **base_result,
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    if rate_check_cases >= 3 and feedback_items == 0:
        reasons.append(f"{rate_check_cases} rate-check cases but no feedback")

        return {
            **base_result,
            "status": "NEEDS_MORE_FEEDBACK",
            "confidence": "LOW",
            "reasons": reasons,
        }

    return {
        **base_result,
        "status": "INSUFFICIENT_DRIVER_DATA",
        "confidence": "LOW",
        "reasons": [],
    }


def format_driver_preference_status(preference_status):
    status = preference_status.get("status", "UNKNOWN")
    confidence = preference_status.get("confidence", "UNKNOWN")
    sample_quality = preference_status.get("sample_quality", "UNKNOWN")
    sample_size = preference_status.get("sample_size", 0)
    reasons = preference_status.get("reasons", [])

    base_text = f"{status} / {confidence} / {sample_quality} ({sample_size} signals)"

    if reasons:
        reason_text = "; ".join(reasons)
        return f"{base_text} — {reason_text}"

    return base_text
