from app.market_intelligence.telegram_notifier import (
    send_market_summary_to_telegram,
    send_review_once_to_telegram,
    send_search_health_check_to_telegram,
    send_top_opportunities_to_telegram,
)


def send_market_snapshot_to_telegram(
    stats,
    recommendation,
    top_opportunities,
    review_once_loads,
    search_request,
    loads,
    search_location="",
):
    telegram_loads = top_opportunities

    print(f"\n===== TELEGRAM SUMMARY SEND - {search_request.driver_name} =====\n")

    send_market_summary_to_telegram(
        stats,
        recommendation,
        top_opportunities,
        search_request,
        search_location=search_location,
    )

    print(f"\n===== TELEGRAM MATCH LOADS SEND - {search_request.driver_name} =====\n")

    send_top_opportunities_to_telegram(
        telegram_loads,
        search_request,
        limit=3,
    )

    print(f"\n===== TELEGRAM REVIEW ONCE SEND - {search_request.driver_name} =====\n")

    send_review_once_to_telegram(
        review_once_loads,
        search_request,
        limit=3,
    )

    print(f"\n===== TELEGRAM SEARCH HEALTH CHECK - {search_request.driver_name} =====\n")

    send_search_health_check_to_telegram(
        search_request,
        loads,
        top_opportunities,
        review_once_loads,
        monitored_minutes=30,
    )
