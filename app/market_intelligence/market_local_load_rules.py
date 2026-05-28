def apply_local_load_rules(load, origin_text, destination_text):
    if origin_text and destination_text and origin_text == destination_text:
        load.is_local_load = True
        load.is_blocked = True
        load.block_reasons.append("Same pickup and delivery city.")

    if load.loaded_miles and load.loaded_miles <= 10:
        load.is_local_load = True
        load.is_blocked = True
        load.block_reasons.append("Loaded miles are too low / local load.")

    return load
