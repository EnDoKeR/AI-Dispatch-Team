"""Anonymized synthetic RateCon text scenarios.

These scenarios use fake values only. They are designed to exercise label
vocabulary and parser coverage without copying private RateCon text.
"""


ANONYMIZED_RATECON_SCENARIOS = [
    {
        "scenario_id": "truckload_rate_confirmation_header",
        "scenario_name": "Truckload rate confirmation header with total",
        "text": """
TRUCKLOAD RATE CONFIRMATION
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
TOTAL: USD $3200
Load #: FAKE-REF-001
Pickup: Fake City, ST
Pickup Date: 2026-10-01
Delivery: Fake Town, ST
Delivery Date: 2026-10-03
Commodity: FAKE COMMODITY
Weight: 40000 LBS
Equipment: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "shipper_information_block",
        "scenario_name": "Shipper Information block",
        "text": """
Broker: FAKE BROKER LLC
MC Number: MC000000
Rate: 3100
Reference #: FAKE-REF-002
Shipper Information:
Name: FAKE SHIPPER LLC
Address: Fake City, ST 00000
Pick Up Time: 2026-10-04 08:00
Delivery: Fake Town, ST
Delivery Date: 2026-10-05
Commodity: FAKE MATERIAL
Weight: 39000 LBS
Equipment: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["pickup_location"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "consignee_information_block",
        "scenario_name": "Consignee Information block",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Rate: 3000
Load Number: FAKE-REF-003
Pickup: Fake City, ST
Pickup Date: 2026-10-06
Consignee Information:
Name: FAKE CONSIGNEE LLC
Address: Fake Town, ST 00000
Delivery Time: 2026-10-08 09:00
Commodity Description: FAKE PRODUCT
Total Weight: 38000 LBS
Trailer Type/Size: Conestoga 48
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["delivery_location"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "total_usd_rate_label",
        "scenario_name": "TOTAL USD rate label",
        "text": """
Broker Name: FAKE BROKER LLC
MC#: MC000000
TOTAL: USD $3450
Reference #: FAKE-REF-004
Pickup Location: Fake City, ST
Pickup Date: 2026-10-09
Delivery Location: Fake Town, ST
Delivery Date: 2026-10-10
Commodity: FAKE COILS
Weight: 41000
Equipment: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "split_pickup_delivery_times",
        "scenario_name": "Pick Up Time and Delivery Time labels",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 2950
Load #: FAKE-REF-005
Pickup Location: Fake City, ST
Pick Up Time: 2026-10-11 07:00-10:00
Delivery Location: Fake Town, ST
Delivery Time: 2026-10-12 13:00-15:00
Commodity: FAKE MACHINERY
Weight: 36000
Equipment: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "pickup_time",
            "delivery_location",
            "delivery_date",
            "delivery_time",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["pickup_time", "delivery_time"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "load_number_reference_labels",
        "scenario_name": "Load number and reference labels",
        "text": """
Broker: FAKE BROKER LLC
MC Number: MC000000
Carrier Pay: 3300
Load #: FAKE-REF-006
Reference #: FAKE-ALT-006
Pickup: Fake City, ST
Pickup Date: 2026-10-13
Delivery: Fake Town, ST
Delivery Date: 2026-10-14
Commodity: FAKE FREIGHT
Weight: 37000
Equipment: Step Deck
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["reference_id"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "carrier_name_trailer_type",
        "scenario_name": "Carrier name and trailer type labels",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Carrier Pay: 3600
Order #: FAKE-REF-007
Carrier Name: FAKE CARRIER LLC
Trailer Type/Size: Conestoga 48
Pickup: Fake City, ST
Pickup Date: 2026-10-15
Delivery: Fake Town, ST
Delivery Date: 2026-10-16
Commodity: FAKE LOAD
Weight: 42000
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "commodity_description_total_weight",
        "scenario_name": "Commodity Description and Total Weight labels",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 2800
Shipment #: FAKE-REF-008
Pickup: Fake City, ST
Pickup Date: 2026-10-17
Delivery: Fake Town, ST
Delivery Date: 2026-10-18
Commodity Description: FAKE BUILDING PRODUCT
Total Weight: 44000 LBS
Equipment: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "linehaul_accessorial_total",
        "scenario_name": "Linehaul and accessorials with clear total",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Linehaul: 2500
Fuel Surcharge: 300
Detention: FAKE TERMS
Total Carrier Pay: 2800
Reference #: FAKE-REF-009
Pickup: Fake City, ST
Pickup Date: 2026-10-19
Delivery: Fake Town, ST
Delivery Date: 2026-10-20
Commodity: FAKE EQUIPMENT
Weight: 35000
Equipment: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["rate"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "accessorials",
        ],
    },
    {
        "scenario_id": "appointment_windows",
        "scenario_name": "Appointment window labels",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 3700
Reference #: FAKE-REF-010
Pickup Location: Fake City, ST
Pickup Window: 2026-10-21 08:00-12:00
Delivery Location: Fake Town, ST
Delivery Window: 2026-10-23 09:00-11:00
Commodity: FAKE CRATES
Weight: 33000
Equipment: Van
Special Requirements: APPOINTMENT REQUIRED
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "pickup_time",
            "delivery_location",
            "delivery_date",
            "delivery_time",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["pickup_time", "delivery_time"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
    },
    {
        "scenario_id": "multi_stop_like",
        "scenario_name": "Multi-stop-like layout",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 4300
Reference #: FAKE-REF-011
PU1: Fake City, ST
PU2: Fake City, ST
Drop 1: Fake Town, ST
Drop 2: Fake Town, ST
Pickup Date: 2026-10-24
Delivery Date: 2026-10-26
Commodity: FAKE PALLETS
Weight: 41000
Equipment: Flatbed
Special Requirements: MULTI STOP REVIEW
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_date",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": ["pickup_location", "delivery_location"],
        "expected_needs_check_fields": ["multi_stop"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
    },
    {
        "scenario_id": "broker_contact_heavy",
        "scenario_name": "Broker/contact-heavy layout",
        "text": """
TRUCKLOAD RATE CONFIRMATION
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
Dispatch Contact: FAKE CONTACT
After Hours Contact: FAKE CONTACT
Rate: 3050
Load Number: FAKE-REF-012
Pickup: Fake City, ST
Pickup Date: 2026-10-27
Delivery: Fake Town, ST
Delivery Date: 2026-10-28
Commodity: FAKE MATERIAL
Weight: 39000
Equipment: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "equipment_label_variants",
        "scenario_name": "Equipment label variants",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 3150
Reference #: FAKE-REF-013
Pickup: Fake City, ST
Pickup Date: 2026-10-29
Delivery: Fake Town, ST
Delivery Date: 2026-10-30
Commodity: FAKE STEEL
Weight: 40000
Mode: Truckload
Equipment: Step Deck
Trailer Type: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["equipment"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "missing_weight",
        "scenario_name": "Missing weight case",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 3000
Reference #: FAKE-REF-014
Pickup: Fake City, ST
Pickup Date: 2026-10-31
Delivery: Fake Town, ST
Delivery Date: 2026-11-01
Commodity: FAKE MACHINERY
Equipment: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "equipment",
        ],
        "expected_missing_fields": ["weight"],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "equipment",
        ],
    },
    {
        "scenario_id": "missing_commodity",
        "scenario_name": "Missing commodity case",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Rate: 3000
Reference #: FAKE-REF-015
Pickup: Fake City, ST
Pickup Date: 2026-11-02
Delivery: Fake Town, ST
Delivery Date: 2026-11-03
Weight: 40000
Equipment: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": ["commodity"],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "accessorials_without_total",
        "scenario_name": "Accessorial amounts without total",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Linehaul: 2400
Fuel Surcharge: 350
Lumper: FAKE TERMS
Detention: FAKE TERMS
Reference #: FAKE-REF-016
Pickup: Fake City, ST
Pickup Date: 2026-11-04
Delivery: Fake Town, ST
Delivery Date: 2026-11-05
Commodity: FAKE FREIGHT
Weight: 38000
Equipment: Van
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": ["rate"],
        "expected_needs_check_fields": ["rate"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "accessorials",
        ],
    },
    {
        "scenario_id": "tbd_weight_and_product",
        "scenario_name": "TBD weight and product needs check",
        "text": """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
Carrier Pay: 3050
Reference #: FAKE-REF-017
Pickup: Fake City, ST
Pickup Date: 2026-11-06
Delivery: Fake Town, ST
Delivery Date: 2026-11-07
Product: TBD
Total Weight: TBD
Equipment: Flatbed
Special Requirements: Call for weight
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": ["commodity", "weight"],
        "expected_needs_check_fields": ["commodity", "weight"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
    },
    {
        "scenario_id": "flatbed_special_requirements",
        "scenario_name": "Flatbed special requirements",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Rate: 3550
Reference #: FAKE-REF-018
Pickup: Fake City, ST
Pickup Date: 2026-11-08
Delivery: Fake Town, ST
Delivery Date: 2026-11-09
Freight Description: FAKE PIPE
Pounds: 42000
Equipment: Flatbed
Special Requirements: Tarps required; straps required; appointment required
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["special_requirements"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
    },
    {
        "scenario_id": "shape_total_usd_amount",
        "scenario_name": "Shape TOTAL USD amount",
        "text": """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
TOTAL: USD $0000.00
Load #: FAKE-REF-019
Pickup: Fake City, ST 00000
Pickup Date: 2026-11-10
Delivery: Fake Town, ST 00000
Delivery Date: 2026-11-11
Commodity: FAKE COMMODITY
Weight: 40000 LBS
Equipment: Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_layout_shapes": {
            "rate": ["TOTAL: USD $ <AMOUNT>"],
            "reference_id": ["load #: <ID>"],
        },
    },
    {
        "scenario_id": "shape_shipper_address_next_line",
        "scenario_name": "Shape shipper address on following line",
        "text": """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
Rate: $0000.00
Load #: FAKE-REF-020
Shipper Information:
Address: Fake City, ST 00000
Pick Up Time: 2026-11-12
Consignee Information:
Address: Fake Town, ST 00000
Delivery Time: 2026-11-13
Commodity: FAKE PRODUCT
Total Weight: 40000 LBS
Trailer Type/Size: Flatbed 48
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_layout_shapes": {
            "pickup_location": ["shipper information -> Address: <LOCATION>"],
            "delivery_location": ["consignee information -> Address: <LOCATION>"],
        },
    },
    {
        "scenario_id": "shape_trailer_before_shipper",
        "scenario_name": "Shape trailer before shipper block",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Carrier Pay: $0000.00
Reference #: FAKE-REF-021
Trailer Type/Size: Conestoga 53
Commodity Description: FAKE MACHINERY
Total Weight: 39000 LBS
Shipper Information:
Address: Fake City, ST 00000
Pickup Date: 2026-11-14
Consignee Information:
Address: Fake Town, ST 00000
Delivery Date: 2026-11-15
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "equipment",
            "commodity",
            "weight",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "equipment",
            "commodity",
            "weight",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
        ],
        "expected_layout_shapes": {
            "equipment": ["trailer type/size: <EQUIPMENT>"],
            "commodity": ["commodity description: <VALUE>"],
            "weight": ["total weight: <WEIGHT>"],
        },
    },
    {
        "scenario_id": "shape_table_like_commodity_weight",
        "scenario_name": "Shape commodity and weight table-like rows",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Carrier Pay: $0000.00
Order #: FAKE-REF-022
Pickup Location: Fake City, ST 00000
Pickup Date: 2026-11-16
Delivery Location: Fake Town, ST 00000
Delivery Date: 2026-11-17
Commodity Description: FAKE TABLE PRODUCT
Total Weight: 40000 LBS
Trailer Type: Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_layout_shapes": {
            "commodity": ["commodity description: <VALUE>"],
            "weight": ["total weight: <WEIGHT>"],
            "equipment": ["trailer type: <EQUIPMENT>"],
        },
    },
    {
        "scenario_id": "shape_multiple_amount_accessorials",
        "scenario_name": "Shape multiple amounts and accessorials",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Linehaul: $0000.00
Fuel Surcharge: $000.00
Detention: FAKE TERMS
Lumper: FAKE TERMS
Total Carrier Pay: $0000.00
Load #: FAKE-REF-023
Pickup: Fake City, ST 00000
Pickup Date: 2026-11-18
Delivery: Fake Town, ST 00000
Delivery Date: 2026-11-19
Commodity: FAKE FREIGHT
Weight: 40000
Equipment: Van
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["rate"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "accessorials",
        ],
        "expected_layout_shapes": {
            "rate": ["total carrier pay: <AMOUNT>"],
            "accessorials": [
                "linehaul: <AMOUNT>",
                "fuel surcharge: <AMOUNT>",
                "detention: <VALUE>",
                "lumper: <VALUE>",
            ],
        },
    },
    {
        "scenario_id": "batch3_next_line_identity_and_rate",
        "scenario_name": "Batch 3 next-line identity and rate labels",
        "text": """
TRUCKLOAD RATE CONFIRMATION
Broker
FAKE BROKER LLC
MC Number
MC000000
Load Number
FAKE-REF-024
Total Carrier Pay
USD $0000.00
Shipper Information
Address
Fake City, ST 00000
Pickup Time
2026-11-20
Consignee Information
Address
Fake Town, ST 00000
Delivery Time
2026-11-21
Commodity
FAKE PRODUCT
Weight
40000 LBS
Equipment
Flatbed
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_parser_gap_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "batch3_table_like_stops_and_freight",
        "scenario_name": "Batch 3 table-like stop and freight layout",
        "text": """
Broker: FAKE BROKER LLC
Broker MC: MC000000
Total Carrier Pay: $0000.00
Load #: FAKE-REF-025
Stop Type    Location    Date    Time
Pickup Date / Delivery Date
Pickup    Fake City, ST 00000    2026-11-22    08:00
Delivery    Fake Town, ST 00000    2026-11-23    09:00
Freight Table
Commodity / Weight / Equipment
FAKE COMMODITY    40000 LBS    Conestoga
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_parser_gap_fields": [
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "batch3_authority_and_origin_destination_blocks",
        "scenario_name": "Batch 3 authority and origin destination blocks",
        "text": """
Customer:
FAKE BROKER LLC
Motor Carrier:
MC000000
Order Number:
FAKE-REF-026
Carrier Pay:
$0000.00
Origin:
Fake City, ST 00000
Destination:
Fake Town, ST 00000
Pickup Appt:
2026-11-24
Delivery Appt:
2026-11-25
Description:
FAKE PRODUCT
WT:
40000 LBS
Trailer:
Step Deck
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
        "expected_parser_gap_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
        ],
    },
    {
        "scenario_id": "batch3_accessorial_total_next_line",
        "scenario_name": "Batch 3 accessorial and total next-line labels",
        "text": """
Broker Name: FAKE BROKER LLC
Broker MC: MC000000
Load #: FAKE-REF-027
Linehaul Charge
$0000.00
Detention
FAKE TERMS
Lumper
FAKE TERMS
Total
USD $0000.00
Pickup Location: Fake City, ST 00000
Pickup Date: 2026-11-26
Delivery Location: Fake Town, ST 00000
Delivery Date: 2026-11-27
Commodity: FAKE FREIGHT
Weight: 40000 LBS
Equipment: Van
""".strip(),
        "expected_present_fields": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "special_requirements",
        ],
        "expected_missing_fields": [],
        "expected_needs_check_fields": ["rate"],
        "expected_signal_categories": [
            "broker_name",
            "broker_mc",
            "rate",
            "reference_id",
            "pickup_location",
            "pickup_date",
            "delivery_location",
            "delivery_date",
            "commodity",
            "weight",
            "equipment",
            "accessorials",
        ],
        "expected_parser_gap_fields": [
            "rate",
            "accessorials",
        ],
    },
]
