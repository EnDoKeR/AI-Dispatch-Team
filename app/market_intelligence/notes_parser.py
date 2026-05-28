from app.market_intelligence.notes_parser_text_helpers import (
    clean_text,
    lower_text,
    normalize_email,
    normalize_phone,
    normalize_text,
)


from app.market_intelligence.notes_parser_securement import (
    detect_number_of_straps,
    detect_straps_required,
    detect_tarp_required,
    detect_tarp_size,
)


from app.market_intelligence.notes_parser_dimensions import (
    detect_dimensions,
    detect_od,
    detect_overweight,
)


from app.market_intelligence.notes_parser_equipment import (
    detect_conestoga_ok,
    detect_flatbed_preferred,
    detect_flatbed_required,
    detect_no_box_truck,
    detect_no_conestoga,
    detect_stepdeck_allowed,
)


from app.market_intelligence.notes_parser_load_requirements import (
    detect_appointment_required,
    detect_forklift_required,
    detect_ramps_required,
    detect_straight_through,
    detect_tracking_required,
)


from app.market_intelligence.notes_parser_payment import (
    detect_cash_or_zelle,
    detect_quickpay_review,
)


from app.market_intelligence.notes_parser_documents import (
    detect_document_required,
    detect_hazmat_required,
    detect_iso_tank_required,
    detect_tanker_required,
    detect_twic_required,
)


from app.market_intelligence.notes_parser_weight_stops import (
    detect_stops_from_text,
    detect_weight_from_text,
    detect_weight_unknown,
)


from app.market_intelligence.notes_parser_pickup import (
    detect_actual_pickup_city,
    detect_extra_pickup,
    detect_multiple_loads_available,
    detect_pickup_time_from_text,
)


from app.market_intelligence.notes_parser_contact import detect_contact_override


from app.market_intelligence.notes_parser_flags import (
    detect_dedicated_lane,
    detect_double_brokering_language,
    detect_mc_must_match,
)


