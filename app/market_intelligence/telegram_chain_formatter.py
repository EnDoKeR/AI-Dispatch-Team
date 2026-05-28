from app.market_intelligence.telegram_broker_block import broker_block
from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    normalize,
)
from app.market_intelligence.telegram_sent_state import (
    get_lines,
    save_line,
)
from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    safe_value,
)


SENT_CHAIN_FILE = "data/sent_reload_chain_alerts.txt"


def chain_duplicate_key(chain_candidate, search_request):
    first_load = chain_candidate["first_load"]
    reload_load = chain_candidate["reload_load"]

    key_parts = [
        normalize(search_request.driver_name),
        load_duplicate_key(first_load, driver_name=search_request.driver_name),
        load_duplicate_key(reload_load, driver_name=search_request.driver_name),
    ]

    return "|".join(key_parts)


def get_sent_chain_alerts():
    return get_lines(SENT_CHAIN_FILE)


def save_sent_chain_alert(chain_candidate, search_request):
    save_line(
        SENT_CHAIN_FILE,
        chain_duplicate_key(chain_candidate, search_request),
    )



def important_checklist(load, search_request):
    checks = []

    if safe_value(load.pickup_time) == "NEEDS CHECK":
        checks.append("pickup time / pickup hours")

    if safe_value(load.delivery_time) == "NEEDS CHECK":
        checks.append("delivery time / delivery hours")

    if getattr(load, "posted_trailer_type", "") == "Flatbed" and search_request.equipment == "Conestoga":
        checks.append("if Conestoga is accepted")

    if getattr(load, "requires_tarp", False):
        checks.append("tarp requirements")

    if getattr(load, "is_od", False):
        checks.append("OD / permit details")

    if getattr(load, "is_overweight", False):
        checks.append("overweight details")

    if getattr(load, "weight", 0) > search_request.max_weight:
        checks.append("weight approval from driver")

    if getattr(load, "broker_status", "") in ["UNKNOWN", "BUY_REVIEW"]:
        checks.append("broker / factoring status")

    if not checks:
        return "No major missing checks detected."

    text = ""

    for check in checks:
        text += f"- {check}\n"

    return text.strip()


def format_chain_candidate_message(chain_candidate, search_request, index):
    first_load = chain_candidate["first_load"]
    reload_load = chain_candidate["reload_load"]
    chain_data = chain_candidate["chain_data"]

    message = ""

    message += f"рџ”Ѓ LOAD WITH RELOAD PLAN #{index} вЂ” {search_request.driver_name}\n\n"

    message += "FIRST LOAD:\n"
    message += f"{first_load.pickup} в†’ {first_load.delivery}\n"
    message += f"Rate: ${first_load.rate}\n"
    message += f"Loaded miles: {first_load.loaded_miles}\n"
    message += f"Empty miles: {first_load.empty_miles}\n"
    message += f"Total miles: {first_load.total_miles}\n"
    message += f"Total RPM: ${first_load.total_rpm}\n"
    message += f"Weight: {first_load.weight}\n"
    message += f"Posted trailer: {first_load.posted_trailer_type}\n"
    message += f"Pickup: {safe_value(first_load.pickup_time)}\n"
    message += f"Delivery: {safe_value(first_load.delivery_time)}\n"
    message += f"Delivery Zone: {delivery_zone_outlook(first_load.delivery)}\n"

    if getattr(first_load, "reference_id", ""):
        message += f"Reference ID: {first_load.reference_id}\n"

    message += "\nFirst Load Broker:\n"
    message += broker_block(first_load)

    message += "\nFirst Load Notes:\n"
    message += f"{safe_value(first_load.notes, fallback='No notes posted')}\n\n"

    message += "First Load Must Check:\n"
    message += f"{important_checklist(first_load, search_request)}\n\n"

    message += "RELOAD OPTION:\n"
    message += f"{reload_load.pickup} в†’ {reload_load.delivery}\n"
    message += f"Rate: ${reload_load.rate}\n"
    message += f"Loaded miles: {reload_load.loaded_miles}\n"
    message += f"Empty miles: {reload_load.empty_miles}\n"
    message += f"Total miles: {reload_load.total_miles}\n"
    message += f"Total RPM: ${reload_load.total_rpm}\n"
    message += f"Weight: {reload_load.weight}\n"
    message += f"Posted trailer: {reload_load.posted_trailer_type}\n"
    message += f"Pickup: {safe_value(reload_load.pickup_time)}\n"
    message += f"Delivery: {safe_value(reload_load.delivery_time)}\n"
    message += f"Delivery Zone: {delivery_zone_outlook(reload_load.delivery)}\n"

    if getattr(reload_load, "reference_id", ""):
        message += f"Reference ID: {reload_load.reference_id}\n"

    message += "\nReload Broker:\n"
    message += broker_block(reload_load)

    message += "\nReload Notes:\n"
    message += f"{safe_value(reload_load.notes, fallback='No notes posted')}\n\n"

    message += "Reload Must Check:\n"
    message += f"{important_checklist(reload_load, search_request)}\n\n"

    message += "TOTAL CHAIN:\n"
    message += f"Gross: ${chain_data['total_gross']}\n"
    message += f"Total miles: {chain_data['total_miles']}\n"
    message += f"Chain RPM: ${chain_data['total_rpm']}\n"
    message += f"Chain Score: {chain_data['chain_score']}\n\n"

    message += "Why shown:\n"
    message += "- First load does not match target direction by itself.\n"
    message += "- It is only shown because a reload toward target was found.\n"
    message += "- This chain is valid only while the first load is still active on the board.\n\n"

    message += "Action:\n"
    message += "Review as a package. Verify both loads before booking the first one."

    return message
