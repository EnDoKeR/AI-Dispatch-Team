STRONG_RELOAD = [
    "IL",
    "OH",
    "IN",
    "PA",
    "TX",
    "GA",
    "NC",
    "SC",
]

AVERAGE_RELOAD = [
    "FL",
    "TN",
    "KY",
    "MO",
    "AR",
    "AL",
]

WEAK_RELOAD = [
    "MT",
    "ND",
    "SD",
    "WY",
    "ID",
    "NM",
]


def evaluate_reload(destination):
    destination = destination.upper()

    for state in STRONG_RELOAD:
        if state in destination:
            return 85, "STRONG"

    for state in AVERAGE_RELOAD:
        if state in destination:
            return 65, "AVERAGE"

    for state in WEAK_RELOAD:
        if state in destination:
            return 25, "WEAK"

    return 50, "UNKNOWN"


def adjust_score(final_score, reload_score):
    try:
        final_score = float(final_score)
        reload_score = float(reload_score)

        adjusted = final_score * 0.75 + reload_score * 0.25

        return round(adjusted)

    except:
        return final_score


def adjusted_decision(adjusted_score):
    try:
        adjusted_score = int(adjusted_score)

        if adjusted_score >= 80:
            return "BOOK"

        if adjusted_score >= 60:
            return "REVIEW"

        return "PASS"

    except:
        return "REVIEW"