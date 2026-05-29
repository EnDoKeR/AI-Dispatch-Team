from app.market_intelligence.telegram_chain_formatter import chain_duplicate_key


def select_new_chain_candidates(
    chain_candidates,
    search_request,
    sent_history,
    limit,
):
    selected_candidates = chain_candidates[:limit]

    candidates_to_send = []
    duplicate_candidates = []
    already_sent_candidates = []
    seen_this_run = set()

    for candidate in selected_candidates:
        key = chain_duplicate_key(candidate, search_request)

        if key in seen_this_run:
            duplicate_candidates.append(candidate)
            continue

        seen_this_run.add(key)

        if key in sent_history:
            already_sent_candidates.append(candidate)
            continue

        candidates_to_send.append(candidate)

    return {
        "selected_candidates": selected_candidates,
        "duplicate_candidates": duplicate_candidates,
        "already_sent_candidates": already_sent_candidates,
        "candidates_to_send": candidates_to_send,
    }
