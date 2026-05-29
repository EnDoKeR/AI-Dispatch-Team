def safe_attr(source, field_name, default=""):
    if source is None:
        return default

    value = getattr(source, field_name, default)

    if value is None:
        return default

    return value


def first_non_empty(*values):
    for value in values:
        if value is None:
            continue

        if str(value).strip():
            return value

    return ""


def reference_id_value(load):
    reference_id = safe_attr(load, "reference_id", "")

    if str(reference_id).strip():
        return reference_id

    return "NO ID"


def build_load_alert_metadata(
    load,
    search_request=None,
    message_type="",
    category="",
):
    driver_name = first_non_empty(
        safe_attr(search_request, "driver_name", ""),
        safe_attr(load, "driver_name", ""),
    )
    broker = first_non_empty(
        safe_attr(load, "broker_name", ""),
        safe_attr(load, "broker", ""),
    )

    return {
        "message_type": message_type,
        "category": category,
        "driver_name": driver_name,
        "pickup": safe_attr(load, "pickup", ""),
        "delivery": safe_attr(load, "delivery", ""),
        "rate": safe_attr(load, "rate", ""),
        "broker": broker,
        "broker_mc": safe_attr(load, "broker_mc", ""),
        "reference_id": reference_id_value(load),
    }


def build_load_opportunity_metadata(
    load,
    search_request=None,
    category="LOAD OPPORTUNITY",
):
    return build_load_alert_metadata(
        load=load,
        search_request=search_request,
        message_type="LOAD_OPPORTUNITY",
        category=category,
    )


def build_review_once_metadata(
    load,
    search_request=None,
    category="REVIEW ONCE",
):
    return build_load_alert_metadata(
        load=load,
        search_request=search_request,
        message_type="REVIEW_ONCE",
        category=category,
    )
