import re


def get_tarp_size_feet(text):
    text = str(text or "").lower()

    match = re.search(
        r"\b(4|6|8)\s*(?:ft|feet|foot|['РІР‚в„ў])\b",
        text,
    )

    if not match:
        return 0

    return int(match.group(1))


def detect_tarps_requirement(text):
    text = str(text or "").lower()

    no_tarp_terms = [
        "no tarp",
        "no tarps",
        "no tarping",
        "no tarp required",
        "no tarps required",
        "does not need tarps",
        "tarps not required",
        "tarp not required",
    ]

    if any(term in text for term in no_tarp_terms):
        return False, 0

    tarp_patterns = [
        r"\b4\s*(?:ft|feet|foot|['РІР‚в„ў])\s*tarps?\b",
        r"\b6\s*(?:ft|feet|foot|['РІР‚в„ў])\s*tarps?\b",
        r"\b8\s*(?:ft|feet|foot|['РІР‚в„ў])\s*tarps?\b",
        r"\b4ft\s*tarps?\b",
        r"\b6ft\s*tarps?\b",
        r"\b8ft\s*tarps?\b",
        r"\btarps?\s*required\b",
        r"\btarps?\s*req\b",
        r"\bneed\s*tarps?\b",
        r"\bneeds\s*tarps?\b",
        r"\bmust\s*tarp\b",
        r"\btarping\s*required\b",
    ]

    for pattern in tarp_patterns:
        if re.search(pattern, text):
            required_size = get_tarp_size_feet(text)
            return True, required_size

    return None, 0


def apply_tarps_requirement(load, search_request, combined_text):
    tarps_required, required_tarp_size = detect_tarps_requirement(combined_text)

    if tarps_required is not True:
        return load

    driver_equipment = str(
        getattr(search_request, "equipment", "") or ""
    ).lower()

    if "conestoga" in driver_equipment:
        if required_tarp_size:
            load.match_reasons.append(
                f"{required_tarp_size} ft tarp requirement covered by Conestoga."
            )
        else:
            load.match_reasons.append(
                "Tarp requirement covered by Conestoga."
            )

        return load

    driver_can_take_tarps_value = getattr(
        search_request,
        "driver_can_take_tarps",
        None,
    )

    driver_max_tarp_size_value = getattr(
        search_request,
        "driver_max_tarp_size",
        "",
    )

    driver_max_tarp_size_feet = get_tarp_size_feet(
        driver_max_tarp_size_value
    )

    if driver_can_take_tarps_value is True:
        if (
            required_tarp_size
            and driver_max_tarp_size_feet
            and required_tarp_size > driver_max_tarp_size_feet
        ):
            load.is_review_once = True
            load.review_reasons.append(
                f"{required_tarp_size} ft tarps required, but driver max tarp size is {driver_max_tarp_size_feet} ft."
            )
            return load

        if required_tarp_size:
            load.match_reasons.append(
                f"{required_tarp_size} ft tarps accepted by driver profile."
            )
        else:
            load.match_reasons.append(
                "Tarps accepted by driver profile."
            )

        return load

    if driver_can_take_tarps_value is False:
        load.is_blocked = True

        if required_tarp_size:
            load.block_reasons.append(
                f"{required_tarp_size} ft tarps required, but driver profile says driver cannot take tarps."
            )
        else:
            load.block_reasons.append(
                "Tarps required, but driver profile says driver cannot take tarps."
            )

        return load

    load.is_review_once = True

    if required_tarp_size:
        load.review_reasons.append(
            f"{required_tarp_size} ft tarps required; ask driver and save answer in driver profile."
        )
    else:
        load.review_reasons.append(
            "Tarps required; ask driver and save answer in driver profile."
        )

    return load
