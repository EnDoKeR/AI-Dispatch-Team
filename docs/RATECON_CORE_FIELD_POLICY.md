# RateCon Core Field Policy

This policy aligns RateCon dry-run extraction with the user's working review table. It is local/dry-run intake policy only. It does not create or link DispatchCases, write events, call Google Maps, add Google Sheets, add OCR, or change Telegram behavior.

## Required Core Fields

RateCon review should treat these fields as the current core extraction target:

- `customer_name`
- `load_label`
- `pickup_location`
- `pickup_date`
- `delivery_location`
- `delivery_date`
- `load_number`
- `rate`
- `commodity`
- `weight`

Field aliases are allowed for compatibility:

- `customer_name` may be represented by existing `broker_name` until the parser emits the newer field directly.
- `load_number` may be represented by existing `reference_id` until the parser emits the newer field directly.
- `load_label` may later accept `load_type` or `load_title`.

## Optional Fields

These fields are useful but must not make current RateCon core extraction fail:

- `broker_mc`
- `equipment`

Broker MC is often absent from RateCons. Equipment is useful when present, but missing equipment alone should not block core RateCon review.

## Deferred Fields

Loaded miles are usually not present in RateCons. The user normally gets miles from Google Maps, which is not part of this block.

Until a later Google Maps/mileage block exists:

```text
loaded_miles = ""
miles_status = DEFERRED_GOOGLE_MAPS
miles_source = NOT_FROM_RATECON
```

Missing loaded miles must not make RateCon dry-run fail.

## Generic Intake Compatibility

Existing generic `IntakeRecord.missing_fields` may remain for older tests and report compatibility. User-facing RateCon dry-run result categories should use `missing_core_fields` from the RateCon core policy instead of generic mandatory fields.

## Success Rule

RateCon dry-run is core-ready when all required core fields are present or safely mapped through aliases.

RateCon dry-run should not be downgraded to field-fix status only because:

- `broker_mc` is absent;
- `equipment` is absent;
- `loaded_miles` is absent.

## Privacy Boundary

Tracked tests and docs must use fake values only. Do not commit private PDFs, extracted text, real customer/broker/contact names, MCs, addresses, phone numbers, emails, reference numbers, appointment details, or document snippets.
