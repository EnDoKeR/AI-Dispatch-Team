import re


def normalize_text(value):
    return str(value or "").strip()


def lower_text(value):
    return normalize_text(value).lower()


def clean_text(value):
    text = lower_text(value)

    replacements = {
        "`": ".",
        "РІР‚в„ў": "'",
        "РІР‚В": "'",
        "РІР‚Сљ": '"',
        "РІР‚Сњ": '"',
        "_": " ",
        ";": " ",
        "|": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_email(raw_email):
    if not raw_email:
        return ""

    email = str(raw_email).strip().lower()

    email = email.replace("`", ".")
    email = email.replace("'", "")

    email = re.sub(r"\s*\(\s*at\s*\)\s*", "@", email)
    email = re.sub(r"\s*\[\s*at\s*\]\s*", "@", email)
    email = re.sub(r"\s+at\s+", "@", email)
    email = re.sub(r"\bat\b", "@", email)

    email = re.sub(r"\s*\(\s*dot\s*\)\s*", ".", email)
    email = re.sub(r"\s*\[\s*dot\s*\]\s*", ".", email)
    email = re.sub(r"\s+dot\s+", ".", email)
    email = re.sub(r"\bdot\b", ".", email)

    email = email.replace(" ", "")

    # Common DAT/manual mistakes:
    # info@national-transportservices`com
    # info@national-transportservices com
    # info@national-transportservices,com
    email = email.replace(",", ".")
    email = email.replace(";", ".")

    # Fix duplicated dots
    email = re.sub(r"\.{2,}", ".", email)

    # Remove invalid trailing characters
    email = email.strip(".-_:,/")

    if "@" not in email:
        return ""

    if not re.search(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$", email):
        return ""

    return email


def normalize_phone(raw_phone):
    if not raw_phone:
        return ""

    phone = str(raw_phone).strip()
    phone = re.sub(r"\s+", " ", phone)
    return phone
