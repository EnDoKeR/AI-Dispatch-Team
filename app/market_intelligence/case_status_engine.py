WORKING_STATUS_ORDER = {
    "OPEN": 0,
    "CALLED": 1,
    "SENT_TO_DRIVER": 2,
}


FINAL_STATUSES = {
    "BOOKED",
    "RATECON_RECEIVED",
    "REJECTED",
    "SKIPPED",
    "COVERED",
    "REMOVED",
    "DUPLICATE",
}


def status_update_from_feedback(feedback_type):
    feedback_type = str(feedback_type or "").lower().strip()

    working_status_map = {
        "called_broker": "CALLED",
        "called": "CALLED",
        "sent_to_driver": "SENT_TO_DRIVER",
    }

    final_status_map = {
        "booked": "BOOKED",
        "ratecon": "RATECON_RECEIVED",
        "ratecon_received": "RATECON_RECEIVED",
        "driver_rejected": "REJECTED",
        "rate_too_low": "REJECTED",
        "bad_broker": "REJECTED",
        "wrong_equipment": "REJECTED",
        "weight_issue": "REJECTED",
        "time_issue": "REJECTED",
        "covered": "COVERED",
        "removed": "REMOVED",
        "duplicate": "DUPLICATE",
        "skipped": "SKIPPED",
        "not_interested": "SKIPPED",
    }

    if feedback_type in working_status_map:
        return {
            "status": working_status_map[feedback_type],
            "final_outcome": None,
        }

    if feedback_type in final_status_map:
        final_status = final_status_map[feedback_type]

        return {
            "status": final_status,
            "final_outcome": final_status,
        }

    return {
        "status": "OPEN",
        "final_outcome": None,
    }


def status_from_feedback(feedback_type):
    status_update = status_update_from_feedback(feedback_type)

    return status_update.get("status", "OPEN")


def is_final_status(status):
    status = str(status or "").strip().upper()

    return status in FINAL_STATUSES


def is_final_outcome(final_outcome):
    final_outcome = str(final_outcome or "").strip().upper()

    return final_outcome in FINAL_STATUSES


def should_apply_working_status(current_status, new_status):
    current_status = str(current_status or "OPEN").strip().upper()
    new_status = str(new_status or "OPEN").strip().upper()

    if new_status == "OPEN":
        return False

    if current_status in FINAL_STATUSES:
        return False

    current_rank = WORKING_STATUS_ORDER.get(current_status, 0)
    new_rank = WORKING_STATUS_ORDER.get(new_status, 0)

    return new_rank >= current_rank


def apply_status_update_to_case(case_record, status_update):
    new_status = status_update.get("status", "OPEN")
    new_final_outcome = status_update.get("final_outcome")

    current_status = str(case_record.get("status", "") or "").strip()
    current_final_outcome = case_record.get("final_outcome")

    # Final feedback always wins.
    if new_final_outcome:
        case_record["status"] = new_status
        case_record["final_outcome"] = new_final_outcome
        return case_record

    # If the case already has a final outcome, do not downgrade it
    # with working feedback like called_broker or sent_to_driver.
    if current_final_outcome:
        return case_record

    if is_final_status(current_status):
        return case_record

    # Working statuses can only move forward:
    # OPEN -> CALLED -> SENT_TO_DRIVER
    if should_apply_working_status(current_status, new_status):
        case_record["status"] = new_status

    return case_record


def status_update_from_simulation_removed(reason):
    reason = str(reason or "").strip().lower()

    if reason == "covered":
        return {
            "status": "COVERED",
            "final_outcome": "COVERED",
        }

    return {
        "status": "REMOVED",
        "final_outcome": "REMOVED",
    }