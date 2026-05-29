from app.market_intelligence.telegram_duplicate_keys import (
    load_duplicate_key,
    remove_duplicates,
)


def select_new_loads(loads, search_request, sent_history, limit):
    unique_loads = remove_duplicates(loads, search_request)
    selected_loads = unique_loads[:limit]

    already_sent_loads = []
    loads_to_send = []

    for load in selected_loads:
        key = load_duplicate_key(
            load,
            driver_name=search_request.driver_name,
        )

        if key in sent_history:
            already_sent_loads.append(load)
            continue

        loads_to_send.append(load)

    return {
        "selected_loads": selected_loads,
        "already_sent_loads": already_sent_loads,
        "loads_to_send": loads_to_send,
    }
