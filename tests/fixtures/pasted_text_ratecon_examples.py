PASTED_TEXT_RATECON_EXAMPLES = [
    {
        "scenario_id": "clean_simple_ratecon_text",
        "scenario_name": "Clean simple synthetic RateCon text",
        "pasted_text": """
Broker: Synthetic Pasted Broker A
Broker MC: SYNTH-MC-9101
Rate: 3600
Pickup: Dade City, FL
Pickup Date: 2026-07-01
Pickup Time: 08:00
Delivery: Denver, CO
Delivery Date: 2026-07-03
Delivery Time: 09:00
Commodity: Synthetic steel coils
Weight: 42000
Reference: SYNTH-PASTE-001
Equipment: Conestoga
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker A",
            "broker_mc": "SYNTH-MC-9101",
            "rate": 3600,
            "pickup_location": "Dade City, FL",
            "pickup_date": "2026-07-01",
            "pickup_time": "08:00",
            "delivery_location": "Denver, CO",
            "delivery_date": "2026-07-03",
            "delivery_time": "09:00",
            "commodity": "Synthetic steel coils",
            "weight": 42000,
            "reference_id": "SYNTH-PASTE-001",
            "equipment": "Conestoga",
            "special_requirements": [],
            "field_confidence": {
                "broker_name": "HIGH",
                "broker_mc": "HIGH",
                "rate": "HIGH",
                "pickup_location": "HIGH",
                "pickup_date": "HIGH",
                "pickup_time": "HIGH",
                "delivery_location": "HIGH",
                "delivery_date": "HIGH",
                "delivery_time": "HIGH",
                "commodity": "HIGH",
                "weight": "HIGH",
                "reference_id": "HIGH",
                "equipment": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "broker_name": "HIGH",
            "broker_mc": "HIGH",
            "rate": "HIGH",
            "pickup_location": "HIGH",
            "pickup_date": "HIGH",
            "pickup_time": "HIGH",
            "delivery_location": "HIGH",
            "delivery_date": "HIGH",
            "delivery_time": "HIGH",
            "commodity": "HIGH",
            "weight": "HIGH",
            "reference_id": "HIGH",
            "equipment": "HIGH",
        },
        "expected_special_requirements": [],
    },
    {
        "scenario_id": "missing_broker_mc",
        "scenario_name": "Broker name present but broker MC missing",
        "pasted_text": """
Broker: Synthetic Pasted Broker B
Rate: 2800
Pickup: Laredo, TX
Pickup Date: 2026-07-04
Delivery: Atlanta, GA
Delivery Date: 2026-07-05
Commodity: Synthetic pipe
Weight: 39000
Reference: SYNTH-PASTE-002
Equipment: Flatbed
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker B",
            "broker_mc": "",
            "rate": 2800,
            "pickup_location": "Laredo, TX",
            "pickup_date": "2026-07-04",
            "delivery_location": "Atlanta, GA",
            "delivery_date": "2026-07-05",
            "commodity": "Synthetic pipe",
            "weight": 39000,
            "reference_id": "SYNTH-PASTE-002",
            "equipment": "Flatbed",
            "special_requirements": [],
            "field_confidence": {
                "broker_name": "HIGH",
                "broker_mc": "UNKNOWN",
                "rate": "HIGH",
                "pickup_location": "HIGH",
                "pickup_date": "HIGH",
                "delivery_location": "HIGH",
                "delivery_date": "HIGH",
                "commodity": "HIGH",
                "weight": "HIGH",
                "reference_id": "HIGH",
                "equipment": "HIGH",
            },
        },
        "expected_missing_fields": ["broker_mc"],
        "expected_needs_check_fields": ["broker_mc"],
        "expected_confidence": {
            "broker_name": "HIGH",
            "broker_mc": "UNKNOWN",
            "rate": "HIGH",
            "pickup_location": "HIGH",
            "pickup_date": "HIGH",
            "delivery_location": "HIGH",
            "delivery_date": "HIGH",
            "commodity": "HIGH",
            "weight": "HIGH",
            "reference_id": "HIGH",
            "equipment": "HIGH",
        },
        "expected_special_requirements": [],
    },
    {
        "scenario_id": "missing_weight",
        "scenario_name": "Weight missing",
        "pasted_text": """
Broker: Synthetic Pasted Broker C
Broker MC: SYNTH-MC-9103
Rate: 3050
Pickup: Tulsa, OK
Pickup Date: 2026-07-06
Delivery: Nashville, TN
Delivery Date: 2026-07-07
Commodity: Synthetic beams
Reference: SYNTH-PASTE-003
Equipment: Conestoga
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker C",
            "broker_mc": "SYNTH-MC-9103",
            "rate": 3050,
            "pickup_location": "Tulsa, OK",
            "pickup_date": "2026-07-06",
            "delivery_location": "Nashville, TN",
            "delivery_date": "2026-07-07",
            "commodity": "Synthetic beams",
            "weight": "",
            "reference_id": "SYNTH-PASTE-003",
            "equipment": "Conestoga",
            "special_requirements": [],
            "field_confidence": {
                "weight": "UNKNOWN",
            },
        },
        "expected_missing_fields": ["weight"],
        "expected_needs_check_fields": [],
        "expected_confidence": {"weight": "UNKNOWN"},
        "expected_special_requirements": [],
    },
    {
        "scenario_id": "missing_commodity",
        "scenario_name": "Commodity missing",
        "pasted_text": """
Broker: Synthetic Pasted Broker D
Broker MC: SYNTH-MC-9104
Rate: 3150
Pickup: Houston, TX
Pickup Date: 2026-07-08
Delivery: Memphis, TN
Delivery Date: 2026-07-09
Weight: 40000
Reference: SYNTH-PASTE-004
Equipment: Flatbed
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker D",
            "broker_mc": "SYNTH-MC-9104",
            "rate": 3150,
            "pickup_location": "Houston, TX",
            "pickup_date": "2026-07-08",
            "delivery_location": "Memphis, TN",
            "delivery_date": "2026-07-09",
            "commodity": "",
            "weight": 40000,
            "reference_id": "SYNTH-PASTE-004",
            "equipment": "Flatbed",
            "special_requirements": [],
            "field_confidence": {
                "commodity": "UNKNOWN",
            },
        },
        "expected_missing_fields": ["commodity"],
        "expected_needs_check_fields": [],
        "expected_confidence": {"commodity": "UNKNOWN"},
        "expected_special_requirements": [],
    },
    {
        "scenario_id": "multiple_rates_accessorials",
        "scenario_name": "Multiple rate-like values with accessorials",
        "pasted_text": """
Broker: Synthetic Pasted Broker E
Broker MC: SYNTH-MC-9105
Linehaul: 2800
Fuel: 300
Accessorial: synthetic detention language
Pickup: Mobile, AL
Pickup Date: 2026-07-10
Delivery: Columbus, OH
Delivery Date: 2026-07-11
Commodity: Synthetic steel plate
Weight: 45000
Reference: SYNTH-PASTE-005
Equipment: Flatbed
Special Requirements: ACCESSORIALS_PRESENT, RATE_NEEDS_REVIEW
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker E",
            "broker_mc": "SYNTH-MC-9105",
            "rate": "",
            "pickup_location": "Mobile, AL",
            "pickup_date": "2026-07-10",
            "delivery_location": "Columbus, OH",
            "delivery_date": "2026-07-11",
            "commodity": "Synthetic steel plate",
            "weight": 45000,
            "reference_id": "SYNTH-PASTE-005",
            "equipment": "Flatbed",
            "special_requirements": [
                "ACCESSORIALS_PRESENT",
                "RATE_NEEDS_REVIEW",
            ],
            "field_confidence": {
                "rate": "UNKNOWN",
                "special_requirements": "MEDIUM",
            },
        },
        "expected_missing_fields": ["rate"],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "rate": "UNKNOWN",
            "special_requirements": "MEDIUM",
        },
        "expected_special_requirements": [
            "ACCESSORIALS_PRESENT",
            "RATE_NEEDS_REVIEW",
        ],
    },
    {
        "scenario_id": "appointment_window",
        "scenario_name": "Appointment window text",
        "pasted_text": """
Broker: Synthetic Pasted Broker F
Broker MC: SYNTH-MC-9106
Rate: 2950
Pickup: San Antonio, TX
Pickup Date: 2026-07-12
Pickup Window: 08:00-12:00
Delivery: Savannah, GA
Delivery Date: 2026-07-14
Delivery Window: 09:00-15:00
Commodity: Synthetic construction equipment
Weight: 40000
Load Number: SYNTH-PASTE-006
Equipment: Flatbed
Special Requirements: APPOINTMENT_WINDOWS
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker F",
            "broker_mc": "SYNTH-MC-9106",
            "rate": 2950,
            "pickup_location": "San Antonio, TX",
            "pickup_date": "2026-07-12",
            "pickup_time": "08:00-12:00",
            "delivery_location": "Savannah, GA",
            "delivery_date": "2026-07-14",
            "delivery_time": "09:00-15:00",
            "commodity": "Synthetic construction equipment",
            "weight": 40000,
            "reference_id": "SYNTH-PASTE-006",
            "equipment": "Flatbed",
            "special_requirements": ["APPOINTMENT_WINDOWS"],
            "field_confidence": {
                "pickup_time": "MEDIUM",
                "delivery_time": "MEDIUM",
                "reference_id": "MEDIUM",
                "special_requirements": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "pickup_time": "MEDIUM",
            "delivery_time": "MEDIUM",
            "reference_id": "MEDIUM",
            "special_requirements": "HIGH",
        },
        "expected_special_requirements": ["APPOINTMENT_WINDOWS"],
    },
    {
        "scenario_id": "special_requirements",
        "scenario_name": "Special requirements present",
        "pasted_text": """
Broker: Synthetic Pasted Broker G
Broker MC: SYNTH-MC-9107
Rate: 3450
Pickup: Phoenix, AZ
Pickup Date: 2026-07-15
Delivery: Dallas, TX
Delivery Date: 2026-07-16
Commodity: Synthetic machinery
Weight: 36000
Reference: SYNTH-PASTE-007
Equipment: Conestoga
Special Requirements: CONESTOGA_REQUIRED, TRACKING_REQUIRED
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker G",
            "broker_mc": "SYNTH-MC-9107",
            "rate": 3450,
            "pickup_location": "Phoenix, AZ",
            "pickup_date": "2026-07-15",
            "delivery_location": "Dallas, TX",
            "delivery_date": "2026-07-16",
            "commodity": "Synthetic machinery",
            "weight": 36000,
            "reference_id": "SYNTH-PASTE-007",
            "equipment": "Conestoga",
            "special_requirements": [
                "CONESTOGA_REQUIRED",
                "TRACKING_REQUIRED",
            ],
            "field_confidence": {
                "special_requirements": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "special_requirements": "HIGH",
        },
        "expected_special_requirements": [
            "CONESTOGA_REQUIRED",
            "TRACKING_REQUIRED",
        ],
    },
    {
        "scenario_id": "conestoga_specific",
        "scenario_name": "Conestoga-specific requirement",
        "pasted_text": """
Broker: Synthetic Pasted Broker H
Broker MC: SYNTH-MC-9108
Rate: 3700
Pickup: Cleveland, OH
Pickup Date: 2026-07-17
Delivery: Charlotte, NC
Delivery Date: 2026-07-18
Commodity: Synthetic covered freight
Weight: 37000
Reference: SYNTH-PASTE-008
Equipment: Conestoga
Special Requirements: CONESTOGA_REQUIRED, SIDE_LOAD_VERIFY
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker H",
            "broker_mc": "SYNTH-MC-9108",
            "rate": 3700,
            "pickup_location": "Cleveland, OH",
            "pickup_date": "2026-07-17",
            "delivery_location": "Charlotte, NC",
            "delivery_date": "2026-07-18",
            "commodity": "Synthetic covered freight",
            "weight": 37000,
            "reference_id": "SYNTH-PASTE-008",
            "equipment": "Conestoga",
            "special_requirements": [
                "CONESTOGA_REQUIRED",
                "SIDE_LOAD_VERIFY",
            ],
            "field_confidence": {
                "equipment": "HIGH",
                "special_requirements": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "equipment": "HIGH",
            "special_requirements": "HIGH",
        },
        "expected_special_requirements": [
            "CONESTOGA_REQUIRED",
            "SIDE_LOAD_VERIFY",
        ],
    },
    {
        "scenario_id": "flatbed_specific",
        "scenario_name": "Flatbed-specific requirement",
        "pasted_text": """
Broker: Synthetic Pasted Broker I
Broker MC: SYNTH-MC-9109
Rate: 3300
Pickup: Reno, NV
Pickup Date: 2026-07-19
Delivery: Boise, ID
Delivery Date: 2026-07-20
Commodity: Synthetic crated machinery
Weight: 33000
Reference: SYNTH-PASTE-009
Equipment: Flatbed
Special Requirements: TARPS_REQUIRED
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker I",
            "broker_mc": "SYNTH-MC-9109",
            "rate": 3300,
            "pickup_location": "Reno, NV",
            "pickup_date": "2026-07-19",
            "delivery_location": "Boise, ID",
            "delivery_date": "2026-07-20",
            "commodity": "Synthetic crated machinery",
            "weight": 33000,
            "reference_id": "SYNTH-PASTE-009",
            "equipment": "Flatbed",
            "special_requirements": ["TARPS_REQUIRED"],
            "field_confidence": {
                "equipment": "HIGH",
                "special_requirements": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "equipment": "HIGH",
            "special_requirements": "HIGH",
        },
        "expected_special_requirements": ["TARPS_REQUIRED"],
    },
    {
        "scenario_id": "unusual_reference_label",
        "scenario_name": "Unusual load number label",
        "pasted_text": """
Broker: Synthetic Pasted Broker J
Broker MC: SYNTH-MC-9110
Rate: 3250
Pickup: Omaha, NE
Pickup Date: 2026-07-21
Delivery: Kansas City, MO
Delivery Date: 2026-07-22
Commodity: Synthetic palletized metal
Weight: 35000
Shipment ID: SYNTH-PASTE-010
Equipment: Conestoga
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker J",
            "broker_mc": "SYNTH-MC-9110",
            "rate": 3250,
            "pickup_location": "Omaha, NE",
            "pickup_date": "2026-07-21",
            "delivery_location": "Kansas City, MO",
            "delivery_date": "2026-07-22",
            "commodity": "Synthetic palletized metal",
            "weight": 35000,
            "reference_id": "SYNTH-PASTE-010",
            "equipment": "Conestoga",
            "special_requirements": [],
            "field_confidence": {
                "reference_id": "MEDIUM",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "reference_id": "MEDIUM",
        },
        "expected_special_requirements": [],
    },
    {
        "scenario_id": "ambiguous_broker_contact_heavy",
        "scenario_name": "Contact-heavy text with ambiguous broker identity",
        "pasted_text": """
Company Header: Synthetic Header Entity K
Dispatch Contact: FAKE CONTACT ONLY
Rate: 3000
Pickup: Birmingham, AL
Pickup Date: 2026-07-23
Delivery: Richmond, VA
Delivery Date: 2026-07-24
Commodity: Synthetic building materials
Weight: 35000
Reference: SYNTH-PASTE-011
Equipment: Flatbed
""",
        "expected_parser_output": {
            "broker_name": "",
            "broker_mc": "",
            "rate": 3000,
            "pickup_location": "Birmingham, AL",
            "pickup_date": "2026-07-23",
            "delivery_location": "Richmond, VA",
            "delivery_date": "2026-07-24",
            "commodity": "Synthetic building materials",
            "weight": 35000,
            "reference_id": "SYNTH-PASTE-011",
            "equipment": "Flatbed",
            "special_requirements": ["BROKER_IDENTITY_NEEDS_REVIEW"],
            "field_confidence": {
                "broker_name": "LOW",
                "broker_mc": "UNKNOWN",
                "special_requirements": "LOW",
            },
        },
        "expected_missing_fields": ["broker_name", "broker_mc"],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "broker_name": "LOW",
            "broker_mc": "UNKNOWN",
            "special_requirements": "LOW",
        },
        "expected_special_requirements": ["BROKER_IDENTITY_NEEDS_REVIEW"],
    },
    {
        "scenario_id": "multi_stop_like_text",
        "scenario_name": "Multi-stop-like text without multi-stop parsing",
        "pasted_text": """
Broker: Synthetic Pasted Broker L
Broker MC: SYNTH-MC-9112
Rate: 4300
Pickup: Dallas, TX
Pickup Date: 2026-07-25
Delivery: Omaha, NE
Delivery Date: 2026-07-27
Commodity: Synthetic building materials
Weight: 43000
Reference: SYNTH-PASTE-012
Equipment: Flatbed
Special Requirements: MULTI_STOP_NEEDS_REVIEW, STOP_DETAILS_NEED_REVIEW
Notes: PU1 Dallas, PU2 Fort Worth, DEL1 Kansas City, DEL2 Omaha - synthetic only
""",
        "expected_parser_output": {
            "broker_name": "Synthetic Pasted Broker L",
            "broker_mc": "SYNTH-MC-9112",
            "rate": 4300,
            "pickup_location": "Dallas, TX",
            "pickup_date": "2026-07-25",
            "delivery_location": "Omaha, NE",
            "delivery_date": "2026-07-27",
            "commodity": "Synthetic building materials",
            "weight": 43000,
            "reference_id": "SYNTH-PASTE-012",
            "equipment": "Flatbed",
            "special_requirements": [
                "MULTI_STOP_NEEDS_REVIEW",
                "STOP_DETAILS_NEED_REVIEW",
            ],
            "field_confidence": {
                "pickup_location": "MEDIUM",
                "delivery_location": "MEDIUM",
                "special_requirements": "HIGH",
            },
        },
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_confidence": {
            "pickup_location": "MEDIUM",
            "delivery_location": "MEDIUM",
            "special_requirements": "HIGH",
        },
        "expected_special_requirements": [
            "MULTI_STOP_NEEDS_REVIEW",
            "STOP_DETAILS_NEED_REVIEW",
        ],
    },
]
