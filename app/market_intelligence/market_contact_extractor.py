import re


def collect_contact_candidates(parsed_contact, broker_contact="", broker_contact_raw="", notes=""):
    candidates = []

    if isinstance(parsed_contact, dict):
        for key in ["email", "emails", "contact_email", "phone", "phones", "contact_phone"]:
            value = parsed_contact.get(key)

            if isinstance(value, list):
                candidates.extend(value)
            elif value:
                candidates.append(value)

    candidates.extend([
        broker_contact,
        broker_contact_raw,
        notes,
    ])

    return candidates


def extract_email(parsed_contact, broker_contact="", broker_contact_raw="", notes=""):
    candidates = []

    if isinstance(parsed_contact, dict):
        for key in ["email", "emails", "contact_email"]:
            value = parsed_contact.get(key)

            if isinstance(value, list):
                candidates.extend(value)
            elif value:
                candidates.append(value)

    candidates.extend([
        broker_contact,
        broker_contact_raw,
        notes,
    ])

    combined = " ".join(str(item or "") for item in candidates)

    combined = combined.replace("`", ".")
    combined = combined.replace(" dot ", ".")
    combined = combined.replace("[dot]", ".")
    combined = combined.replace("(dot)", ".")
    combined = combined.replace(" at ", "@")
    combined = combined.replace("[at]", "@")
    combined = combined.replace("(at)", "@")

    match = re.search(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
        combined,
    )

    if match:
        return match.group(0).strip()

    return ""


def extract_phone(parsed_contact, broker_contact="", broker_contact_raw="", notes=""):
    candidates = []

    if isinstance(parsed_contact, dict):
        for key in ["phone", "phones", "contact_phone"]:
            value = parsed_contact.get(key)

            if isinstance(value, list):
                candidates.extend(value)
            elif value:
                candidates.append(value)

    candidates.extend([
        broker_contact,
        broker_contact_raw,
        notes,
    ])

    combined = " ".join(str(item or "") for item in candidates)

    phone_match = re.search(
        r"(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})",
        combined,
    )

    if not phone_match:
        return ""

    phone = phone_match.group(1).strip()

    ext_match = re.search(
        r"(?:ext|x|extension|ref)\s*[:#.]?\s*(\d{1,6})",
        combined,
        re.IGNORECASE,
    )

    if ext_match:
        phone = f"{phone} x{ext_match.group(1)}"

    return phone
