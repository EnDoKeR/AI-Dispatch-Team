def build_market_explanation(stats, recommendation):
    best_bucket = recommendation["best_bucket"]
    best_data = stats[best_bucket]

    explanation = []

    explanation.append(
        f"Market activity is {recommendation['market_activity']} based on all current available loads."
    )

    explanation.append(
        f"Driver fit is {recommendation['driver_fit']} based on clean matches and review-once options."
    )

    explanation.append(
        f"Best distance bucket is {best_bucket} miles."
    )

    explanation.append(
        f"This bucket has {best_data['total_loads']} total loads, "
        f"{best_data['qualified_loads']} qualified loads, "
        f"{best_data['good_loads']} good loads, "
        f"{best_data['clean_match_loads']} clean matches, "
        f"and {best_data['review_once_loads']} review-once options."
    )

    explanation.append(
        f"Average total RPM in this bucket is ${best_data['avg_total_rpm']}."
    )

    explanation.append(
        f"Average gross in this bucket is ${best_data['avg_rate']}."
    )

    explanation.append(
        f"Average score for clean matches is {best_data['avg_clean_match_score']}."
    )

    explanation.append(
        f"Average score for review-once loads is {best_data['avg_review_once_score']}."
    )

    return explanation
