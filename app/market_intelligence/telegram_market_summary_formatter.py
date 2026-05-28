from app.market_intelligence.telegram_text_helpers import (
    delivery_zone_outlook,
    safe_value,
)


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

    message += f"СЂСџвЂњР‰ MARKET SNAPSHOT РІР‚вЂќ {search_request.driver_name}\n\n"
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
        message += f"{best_load.pickup} РІвЂ вЂ™ {best_load.delivery}\n"
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
