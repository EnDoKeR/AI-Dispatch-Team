from app.market_intelligence.reload_chain_identity import (
    chain_identity,
    is_same_load,
    load_identity,
)
from app.market_intelligence.reload_chain_location import (
    city_state_key,
    pickup_near_first_delivery,
    same_state,
)
from app.market_intelligence.reload_chain_rules import (
    is_good_reload_load,
    is_strong_first_load,
    is_wrong_direction_block,
)
from app.market_intelligence.reload_chain_scoring import build_chain_score


__all__ = [
    "build_chain_candidates",
    "build_chain_score",
    "chain_identity",
    "city_state_key",
    "is_good_reload_load",
    "is_same_load",
    "is_strong_first_load",
    "is_wrong_direction_block",
    "load_identity",
    "pickup_near_first_delivery",
    "same_state",
]


def build_chain_candidates(loads, search_request, limit=5):
    candidates = []
    seen_first_loads = set()
    seen_chains = set()

    for first_load in loads:
        first_key = load_identity(first_load)

        if first_key in seen_first_loads:
            continue

        if not is_wrong_direction_block(first_load):
            continue

        if not is_strong_first_load(first_load):
            continue

        best_reload = None
        best_chain_data = None

        for reload_load in loads:
            if is_same_load(first_load, reload_load):
                continue

            if not pickup_near_first_delivery(first_load, reload_load):
                continue

            if not is_good_reload_load(reload_load, search_request):
                continue

            chain_data = build_chain_score(first_load, reload_load)

            if best_chain_data is None:
                best_reload = reload_load
                best_chain_data = chain_data
                continue

            if chain_data["chain_score"] > best_chain_data["chain_score"]:
                best_reload = reload_load
                best_chain_data = chain_data

        if best_reload:
            chain_key = chain_identity(
                first_load,
                best_reload,
                search_request,
            )

            if chain_key in seen_chains:
                continue

            seen_first_loads.add(first_key)
            seen_chains.add(chain_key)

            candidates.append(
                {
                    "first_load": first_load,
                    "reload_load": best_reload,
                    "chain_data": best_chain_data,
                }
            )

    candidates = sorted(
        candidates,
        key=lambda item: (
            item["chain_data"]["chain_score"],
            item["chain_data"]["total_gross"],
            item["chain_data"]["total_rpm"],
        ),
        reverse=True,
    )

    return candidates[:limit]
