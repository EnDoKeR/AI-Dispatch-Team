from app.market_intelligence.telegram_broker_block import broker_block
from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    safe_value,
)


def _dedupe_review_reasons(reasons):
    """
    Removes duplicated or near-duplicated REVIEW ONCE reasons.

    Example:
    - "Tanker endorsement required; ask driver and save answer in driver profile."
    - "Tanker endorsement required."

    Result:
    - keeps only the longer / more useful reason.
    """
    if not reasons:
        return []

    cleaned = []

    for reason in reasons:
        if not reason:
            continue

        reason_text = str(reason).strip()
        if not reason_text:
            continue

        normalized = (
            reason_text.lower()
            .replace(".", "")
            .replace(";", "")
            .replace(",", "")
            .strip()
        )

        is_duplicate = False

        for existing in list(cleaned):
            existing_text = str(existing).strip()
            existing_normalized = (
                existing_text.lower()
                .replace(".", "")
                .replace(";", "")
                .replace(",", "")
                .strip()
            )

            # Exact duplicate
            if normalized == existing_normalized:
                is_duplicate = True
                break

            # Near duplicate:
            # Example: "tanker endorsement required" is already inside
            # "tanker endorsement required ask driver and save answer..."
            if normalized in existing_normalized:
                is_duplicate = True
                break

            if existing_normalized in normalized:
                cleaned.remove(existing)
                cleaned.append(reason_text)
                is_duplicate = True
                break

        if not is_duplicate:
            cleaned.append(reason_text)

    return cleaned

def format_review_once_message(load, index, search_request):
    notes = safe_value(getattr(load, "notes", ""), fallback="No notes posted")

    zone_outlook = (
        getattr(load, "delivery_zone", "")
        or getattr(load, "zone_outlook", "")
        or getattr(load, "delivery_zone_outlook", "")
    )

    zone_outlook_text = str(zone_outlook).strip().upper()

    if (
        not zone_outlook
        or zone_outlook_text in ["UNKNOWN", "NEEDS CHECK", "UNKNOWN / NEEDS MARKET CHECK"]
    ):
        zone_outlook = delivery_zone_outlook(load.delivery)

    zone_outlook = safe_value(zone_outlook, fallback="UNKNOWN / NEEDS MARKET CHECK")

    if hasattr(load, "review_category") and callable(load.review_category):
        category = safe_value(load.review_category(), fallback="GENERAL REVIEW")
    else:
        category = "GENERAL REVIEW"

    message = ""

    message += (
        f"вљ пёЏ REVIEW ONCE вЂ” {category} вЂ” "
        f"{search_request.driver_name} #{index}\n\n"
    )

    message += f"{load.pickup} в†’ {load.delivery}\n\n"

    message += f"Rate: ${load.rate}\n"
    message += f"Loaded miles: {load.loaded_miles}\n"
    message += f"Empty miles: {load.empty_miles}\n"
    message += f"Total miles: {load.total_miles}\n"
    message += f"Total RPM: ${load.total_rpm}\n"
    message += f"Weight: {load.weight}\n"
    message += f"Driver Max Weight: {search_request.max_weight}\n"
    message += f"Posted trailer: {load.posted_trailer_type}\n"
    message += f"Delivery Zone: {zone_outlook}\n\n"

    message += f"Pickup Time: {safe_value(load.pickup_time)}\n"
    message += f"Delivery Time: {safe_value(load.delivery_time)}\n"
    message += f"Notes: {notes}\n\n"

    message += broker_block(load)
    message += "\n"

    if "RISKY" in zone_outlook:
        message += "вљ пёЏ Reload risk: exit plan should be checked before booking.\n\n"

    message += "Why shown:\n"
    shown_notes = []

    if load.driver_match_notes:
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

            for existing_note in list(shown_notes):
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
                    shown_notes.remove(existing_note)
                    shown_notes.append(note_text)
                    already_exists = True
                    break

            if already_exists:
                continue

            shown_notes.append(note_text)

    if shown_notes:
        for note in shown_notes:
            message += f"- {note}\n"
    else:
        message += "- Outside driver settings, but still potentially workable.\n"

    message += "\nAction:\n"
    message += "Review once. Ask dispatcher/driver if this exception is acceptable.\n"
    message += "This alert will not repeat unless significant update logic is added."

    return message
