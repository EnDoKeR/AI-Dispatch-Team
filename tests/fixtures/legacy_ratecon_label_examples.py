"""Synthetic legacy RateCon label examples for redacted diagnostics tests."""


LEGACY_RATECON_LABEL_EXAMPLES = [
    {
        "scenario_id": "legacy_header_broker_rate",
        "scenario_name": "Legacy-style header broker and total rate labels",
        "text": """
TRUCKLOAD RATE CONFIRMATION
Broker Name: FAKE BROKER LLC
MC Number: MC000000
TOTAL: USD $3000
Load #: FAKE-REF-001
""".strip(),
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
        ],
    },
    {
        "scenario_id": "legacy_shipper_consignee",
        "scenario_name": "Legacy shipper and consignee section labels",
        "text": """
Shipper Information:
Address:
Fake City, ST 00000
Pick Up Time: 2026-09-01 08:00
Consignee Information:
Address:
Fake City, ST 00000
Delivery Time: 2026-09-03 09:00
""".strip(),
        "expected_signal_categories": [
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
        ],
    },
    {
        "scenario_id": "legacy_carrier_equipment",
        "scenario_name": "Legacy carrier and trailer labels",
        "text": """
Carrier Name: FAKE CARRIER LLC
Trailer Type/Size: Conestoga 48
Equipment: Conestoga
""".strip(),
        "expected_signal_categories": [
            "equipment",
        ],
    },
    {
        "scenario_id": "legacy_commodity_weight",
        "scenario_name": "Legacy commodity and total weight labels",
        "text": """
Commodity Description: FAKE PRODUCT
Total Weight: 40000 LBS
Weight: 40000
""".strip(),
        "expected_signal_categories": [
            "commodity",
            "weight",
        ],
    },
    {
        "scenario_id": "legacy_accessorials",
        "scenario_name": "Legacy accessorial labels",
        "text": """
Linehaul: 2500
Fuel Surcharge: 500
Accessorials: detention, layover, lumper
TONU: applies by agreement
""".strip(),
        "expected_signal_categories": [
            "rate",
            "accessorials",
        ],
    },
]
