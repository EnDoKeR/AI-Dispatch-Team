def print_driver_report(
    request_file,
    stats,
    recommendation,
    top_opportunities,
    review_once_loads,
    search_request,
    chain_candidates,
):
    print("\nReload Chain Candidates:")
    if not chain_candidates:
        print("No reload chain candidates.")

    for index, candidate in enumerate(chain_candidates, start=1):
        first_load = candidate["first_load"]
        reload_load = candidate["reload_load"]
        chain_data = candidate["chain_data"]

        print(
            f"{index}. {first_load.pickup} -> {first_load.delivery} "
            f"+ {reload_load.pickup} -> {reload_load.delivery} | "
            f"Gross ${chain_data['total_gross']} | "
            f"RPM ${chain_data['total_rpm']} | "
            f"Score {chain_data['chain_score']}"
        )

    print("\n" + "=" * 60)
    print(f"ACTIVE SEARCH: {request_file}")
    print("=" * 60)

    print(f"Driver: {search_request.driver_name}")
    print(f"Location: {search_request.current_location}")
    print(f"Available: {search_request.available_time}")
    print(f"Equipment: {search_request.equipment}")
    print(f"Driver Max Weight: {search_request.max_weight}")
    print(f"Default Max Empty: {search_request.max_empty_miles}")
    print(f"Target Direction: {search_request.target_direction}")

    print("\nMarket:")
    print(f"Market Activity: {recommendation['market_activity']}")
    print(f"Driver Fit: {recommendation['driver_fit']}")
    print(f"Action Status: {recommendation['action_status']}")
    print(f"Best Bucket: {recommendation['best_bucket']}")
    print(f"Good Loads: {recommendation['total_good_loads']}")
    print(f"Qualified Loads: {recommendation['total_qualified_loads']}")
    print(f"Clean Matches: {recommendation['total_clean_matches']}")
    print(f"Review Once: {recommendation['total_review_once']}")
    print(f"Blocked: {recommendation['total_blocked']}")

    print("\nTop Match Opportunities:")
    if not top_opportunities:
        print("No clean match opportunities.")

    for index, load in enumerate(top_opportunities, start=1):
        print(
            f"{index}. {load.pickup} -> {load.delivery} | "
            f"${load.rate} | RPM ${load.total_rpm} | "
            f"Score {load.opportunity_score()} | {load.suggested_action()}"
        )

    print("\nReview Once Opportunities:")
    if not review_once_loads:
        print("No review-once opportunities.")

    for index, load in enumerate(review_once_loads, start=1):
        print(
            f"{index}. {load.pickup} -> {load.delivery} | "
            f"${load.rate} | RPM ${load.total_rpm} | "
            f"Score {load.opportunity_score()} | Notes: {load.driver_match_notes}"
        )
