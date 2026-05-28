def load_identity(load):
    reference_id = getattr(load, "reference_id", "")

    if reference_id:
        return str(reference_id).strip().lower()

    return "|".join(
        [
            str(load.pickup).strip().lower(),
            str(load.delivery).strip().lower(),
            str(load.rate).strip().lower(),
            str(load.loaded_miles).strip().lower(),
            str(load.weight).strip().lower(),
        ]
    )


def chain_identity(first_load, reload_load, search_request):
    return "|".join(
        [
            str(search_request.driver_name).strip().lower(),
            load_identity(first_load),
            load_identity(reload_load),
        ]
    )


def is_same_load(load_a, load_b):
    return load_identity(load_a) == load_identity(load_b)


def is_strong_first_load(load):
    if load.is_od:
        return False

    if load.is_overweight:
        return False

    if load.weight > 46000:
        return False

    if load.broker_status == "NO BUY":
        return False

    if load.rate < 3000:
        return False

    if load.total_rpm < 3.0:
        return False

    if load.empty_miles > 150:
        return False

    return True


def is_good_reload_load(load, search_request):
    if load.is_od:
        return False

    if load.is_overweight:
        return False

    if load.weight > search_request.max_weight + 3000:
        return False

    if load.broker_status == "NO BUY":
        return False

    if load.rate < 2000:
        return False

    if load.total_rpm < search_request.min_total_rpm:
        return False

    if not load.matches_target_state_or_region(search_request):
        if not load.matches_target_city_radius(search_request):
            return False

    return True


def city_state_key(location):
    text = str(location).strip()

    if "," not in text:
        return text

    city = text.split(",")[0].strip()
    state = text.split(",")[-1].strip().split()[0]

    return f"{city}, {state}"


def same_state(location_a, location_b):
    if "," not in str(location_a) or "," not in str(location_b):
        return False

    state_a = str(location_a).split(",")[-1].strip().split()[0].upper()
    state_b = str(location_b).split(",")[-1].strip().split()[0].upper()

    return state_a == state_b


def pickup_near_first_delivery(first_load, reload_load, max_miles=175):
    first_delivery = city_state_key(first_load.delivery)
    reload_pickup = city_state_key(reload_load.pickup)

    distance = first_load.distance_between_known_cities(
        first_delivery,
        reload_pickup,
    )

    if distance is not None:
        return distance <= max_miles

    return same_state(first_load.delivery, reload_load.pickup)


def is_wrong_direction_block(load):
    for note in load.driver_match_notes:
        if "Delivery does not match target direction" in note:
            return True

        if "Delivery does not match strict target" in note:
            return True

    return False


def build_chain_score(first_load, reload_load):
    total_gross = first_load.rate + reload_load.rate
    total_miles = first_load.total_miles + reload_load.total_miles

    if total_miles == 0:
        total_rpm = 0
    else:
        total_rpm = round(total_gross / total_miles, 2)

    score = 0

    if total_rpm >= 3.0:
        score += 40
    elif total_rpm >= 2.5:
        score += 25

    if total_gross >= 6500:
        score += 30
    elif total_gross >= 5000:
        score += 20

    if first_load.empty_miles <= 100:
        score += 15

    if reload_load.empty_miles <= 150:
        score += 15

    return {
        "total_gross": total_gross,
        "total_miles": total_miles,
        "total_rpm": total_rpm,
        "chain_score": score,
    }


def build_chain_candidates(loads, search_request, limit=5):
    candidates = []
    seen_first_loads = set()
    seen_chains = set()

    for first_load in loads:
        first_key = load_identity(first_load)

        if first_key in seen_first_loads:
            continue

        if not is_wrong_direction_block(first_load):
            continue

        if not is_strong_first_load(first_load):
            continue

        best_reload = None
        best_chain_data = None

        for reload_load in loads:
            if is_same_load(first_load, reload_load):
                continue

            if not pickup_near_first_delivery(first_load, reload_load):
                continue

            if not is_good_reload_load(reload_load, search_request):
                continue

            chain_data = build_chain_score(first_load, reload_load)

            if best_chain_data is None:
                best_reload = reload_load
                best_chain_data = chain_data
                continue

            if chain_data["chain_score"] > best_chain_data["chain_score"]:
                best_reload = reload_load
                best_chain_data = chain_data

        if best_reload:
            chain_key = chain_identity(
                first_load,
                best_reload,
                search_request,
            )

            if chain_key in seen_chains:
                continue

            seen_first_loads.add(first_key)
            seen_chains.add(chain_key)

            candidates.append(
                {
                    "first_load": first_load,
                    "reload_load": best_reload,
                    "chain_data": best_chain_data,
                }
            )

    candidates = sorted(
        candidates,
        key=lambda item: (
            item["chain_data"]["chain_score"],
            item["chain_data"]["total_gross"],
            item["chain_data"]["total_rpm"],
        ),
        reverse=True,
    )

    return candidates[:limit]
