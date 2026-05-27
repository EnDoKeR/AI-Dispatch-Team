import json
import urllib.parse
import urllib.request
from pathlib import Path


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


def normalize(value):
    return str(value).strip().lower()


def load_duplicate_key(load, driver_name=""):
    broker = getattr(load, "broker", "")
    pickup_date = getattr(load, "pickup_date", "")

    key_parts = [
        normalize(driver_name),
        normalize(broker),
        normalize(load.pickup),
        normalize(load.delivery),
        normalize(load.rate),
        normalize(load.loaded_miles),
        normalize(pickup_date),
    ]

    return "|".join(key_parts)


def market_summary_key(
    stats,
    recommendation,
    top_opportunities,
    search_location,
    search_request,
):
    best_load_key = "no_best_load"

    if top_opportunities:
        best_load_key = load_duplicate_key(
            top_opportunities[0],
            driver_name=search_request.driver_name,
        )

    key_parts = [
        normalize(search_request.driver_name),
        normalize(search_request.current_location),
        normalize(search_request.available_time),
        normalize(search_request.equipment),
        normalize(search_request.target_direction),
        normalize(search_location),
        normalize(recommendation["market_status"]),
        normalize(recommendation["best_bucket"]),
        normalize(recommendation["total_good_loads"]),
        normalize(recommendation["total_qualified_loads"]),
        normalize(best_load_key),
    ]

    return "|".join(key_parts)


def search_health_key(search_request):
    return "|".join(
        [
            normalize(search_request.driver_name),
            normalize(search_request.current_location),
            normalize(search_request.available_time),
            normalize(search_request.equipment),
            normalize(search_request.target_direction),
            normalize(search_request.min_total_rpm),
            normalize(search_request.max_weight),
        ]
    )


def get_lines(file_path):
    path = Path(file_path)

    if not path.exists():
        return set()

    with open(path, "r", encoding="utf-8") as file:
        return set(file.read().splitlines())


def save_line(file_path, value):
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "a", encoding="utf-8") as file:
        file.write(value + "\n")


def get_sent_loads():
    return get_lines(SENT_FILE)


def save_sent_load(load, search_request):
    save_line(
        SENT_FILE,
        load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        ),
    )


def get_sent_review_once_loads():
    return get_lines(SENT_REVIEW_ONCE_FILE)


def save_sent_review_once_load(load, search_request):
    save_line(
        SENT_REVIEW_ONCE_FILE,
        load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        ),
    )


def get_sent_health_alerts():
    return get_lines(SENT_HEALTH_FILE)


def save_sent_health_alert(search_request):
    save_line(SENT_HEALTH_FILE, search_health_key(search_request))


def get_sent_summaries():
    return get_lines(SENT_SUMMARY_FILE)


def save_sent_summary(summary_key):
    save_line(SENT_SUMMARY_FILE, summary_key)


def remove_duplicates(loads, search_request):
    unique_loads = []
    seen_keys = set()

    for load in loads:
        key = load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        )

        if key in seen_keys:
            print(
                f"Duplicate skipped in current run for {search_request.driver_name}: "
                f"{load.pickup} -> {load.delivery}"
            )
            continue

        seen_keys.add(key)
        unique_loads.append(load)

    return unique_loads


def send_telegram_message(text):
    env = load_env()

    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")

    if not token:
        print("TELEGRAM_BOT_TOKEN is missing in .env")
        return False

    if not chat_id:
        print("TELEGRAM_CHAT_ID is missing in .env")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }

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

        if result.get("ok"):
            print("Telegram message sent ✅")
            return True

        print("Telegram API returned error:")
        print(result)
        return False

    except Exception as error:
        print("Telegram send failed:")
        print(error)
        return False


def safe_value(value, fallback="NEEDS CHECK"):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def extract_state(location):
    text = str(location).strip().upper()

    if "," in text:
        parts = text.split(",")
        state_part = parts[-1].strip()

        if state_part:
            return state_part.split()[0]

    words = text.split()

    if words:
        return words[-1]

    return ""


def delivery_zone_outlook(destination):
    state = extract_state(destination)

    strong_states = [
        "IL",
        "IN",
        "OH",
        "PA",
        "GA",
        "NC",
        "SC",
        "TX",
    ]

    workable_states = [
        "TN",
        "KY",
        "MO",
        "AR",
        "AL",
        "FL",
        "VA",
    ]

    risky_states = [
        "MT",
        "ND",
        "SD",
        "WY",
        "ID",
        "NM",
        "ME",
    ]

    if state in strong_states:
        return "GOOD / STRONG RELOAD AREA"

    if state in workable_states:
        return "WORKABLE / CHECK RELOADS"

    if state in risky_states:
        return "RISKY / EXIT PLAN NEEDED"

    return "UNKNOWN / NEEDS MARKET CHECK"


