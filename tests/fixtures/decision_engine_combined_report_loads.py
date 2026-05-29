DECISION_ENGINE_COMBINED_REPORT_LOADS = [
    {
        "scenario_id": "match_load_opportunity",
        "scenario_name": "MATCH / load opportunity",
        "load": {
            "case_id": "CASE-COMBINED-MATCH",
            "load_id": "LOAD-COMBINED-MATCH",
            "reference_id": "REF-COMBINED-MATCH",
            "timestamp_utc": "2026-05-29T10:00:00Z",
            "driver_match_status": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "driver_match_notes": ["Synthetic clean lane fit."],
            "match_reasons": ["Synthetic strong RPM."],
        },
        "expected_decision": "MATCH",
        "expected_category": "LOAD OPPORTUNITY",
    },
    {
        "scenario_id": "review_once_rate_check",
        "scenario_name": "REVIEW_ONCE / rate check",
        "load": {
            "case_id": "CASE-COMBINED-RATE",
            "load_id": "LOAD-COMBINED-RATE",
            "reference_id": "REF-COMBINED-RATE",
            "timestamp_utc": "2026-05-29T10:05:00Z",
            "driver_match_status": "REVIEW_ONCE",
            "category": "RATE CHECK",
            "driver_match_notes": [
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            "review_reasons": [
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            ],
            "rate": 0,
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "RATE CHECK",
        "expected_risk_flags": ["RATE_MISSING", "RATE_CHECK_REQUIRED"],
    },
    {
        "scenario_id": "review_once_conestoga_verify",
        "scenario_name": "REVIEW_ONCE / Conestoga verify",
        "load": {
            "case_id": "CASE-COMBINED-CONESTOGA",
            "load_id": "LOAD-COMBINED-CONESTOGA",
            "reference_id": "REF-COMBINED-CONESTOGA",
            "timestamp_utc": "2026-05-29T10:10:00Z",
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
    },
    {
        "scenario_id": "block_payment_risk",
        "scenario_name": "BLOCK / payment risk",
        "load": {
            "case_id": "CASE-COMBINED-PAYMENT",
            "load_id": "LOAD-COMBINED-PAYMENT",
            "reference_id": "REF-COMBINED-PAYMENT",
            "timestamp_utc": "2026-05-29T10:15:00Z",
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
    },
    {
        "scenario_id": "block_equipment_mismatch",
        "scenario_name": "BLOCK / equipment mismatch",
        "load": {
            "case_id": "CASE-COMBINED-EQUIPMENT",
            "load_id": "LOAD-COMBINED-EQUIPMENT",
            "reference_id": "REF-COMBINED-EQUIPMENT",
            "timestamp_utc": "2026-05-29T10:20:00Z",
            "driver_match_status": "BLOCK",
            "category": "BLOCK",
            "driver_match_notes": ["Notes say Conestoga is not accepted."],
            "block_reasons": ["Notes say Conestoga is not accepted."],
            "is_blocked": True,
        },
        "expected_decision": "BLOCK",
        "expected_category": "BLOCK",
        "expected_risk_flags": ["NO_CONESTOGA"],
    },
    {
        "scenario_id": "missing_reference_id",
        "scenario_name": "Missing reference ID",
        "load": {
            "case_id": "CASE-COMBINED-NOREF",
            "load_id": "LOAD-COMBINED-NOREF",
            "reference_id": "",
            "timestamp_utc": "2026-05-29T10:25:00Z",
            "driver_match_status": "MATCH",
            "category": "LOAD OPPORTUNITY",
            "driver_match_notes": ["Synthetic clean lane fit."],
            "match_reasons": ["Synthetic clean lane fit."],
        },
        "expected_decision": "MATCH",
        "expected_category": "LOAD OPPORTUNITY",
        "expected_warnings": ["missing_reference_id"],
    },
    {
        "scenario_id": "weak_exit_market",
        "scenario_name": "REVIEW_ONCE / weak exit market",
        "load": {
            "case_id": "CASE-COMBINED-EXIT",
            "load_id": "LOAD-COMBINED-EXIT",
            "reference_id": "REF-COMBINED-EXIT",
            "timestamp_utc": "2026-05-29T10:30:00Z",
            "driver_match_status": "REVIEW_ONCE",
            "category": "EXIT PLAN NEEDED",
            "driver_match_notes": [
                "Synthetic delivery market is weak; reload plan should be reviewed."
            ],
            "review_reasons": [
                "Synthetic delivery market is weak; reload plan should be reviewed."
            ],
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "EXIT PLAN NEEDED",
    },
    {
        "scenario_id": "broker_mc_missing",
        "scenario_name": "REVIEW_ONCE / broker MC missing",
        "load": {
            "case_id": "CASE-COMBINED-BROKER",
            "load_id": "LOAD-COMBINED-BROKER",
            "reference_id": "REF-COMBINED-BROKER",
            "timestamp_utc": "2026-05-29T10:35:00Z",
            "driver_match_status": "REVIEW_ONCE",
            "category": "BROKER REVIEW",
            "broker_mc": "",
            "driver_match_notes": ["Broker MC is missing and needs review."],
            "review_reasons": ["Broker MC is missing and needs review."],
        },
        "expected_decision": "REVIEW_ONCE",
        "expected_category": "BROKER REVIEW",
        "expected_risk_flags": ["BROKER_MC_MISSING"],
    },
]
