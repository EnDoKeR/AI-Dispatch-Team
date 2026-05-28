import json
from operator import index
import urllib.parse
import urllib.request
from app.market_intelligence.telegram_buttons import build_feedback_buttons
from pathlib import Path
from app.market_intelligence.telegram_outbox_logger import log_outgoing_telegram_message
from app.market_intelligence.telegram_broker_block import (broker_block, get_broker_status_text)
from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    market_summary_key,
    normalize,
    remove_duplicates,
    search_health_key,
)
from app.market_intelligence.telegram_sent_state import (
    get_lines,
    get_sent_health_alerts,
    get_sent_loads,
    get_sent_review_once_loads,
    get_sent_summaries,
    save_line,
    save_sent_health_alert,
    save_sent_load,
    save_sent_review_once_load,
    save_sent_summary,
)
from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    safe_value,
)
from app.market_intelligence.telegram_market_summary_formatter import format_market_summary_message
from app.market_intelligence.telegram_opportunity_formatter import format_opportunity_message
from app.market_intelligence.telegram_review_once_formatter import (
    _dedupe_review_reasons,
    format_review_once_message,
)
from app.market_intelligence.telegram_search_health_formatter import format_search_health_message


ENV_FILE = ".env"

SENT_FILE = "data/sent_telegram_loads.txt"
SENT_REVIEW_ONCE_FILE = "data/sent_review_once_loads.txt"
SENT_HEALTH_FILE = "data/sent_search_health_alerts.txt"
SENT_SUMMARY_FILE = "data/sent_market_summaries.txt"
SENT_CHAIN_FILE = "data/sent_reload_chain_alerts.txt"


def load_env():
    values = {}

    try:
        with open(ENV_FILE, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()

    except FileNotFoundError:
        print(".env file not found")

    return values



def send_telegram_message(text, reply_markup=None):
    env = load_env()

    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")

    if not token:
        print("TELEGRAM_BOT_TOKEN is missing in .env")

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_BOT_TOKEN is missing in .env",
        )

        return False

    if not chat_id:
        print("TELEGRAM_CHAT_ID is missing in .env")

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text="TELEGRAM_CHAT_ID is missing in .env",
        )

        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)

    encoded_data = urllib.parse.urlencode(data).encode("utf-8")

    try:
        request = urllib.request.Request(
            url,
            data=encoded_data,
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=20) as response:
            response_text = response.read().decode("utf-8")
            result = json.loads(response_text)

    except Exception as error:
        print("Telegram send failed:")
        print(error)

        log_outgoing_telegram_message(
            text=text,
            success=False,
            telegram_response=None,
            error_text=str(error),
        )

        return False

    if result.get("ok"):
        print("Telegram message sent вњ…")

        log_outgoing_telegram_message(
            text=text,
            success=True,
            telegram_response=result,
            error_text="",
        )

        return True

    print("Telegram API returned error:")
    print(result)

    log_outgoing_telegram_message(
        text=text,
        success=False,
        telegram_response=result,
        error_text=str(result),
    )

    return False



def send_market_summary_to_telegram(
    stats,
    recommendation,
    top_opportunities,
    search_request,
    search_location="Mock Market",
):
    key = market_summary_key(
        stats,
        recommendation,
        top_opportunities,
        search_location,
        search_request,
    )

    sent_summaries = get_sent_summaries()

    if key in sent_summaries:
        print(
            f"Market summary already sent for this market state: "
            f"{search_request.driver_name}"
        )
        return False

    message = format_market_summary_message(
        stats,
        recommendation,
        top_opportunities,
        search_request,
        search_location,
    )

    success = send_telegram_message(message)


    if success:
        save_sent_summary(key)
        print(f"Market summary sent вњ… ({search_request.driver_name})")

    return success





def send_top_opportunities_to_telegram(loads, search_request, limit=3):
    if not loads:
        print(f"No loads to send to Telegram ({search_request.driver_name})")
        return

    sent_history = get_sent_loads()

    unique_loads = remove_duplicates(loads, search_request)

    selected_loads = unique_loads[:limit]

    loads_to_send = []

    for load in selected_loads:
        key = load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        )

        if key in sent_history:
            print(
                f"Already sent before for {search_request.driver_name}, skipped: "
                f"{load.pickup} -> {load.delivery}"
            )
            continue

        loads_to_send.append(load)

    if not loads_to_send:
        print(f"No new Telegram loads to send ({search_request.driver_name})")
        return

    sent = 0

    for index, load in enumerate(loads_to_send, start=1):
        message = format_opportunity_message(load, index, search_request)

        success = send_telegram_message(
        message,
        reply_markup=build_feedback_buttons(
            "load",
            reference_id=getattr(load, "reference_id", ""),
        ),
)

        if success:
            save_sent_load(load, search_request)
            sent += 1

    print(f"Telegram sent for {search_request.driver_name}: {sent}/{len(loads_to_send)}")