def format_market_summary_message(
    stats,
    recommendation,
    top_opportunities,
    search_request,
    search_location="Mock Market",
):
    best_bucket = recommendation["best_bucket"]
    best_data = stats[best_bucket]

    best_load = None

    if top_opportunities:
        best_load = top_opportunities[0]

    market_activity = recommendation.get(
        "market_activity",
        recommendation.get("market_status", "UNKNOWN"),
    )

    driver_fit = recommendation.get("driver_fit", "UNKNOWN")
    action_status = recommendation.get("action_status", "UNKNOWN")

    message = ""

    message += f"📊 MARKET SNAPSHOT — {search_request.driver_name}\n\n"
    message += f"Search Area: {search_location}\n"
    message += f"Available: {search_request.available_time}\n"
    message += f"Equipment: {search_request.equipment}\n"
    message += f"Target: {search_request.target_direction}\n\n"

    message += f"Market Activity: {market_activity}\n"
    message += f"Driver Fit: {driver_fit}\n"
    message += f"Action Status: {action_status}\n\n"

    message += f"Best Bucket: {recommendation['best_bucket']}\n"
    message += f"Good Loads: {recommendation['total_good_loads']}\n"
    message += f"Qualified Loads: {recommendation['total_qualified_loads']}\n"
    message += f"Clean Matches: {recommendation.get('total_clean_matches', 0)}\n"
    message += f"Review Once: {recommendation.get('total_review_once', 0)}\n"
    message += f"Blocked: {recommendation.get('total_blocked', 0)}\n\n"

    message += "Best Bucket Details:\n"
    message += f"- Total loads: {best_data['total_loads']}\n"
    message += f"- Qualified: {best_data['qualified_loads']}\n"
    message += f"- Good: {best_data['good_loads']}\n"
    message += f"- Clean matches: {best_data.get('clean_match_loads', 0)}\n"
    message += f"- Review once: {best_data.get('review_once_loads', 0)}\n"
    message += f"- Avg total RPM: ${best_data['avg_total_rpm']}\n"
    message += f"- Avg good score: {best_data['avg_good_score']}\n\n"

    if best_load:
        message += "Best Clean Match:\n"
        message += f"{best_load.pickup} → {best_load.delivery}\n"
        message += f"Rate: ${best_load.rate}\n"
        message += f"Total miles: {best_load.total_miles}\n"
        message += f"Total RPM: ${best_load.total_rpm}\n"
        message += f"Pickup: {safe_value(best_load.pickup_time)}\n"
        message += f"Delivery: {safe_value(best_load.delivery_time)}\n"
        message += f"Delivery Zone: {delivery_zone_outlook(best_load.delivery)}\n"
        message += f"Score: {best_load.opportunity_score()}\n"
        message += f"Action: {best_load.suggested_action()}\n\n"

    else:
        message += "Best Clean Match:\n"
        message += "No clean match under current driver settings.\n\n"

    message += "Recommendation:\n"

    if driver_fit == "GOOD":
        message += "Strong driver fit. Call clean matches first and keep monitoring."

    elif driver_fit == "WORKABLE":
        message += "Some clean matches available. Focus on the strongest options first."

    elif driver_fit == "REVIEW_ONLY":
        message += "Market has activity, but no clean matches. Review exceptions or relax filters."

    elif driver_fit == "WEAK_FIT":
        message += "Weak driver fit. Only limited review options exist. Consider changing filters."

    elif driver_fit == "NO_MATCH":
        message += "No clean matches found. Keep monitoring or adjust search settings."

    else:
        if market_activity == "GOOD":
            message += "Strong market activity, but driver fit should be reviewed."
        elif market_activity == "MEDIUM":
            message += "Workable market activity. Focus only on clean or high-confidence options."
        elif market_activity == "WEAK":
            message += "Weak market. Be careful with empty miles and pickup timing."
        else:
            message += "Bad market. Avoid unless rate or reload plan strongly compensates."

    return message


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
        print(f"Market summary sent ✅ ({search_request.driver_name})")

    return success


def format_opportunity_message(load, index, search_request):
    pickup_time = safe_value(load.pickup_time)
    delivery_time = safe_value(load.delivery_time)
    notes = safe_value(getattr(load, "notes", ""), fallback="No notes posted")
    zone_outlook = delivery_zone_outlook(load.delivery)

    message = ""

    message += f"🔥 HIGH PRIORITY LOAD #{index} — {search_request.driver_name}\n\n"
    message += f"{load.pickup} → {load.delivery}\n\n"

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

    if pickup_time == "NEEDS CHECK" or delivery_time == "NEEDS CHECK":
        message += "⚠️ Time check required before booking.\n\n"

    if "RISKY" in zone_outlook:
        message += "⚠️ Reload risk: check exit plan before booking.\n\n"

    message += f"Priority: {load.priority()}\n"
    message += f"Score: {load.opportunity_score()}\n"
    message += f"Action: {load.suggested_action()}\n\n"

    message += "Reason:\n"
    message += f"{load.opportunity_reason()}\n\n"

    if load.has_email:
        message += "Email: available\n"
        message += "Email draft: hidden for now. Later we will add a button to prepare/edit email."

    return message


