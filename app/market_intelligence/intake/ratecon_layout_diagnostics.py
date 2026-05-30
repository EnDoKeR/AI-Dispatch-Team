"""Redacted layout-shape diagnostics for RateCon text."""

from collections import Counter, defaultdict
import re


FIELD_CATEGORIES = [
    "broker_name",
    "broker_mc",
    "rate",
    "pickup_location",
    "delivery_location",
    "pickup_date",
    "delivery_date",
    "weight",
    "commodity",
    "reference_id",
    "equipment",
    "special_requirements",
    "accessorials",
]

LABEL_CATEGORY_MAP = {
    "broker": ("broker_name", "<VALUE>"),
    "broker name": ("broker_name", "<VALUE>"),
    "bill to": ("broker_name", "<VALUE>"),
    "customer": ("broker_name", "<VALUE>"),
    "mc": ("broker_mc", "<MC>"),
    "mc#": ("broker_mc", "<MC>"),
    "mc #": ("broker_mc", "<MC>"),
    "mc number": ("broker_mc", "<MC>"),
    "broker mc": ("broker_mc", "<MC>"),
    "motor carrier": ("broker_mc", "<MC>"),
    "total": ("rate", "<AMOUNT>"),
    "total rate": ("rate", "<AMOUNT>"),
    "total carrier pay": ("rate", "<AMOUNT>"),
    "carrier pay": ("rate", "<AMOUNT>"),
    "linehaul total": ("rate", "<AMOUNT>"),
    "rate": ("rate", "<AMOUNT>"),
    "pickup": ("pickup_location", "<LOCATION>"),
    "pick up": ("pickup_location", "<LOCATION>"),
    "pu": ("pickup_location", "<LOCATION>"),
    "pickup location": ("pickup_location", "<LOCATION>"),
    "shipper": ("pickup_location", "<LOCATION>"),
    "shipper information": ("pickup_location", "<LOCATION>"),
    "pickup date": ("pickup_date", "<DATE>"),
    "pickup time": ("pickup_date", "<DATE> <TIME>"),
    "pick up time": ("pickup_date", "<DATE> <TIME>"),
    "pickup window": ("pickup_date", "<DATE> <TIME>"),
    "delivery": ("delivery_location", "<LOCATION>"),
    "drop": ("delivery_location", "<LOCATION>"),
    "delivery location": ("delivery_location", "<LOCATION>"),
    "receiver": ("delivery_location", "<LOCATION>"),
    "consignee": ("delivery_location", "<LOCATION>"),
    "consignee information": ("delivery_location", "<LOCATION>"),
    "delivery date": ("delivery_date", "<DATE>"),
    "delivery time": ("delivery_date", "<DATE> <TIME>"),
    "delivery window": ("delivery_date", "<DATE> <TIME>"),
    "commodity": ("commodity", "<VALUE>"),
    "commodity description": ("commodity", "<VALUE>"),
    "product": ("commodity", "<VALUE>"),
    "freight description": ("commodity", "<VALUE>"),
    "weight": ("weight", "<WEIGHT>"),
    "total weight": ("weight", "<WEIGHT>"),
    "lbs": ("weight", "<WEIGHT>"),
    "pounds": ("weight", "<WEIGHT>"),
    "reference": ("reference_id", "<ID>"),
    "reference #": ("reference_id", "<ID>"),
    "reference id": ("reference_id", "<ID>"),
    "ref #": ("reference_id", "<ID>"),
    "load #": ("reference_id", "<ID>"),
    "load number": ("reference_id", "<ID>"),
    "order #": ("reference_id", "<ID>"),
    "shipment #": ("reference_id", "<ID>"),
    "shipment id": ("reference_id", "<ID>"),
    "equipment": ("equipment", "<EQUIPMENT>"),
    "trailer type/size": ("equipment", "<EQUIPMENT>"),
    "trailer type": ("equipment", "<EQUIPMENT>"),
    "mode": ("equipment", "<EQUIPMENT>"),
    "special requirements": ("special_requirements", "<VALUE>"),
    "requirements": ("special_requirements", "<VALUE>"),
    "instructions": ("special_requirements", "<VALUE>"),
    "notes": ("special_requirements", "<VALUE>"),
    "accessorial": ("accessorials", "<VALUE>"),
    "accessorials": ("accessorials", "<VALUE>"),
    "linehaul": ("accessorials", "<AMOUNT>"),
    "fuel": ("accessorials", "<AMOUNT>"),
    "fuel surcharge": ("accessorials", "<AMOUNT>"),
    "detention": ("accessorials", "<VALUE>"),
    "layover": ("accessorials", "<VALUE>"),
    "lumper": ("accessorials", "<VALUE>"),
    "tonu": ("accessorials", "<VALUE>"),
}

