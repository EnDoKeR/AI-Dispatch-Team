def average_score(loads):
    if not loads:
        return 0

    return round(
        sum(load.opportunity_score() for load in loads)
        / len(loads)
    )


def bucket_stats(loads):
    buckets = {
        "0-450": [],
        "450-700": [],
        "700-1300": [],
        "1300+": [],
    }

    for load in loads:
        buckets[load.bucket].append(load)

    result = {}

    for bucket_name, bucket_loads in buckets.items():
        qualified = [
            load
            for load in bucket_loads
            if load.is_qualified()
        ]

        good = [
            load
            for load in bucket_loads
            if load.is_good()
        ]

        clean_match = [
            load
            for load in bucket_loads
            if load.is_good()
            and load.driver_match_status == "MATCH"
        ]

        review_once = [
            load
            for load in bucket_loads
            if load.is_good()
            and load.driver_match_status == "REVIEW_ONCE"
        ]

        blocked = [
            load
            for load in bucket_loads
            if load.driver_match_status == "BLOCK"
        ]

        if bucket_loads:
            avg_rpm = round(
                sum(load.total_rpm for load in bucket_loads)
                / len(bucket_loads),
                2,
            )

            avg_rate = round(
                sum(load.rate for load in bucket_loads)
                / len(bucket_loads),
            )

        else:
            avg_rpm = 0
            avg_rate = 0

        result[bucket_name] = {
            "total_loads": len(bucket_loads),
            "qualified_loads": len(qualified),
            "good_loads": len(good),
            "clean_match_loads": len(clean_match),
            "review_once_loads": len(review_once),
            "blocked_loads": len(blocked),
            "avg_total_rpm": avg_rpm,
            "avg_rate": avg_rate,
            "avg_opportunity_score": average_score(bucket_loads),
            "avg_qualified_score": average_score(qualified),
            "avg_good_score": average_score(good),
            "avg_clean_match_score": average_score(clean_match),
            "avg_review_once_score": average_score(review_once),
        }

    return result


def fit_stats(loads):
    clean_matches = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "MATCH"
    ]

    review_once = [
        load
        for load in loads
        if load.is_good()
        and load.driver_match_status == "REVIEW_ONCE"
    ]

    blocked = [
        load
        for load in loads
        if load.driver_match_status == "BLOCK"
    ]

    qualified = [
        load
        for load in loads
        if load.is_qualified()
    ]

    good = [
        load
        for load in loads
        if load.is_good()
    ]

    if len(clean_matches) >= 3:
        driver_fit = "GOOD"
    elif len(clean_matches) >= 1:
        driver_fit = "WORKABLE"
    elif len(review_once) >= 3:
        driver_fit = "REVIEW_ONLY"
    elif len(review_once) >= 1:
        driver_fit = "WEAK_FIT"
    else:
        driver_fit = "NO_MATCH"

    return {
        "driver_fit": driver_fit,
        "clean_matches": len(clean_matches),
        "review_once": len(review_once),
        "blocked": len(blocked),
        "qualified": len(qualified),
        "good": len(good),
    }


def choose_best_bucket(stats):
    best_bucket = None
    best_score = -1

    for bucket, data in stats.items():
        score = (
            data["clean_match_loads"] * 5
            + data["good_loads"] * 3
            + data["qualified_loads"] * 2
            + data["avg_clean_match_score"] / 8
            + data["avg_good_score"] / 15
        )

        if score > best_score:
            best_score = score
            best_bucket = bucket

    return best_bucket


def market_recommendation(stats, fit):
    total_good = sum(
        data["good_loads"]
        for data in stats.values()
    )

    total_qualified = sum(
        data["qualified_loads"]
        for data in stats.values()
    )

    total_clean_matches = fit["clean_matches"]
    total_review_once = fit["review_once"]
    total_blocked = fit["blocked"]

    best_bucket = choose_best_bucket(stats)

    if total_good >= 6:
        market_activity = "GOOD"
    elif total_good >= 3:
        market_activity = "MEDIUM"
    elif total_qualified >= 2:
        market_activity = "WEAK"
    else:
        market_activity = "BAD"

    driver_fit = fit["driver_fit"]

    if driver_fit == "GOOD":
        action_status = "STRONG_MATCHES_AVAILABLE"
    elif driver_fit == "WORKABLE":
        action_status = "SOME_MATCHES_AVAILABLE"
    elif driver_fit == "REVIEW_ONLY":
        action_status = "REVIEW_ONLY"
    elif driver_fit == "WEAK_FIT":
        action_status = "WEAK_FIT"
    else:
        action_status = "NO_CLEAN_MATCHES"

    return {
        "market_activity": market_activity,
        "driver_fit": driver_fit,
        "action_status": action_status,
        "best_bucket": best_bucket,
        "total_good_loads": total_good,
        "total_qualified_loads": total_qualified,
        "total_clean_matches": total_clean_matches,
        "total_review_once": total_review_once,
        "total_blocked": total_blocked,

        # backwards compatibility for old telegram_notifier code
        "market_status": market_activity,
    }