def parse_notes(notes="", commodity="", posted_trailer_type="", posted_weight=0):
    combined_text = " ".join(
        [
            normalize_text(notes),
            normalize_text(commodity),
            normalize_text(posted_trailer_type),
        ]
    )

    detected_weight = detect_weight_from_text(combined_text)
    detected_stops = detect_stops_from_text(combined_text)
    detected_pickup_time = detect_pickup_time_from_text(combined_text)
    detected_contact = detect_contact_override(combined_text)
    detected_actual_pickup_city = detect_actual_pickup_city(combined_text)
    detected_dimensions = detect_dimensions(combined_text)
    tarp_size = detect_tarp_size(combined_text)
    strap_count = detect_number_of_straps(combined_text)

    flags = {
        "requires_tarp": detect_tarp_required(combined_text),
        "tarp_size": tarp_size,

        "requires_straps": detect_straps_required(combined_text),
        "strap_count": strap_count,

        "is_od": detect_od(combined_text),
        "dimensions": detected_dimensions,

        "is_overweight": detect_overweight(combined_text),
        "no_conestoga": detect_no_conestoga(combined_text),
        "conestoga_ok": detect_conestoga_ok(combined_text),
        "flatbed_required": detect_flatbed_required(combined_text),
        "flatbed_preferred": detect_flatbed_preferred(combined_text),
        "stepdeck_allowed": detect_stepdeck_allowed(combined_text),
        "no_box_truck": detect_no_box_truck(combined_text),

        "forklift_required": detect_forklift_required(combined_text),
        "ramps_required": detect_ramps_required(combined_text),
        "tracking_required": detect_tracking_required(combined_text),
        "appointment_required": detect_appointment_required(combined_text),
        "straight_through": detect_straight_through(combined_text),

        "cash_or_zelle": detect_cash_or_zelle(combined_text),
        "quickpay_review": detect_quickpay_review(combined_text),

        "hazmat_required": detect_hazmat_required(combined_text),
        "tanker_required": detect_tanker_required(combined_text),
        "twic_required": detect_twic_required(combined_text),
        "document_required": detect_document_required(combined_text),
        "iso_tank_required": detect_iso_tank_required(combined_text),

        "weight_unknown": detect_weight_unknown(combined_text, posted_weight),
        "detected_weight": detected_weight,
        "detected_stops": detected_stops,
        "detected_pickup_time": detected_pickup_time,
        "detected_contact": detected_contact,
        "actual_pickup_city": detected_actual_pickup_city,

        "extra_pickup": detect_extra_pickup(combined_text),
        "multiple_loads_available": detect_multiple_loads_available(combined_text),
        "dedicated_lane": detect_dedicated_lane(combined_text),
        "double_brokering_language": detect_double_brokering_language(combined_text),
        "mc_must_match": detect_mc_must_match(combined_text),
    }

    notes_summary = []

    if flags["requires_tarp"]:
        if tarp_size:
            notes_summary.append(f"{tarp_size} tarps detected")
        else:
            notes_summary.append("tarps detected")

    if flags["requires_straps"]:
        if strap_count:
            notes_summary.append(f"{strap_count} straps required")
        else:
            notes_summary.append("straps required")

    if flags["is_od"]:
        notes_summary.append("OD / permit / wide load detected")

    if detected_dimensions["raw"]:
        notes_summary.append(f"dimensions detected: {detected_dimensions['raw']}")

    if flags["is_overweight"]:
        notes_summary.append("overweight detected")

    if flags["no_conestoga"]:
        notes_summary.append("Conestoga may not be accepted")

    if flags["conestoga_ok"]:
        notes_summary.append("Conestoga appears acceptable")

    if flags["flatbed_required"]:
        notes_summary.append("flatbed required")

    if flags["flatbed_preferred"]:
        notes_summary.append("flatbed preferred; verify Conestoga acceptance")

    if flags["stepdeck_allowed"]:
        notes_summary.append("flatbed or step deck allowed")

    if flags["no_box_truck"]:
        notes_summary.append("no box truck")

    if flags["forklift_required"]:
        notes_summary.append("forklift / moffett / unloading equipment detected")

    if flags["ramps_required"]:
        notes_summary.append("ramps required")

    if flags["tracking_required"]:
        notes_summary.append("tracking required")

    if flags["appointment_required"]:
        notes_summary.append("appointment required")

    if flags["straight_through"]:
        notes_summary.append("straight-through delivery detected")

    if flags["cash_or_zelle"]:
        notes_summary.append("cash/Zelle payment language detected")

    if flags["quickpay_review"]:
        notes_summary.append("QuickPay language detected; check broker MC")

    if flags["hazmat_required"]:
        notes_summary.append("hazmat required")

    if flags["tanker_required"]:
        notes_summary.append("tanker endorsement required")

    if flags["twic_required"]:
        notes_summary.append("TWIC required")

    if flags["document_required"]:
        notes_summary.append("driver document requirement detected")

    if flags["iso_tank_required"]:
        notes_summary.append("ISO tank document/review warning detected")

    if flags["weight_unknown"]:
        notes_summary.append("posted weight may be incorrect / must verify real weight")

    if detected_weight:
        notes_summary.append(f"weight detected from notes: {detected_weight}")

    if detected_stops:
        notes_summary.append(f"stops detected from notes: {detected_stops}")

    if detected_pickup_time:
        notes_summary.append(f"pickup time detected from notes: {detected_pickup_time}")

    if detected_contact["phone"] or detected_contact["email"]:
        contact_parts = []

        if detected_contact["phone"]:
            phone_text = detected_contact["phone"]
            if detected_contact["extension"]:
                phone_text += f" x{detected_contact['extension']}"
            contact_parts.append(phone_text)

        if detected_contact["email"]:
            contact_parts.append(detected_contact["email"])

        notes_summary.append("contact override detected: " + " / ".join(contact_parts))

    if detected_actual_pickup_city:
        notes_summary.append(f"actual pickup city detected from notes: {detected_actual_pickup_city}")

    if flags["extra_pickup"]:
        notes_summary.append("extra pickup detected")

    if flags["multiple_loads_available"]:
        notes_summary.append("multiple loads available")

    if flags["dedicated_lane"]:
        notes_summary.append("dedicated lane / solid driver language detected")

    if flags["double_brokering_language"]:
        notes_summary.append("double brokering language detected")

    if flags["mc_must_match"]:
        notes_summary.append("MC / carrier name must match")

    flags["notes_summary"] = notes_summary

    return flags
