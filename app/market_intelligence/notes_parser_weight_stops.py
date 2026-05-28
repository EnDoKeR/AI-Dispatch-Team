import re

from app.market_intelligence.notes_parser_text_helpers import clean_text


def detect_weight_unknown(text, posted_weight=0):
    text = clean_text(text)

    try:
        if int(float(posted_weight or 0)) == 1:
            return True
    except Exception:
        pass

    patterns = [
        r"\bweight\s*needs\s*check\b",
        r"\bconfirm\s*weight\b",
        r"\bverify\s*weight\b",
        r"\bweight\s*tbd\b",
        r"\bweight\s*unknown\b",
        r"\bcall\s*for\s*weight\b",
        r"\bweight\s*1\s*lb\b",
        r"\bweight\s*1\s*lbs\b",
        r"\bposted\s*weight\s*1\b",
    ]

    for pattern in patterns:
        if re.search(pattern, text):
            return True

    return False


def detect_weight_from_text(text):
    text = clean_text(text)

    patterns = [
        r"\b(\d{2,3})\s*k\s*lbs\b",
        r"\b(\d{2,3})\s*k\s*lb\b",
        r"\b(\d{2,3})\s*k\b",
        r"\b(\d{2,3},?\d{3})\s*lbs\b",
        r"\b(\d{2,3},?\d{3})\s*lb\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if not match:
            continue

        raw = match.group(1).replace(",", "")

        try:
            number = int(raw)

            if number < 1000:
                number = number * 1000

            if 1000 <= number <= 100000:
                return number

        except Exception:
            pass

    return 0


def detect_stops_from_text(text):
    text = clean_text(text)

    pickup_count = None
    delivery_count = None

    pickup_patterns = [
        r"\b(\d+)\s*p/u\b",
        r"\b(\d+)\s*pu\b",
        r"\b(\d+)\s*pick\b",
        r"\b(\d+)\s*pickup\b",
        r"\b(\d+)\s*pickups\b",
        r"\b(\d+)\s*p\b",
    ]

    delivery_patterns = [
        r"\b(\d+)\s*d/o\b",
        r"\b(\d+)\s*del\b",
        r"\b(\d+)\s*drop\b",
        r"\b(\d+)\s*drops\b",
        r"\b(\d+)\s*delivery\b",
        r"\b(\d+)\s*deliveries\b",
        r"\b(\d+)\s*d\b",
    ]

    # Common DAT style: 1P/1D, 2P/1D
    match = re.search(r"\b(\d+)\s*p\s*/\s*(\d+)\s*d\b", text)
    if match:
        return int(match.group(1)) + int(match.group(2))

    for pattern in pickup_patterns:
        match = re.search(pattern, text)
        if match:
            pickup_count = int(match.group(1))
            break

    for pattern in delivery_patterns:
        match = re.search(pattern, text)
        if match:
            delivery_count = int(match.group(1))
            break

    if pickup_count is not None or delivery_count is not None:
        if pickup_count is None:
            pickup_count = 1

        if delivery_count is None:
            delivery_count = 1

        return pickup_count + delivery_count

    # Examples:
    # "1 drop in hayward, 1 drop in tacoma"
    drop_matches = re.findall(r"\b\d+\s*drop\b", text)
    if drop_matches:
        return len(drop_matches) + 1

    multistop_patterns = [
        r"\bmultistop\b",
        r"\bmulti\s*stop\b",
        r"\bmulti\s*stops\b",
        r"\bmultiple\s*stops\b",
        r"\bmultiple\s*drops\b",
        r"\bmultiple\s*pickups\b",
    ]

    for pattern in multistop_patterns:
        if re.search(pattern, text):
            return 2

    # "multiple loads available" is NOT stops.
    return 0
