from app.market_intelligence.case_id_resolver import normalize_text


def feedback_matches_case(feedback_record, case_record):
    feedback_driver = normalize_text(feedback_record.get("driver_name", ""))
    feedback_load_id = normalize_text(feedback_record.get("load_id", ""))
    feedback_reference_id = normalize_text(feedback_record.get("reference_id", ""))

    case_driver = normalize_text(case_record.get("driver_name", ""))
    case_load_id = normalize_text(case_record.get("load_id", ""))
    case_reference_id = normalize_text(case_record.get("reference_id", ""))

    if feedback_driver and case_driver and feedback_driver != case_driver:
        return False

    if feedback_load_id and feedback_load_id == case_load_id:
        return True

    if feedback_reference_id and feedback_reference_id == case_reference_id:
        return True

    if feedback_load_id and feedback_load_id == case_reference_id:
        return True

    if feedback_reference_id and feedback_reference_id == case_load_id:
        return True

    return False


def outbox_matches_case(outbox_record, case_record):
    outbox_reference_id = normalize_text(outbox_record.get("reference_id", ""))
    outbox_driver = normalize_text(outbox_record.get("driver_name", ""))
    outbox_pickup = normalize_text(outbox_record.get("pickup", ""))
    outbox_delivery = normalize_text(outbox_record.get("delivery", ""))
    outbox_broker_mc = normalize_text(outbox_record.get("broker_mc", ""))

    case_reference_id = normalize_text(case_record.get("reference_id", ""))
    case_driver = normalize_text(case_record.get("driver_name", ""))
    case_pickup = normalize_text(case_record.get("pickup", ""))
    case_delivery = normalize_text(case_record.get("delivery", ""))
    case_broker_mc = normalize_text(case_record.get("broker_mc", ""))

    if outbox_reference_id and outbox_reference_id != "no id":
        if outbox_reference_id == case_reference_id and outbox_driver == case_driver:
            return True

    if (
        outbox_driver
        and outbox_pickup
        and outbox_delivery
        and outbox_driver == case_driver
        and outbox_pickup == case_pickup
        and outbox_delivery == case_delivery
    ):
        if not outbox_broker_mc or not case_broker_mc:
            return True

        if outbox_broker_mc == case_broker_mc:
            return True

    return False


def simulation_event_matches_case(simulation_event, case_record):
    payload = simulation_event.get("payload", {}) or {}

    simulation_load_id = normalize_text(simulation_event.get("load_id", ""))
    event_load = payload.get("load", {}) or {}
    updates = payload.get("updates", {}) or {}

    possible_reference_ids = [
        simulation_load_id,
        normalize_text(event_load.get("reference_id", "")),
        normalize_text(updates.get("reference_id", "")),
    ]

    case_reference_id = normalize_text(case_record.get("reference_id", ""))
    case_load_id = normalize_text(case_record.get("load_id", ""))

    for possible_id in possible_reference_ids:
        if not possible_id:
            continue

        if possible_id == case_reference_id:
            return True

        if possible_id == case_load_id:
            return True

    return False
