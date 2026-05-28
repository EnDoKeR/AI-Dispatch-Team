def prepare_route_fallback(loads, search_request):
    mode = getattr(search_request, "target_direction_mode", "SOFT")

    if mode != "TARGET_THEN_ROUTE":
        search_request.route_fallback_active = False
        return search_request

    direct_target_loads = []

    for load in loads:
        if load.matches_target_city_radius(search_request):
            direct_target_loads.append(load)
            continue

        if load.matches_target_state_or_region(search_request):
            direct_target_loads.append(load)

    if direct_target_loads:
        search_request.route_fallback_active = False
        print(
            f"Direct target loads found for {search_request.driver_name}: "
            f"{len(direct_target_loads)}. Route fallback disabled."
        )
    else:
        search_request.route_fallback_active = True
        print(
            f"No direct target loads found for {search_request.driver_name}. "
            f"Route fallback enabled."
        )

    return search_request
