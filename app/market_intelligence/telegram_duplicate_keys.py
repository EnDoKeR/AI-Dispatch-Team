def normalize(value):
    return str(value).strip().lower()


def has_value(value):
    text = normalize(value)

    return text not in [
        "",
        "no id",
        "no_id",
        "needs check",
        "needs_check",
        "unknown",
        "none",
        "n/a",
        "na",
        "no mc",
    ]


def load_field(load, *field_names):
    for field_name in field_names:
        value = getattr(load, field_name, "")

        if has_value(value):
            return value

    return ""


def load_repost_identity_key(load):
    reference_id = load_field(load, "reference_id")

    if reference_id:
        return f"ref:{normalize(reference_id)}"

    broker_mc = load_field(load, "broker_mc")
    pickup_date = getattr(load, "pickup_date", "")
    pickup = getattr(load, "pickup", "")
    delivery = getattr(load, "delivery", "")

    if (
        has_value(broker_mc)
        and has_value(pickup)
        and has_value(delivery)
        and has_value(pickup_date)
    ):
        return "|".join(
            [
                f"broker_mc_lane_date:{normalize(broker_mc)}",
                normalize(pickup),
                normalize(delivery),
                normalize(pickup_date),
            ]
        )

    broker_name = load_field(load, "broker_name", "broker")
    rate = getattr(load, "rate", "")
    loaded_miles = getattr(load, "loaded_miles", "")

    if (
        has_value(broker_name)
        and has_value(pickup)
        and has_value(delivery)
        and has_value(pickup_date)
    ):
        return "|".join(
            [
                f"broker_lane_date_rate_miles:{normalize(broker_name)}",
                normalize(pickup),
                normalize(delivery),
                normalize(pickup_date),
                normalize(rate),
                normalize(loaded_miles),
            ]
        )

    weight = getattr(load, "weight", "")
    commodity = getattr(load, "commodity", "")

    return "|".join(
        [
            f"lane_date_rate_miles_weight_commodity:{normalize(pickup)}",
            normalize(delivery),
            normalize(pickup_date),
            normalize(rate),
            normalize(loaded_miles),
            normalize(weight),
            normalize(commodity),
        ]
    )


def load_update_signature(load):
    return "|".join(
        [
            "update_signature",
            normalize(getattr(load, "rate", "")),
            normalize(getattr(load, "loaded_miles", "")),
            normalize(getattr(load, "pickup_time", "")),
            normalize(getattr(load, "delivery_time", "")),
            normalize(getattr(load, "notes", "")),
            normalize(getattr(load, "weight", "")),
            normalize(getattr(load, "commodity", "")),
        ]
    )


def legacy_load_duplicate_key(load, driver_name=""):
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


def load_duplicate_key(load, driver_name=""):
    return "|".join(
        [
            normalize(driver_name),
            load_repost_identity_key(load),
        ]
    )


def load_duplicate_keys(load, driver_name=""):
    keys = [
        load_duplicate_key(load, driver_name=driver_name),
        legacy_load_duplicate_key(load, driver_name=driver_name),
    ]

    return list(dict.fromkeys(keys))


def sent_history_matches_load(sent_history, load, driver_name=""):
    return any(
        key in sent_history
        for key in load_duplicate_keys(load, driver_name=driver_name)
    )


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