SECTION_LABELS = {
    "shipper": "pickup_location",
    "shipper information": "pickup_location",
    "pickup": "pickup_location",
    "pick up": "pickup_location",
    "consignee": "delivery_location",
    "consignee information": "delivery_location",
    "receiver": "delivery_location",
    "delivery": "delivery_location",
    "drop": "delivery_location",
}


def _normalize_label(label):
    text = re.sub(r"\s+", " ", str(label or "").strip().lower())
    text = text.replace(" :", ":")
    return text


def _display_label(label):
    return str(label or "").strip()


def _split_label_value(line):
    if ":" not in line:
        return "", ""

    label, value = line.split(":", 1)
    return _normalize_label(label), value.strip()


def _line_position(index, total):
    if total <= 0:
        return "unknown"

    ratio = index / total

    if ratio < 0.34:
        return "beginning"

    if ratio < 0.67:
        return "middle"

    return "end"


def _shape_for_label(label, placeholder):
    display = _display_label(label)

    if not display:
        return ""

    if label == "total":
        return "TOTAL: USD $ <AMOUNT>"

    return f"{display}: {placeholder}"


def _line_shapes(lines):
    total = len(lines)

    for index, line in enumerate(lines):
        label, value = _split_label_value(line)

        if not label or not value:
            continue

        mapping = LABEL_CATEGORY_MAP.get(label)

        if not mapping:
            continue

        category, placeholder = mapping
        yield {
            "category": category,
            "shape": _shape_for_label(label, placeholder),
            "position_group": _line_position(index, total),
        }


def _section_address_shapes(lines):
    total = len(lines)
    active_section = ""
    active_label = ""

    for index, line in enumerate(lines):
        label, value = _split_label_value(line)

        if not label:
            continue

        if label in SECTION_LABELS:
            active_section = SECTION_LABELS[label]
            active_label = _display_label(label)
            continue

        if label == "address" and active_section:
            yield {
                "category": active_section,
                "shape": f"{active_label} -> Address: <LOCATION>",
                "position_group": _line_position(index, total),
            }


def _empty_shape_buckets():
    return {category: [] for category in FIELD_CATEGORIES}


def _append_shape(shapes_by_category, shape_record):
    category = shape_record["category"]
    shape = {
        "shape": shape_record["shape"],
        "position_group": shape_record["position_group"],
    }

    if shape not in shapes_by_category[category]:
        shapes_by_category[category].append(shape)


def _shape_counts(shapes_by_category):
    counts = {}

    for category, shapes in shapes_by_category.items():
        counter = Counter(record["shape"] for record in shapes)
        counts[category] = dict(sorted(counter.items()))

    return counts


def detect_ratecon_layout_shapes(text):
    clean_text = str(text or "")
    lines = [line.strip() for line in clean_text.splitlines() if line.strip()]
    shapes_by_category = _empty_shape_buckets()
    warnings = []

    for shape in list(_line_shapes(lines)) + list(_section_address_shapes(lines)):
        _append_shape(shapes_by_category, shape)

    if not clean_text.strip():
        warnings.append("empty_text")

    populated_shapes = {
        category: shapes
        for category, shapes in shapes_by_category.items()
        if shapes
    }
    counts = defaultdict(dict)

    for category, shapes in _shape_counts(populated_shapes).items():
        counts[category] = shapes

    return {
        "text_present": bool(clean_text.strip()),
        "char_count": len(clean_text),
        "shape_counts_by_category": dict(counts),
        "shapes_by_category": populated_shapes,
        "warnings": warnings,
    }
