def score_rpm(rpm):
    try:
        rpm = float(rpm)

        if rpm >= 4.0:
            return 95

        if rpm >= 3.0:
            return 80

        if rpm >= 2.5:
            return 60

        if rpm >= 2.0:
            return 45

        return 25

    except:
        return 50


def calculate_final_score(rpm_score, zone_score, broker_score):
    try:
        rpm_score = float(rpm_score)
        zone_score = float(zone_score)
        broker_score = float(broker_score)

        final_score = (
            rpm_score * 0.4
            + zone_score * 0.3
            + broker_score * 0.3
        )

        return round(final_score)

    except:
        return 50


def final_decision(final_score, broker_status):
    if broker_status == "BLOCK":
        return "PASS"

    try:
        final_score = int(final_score)

        if final_score >= 80:
            return "BOOK"

        if final_score >= 60:
            return "REVIEW"

        return "PASS"

    except:
        return "REVIEW"
