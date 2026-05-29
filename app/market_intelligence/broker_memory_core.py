def normalize_mc(broker_mc):
    return str(broker_mc or "").strip()


def is_valid_mc(broker_mc):
    broker_mc = normalize_mc(broker_mc)

    if not broker_mc:
        return False

    if broker_mc.upper() == "NEEDS CHECK":
        return False

    if broker_mc.upper() == "NO MC":
        return False

    return True


def classify_broker_from_counts(feedback_counts, case_counts):
    bad_broker_count = feedback_counts.get("bad_broker", 0)
    rate_too_low_count = feedback_counts.get("rate_too_low", 0)
    covered_count = feedback_counts.get("covered", 0)
    booked_count = feedback_counts.get("booked", 0)
    sent_to_driver_count = feedback_counts.get("sent_to_driver", 0)
    ratecon_received_count = feedback_counts.get("ratecon_received", 0)
    called_broker_count = feedback_counts.get("called_broker", 0)

    total_cases = case_counts.get("total_cases", 0)
    rate_check_cases = case_counts.get("rate_check_cases", 0)
    load_opportunity_cases = case_counts.get("load_opportunity_cases", 0)
    telegram_alerts = case_counts.get("telegram_alerts", 0)

    reasons = []

    if bad_broker_count >= 2:
        reasons.append(f"bad_broker feedback {bad_broker_count}x")
        return {
            "status": "BAD_BROKER_REVIEW",
            "risk_level": "HIGH",
            "reasons": reasons,
        }

    if rate_too_low_count >= 2:
        reasons.append(f"rate_too_low feedback {rate_too_low_count}x")
        return {
            "status": "RATE_NEGOTIATION_REQUIRED",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    if covered_count >= 2:
        reasons.append(f"covered feedback {covered_count}x")
        return {
            "status": "WATCHLIST",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    if booked_count >= 1 or ratecon_received_count >= 1:
        if booked_count:
            reasons.append(f"booked feedback {booked_count}x")

        if ratecon_received_count:
            reasons.append(f"ratecon_received feedback {ratecon_received_count}x")

        return {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if sent_to_driver_count >= 2:
        reasons.append(f"sent_to_driver feedback {sent_to_driver_count}x")
        return {
            "status": "GOOD",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if called_broker_count >= 2 and rate_check_cases >= 1:
        reasons.append(f"called_broker feedback {called_broker_count}x on rate-check activity")
        return {
            "status": "WATCHLIST",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if total_cases >= 3 and telegram_alerts == 0:
        reasons.append(f"{total_cases} cases but no Telegram alerts")
        return {
            "status": "LOW_RELEVANCE",
            "risk_level": "LOW",
            "reasons": reasons,
        }

    if rate_check_cases >= 3 and load_opportunity_cases == 0:
        reasons.append(f"{rate_check_cases} rate-check cases and no load opportunities")
        return {
            "status": "RATE_NEGOTIATION_REQUIRED",
            "risk_level": "MEDIUM",
            "reasons": reasons,
        }

    return {
        "status": "UNKNOWN",
        "risk_level": "UNKNOWN",
        "reasons": [],
    }


def format_broker_memory_status(memory_status):
    status = memory_status.get("status", "UNKNOWN")
    risk_level = memory_status.get("risk_level", "UNKNOWN")
    reasons = memory_status.get("reasons", [])

    if reasons:
        reason_text = "; ".join(reasons)
        return f"{status} / {risk_level} — {reason_text}"

    return f"{status} / {risk_level}"
