class SyntheticObjectParserOutput:
    source_type = "synthetic_object_parser"
    source_file_name = "synthetic_object_parser_output.txt"
    broker_name = "Synthetic Parser Broker H"
    broker_mc = "SYNTH-MC-5008"
    rate = 3350
    pickup_location = "Tulsa, OK"
    pickup_date = "2026-06-20"
    delivery_location = "Nashville, TN"
    delivery_date = "2026-06-21"
    commodity = "Synthetic steel beams"
    weight = 40000
    reference_id = "SYNTH-PARSER-008"
    equipment = "Conestoga"
    special_requirements = ["APPOINTMENT_REQUIRED"]
    field_confidence = {"rate": "HIGH"}


PARSER_CONTRACT_OUTPUTS = [
    {
        "scenario_id": "clean_parser_output",
        "raw_output": {
            "source_type": "synthetic_parser",
            "source_file_name": "synthetic_clean_output.txt",
            "broker_name": "Synthetic Parser Broker A",
            "broker_mc": "SYNTH-MC-5001",
            "rate": 3200,
            "pickup_location": "Dallas, TX",
            "pickup_date": "2026-05-30",
            "delivery_location": "Denver, CO",
            "delivery_date": "2026-05-31",
            "commodity": "Synthetic steel coils",
            "weight": 42000,
            "reference_id": "SYNTH-PARSER-001",
            "equipment": "Conestoga",
        },
        "expected_status": "READY_FOR_REVIEW",
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
    },
    {
        "scenario_id": "missing_broker_mc",
        "raw_output": {
            "broker_name": "Synthetic Parser Broker B",
            "rate": 2800,
            "pickup_location": "Laredo, TX",
            "pickup_date": "2026-06-01",
            "delivery_location": "Atlanta, GA",
            "delivery_date": "2026-06-02",
            "commodity": "Synthetic pipe",
            "weight": 39000,
            "reference_id": "SYNTH-PARSER-002",
            "equipment": "Flatbed",
        },
        "expected_status": "MISSING_FIELDS",
        "expected_missing_fields": ["broker_mc"],
        "expected_needs_check_fields": ["broker_mc"],
    },
    {
        "scenario_id": "missing_dates",
        "raw_output": {
            "broker_name": "Synthetic Parser Broker C",
            "broker_mc": "SYNTH-MC-5003",
            "rate": 3000,
            "pickup_location": "Phoenix, AZ",
            "delivery_location": "Dallas, TX",
            "commodity": "Synthetic machinery",
            "weight": 36000,
            "reference_id": "SYNTH-PARSER-003",
            "equipment": "Conestoga",
        },
        "expected_status": "MISSING_FIELDS",
        "expected_missing_fields": ["pickup_date", "delivery_date"],
        "expected_needs_check_fields": ["pickup_date", "delivery_date"],
    },
    {
        "scenario_id": "missing_commodity_weight",
        "raw_output": {
            "broker_name": "Synthetic Parser Broker D",
            "broker_mc": "SYNTH-MC-5004",
            "rate": 2950,
            "pickup_location": "Houston, TX",
            "pickup_date": "2026-06-03",
            "delivery_location": "Memphis, TN",
            "delivery_date": "2026-06-04",
            "reference_id": "SYNTH-PARSER-004",
            "equipment": "Flatbed",
        },
        "expected_status": "MISSING_FIELDS",
        "expected_missing_fields": ["weight", "commodity"],
        "expected_needs_check_fields": [],
    },
    {
        "scenario_id": "weak_field_confidence",
        "raw_output": {
            "broker_name": "Synthetic Parser Broker E",
            "broker_mc": "SYNTH-MC-5005",
            "rate": 3050,
            "pickup_location": "Reno, NV",
            "pickup_date": "2026-06-15",
            "delivery_location": "Boise, ID",
            "delivery_date": "2026-06-16",
            "commodity": "Synthetic crated machinery",
            "weight": 33000,
            "reference_id": "SYNTH-PARSER-005",
            "equipment": "Conestoga",
            "field_confidence": {
                "rate": "LOW",
                "weight": "LOW",
            },
        },
        "expected_status": "READY_FOR_REVIEW",
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
    },
    {
        "scenario_id": "special_requirements",
        "raw_output": {
            "broker_name": "Synthetic Parser Broker F",
            "broker_mc": "SYNTH-MC-5006",
            "rate": 3400,
            "pickup_location": "Mobile, AL",
            "pickup_date": "2026-06-13",
            "delivery_location": "Columbus, OH",
            "delivery_date": "2026-06-14",
            "commodity": "Synthetic steel plate",
            "weight": 45000,
            "reference_id": "SYNTH-PARSER-006",
            "equipment": "Flatbed",
            "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
        },
        "expected_status": "READY_FOR_REVIEW",
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
    },
    {
        "scenario_id": "source_metadata_override",
        "raw_output": {
            "source_type": "synthetic_raw_parser",
            "source_file_name": "raw_source_name.txt",
            "broker_name": "Synthetic Parser Broker G",
            "broker_mc": "SYNTH-MC-5007",
            "rate": 3600,
            "pickup_location": "San Antonio, TX",
            "pickup_date": "2026-06-17",
            "delivery_location": "Savannah, GA",
            "delivery_date": "2026-06-19",
            "commodity": "Synthetic construction equipment",
            "weight": 40000,
            "reference_id": "SYNTH-PARSER-007",
            "equipment": "Flatbed",
        },
        "source_type": "contract_override",
        "source_file_name": "synthetic_override.pdf",
        "expected_status": "READY_FOR_REVIEW",
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
        "expected_source_type": "contract_override",
        "expected_source_file_name": "synthetic_override.pdf",
    },
    {
        "scenario_id": "object_style_parser_output",
        "raw_output": SyntheticObjectParserOutput(),
        "expected_status": "READY_FOR_REVIEW",
        "expected_missing_fields": [],
        "expected_needs_check_fields": [],
    },
]
