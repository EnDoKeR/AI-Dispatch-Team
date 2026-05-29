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