def send_review_once_to_telegram(loads, search_request, limit=3):
    if not loads:
        print(f"No review-once loads to send ({search_request.driver_name})")
        return

    sent_history = get_sent_review_once_loads()

    unique_loads = remove_duplicates(loads, search_request)
    selected_loads = unique_loads[:limit]

    loads_to_send = []

    for load in selected_loads:
        key = load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        )

        if key in sent_history:
            print(
                f"Review-once already sent for {search_request.driver_name}, skipped: "
                f"{load.pickup} -> {load.delivery}"
            )
            continue

        loads_to_send.append(load)

    if not loads_to_send:
        print(f"No new review-once loads to send ({search_request.driver_name})")
        return

    sent = 0

    for index, load in enumerate(loads_to_send, start=1):
        message = format_review_once_message(
            load,
            index,
            search_request,
        )

        success = send_telegram_message(
            message,
            reply_markup=build_feedback_buttons(
            "review_once",
            reference_id=getattr(load, "reference_id", ""),
),
)

        if success:
            save_sent_review_once_load(load, search_request)
            sent += 1

    print(
        f"Review-once Telegram sent for {search_request.driver_name}: "
        f"{sent}/{len(loads_to_send)}"
    )


def send_search_health_check_to_telegram(
    search_request,
    loads,
    top_opportunities,
    review_once_loads,
    monitored_minutes=30,
):
    if top_opportunities:
        print(
            f"Search health check skipped: strong/top opportunities exist "
            f"({search_request.driver_name})"
        )
        return

    sent_history = get_sent_health_alerts()
    key = search_health_key(search_request)

    if key in sent_history:
        print(f"Search health check already sent for this request ({search_request.driver_name})")
        return

    message = format_search_health_message(
        search_request,
        loads,
        top_opportunities,
        review_once_loads,
        monitored_minutes=monitored_minutes,
    )

    success = send_telegram_message(message)

    if success:
        save_sent_health_alert(search_request)
        print(f"Search health check sent вњ… ({search_request.driver_name})")
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


def send_chain_candidates_to_telegram(chain_candidates, search_request, limit=3):
    if not chain_candidates:
        print(f"No reload chain candidates ({search_request.driver_name})")
        return

    sent_history = get_sent_chain_alerts()
    selected_candidates = chain_candidates[:limit]

    candidates_to_send = []
    seen_this_run = set()

    for candidate in selected_candidates:
        key = chain_duplicate_key(candidate, search_request)

        if key in seen_this_run:
            first_load = candidate["first_load"]
            reload_load = candidate["reload_load"]

            print(
                f"Duplicate reload chain skipped in current run for {search_request.driver_name}: "
                f"{first_load.pickup} -> {first_load.delivery} + "
                f"{reload_load.pickup} -> {reload_load.delivery}"
            )
            continue

        seen_this_run.add(key)

        if key in sent_history:
            first_load = candidate["first_load"]
            reload_load = candidate["reload_load"]

            print(
                f"Reload chain already sent for {search_request.driver_name}, skipped: "
                f"{first_load.pickup} -> {first_load.delivery} + "
                f"{reload_load.pickup} -> {reload_load.delivery}"
            )
            continue

        candidates_to_send.append(candidate)

    if not candidates_to_send:
        print(f"No new reload chain candidates to send ({search_request.driver_name})")
        return

    sent = 0

    for index, candidate in enumerate(candidates_to_send, start=1):
        message = format_chain_candidate_message(
            candidate,
            search_request,
            index,
        )

        success = send_telegram_message(message)

        if success:
            save_sent_chain_alert(candidate, search_request)
            sent += 1

    print(
        f"Reload chain Telegram sent for {search_request.driver_name}: "
        f"{sent}/{len(candidates_to_send)}"
    )
