def reset_driver_match_state(load):
    load.match_reasons = []
    load.review_reasons = []
    load.block_reasons = []

    load.is_blocked = False
    load.is_review_once = False
    load.is_clean_match = False

    load.target_relation = "MISMATCH"
    load.driver_fit_status = "UNKNOWN"
    load.driver_match_status = "UNKNOWN"
    load.driver_match_notes = []

    return load


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
