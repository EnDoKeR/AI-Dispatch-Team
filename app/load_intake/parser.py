from datetime import datetime
import re

from pypdf import PdfReader

from app.market_intelligence.market_models import Load
from app.load_intake.mileage import get_miles
from app.load_intake.zone_engine import evaluate_zone
from app.load_intake.broker_engine import get_broker_data
from app.load_intake.decision_engine import (
    score_rpm,
    calculate_final_score,
    final_decision,
)
from app.load_intake.reload_engine import (
    evaluate_reload,
    adjust_score,
    adjusted_decision,
)


def extract(pattern, text):
    match = re.search(pattern, text, re.DOTALL)

    if match:
        return match.group(1).strip()

    return ""


def extract_all(pattern, text):
    return re.findall(pattern, text, re.DOTALL)


def parse_weight(value):
    try:
        return int(
            str(value)
            .replace(",", "")
            .strip()
        )

    except:
        return 0


def sum_weights(text):
    weights = extract_all(
        r"\s([0-9]{1,3},[0-9]{3})\s",
        text,
    )

    total = 0

    for weight in weights:
        total += parse_weight(weight)

    if total == 0:
        return ""

    return str(total)


def calc_rpm(rate, miles):
    try:
        rate = float(
            str(rate)
            .replace(",", "")
            .replace("$", "")
        )

        miles = float(
            str(miles)
            .replace(",", "")
        )

        if miles == 0:
            return ""

        return round(
            rate / miles,
            2,
        )

    except:
        return ""


def parse_ratecon(pdf_path):
    reader = PdfReader(pdf_path)

    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    broker = extract(
        r"TRUCKLOAD RATE CONFIRMATION\s*(.*?)\s*440",
        text,
    )

    pickup = extract(
        r"Shipper Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
        text,
    )

    delivery = extract(
        r"Consignee Information:.*?Address:.*?\n([A-Za-z\s]+,\s*[A-Z]{2}\s*[0-9]{5})",
        text,
    )

    final_rate = extract(
        r"TOTAL:\s*USD\s*\$([0-9,\.]+)",
        text,
    )

    total_weight = sum_weights(text)

    loaded_miles = get_miles(
        pickup,
        delivery,
    )

    rpm = calc_rpm(
        final_rate,
        loaded_miles,
    )

    zone, zone_score = evaluate_zone(
        delivery,
    )

    broker_score, broker_status = get_broker_data(
        broker,
    )

    rpm_score = score_rpm(
        rpm,
    )

    final_score = calculate_final_score(
        rpm_score,
        zone_score,
        broker_score,
    )

    decision = final_decision(
        final_score,
        broker_status,
    )

    reload_score, reload_status = evaluate_reload(
        delivery,
    )

    adjusted_score = adjust_score(
        final_score,
        reload_score,
    )

    adjusted = adjusted_decision(
        adjusted_score,
    )

    book = (
        "YES"
        if final_score >= 80
        else "REVIEW"
    )

    load = Load(
        booked_at=datetime.now().strftime(
            "%m/%d/%Y %I:%M %p"
        ),
        source="Rate Confirmation",
        why_booked="Imported automatically",
        why_note="Waiting dispatcher review",
        next_plan="Search next load",
        next_note="Pending",
        outcome="",
        outcome_note="",
        broker=broker,
        pickup=pickup,
        pickup_date=extract(
            r"Pick Up\s*Time:\s*([0-9\/]+)",
            text,
        ),
        delivery=delivery,
        delivery_date=extract(
            r"Delivery\s*Time:\s*([0-9\/]+)",
            text,
        ),
        load_no=extract(
            r"Load #:\s*([0-9]+)",
            text,
        ),
        carrier=extract(
            r"Carrier Name:\s*(.*?)\s*Load #:",
            text,
        ),
        trailer_type=extract(
            r"Trailer Type/Size:\s*(.*?)\s*Shipper Information:",
            text,
        ),
        commodity=extract(
            r"HAZMAT\s*Commodity Description\s*Total Weight\s*.*?\s*(Coil.*?)\s*[0-9,]+",
            text,
        ),
        total_weight=total_weight,
        final_rate=final_rate,
        loaded_miles=loaded_miles,
        rpm=rpm,
        zone=zone,
        zone_score=zone_score,
        broker_score=broker_score,
        broker_status=broker_status,
        book=book,
        rpm_score=rpm_score,
        final_score=final_score,
        final_decision=decision,
        reload_score=reload_score,
        reload_status=reload_status,
        adjusted_score=adjusted_score,
        adjusted_decision=adjusted,
        rate=final_rate,
    )

    return load