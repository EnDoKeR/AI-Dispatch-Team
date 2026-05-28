NO_CONESTOGA_TERMS = [
    "no conestoga",
    "no conestogas",
    "no stoga",
    "no stogas",
    "conestoga wouldn't work",
    "conestoga wont work",
    "conestoga will not work",
    "flatbed only",
]


def apply_conestoga_rules(load, equipment, notes_lower, posted_lower):
    if "conestoga" not in equipment:
        return load

    if any(term in notes_lower for term in NO_CONESTOGA_TERMS):
        load.is_blocked = True
        load.block_reasons.append("Notes say Conestoga is not accepted.")
        return load

    if "flatbed" in posted_lower or "step" in posted_lower or posted_lower in ["f", "fd", "ft"]:
        load.is_review_once = True
        load.review_reasons.append(
            "Posted as Flatbed/Step Deck; Conestoga must be verified."
        )

    return load
