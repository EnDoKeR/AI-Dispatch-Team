from app.market_intelligence.telegram_broker_block import broker_block
from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    safe_value,
)


def format_opportunity_message(load, index, search_request):
    pickup_time = safe_value(load.pickup_time)
    delivery_time = safe_value(load.delivery_time)
    notes = safe_value(getattr(load, "notes", ""), fallback="No notes posted")
    zone_outlook = delivery_zone_outlook(load.delivery)

    message = ""

    message = f"рџ”Ґ LOAD OPPORTUNITY #{index} вЂ” {search_request.driver_name}\n\n"
    message += f"{load.pickup} в†’ {load.delivery}\n\n"

    message += f"Rate: ${load.rate}\n"
    message += f"Loaded miles: {load.loaded_miles}\n"
    message += f"Empty miles: {load.empty_miles}\n"
    message += f"Total miles: {load.total_miles}\n"
    message += f"Total RPM: ${load.total_rpm}\n"
    message += f"Bucket: {load.bucket}\n"
    message += f"Weight: {load.weight}\n"
    message += f"Posted trailer: {load.posted_trailer_type}\n"
    message += f"Delivery Zone: {zone_outlook}\n\n"

    message += f"Pickup Time: {pickup_time}\n"
    message += f"Delivery Time: {delivery_time}\n"
    message += f"Notes: {notes}\n\n"

    message += broker_block(load)
    message += "\n"

    if pickup_time == "NEEDS CHECK" or delivery_time == "NEEDS CHECK":
        message += "вљ пёЏ Time check required before booking.\n\n"

    if "RISKY" in zone_outlook:
        message += "вљ пёЏ Reload risk: check exit plan before booking.\n\n"

    message += f"Priority: {load.priority()}\n"
    message += f"Score: {load.opportunity_score()}\n"
    message += f"Action: {load.suggested_action()}\n\n"

    message += "Reason:\n"
    message += f"{load.opportunity_reason()}\n\n"

    driver_fit_notes = []

    if getattr(load, "driver_match_notes", None):
        for note in load.driver_match_notes:
            note_text = str(note).strip()

            if not note_text:
                continue

            note_key = (
                note_text.lower()
                .replace(".", "")
                .replace(";", "")
                .replace(",", "")
                .strip()
            )

            already_exists = False

            for existing_note in list(driver_fit_notes):
                existing_key = (
                    existing_note.lower()
                    .replace(".", "")
                    .replace(";", "")
                    .replace(",", "")
                    .strip()
                )

                if note_key == existing_key:
                    already_exists = True
                    break

                if note_key in existing_key:
                    already_exists = True
                    break

                if existing_key in note_key:
                    driver_fit_notes.remove(existing_note)
                    driver_fit_notes.append(note_text)
                    already_exists = True
                    break

            if already_exists:
                continue

            driver_fit_notes.append(note_text)

    if driver_fit_notes:
        message += "Driver Fit:\n"

        for note in driver_fit_notes:
            message += f"- {note}\n"

        message += "\n"

    return message
