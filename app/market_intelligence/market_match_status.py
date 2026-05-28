def finalize_driver_match(load):
    if load.is_blocked:
        load.driver_fit_status = "BLOCKED"
        load.driver_match_status = "BLOCK"
        load.driver_match_notes = load.block_reasons
        return load

    if load.is_review_once:
        load.driver_fit_status = "REVIEW_ONCE"
        load.driver_match_status = "REVIEW_ONCE"
        load.driver_match_notes = load.review_reasons
        return load

    load.driver_fit_status = "CLEAN_MATCH"
    load.driver_match_status = "MATCH"
    load.driver_match_notes = load.match_reasons
    load.is_clean_match = True

    return load
