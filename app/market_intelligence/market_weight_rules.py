def apply_weight_rules(load, max_weight, equipment):
    if not max_weight:
        return load

    if not load.weight:
        return load

    if load.weight <= max_weight:
        return load

    load.is_overweight = True

    if "conestoga" in equipment:
        load.is_blocked = True
        load.block_reasons.append(
            f"Weight {load.weight} is above Conestoga driver setting {max_weight}."
        )
        return load

    load.is_review_once = True
    load.review_reasons.append(
        f"Weight {load.weight} is above driver setting {max_weight}."
    )

    return load
