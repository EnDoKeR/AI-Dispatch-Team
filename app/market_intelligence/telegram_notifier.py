from app.market_intelligence.telegram_buttons import build_feedback_buttons
from app.market_intelligence.telegram_broker_block import get_broker_status_text
from app.market_intelligence.telegram_duplicate_keys import (
    market_summary_key,
    search_health_key,
)
from app.market_intelligence.telegram_load_selection import select_new_loads
from app.market_intelligence.telegram_sent_state import (
    get_sent_health_alerts,
    get_sent_loads,
    get_sent_review_once_loads,
    get_sent_summaries,
    save_sent_health_alert,
    save_sent_load,
    save_sent_review_once_load,
    save_sent_summary,
)
from app.market_intelligence.telegram_market_summary_formatter import format_market_summary_message
from app.market_intelligence.telegram_opportunity_formatter import format_opportunity_message
from app.market_intelligence.telegram_review_once_formatter import format_review_once_message
from app.market_intelligence.telegram_search_health_formatter import format_search_health_message
from app.market_intelligence.telegram_chain_formatter import (
    format_chain_candidate_message,
    get_sent_chain_alerts,
    save_sent_chain_alert,
)
from app.market_intelligence.telegram_chain_selection import select_new_chain_candidates
from app.market_intelligence.telegram_sender import (
    load_env,
    send_telegram_message,
)


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

    selection = select_new_loads(
        loads,
        search_request,
        sent_history,
        limit,
    )
    loads_to_send = selection["loads_to_send"]

    for load in selection["already_sent_loads"]:
        print(
            f"Already sent before for {search_request.driver_name}, skipped: "
            f"{load.pickup} -> {load.delivery}"
        )

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

    selection = select_new_loads(
        loads,
        search_request,
        sent_history,
        limit,
    )
    loads_to_send = selection["loads_to_send"]

    for load in selection["already_sent_loads"]:
        print(
            f"Review-once already sent for {search_request.driver_name}, skipped: "
            f"{load.pickup} -> {load.delivery}"
        )

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

def send_chain_candidates_to_telegram(chain_candidates, search_request, limit=3):
    if not chain_candidates:
        print(f"No reload chain candidates ({search_request.driver_name})")
        return

    sent_history = get_sent_chain_alerts()
    selection = select_new_chain_candidates(
        chain_candidates,
        search_request,
        sent_history,
        limit,
    )
    candidates_to_send = selection["candidates_to_send"]

    for candidate in selection["duplicate_candidates"]:
        first_load = candidate["first_load"]
        reload_load = candidate["reload_load"]

        print(
            f"Duplicate reload chain skipped in current run for {search_request.driver_name}: "
            f"{first_load.pickup} -> {first_load.delivery} + "
            f"{reload_load.pickup} -> {reload_load.delivery}"
        )

    for candidate in selection["already_sent_candidates"]:
        first_load = candidate["first_load"]
        reload_load = candidate["reload_load"]

        print(
            f"Reload chain already sent for {search_request.driver_name}, skipped: "
            f"{first_load.pickup} -> {first_load.delivery} + "
            f"{reload_load.pickup} -> {reload_load.delivery}"
        )

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
