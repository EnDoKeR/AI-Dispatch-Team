from statistics import mean, median

from app.market_intelligence.telegram_duplicate_keys import load_repost_identity_key


MILEAGE_BUCKETS = [
    "0-400",
    "400-700",
    "700-1300",
    "1300+",
]


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def positive_numbers(values):
    return [
        value
        for value in [to_number(item) for item in values]
        if value > 0
    ]


def rounded(value):
    if value == 0:
        return 0

    return round(value, 2)


def numeric_average(values):
    numbers = positive_numbers(values)

    if not numbers:
        return 0

    return rounded(mean(numbers))


def numeric_median(values):
    numbers = positive_numbers(values)

    if not numbers:
        return 0

    return rounded(median(numbers))


def numeric_quartiles(values):
    numbers = sorted(positive_numbers(values))

    if not numbers:
        return 0, 0

    if len(numbers) == 1:
        value = rounded(numbers[0])
        return value, value

    midpoint = len(numbers) // 2

    if len(numbers) % 2 == 0:
        lower_half = numbers[:midpoint]
        upper_half = numbers[midpoint:]
    else:
        lower_half = numbers[:midpoint]
        upper_half = numbers[midpoint + 1:]

    return rounded(median(lower_half)), rounded(median(upper_half))


def mileage_for_load(load):
    loaded_miles = to_number(getattr(load, "loaded_miles", 0))

    if loaded_miles > 0:
        return loaded_miles

    return to_number(getattr(load, "total_miles", 0))


def mileage_bucket(load):
    miles = mileage_for_load(load)

    if miles <= 400:
        return "0-400"

    if miles <= 700:
        return "400-700"

    if miles <= 1300:
        return "700-1300"

    return "1300+"


def load_status(load):
    return str(getattr(load, "driver_match_status", "") or "").upper()


def is_qualified(load):
    qualified = getattr(load, "is_qualified", None)

    if callable(qualified):
        return bool(qualified())

    return load_status(load) in ["MATCH", "REVIEW_ONCE"]


def load_review_category(load):
    review_category = getattr(load, "review_category", "")

    if callable(review_category):
        return str(review_category() or "").upper()

    return str(review_category or getattr(load, "category", "") or "").upper()


def is_rate_check(load):
    if load_review_category(load) == "RATE CHECK":
        return True

    return to_number(getattr(load, "rate", 0)) <= 0


def gross_value(load):
    gross = to_number(getattr(load, "gross", 0))

    if gross > 0:
        return gross

    return to_number(getattr(load, "rate", 0))


def classify_market_status(load_count, valid_rpm_count, median_rpm):
    if load_count < 3 or valid_rpm_count < 3:
        return "LOW_DATA"

    if median_rpm >= 3.0:
        return "STRONG_MARKET"

    if median_rpm < 2.0:
        return "SOFT_MARKET"

    return "NORMAL_MARKET"


def summarize_loads(loads):
    rpm_values = [getattr(load, "total_rpm", 0) for load in loads]
    rate_values = [getattr(load, "rate", 0) for load in loads]
    gross_values = [gross_value(load) for load in loads]

    bottom_quartile_rpm, top_quartile_rpm = numeric_quartiles(rpm_values)
    median_rpm = numeric_median(rpm_values)
    valid_rpm_count = len(positive_numbers(rpm_values))

    clean_match_count = len([
        load for load in loads if load_status(load) == "MATCH"
    ])
    review_once_count = len([
        load for load in loads if load_status(load) == "REVIEW_ONCE"
    ])
    blocked_count = len([
        load for load in loads if load_status(load) == "BLOCK"
    ])

    return {
        "load_count": len(loads),
        "qualified_count": len([
            load for load in loads if is_qualified(load)
        ]),
        "clean_match_count": clean_match_count,
        "review_once_count": review_once_count,
        "blocked_count": blocked_count,
        "rate_check_count": len([
            load for load in loads if is_rate_check(load)
        ]),
        "avg_rpm": numeric_average(rpm_values),
        "median_rpm": median_rpm,
        "avg_rate": numeric_average(rate_values),
        "median_rate": numeric_median(rate_values),
        "avg_gross": numeric_average(gross_values),
        "median_gross": numeric_median(gross_values),
        "top_quartile_rpm": top_quartile_rpm,
        "bottom_quartile_rpm": bottom_quartile_rpm,
        "market_status": classify_market_status(
            len(loads),
            valid_rpm_count,
            median_rpm,
        ),
    }


def bucketed_stats(loads):
    buckets = {bucket: [] for bucket in MILEAGE_BUCKETS}

    for load in loads:
        buckets[mileage_bucket(load)].append(load)

    return {
        bucket: summarize_loads(bucket_loads)
        for bucket, bucket_loads in buckets.items()
    }


def equipment_view(load):
    equipment_text = (
        f"{getattr(load, 'posted_trailer_type', '')} "
        f"{getattr(load, 'equipment', '')}"
    ).strip().lower()

    if "conestoga" in equipment_text or "stoga" in equipment_text:
        return "conestoga"

    if "flatbed" in equipment_text or equipment_text == "flat" or " flat" in equipment_text:
        return "flatbed"

    return "other"


def equipment_view_stats(loads):
    return {
        "flatbed": summarize_with_buckets([
            load for load in loads if equipment_view(load) == "flatbed"
        ]),
        "conestoga": summarize_with_buckets([
            load for load in loads if equipment_view(load) == "conestoga"
        ]),
    }


def dedupe_loads(loads):
    deduped_loads = []
    seen_keys = set()

    for load in loads:
        key = load_repost_identity_key(load)

        if key in seen_keys:
            continue

        seen_keys.add(key)
        deduped_loads.append(load)

    return deduped_loads


def summarize_with_buckets(loads):
    summary = summarize_loads(loads)
    summary["buckets"] = bucketed_stats(loads)
    return summary


def build_market_baseline(loads):
    source_loads = list(loads)
    deduped_loads = dedupe_loads(source_loads)

    baseline = summarize_with_buckets(deduped_loads)
    baseline["source_load_count"] = len(source_loads)
    baseline["equipment_views"] = equipment_view_stats(deduped_loads)

    return baseline
