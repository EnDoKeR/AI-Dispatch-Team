def get_top_opportunities(loads, limit=5):
    good_loads = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "MATCH"
    ]

    sorted_loads = sorted(
        good_loads,
        key=lambda load: (
            load.opportunity_score(),
            load.rate,
            load.total_rpm,
            -load.empty_miles,
        ),
        reverse=True,
    )

    return sorted_loads[:limit]


def get_review_once_loads(loads, limit=5):
    review_loads = []

    for load in loads:
        if load.driver_match_status != "REVIEW_ONCE":
            continue

        is_rate_check = False

        for reason in getattr(load, "driver_match_notes", []):
            reason_text = str(reason or "").lower()

            if (
                "rate is missing" in reason_text
                or "posted as $0" in reason_text
                or "rate check" in reason_text
                or "check rate with broker" in reason_text
            ):
                is_rate_check = True
                break

        if load.is_good() or is_rate_check:
            review_loads.append(load)

    sorted_loads = sorted(
        review_loads,
        key=lambda load: (
            1 if any(
                "rate is missing" in str(reason or "").lower()
                or "posted as $0" in str(reason or "").lower()
                or "rate check" in str(reason or "").lower()
                for reason in getattr(load, "driver_match_notes", [])
            ) else 0,
            load.opportunity_score(),
            load.rate,
            load.total_rpm,
            -load.empty_miles,
        ),
        reverse=True,
    )

    return sorted_loads[:limit]
