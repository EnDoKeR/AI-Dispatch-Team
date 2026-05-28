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

    message += f"вљ пёЏ SEARCH HEALTH CHECK вЂ” {search_request.driver_name}\n\n"
    message += f"Location: {search_request.current_location}\n"
    message += f"Monitored: ~{monitored_minutes} min\n\n"

    message += "No strong matching loads found with current filters.\n\n"

    message += "Current filters:\n"
    message += f"- Max weight: {search_request.max_weight}\n"
    message += f"- Max empty: {search_request.max_empty_miles} mi\n"
    message += f"- Preferred RPM: {search_request.min_total_rpm}\n"
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

    suggestions = []

    combined_reasons = " ".join(reason_counts.keys()).lower()

    far_pickup_count = 0
    target_mismatch_count = 0
    conestoga_od_count = 0
    low_rpm_count = 0
    overweight_count = 0
    tarps_count = 0
    no_conestoga_count = 0
    same_city_count = 0
    local_load_count = 0
    document_count = 0
    tracking_count = 0

    for reason, count in reason_counts.items():
        reason_text = str(reason or "").lower()

        if "pickup appears too far" in reason_text:
            far_pickup_count += count

        if "does not match target direction" in reason_text:
            target_mismatch_count += count

        if (
            "conestoga should not take od" in reason_text
            or "od / permit / wide load detected" in reason_text
        ):
            conestoga_od_count += count

        if "rpm $" in reason_text and "below minimum" in reason_text:
            low_rpm_count += count

        if "weight" in reason_text and (
            "above driver setting" in reason_text
            or "above conestoga driver setting" in reason_text
            or "overweight" in reason_text
        ):
            overweight_count += count

        if "tarps required" in reason_text or "tarp required" in reason_text:
            tarps_count += count

        if (
            "conestoga is not accepted" in reason_text
            or "no conestoga" in reason_text
            or "flatbed only" in reason_text
        ):
            no_conestoga_count += count

        if "same pickup and delivery city" in reason_text:
            same_city_count += count

        if "loaded miles are too low" in reason_text or "local load" in reason_text:
            local_load_count += count

        if (
            "document" in reason_text
            or "tanker" in reason_text
            or "twic" in reason_text
            or "hazmat" in reason_text
            or "legal status" in reason_text
        ):
            document_count += count

        if "tracking required" in reason_text:
            tracking_count += count

    if target_mismatch_count:
        suggestions.append(
            "Most blocked loads are outside target direction. Consider changing target direction or checking reload-chain options."
        )

    if far_pickup_count:
        suggestions.append(
            "Many loads are too far from driver location. This is expected if test loads are from another state; use a matching test search area for those loads."
        )

    if conestoga_od_count:
        suggestions.append(
            "Conestoga is correctly blocking OD / permit / wide loads. Keep this rule strict."
        )

    if no_conestoga_count:
        suggestions.append(
            "Some loads explicitly reject Conestoga. Keep blocking No Conestoga / flatbed-only postings."
        )

    if low_rpm_count:
        suggestions.append(
            "Some loads are below minimum RPM. Consider lowering min RPM only if the market is weak and reload plan is strong."
        )

    if overweight_count:
        suggestions.append(
            "Some loads are above driver max weight. Ask driver only if close to limit; otherwise keep blocked."
        )

    if tarps_count and str(search_request.equipment or "").lower() != "conestoga":
        suggestions.append(
            "Flatbed tarp requirements are blocking or creating review items. Confirm driver tarp capability and max tarp size in driver profile."
        )

    if tarps_count and str(search_request.equipment or "").lower() == "conestoga":
        suggestions.append(
            "Tarp-required loads should not block Conestoga unless notes also say No Conestoga / flatbed only / OD."
        )

    if same_city_count or local_load_count:
        suggestions.append(
            "Local or same-city loads are being filtered. This is usually correct unless dispatcher wants local partials."
        )

    if document_count:
        suggestions.append(
            "Some loads need driver documents. Ask once and save answers in driver profile."
        )

    if tracking_count:
        suggestions.append(
            "Tracking-required loads depend on driver tracking preference. Confirm tracking_ok in driver profile."
        )

    if not suggestions and review_once_loads:
        suggestions.append(
            "There are review-once options available. Check them manually before relaxing filters."
        )

    if not suggestions:
        suggestions.append(
            "Keep monitoring or expand search radius / target direction."
        )

    for suggestion in suggestions[:5]:
        message += f"- {suggestion}\n"

    message += "\nRecommendation:\n"

    if top_opportunities:
        message += "Clean opportunities exist. Focus on top matches first."
    elif review_once_loads:
        message += "No clean matches, but review-once options exist. Check the safest exceptions first."
    elif far_pickup_count and target_mismatch_count:
        message += "Current test load set does not fit this driver location/direction. Use a matching search request for this market."
    else:
        message += "Consider relaxing one filter or keep monitoring."

    return message
