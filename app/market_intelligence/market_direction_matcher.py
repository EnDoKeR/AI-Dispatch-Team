def apply_direction_match(load, search_request):
    if load.matches_target_city_radius(search_request):
        load.target_relation = "MATCH"
        load.match_reasons.append("Destination matches target city.")
        return load

    if load.delivery_matches_target(search_request):
        load.target_relation = "MATCH"
        load.match_reasons.append("Destination matches target state/region.")
        return load

    reason = load.off_target_review_reason(search_request)

    if load.should_block_off_target(search_request):
        load.target_relation = "MISMATCH"
        load.is_blocked = True
        load.block_reasons.append(
            f"Delivery does not match target direction: {getattr(search_request, 'target_direction', '')}."
        )
        return load

    if load.delivery_is_along_route(search_request):
        load.target_relation = "ALONG_ROUTE"
    else:
        load.target_relation = "OFF_TARGET_EXCEPTION"

    load.is_review_once = True

    if reason:
        load.review_reasons.append(reason)

    return load
