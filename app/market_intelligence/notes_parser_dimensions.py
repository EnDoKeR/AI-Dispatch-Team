import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_od(text):
    text = clean_text(text)

    # Do NOT search simple "od" alone.
    od_patterns = [
        r"\bpermit\s*load\b",
        r"\bpermits\s*required\b",
        r"\bpermit\s*required\b",
        r"\bpermit\s*needed\b",
        r"\bneeds\s*permit\b",
        r"\bneed\s*permit\b",
        r"\bneed\s*permits\b",
        r"\brequires\s*permit\b",
        r"\bover\s*dimension\b",
        r"\bover\s*dimensional\b",
        r"\boverdimension\b",
        r"\boverdimensional\b",
        r"\bover\s*size\b",
        r"\boversize\b",
        r"\bwide\s*load\b",
        r"\bwide\b.*\bload\b",
        r"\bod\s*load\b",
        r"\bod\s*permit\b",
        r"\bod\s*required\b",
        r"\bod\s*req\b",
        r"\bod\s*/\s*permit\b",
        r"\bescort\s*required\b",
        r"\bpilot\s*car\b",
        r"\blegal\s*overdimension\b",
        r"\blegal\s*over\s*dimension\b",
    ]

    for pattern in od_patterns:
        if re.search(pattern, text):
            return True

    # Width over legal 102 inches.
    width_patterns = [
        r"\b(10[3-9]|1[1-9][0-9])\s*w\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*wide\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*inch\s*wide\b",
        r"\b(10[3-9]|1[1-9][0-9])\s*inches\s*wide\b",
    ]

    for pattern in width_patterns:
        if re.search(pattern, text):
            return True

    # Examples: 58L x 111W x 7H
    dimension_patterns = [
        r"\b\d+\s*l\s*x\s*(10[3-9]|1[1-9][0-9])\s*w\b",
        r"\b\d+\s*x\s*(10[3-9]|1[1-9][0-9])\s*x\s*\d+\b",
        r"\b\d+\s*long\s*x\s*(10[3-9]|1[1-9][0-9])\s*wide\b",
    ]

    for pattern in dimension_patterns:
        if re.search(pattern, text):
            return True

    # 9 ft+ width should be review/OD.
    feet_width_patterns = [
        r"\b(9|10|11|12|13|14|15|16)\s*ft\s*wide\b",
        r"\b(9|10|11|12|13|14|15|16)'\s*wide\b",
        r"\b(9|10|11|12|13|14|15|16)\s*feet\s*wide\b",
    ]

    for pattern in feet_width_patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_dimensions(text):
    text = clean_text(text)

    result = {
        "length": "",
        "width": "",
        "height": "",
        "raw": "",
    }

    patterns = [
        r"\b(\d+(?:\.\d+)?)\s*l\s*x\s*(\d+(?:\.\d+)?)\s*w\s*x\s*(\d+(?:\.\d+)?)\s*h\b",
        r"\b(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\b",
        r"\b(\d+(?:\.\d+)?)\s*long\s*x\s*(\d+(?:\.\d+)?)\s*wide\s*x\s*(\d+(?:\.\d+)?)\s*high\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            result["length"] = match.group(1)
            result["width"] = match.group(2)
            result["height"] = match.group(3)
            result["raw"] = match.group(0)
            return result

    return result


def detect_overweight(text):
    text = clean_text(text)

    keywords = [
        "overweight",
        "over weight",
        "heavy haul",
    ]

    for keyword in keywords:
        if keyword in text:
            return True

    return False