def format_review_once_message(load, index, search_request):
    notes = safe_value(getattr(load, "notes", ""), fallback="No notes posted")
    zone_outlook = delivery_zone_outlook(load.delivery)

    message = ""

    message += f"⚠️ REVIEW ONCE — {search_request.driver_name} #{index}\n\n"
    message += f"{load.pickup} → {load.delivery}\n\n"

    message += f"Rate: ${load.rate}\n"
    message += f"Loaded miles: {load.loaded_miles}\n"
    message += f"Empty miles: {load.empty_miles}\n"
    message += f"Total miles: {load.total_miles}\n"
    message += f"Total RPM: ${load.total_rpm}\n"
    message += f"Weight: {load.weight}\n"
    message += f"Driver Max Weight: {search_request.max_weight}\n"
    message += f"Posted trailer: {load.posted_trailer_type}\n"
    message += f"Delivery Zone: {zone_outlook}\n"
    message += f"Pickup Time: {safe_value(load.pickup_time)}\n"
    message += f"Delivery Time: {safe_value(load.delivery_time)}\n"
    message += f"Notes: {notes}\n\n"

    if "RISKY" in zone_outlook:
        message += "⚠️ Reload risk: exit plan should be checked before booking.\n\n"

    message += "Why shown:\n"

    if load.driver_match_notes:
        for note in load.driver_match_notes:
            message += f"- {note}\n"
    else:
        message += "- Outside driver settings, but still potentially workable.\n"

    message += "\nAction:\n"
    message += "Review once. Ask dispatcher/driver if this exception is acceptable.\n"
    message += "This alert will not repeat unless significant update logic is added."

    return message


def format_search_health_message(
    search_request,
    loads,
    top_opportunities,
    review_once_loads,
    monitored_minutes=30,
):
    reason_counts = {}

    for load in loads:
        for reason in load.reject_reasons():
            if reason == "OK":
                continue

            reason_counts[reason] = reason_counts.get(reason, 0) + 1

    sorted_reasons = sorted(
        reason_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    message = ""

    message += f"⚠️ SEARCH HEALTH CHECK — {search_request.driver_name}\n\n"
    message += f"Location: {search_request.current_location}\n"
    message += f"Monitored: ~{monitored_minutes} min\n\n"

    message += "No strong matching loads found with current filters.\n\n"

    message += "Current filters:\n"
    message += f"- Max weight: {search_request.max_weight}\n"
    message += f"- Max empty: {search_request.max_empty_miles} mi\n"
    message += f"- Min RPM: {search_request.min_total_rpm}\n"
    message += f"- Direction: {search_request.target_direction}\n"
    message += f"- Equipment: {search_request.equipment}\n\n"

    message += "Near-miss / review options:\n"
    message += f"- Review once loads: {len(review_once_loads)}\n"
    message += f"- Top matches: {len(top_opportunities)}\n\n"

    if sorted_reasons:
        message += "Most common blockers:\n"

        for reason, count in sorted_reasons[:5]:
            message += f"- {reason}: {count}\n"

        message += "\n"

    message += "Possible adjustments:\n"

    if reason_counts.get("DRIVER_REVIEW_ONCE", 0) > 0:
        message += "- Review one-time exceptions such as weight or trailer verification.\n"

    if reason_counts.get("EMPTY_TOO_FAR", 0) > 0:
        message += "- Consider expanding empty radius above 200 miles.\n"

    if reason_counts.get("PICKUP_TIME_NEEDS_CONFIRMATION", 0) > 0:
        message += "- Allow pickup-time verification loads.\n"

    if reason_counts.get("LOW_RPM", 0) > 0:
        message += "- Consider lowering min RPM slightly if market is weak.\n"

    if not sorted_reasons:
        message += "- Keep monitoring or expand search radius.\n"

    message += "\nRecommendation:\n"
    message += "Consider relaxing one filter or keep monitoring."

    return message


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

        success = send_telegram_message(message)

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

        success = send_telegram_message(message)

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
        print(f"Search health check sent ✅ ({search_request.driver_name})")
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


def broker_block(load):
    broker_name = getattr(load, "broker_name", "")
    broker_mc = getattr(load, "broker_mc", "")
    broker_contact = getattr(load, "broker_contact", "")
    credit_score = getattr(load, "credit_score", 0)
    days_to_pay = getattr(load, "days_to_pay", 0)
    broker_status = getattr(load, "broker_status", "")

    text = ""

    if broker_name:
        text += f"Broker: {broker_name}\n"

    if broker_mc:
        text += f"MC: {broker_mc}\n"

    if broker_contact:
        text += f"Contact: {broker_contact}\n"

    if credit_score:
        text += f"Credit Score: {credit_score}\n"

    if days_to_pay:
        text += f"Days to Pay: {days_to_pay}\n"

    if broker_status:
        text += f"Broker Status: {broker_status}\n"

    if not text:
        text += "Broker: NEEDS CHECK\n"

    return text


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

    message += f"🔁 LOAD WITH RELOAD PLAN #{index} — {search_request.driver_name}\n\n"

    message += "FIRST LOAD:\n"
    message += f"{first_load.pickup} → {first_load.delivery}\n"
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
    message += f"{reload_load.pickup} → {reload_load.delivery}\n"
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