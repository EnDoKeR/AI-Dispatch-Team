from app.market_intelligence.telegram_chain_formatter import chain_duplicate_key


def select_new_chain_candidates(
    chain_candidates,
    search_request,
    sent_history,
    limit,
):
    candidates_to_send = []
    selected_candidates = []
    duplicate_candidates = []
    already_sent_candidates = []
    seen_this_run = set()

    if limit <= 0:
        return {
            "selected_candidates": selected_candidates,
            "duplicate_candidates": duplicate_candidates,
            "already_sent_candidates": already_sent_candidates,
            "candidates_to_send": candidates_to_send,
        }

    for candidate in chain_candidates:
        key = chain_duplicate_key(candidate, search_request)

        if key in seen_this_run:
            duplicate_candidates.append(candidate)
            continue

        seen_this_run.add(key)
        selected_candidates.append(candidate)

        if key in sent_history:
            already_sent_candidates.append(candidate)
            continue

        candidates_to_send.append(candidate)

        if len(candidates_to_send) >= limit:
            break

    return {
        "selected_candidates": selected_candidates,
        "duplicate_candidates": duplicate_candidates,
        "already_sent_candidates": already_sent_candidates,
        "candidates_to_send": candidates_to_send,
    }
