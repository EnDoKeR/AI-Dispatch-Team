def normalize(value):
    return str(value).strip().lower()


def load_duplicate_key(load, driver_name=""):
    broker = getattr(load, "broker", "")
    pickup_date = getattr(load, "pickup_date", "")

    key_parts = [
        normalize(driver_name),
        normalize(broker),
        normalize(load.pickup),
        normalize(load.delivery),
        normalize(load.rate),
        normalize(load.loaded_miles),
        normalize(pickup_date),
    ]

    return "|".join(key_parts)


def market_summary_key(
    stats,
    recommendation,
    top_opportunities,
    search_location,
    search_request,
):
    best_load_key = "no_best_load"

    if top_opportunities:
        best_load_key = load_duplicate_key(
            top_opportunities[0],
            driver_name=search_request.driver_name,
        )

    key_parts = [
        normalize(search_request.driver_name),
        normalize(search_request.current_location),
        normalize(search_request.available_time),
        normalize(search_request.equipment),
        normalize(search_request.target_direction),
        normalize(search_location),
        normalize(recommendation["market_status"]),
        normalize(recommendation["best_bucket"]),
        normalize(recommendation["total_good_loads"]),
        normalize(recommendation["total_qualified_loads"]),
        normalize(best_load_key),
    ]

    return "|".join(key_parts)


def search_health_key(search_request):
    return "|".join(
        [
            normalize(search_request.driver_name),
            normalize(search_request.current_location),
            normalize(search_request.available_time),
            normalize(search_request.equipment),
            normalize(search_request.target_direction),
            normalize(search_request.min_total_rpm),
            normalize(search_request.max_weight),
        ]
    )


def remove_duplicates(loads, search_request):
    unique_loads = []
    seen_keys = set()

    for load in loads:
        key = load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        )

        if key in seen_keys:
            print(
                f"Duplicate skipped in current run for {search_request.driver_name}: "
                f"{load.pickup} -> {load.delivery}"
            )
            continue

        seen_keys.add(key)
        unique_loads.append(load)

    return unique_loads
