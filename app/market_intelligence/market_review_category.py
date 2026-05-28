def classify_review_category(load):
    all_reason_parts = []

    for attr_name in [
        "review_reasons",
        "driver_match_notes",
        "block_reasons",
        "match_reasons",
    ]:
        value = getattr(load, attr_name, [])

        if isinstance(value, list):
            all_reason_parts.extend(str(item) for item in value)
        elif value:
            all_reason_parts.append(str(value))

    notes = str(getattr(load, "notes", "") or "").lower()
    commodity = str(getattr(load, "commodity", "") or "").lower()

    reasons = " ".join(all_reason_parts).lower()

    if (
        "rate is missing" in reasons
        or "posted as $0" in reasons
        or "rate check" in reasons
        or "check rate with broker" in reasons
    ):
        return "RATE CHECK"

    if (
        "broker memory requires review" in reasons
        or "broker memory shows rate negotiation risk" in reasons
        or "broker memory watchlist" in reasons
    ):
        return "BROKER REVIEW"

    if (
        "od / permit" in reasons
        or "od load" in reasons
        or "over dimension" in reasons
        or "overdimensional" in reasons
        or "permit load" in reasons
        or "permits required" in reasons
        or "permit required" in reasons
        or "wide load" in reasons
        or "oversize" in reasons
        or "over size" in reasons
        or "os/ow" in reasons
        or "od / permit" in notes
        or "od load" in notes
        or "permit load" in notes
        or "permits required" in notes
        or "permit required" in notes
        or "wide load" in notes
        or "oversize" in notes
        or "over size" in notes
        or "over-dimensional" in notes
        or "overdimensional" in notes
        or "os/ow" in notes
    ):
        return "OD / PERMIT"

    if (
        "conestoga must be verified" in reasons
        or "posted as flatbed/step deck" in reasons
        or "conestoga verify" in reasons
    ):
        return "CONESTOGA VERIFY"

    if "along route" in reasons:
        return "ALONG ROUTE"

    document_terms = [
        "hazmat",
        "haz mat",
        "tanker endorsement",
        "tank endorsement",
        "twic",
        "us citizen",
        "u.s. citizen",
        "green card",
        "work permit",
        "legal status",
        "ramps required",
        "need ramps",
        "dunnage",
        "must provide wood",
        "provide wood",
        "wood required",
        "blocking and bracing",
        "block and brace",
        "iso tank",
        "iso tanks",
    ]

    if any(term in reasons for term in document_terms):
        return "DOCUMENTS REQUIRED"

    if "iso tank" in notes or "iso tanks" in notes:
        return "DOCUMENTS REQUIRED"

    if "iso tank" in commodity or "iso tanks" in commodity:
        return "DOCUMENTS REQUIRED"

    if "strong off-target" in reasons:
        return "STRONG OFF-TARGET"

    if (
        "pickup time" in reasons
        or "delivery time" in reasons
        or "time check" in reasons
        or "needs check" in reasons
    ):
        return "TIME CHECK"

    if "weight" in reasons:
        return "WEIGHT CHECK"

    if (
        "tarps required" in reasons
        or "tarp required" in reasons
        or "ft tarps" in reasons
    ):
        return "TARPS REQUIRED"

    return "GENERAL REVIEW"
