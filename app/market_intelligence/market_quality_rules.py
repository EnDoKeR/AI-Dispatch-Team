def apply_empty_miles_rule(load, max_empty):
    if max_empty and load.empty_miles and load.empty_miles > max_empty:
        load.is_too_far_empty = True
        load.is_review_once = True
        load.review_reasons.append(
            f"Empty miles {load.empty_miles} are above driver setting {max_empty}."
        )

    return load


def apply_rate_check_rule(load):
    if not load.rate:
        load.is_review_once = True
        load.review_reasons.append(
            "Rate is missing / posted as $0; dispatcher should check rate with broker."
        )

    return load


def apply_rpm_quality_rule(load, min_total_rpm):
    if min_total_rpm and load.total_rpm and load.total_rpm < min_total_rpm:
        load.is_low_rpm = True
        load.match_reasons.append(
            f"RPM ${load.total_rpm} is below preferred minimum ${min_total_rpm}."
        )

    return load


def apply_quality_rules(load, max_empty, min_total_rpm):
    apply_empty_miles_rule(load, max_empty)
    apply_rate_check_rule(load)
    apply_rpm_quality_rule(load, min_total_rpm)

    return load
