from app.market_intelligence.market_document_requirements import (
    require_driver_document,
    require_one_of_driver_documents,
)


def apply_document_triggers(load, search_request, combined_text):
    # Hazmat
    if (
        "hazmat" in combined_text
        or "haz mat" in combined_text
        or "haz-mat" in combined_text
        or "hazardous" in combined_text
    ):
        require_driver_document(
            load,
            search_request,
            "driver_hazmat",
            "Hazmat certificate",
        )

    # Tanker endorsement
    if (
        "tanker" in combined_text
        or "tank endorsement" in combined_text
        or "tanker endorsement" in combined_text
        or "tanker endorsment" in combined_text
        or "tanker endoresment" in combined_text
    ):
        require_driver_document(
            load,
            search_request,
            "driver_tanker_endorsement",
            "Tanker endorsement",
        )

    # TWIC card
    if (
        "twic" in combined_text
        or "twic card" in combined_text
    ):
        require_driver_document(
            load,
            search_request,
            "driver_twic",
            "TWIC card",
        )

    # US legal status
    if (
        "us citizen" in combined_text
        or "u.s. citizen" in combined_text
        or "citizen required" in combined_text
        or "green card" in combined_text
        or "green-card" in combined_text
        or "permanent resident" in combined_text
        or "work permit" in combined_text
        or "employment authorization" in combined_text
        or "ead card" in combined_text
    ):
        require_one_of_driver_documents(
            load,
            search_request,
            [
                ("driver_us_citizen", "US citizen"),
                ("driver_green_card_holder", "Green card"),
                ("driver_work_permit", "Work permit"),
            ],
            "US legal status",
        )

    # Ramps
    if (
        "need ramps" in combined_text
        or "ramps required" in combined_text
        or "ramps req" in combined_text
        or "need ramp" in combined_text
    ):
        require_driver_document(
            load,
            search_request,
            "driver_ramps",
            "Ramps",
        )

    # Dunnage / wood / blocking / bracing
    if (
        "dunnage" in combined_text
        or "must provide wood" in combined_text
        or "provide wood" in combined_text
        or "wood required" in combined_text
        or "blocking and bracing" in combined_text
        or "block and brace" in combined_text
    ):
        require_driver_document(
            load,
            search_request,
            "driver_dunnage",
            "Dunnage / wood / blocking material",
        )

    return load
