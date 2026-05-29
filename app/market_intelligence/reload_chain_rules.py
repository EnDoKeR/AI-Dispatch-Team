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


def is_wrong_direction_block(load):
    for note in load.driver_match_notes:
        if "Delivery does not match target direction" in note:
            return True

        if "Delivery does not match strict target" in note:
            return True

    return False
