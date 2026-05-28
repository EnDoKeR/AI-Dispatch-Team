GOOD = [
    "IL",
    "OH",
    "IN",
    "PA",
    "TX",
]

MEDIUM = [
    "FL",
    "GA",
    "NC",
]

BAD = [
    "MT",
    "ND",
    "SD",
]

TERRIBLE = [
    "ID",
    "WY",
    "NM",
]


def evaluate_zone(delivery):
    delivery = delivery.upper()

    for state in GOOD:
        if state in delivery:
            return "GOOD", 90

    for state in MEDIUM:
        if state in delivery:
            return "MEDIUM", 70

    for state in BAD:
        if state in delivery:
            return "BAD", 40

    for state in TERRIBLE:
        if state in delivery:
            return "TERRIBLE", 10

    return "UNKNOWN", 50
