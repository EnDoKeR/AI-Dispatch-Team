def apply_tracking_requirement(load, search_request, combined_text):
    tracking_required = (
        "tracking required" in combined_text
        or "macro point" in combined_text
        or "macropoint" in combined_text
    )

    if not tracking_required:
        return load

    if getattr(search_request, "driver_tracking_ok", True):
        load.match_reasons.append(
            "Tracking is accepted by driver profile."
        )
        return load

    load.is_blocked = True
    load.block_reasons.append(
        "Tracking required, but driver profile says tracking is not accepted."
    )

    return load
