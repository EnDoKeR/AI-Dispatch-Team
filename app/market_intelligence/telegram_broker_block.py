import re

from app.market_intelligence.broker_memory_rules import (
    format_broker_memory_status,
    get_broker_memory_status,
)


def get_broker_status_text(load, broker_mc_override=None):
    existing_status = str(getattr(load, "broker_status", "") or "").strip()

    if broker_mc_override is None:
        broker_mc = str(getattr(load, "broker_mc", "") or "").strip()
    else:
        broker_mc = str(broker_mc_override or "").strip()

    invalid_mc_values = [
        "",
        "NEEDS CHECK",
        "NO MC",
        "UNKNOWN",
        "NONE",
    ]

    if broker_mc.upper() in invalid_mc_values:
        return "NEEDS MC CHECK"

    memory_status = get_broker_memory_status(broker_mc)
    memory_status_name = memory_status.get("status", "UNKNOWN")

    if memory_status_name and memory_status_name != "UNKNOWN":
        return format_broker_memory_status(memory_status)

    if existing_status and existing_status.upper() != "BUY":
        return existing_status

    return "UNKNOWN"


def broker_block(load):
    """
    Builds a clean broker/contact block for Telegram.

    Uses structured fields first.
    If some fields are missing, tries to extract useful broker/contact data
    from notes because DAT notes often contain broker, MC, phone, email,
    reference ID, factoring and credit information.
    """

    notes = str(getattr(load, "notes", "") or "")

    broker_name = str(getattr(load, "broker_name", "") or "").strip()
    broker_mc = str(getattr(load, "broker_mc", "") or "").strip()
    reference_id = str(getattr(load, "reference_id", "") or "").strip()

    primary_phone = str(getattr(load, "primary_phone", "") or "").strip()
    primary_email = str(getattr(load, "primary_email", "") or "").strip()

    broker_contact = str(getattr(load, "broker_contact", "") or "").strip()
    credit_score = str(getattr(load, "credit_score", "") or "").strip()
    days_to_pay = str(getattr(load, "days_to_pay", "") or "").strip()

    # Do not treat email as phone.
    if "@" in primary_phone:
        primary_phone = ""

    if "@" in broker_contact and not primary_email:
        primary_email = broker_contact

    # Only infer broker name from notes if notes look like a DAT broker block.
    notes_looks_like_broker_block = (
        "mc#" in notes.lower()
        or "contact:" in notes.lower()
        or "reference id" in notes.lower()
        or "factoring" in notes.lower()
    )

    if not broker_name and "|" in notes and notes_looks_like_broker_block:
        possible_broker = notes.split("|")[0].strip()

        # Avoid using normal cargo comments as broker name.
        bad_broker_phrases = [
            "tarp required",
            "no tarps",
            "od load",
            "flatbed posting",
            "test load",
            "overweight load",
        ]

        if possible_broker and not any(
            phrase in possible_broker.lower()
            for phrase in bad_broker_phrases
        ):
            broker_name = possible_broker

    if not broker_mc:
        mc_match = re.search(
            r"\bMC\s*#?\s*(\d+)\b",
            notes,
            re.IGNORECASE,
        )

        if mc_match:
            broker_mc = mc_match.group(1).strip()

    if not reference_id:
        ref_match = re.search(
            r"\bReference\s*ID\s*:\s*([A-Za-z0-9\-]+)",
            notes,
            re.IGNORECASE,
        )

        if ref_match:
            reference_id = ref_match.group(1).strip()

    if not credit_score or credit_score == "0":
        credit_match = re.search(
            r"\bCredit\s*Score\s*:\s*(\d+)",
            notes,
            re.IGNORECASE,
        )

        if credit_match:
            credit_score = credit_match.group(1).strip()

    if not days_to_pay or days_to_pay == "0":
        days_match = re.search(
            r"\bDays\s*to\s*Pay\s*:\s*(\d+)",
            notes,
            re.IGNORECASE,
        )

        if days_match:
            days_to_pay = days_match.group(1).strip()

    factoring_text = ""

    if "factoring eligible" in notes.lower():
        factoring_text = "Factoring: Eligible"
    elif "factoring status not clearly shown" in notes.lower():
        factoring_text = "Factoring: NEEDS CHECK"

    if not primary_phone and broker_contact and "@" not in broker_contact:
        primary_phone = broker_contact

    text = ""

    text += "Broker / Contact:\n"

    if broker_name:
        text += f"Broker: {broker_name}\n"
    else:
        text += "Broker: NEEDS CHECK\n"

    if broker_mc:
        text += f"MC: {broker_mc}\n"
    else:
        text += "MC: NEEDS CHECK\n"

    if primary_phone:
        text += f"Phone: {primary_phone}\n"
    else:
        text += "Phone: NEEDS CHECK\n"

    if primary_email:
        text += f"Email: {primary_email}\n"
    else:
        text += "Email: NEEDS CHECK\n"

    if reference_id:
        text += f"Reference ID: {reference_id}\n"
    else:
        text += "Reference ID: NO ID\n"

    if credit_score and credit_score != "0":
        text += f"Credit Score: {credit_score}\n"

    if days_to_pay and days_to_pay != "0":
        text += f"Days to Pay: {days_to_pay}\n"

    if factoring_text:
        text += f"{factoring_text}\n"

    text += f"Broker Status: {get_broker_status_text(load, broker_mc_override=broker_mc)}\n"

    return text
