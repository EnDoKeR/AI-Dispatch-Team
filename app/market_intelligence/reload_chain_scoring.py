def build_chain_score(first_load, reload_load):
    total_gross = first_load.rate + reload_load.rate
    total_miles = first_load.total_miles + reload_load.total_miles

    if total_miles == 0:
        total_rpm = 0
    else:
        total_rpm = round(total_gross / total_miles, 2)

    score = 0

    if total_rpm >= 3.0:
        score += 40
    elif total_rpm >= 2.5:
        score += 25

    if total_gross >= 6500:
        score += 30
    elif total_gross >= 5000:
        score += 20

    if first_load.empty_miles <= 100:
        score += 15

    if reload_load.empty_miles <= 150:
        score += 15

    return {
        "total_gross": total_gross,
        "total_miles": total_miles,
        "total_rpm": total_rpm,
        "chain_score": score,
    }
