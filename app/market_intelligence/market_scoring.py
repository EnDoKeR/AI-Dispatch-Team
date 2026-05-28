def is_qualified(load):
    if load.driver_match_status == "BLOCK":
        return False

    if not load.rate:
        return False

    if not load.loaded_miles and not load.total_miles:
        return False

    return True


def is_good(load):
    if not is_qualified(load):
        return False

    if load.rate >= 3000:
        return True

    if load.total_rpm >= 3:
        return True

    return False


def opportunity_score(load):
    score = 0

    if load.rate >= 5000:
        score += 30
    elif load.rate >= 3500:
        score += 25
    elif load.rate >= 2500:
        score += 18
    elif load.rate >= 1500:
        score += 10
    else:
        score += 5

    if load.total_rpm >= 4:
        score += 30
    elif load.total_rpm >= 3:
        score += 25
    elif load.total_rpm >= 2.5:
        score += 18
    elif load.total_rpm >= 2:
        score += 10
    else:
        score += 3

    if load.empty_miles <= 50:
        score += 15
    elif load.empty_miles <= 150:
        score += 10
    elif load.empty_miles <= 250:
        score += 5

    if load.driver_match_status == "MATCH":
        score += 20
    elif load.driver_match_status == "REVIEW_ONCE":
        score += 8
    elif load.driver_match_status == "BLOCK":
        score -= 50

    if load.delivery_zone and "GOOD" in str(load.delivery_zone).upper():
        score += 5

    return max(0, round(score))


def priority(load):
    score = opportunity_score(load)

    if load.driver_match_status == "BLOCK":
        return "BLOCK"

    if score >= 90:
        return "HIGH"

    if score >= 75:
        return "MEDIUM"

    return "LOW"


def suggested_action(load):
    if load.driver_match_status == "BLOCK":
        return "DO NOT SEND"

    if load.driver_match_status == "REVIEW_ONCE":
        return "REVIEW ONCE"

    if opportunity_score(load) >= 85:
        return "CALL NOW + EMAIL BACKUP"

    if opportunity_score(load) >= 75:
        return "CALL IF AVAILABLE"

    return "MONITOR"


def reject_reasons(load):
    if hasattr(load, "block_reasons") and load.block_reasons:
        return load.block_reasons

    return []


def opportunity_reason(load):
    reasons = []

    if load.rate >= 5000:
        reasons.append("Strong gross")
    elif load.rate >= 3000:
        reasons.append("Good gross")

    if load.total_rpm >= 4:
        reasons.append("Excellent RPM")
    elif load.total_rpm >= 3:
        reasons.append("Good RPM")

    if load.empty_miles <= 50:
        reasons.append("Low empty miles")
    elif load.empty_miles <= 150:
        reasons.append("Acceptable empty miles")

    if load.driver_match_status == "MATCH":
        reasons.append("Matches driver target")
    elif load.driver_match_status == "REVIEW_ONCE":
        reasons.append("Needs dispatcher review")

    if load.delivery_zone and "GOOD" in str(load.delivery_zone).upper():
        reasons.append("Good reload area")

    if not reasons:
        reasons.append("Potential opportunity based on current filters")

    return ", ".join(reasons)
