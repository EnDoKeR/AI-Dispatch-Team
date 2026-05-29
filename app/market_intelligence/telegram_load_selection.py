from app.market_intelligence.telegram_duplicate_keys import (
    remove_duplicates,
    sent_history_matches_load,
)


def select_new_loads(loads, search_request, sent_history, limit):
    unique_loads = remove_duplicates(loads, search_request)
    selected_loads = []
    already_sent_loads = []
    loads_to_send = []

    for load in unique_loads:
        selected_loads.append(load)

        if sent_history_matches_load(
            sent_history,
            load,
            driver_name=search_request.driver_name,
        ):
            already_sent_loads.append(load)
            continue

        loads_to_send.append(load)

        if len(loads_to_send) >= limit:
            break

    return {
        "selected_loads": selected_loads,
        "already_sent_loads": already_sent_loads,
        "loads_to_send": loads_to_send,
    }
