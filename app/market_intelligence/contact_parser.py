import re


COMMON_EMAIL_FIXES = {
    "gmai.com": "gmail.com",
    "gmial.com": "gmail.com",
    "gnail.com": "gmail.com",
    "gmal.com": "gmail.com",
    "outlok.com": "outlook.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com",
}


def clean_text(value):
    return str(value or "").strip()


def normalize_obfuscated_email_text(text):
    text = clean_text(text)

    replacements = {
        "`com": ".com",
        "'com": ".com",
        ",com": ".com",
        ";com": ".com",
        " com": ".com",
        "(at)": "@",
        "[at]": "@",
        " at ": "@",
        "(dot)": ".",
        "[dot]": ".",
        " dot ": ".",
    }

    normalized = text

    for old, new in replacements.items():
        normalized = normalized.replace(old, new)

    normalized = re.sub(r"\s*@\s*", "@", normalized)
    normalized = re.sub(r"\s*\.\s*", ".", normalized)

    return normalized


def fix_common_email_typos(email):
    email = clean_text(email).lower()

    for wrong, correct in COMMON_EMAIL_FIXES.items():
        if email.endswith(wrong):
            email = email[: -len(wrong)] + correct

    return email


def extract_emails(text):
    normalized = normalize_obfuscated_email_text(text)

    pattern = r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
    emails = re.findall(pattern, normalized)

    cleaned = []

    for email in emails:
        fixed = fix_common_email_typos(email)

        if fixed not in cleaned:
            cleaned.append(fixed)

    return cleaned


def extract_phone_extensions(text):
    text = clean_text(text)

    patterns = [
        r"\b(?:ext|extension)\s*\.?\s*(\d{1,6})\b",
        r"\bx\s*(\d{1,6})\b",
    ]

    extensions = []

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)

        for match in matches:
            if match not in extensions:
                extensions.append(match)

    return extensions


def normalize_phone(phone):
    digits = re.sub(r"\D", "", str(phone or ""))

    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"

    return clean_text(phone)


def extract_phone_numbers(text):
    text = clean_text(text)

    patterns = [
        r"\(\d{3}\)\s*\d{3}[-\s]?\d{4}",
        r"\b\d{3}[-\s]\d{3}[-\s]\d{4}\b",
    ]

    phones = []

    for pattern in patterns:
        matches = re.findall(pattern, text)

        for match in matches:
            cleaned = normalize_phone(match)

            if cleaned and cleaned not in phones:
                phones.append(cleaned)

    return phones


def parse_contact_info(*values):
    combined = " | ".join([clean_text(value) for value in values if clean_text(value)])

    emails = extract_emails(combined)
    phones = extract_phone_numbers(combined)
    extensions = extract_phone_extensions(combined)

    contact_parts = []

    for phone in phones:
        if extensions:
            contact_parts.append(f"{phone} ext {extensions[0]}")
        else:
            contact_parts.append(phone)

    for email in emails:
        contact_parts.append(email)

    return {
        "emails": emails,
        "phones": phones,
        "extensions": extensions,
        "normalized_contact": " / ".join(contact_parts),
    }
