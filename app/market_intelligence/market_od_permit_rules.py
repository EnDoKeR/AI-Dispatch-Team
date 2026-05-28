OD_KEYWORDS = [
    "permit load",
    "permits required",
    "permit required",
    "over dimension",
    "over-dimensional",
    "overdimensional",
    "oversize",
    "over size",
    "wide load",
    "od load",
    "os/ow",
]


def is_od_or_permit_load(parsed_notes, notes_lower):
    parsed_notes = parsed_notes or {}

    is_od_note = bool(
        parsed_notes.get("is_od")
        or parsed_notes.get("is_oversize")
        or parsed_notes.get("is_wide")
        or parsed_notes.get("requires_permit")
        or parsed_notes.get("permit_load")
    )

    if any(keyword in notes_lower for keyword in OD_KEYWORDS):
        is_od_note = True

    return is_od_note


def apply_od_permit_rules(load, search_request, parsed_notes, notes_lower):
    if not is_od_or_permit_load(parsed_notes, notes_lower):
        return load

    load.is_od = True

    if str(search_request.equipment or "").lower() == "conestoga":
        load.is_blocked = True
        load.block_reasons.append(
            "OD / permit / wide load detected; Conestoga should not take OD loads."
        )
        return load

    load.is_review_once = True
    load.review_reasons.append(
        "OD / permit / wide load detected; dispatcher must verify permits/dimensions."
    )

    return load
