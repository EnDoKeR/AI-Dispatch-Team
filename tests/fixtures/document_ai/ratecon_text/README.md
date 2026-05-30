# Fake RateCon Text Fixtures

These fixtures are fake/anonymized and are used only for candidate extraction
tests.

Rules:

- no private RateCon text;
- no real broker/customer/driver data;
- no real MCs, addresses, phone numbers, emails, or reference numbers;
- fixtures test candidate extraction, not production accuracy;
- candidate extraction does not create DispatchCases or dispatch decisions.

Fixture intent:

- `simple_clean_ratecon.txt`: broad happy-path candidate coverage.
- `multi_amount_ratecon.txt`: one true carrier-pay amount plus accessorials.
- `ambiguous_references_ratecon.txt`: multiple typed reference labels.
- `multi_stop_ratecon.txt`: multiple pickup/delivery stop-like sections.
- `missing_core_fields_ratecon.txt`: intentionally absent core fields.
- `conflict_rate_ratecon.txt`: conflicting plausible rate labels.
