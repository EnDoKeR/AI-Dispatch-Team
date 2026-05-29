DECISION_ENGINE_COMPARISON_LOADS = [
    {
        "scenario_id": "match_load_opportunity",
        "scenario_name": "MATCH / LOAD OPPORTUNITY",
        "load": {
            "load_id": "SYN-COMP-LOAD-1",
            "reference_id": "SYN-COMP-REF-1",
            "driver_match_status": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "driver_match_notes": ["Synthetic clean lane fit."],
            "match_reasons": ["Synthetic strong RPM."],
            "review_reasons": [],
            "block_reasons": [],
        },
        "expected_decision": "MATCH",
        "expected_category": "LOAD OPPORTUNITY",
        "expected_risk_flags": [],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
    {
        "scenario_id": "review_once_rate_check",
        "scenario_name": "REVIEW_ONCE / RATE CHECK",
        "load": {
            "load_id": "SYN-COMP-LOAD-2",
            "reference_id": "SYN-COMP-REF-2",
            "driver_match_status": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "driver_match_notes": [
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            "review_reasons": [
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            "block_reasons": [],
            "match_reasons": [],
            "rate": 0,
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "RATE CHECK",
        "expected_risk_flags": ["RATE_MISSING", "RATE_CHECK_REQUIRED"],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
    {
        "scenario_id": "review_once_conestoga_verify",
        "scenario_name": "REVIEW_ONCE / CONESTOGA VERIFY",
        "load": {
            "load_id": "SYN-COMP-LOAD-3",
            "reference_id": "SYN-COMP-REF-3",
            "driver_match_status": "REVIEW_ONCE",
            "category": "CONESTOGA VERIFY",
            "driver_match_notes": [
                "Posted as Flatbed/Step Deck; Conestoga must be verified."
            ],
            "review_reasons": [
                "Posted as Flatbed/Step Deck; Conestoga must be verified."
            ],
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "CONESTOGA VERIFY",
        "expected_risk_flags": ["CONESTOGA_VERIFY"],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
    {
        "scenario_id": "block_payment_risk",
        "scenario_name": "BLOCK / PAYMENT RISK",
        "load": {
            "load_id": "SYN-COMP-LOAD-4",
            "reference_id": "SYN-COMP-REF-4",
            "driver_match_status": "BLOCK",
            "category": "BLOCK",
            "driver_match_notes": [
                "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
            ],
            "block_reasons": [
                "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
            ],
            "is_blocked": True,
        },
        "expected_decision": "BLOCK",
        "expected_category": "BLOCK",
        "expected_risk_flags": ["PAYMENT_RISK"],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
    {
        "scenario_id": "block_equipment_mismatch",
        "scenario_name": "BLOCK / EQUIPMENT MISMATCH",
        "load": {
            "load_id": "SYN-COMP-LOAD-5",
            "reference_id": "SYN-COMP-REF-5",
            "driver_match_status": "BLOCK",
            "category": "BLOCK",
            "driver_match_notes": ["Notes say Conestoga is not accepted."],
            "block_reasons": ["Notes say Conestoga is not accepted."],
            "is_blocked": True,
        },
        "expected_decision": "BLOCK",
        "expected_category": "BLOCK",
        "expected_risk_flags": ["NO_CONESTOGA"],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
    {
        "scenario_id": "missing_reference_id",
        "scenario_name": "Missing reference ID stays safe",
        "load": {
            "load_id": "SYN-COMP-LOAD-6",
            "reference_id": "",
            "driver_match_status": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "driver_match_notes": ["Synthetic clean lane fit."],
            "match_reasons": ["Synthetic clean lane fit."],
        },
        "expected_decision": "MATCH",
        "expected_category": "LOAD OPPORTUNITY",
        "expected_risk_flags": [],
        "expected_decision_matches": True,
        "expected_category_matches": True,
        "expected_warnings": ["missing_reference_id"],
    },
    {
        "scenario_id": "missing_category",
        "scenario_name": "Missing category is reported safely",
        "load": {
            "load_id": "SYN-COMP-LOAD-7",
            "reference_id": "SYN-COMP-REF-7",
            "driver_match_status": "",
            "category": "",
            "driver_match_notes": [],
        },
        "expected_decision": "NO_ACTION",
        "expected_category": "",
        "expected_risk_flags": [],
        "expected_decision_matches": True,
        "expected_category_matches": True,
        "expected_warnings": [
            "missing_original_decision",
            "missing_original_category",
            "unknown_or_empty_decision",
        ],
    },
    {
        "scenario_id": "tracking_risk_mapping",
        "scenario_name": "Risk flag mapping example",
        "load": {
            "load_id": "SYN-COMP-LOAD-8",
            "reference_id": "SYN-COMP-REF-8",
            "driver_match_status": "REVIEW_ONCE",
            "category": "DRIVER REQUIREMENTS",
            "driver_match_notes": [
                "Tracking required; confirm driver accepts tracking."
            ],
            "review_reasons": [
                "Tracking required; confirm driver accepts tracking."
            ],
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "DRIVER REQUIREMENTS",
        "expected_risk_flags": ["TRACKING_REQUIRED"],
        "expected_decision_matches": True,
        "expected_category_matches": True,
    },
]
