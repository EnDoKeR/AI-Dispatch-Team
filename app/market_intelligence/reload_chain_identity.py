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
