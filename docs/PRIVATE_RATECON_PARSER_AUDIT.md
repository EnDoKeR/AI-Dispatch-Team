# Private RateCon Parser Audit

Date: 2026-05-29

This audit prepares the future private RateCon parser boundary. It does not implement PDF parsing, OCR, file reading, Gmail/email intake, Google Sheets, Telegram upload handling, Telegram sending, DispatchCase writes, DAT/API, Google Maps, scheduler/background processing, or legacy `app/load_intake` changes.

## Parser Goal

The future parser should extract structured evidence from a broker document and pass that evidence into the intake parser contract:

```text
parser output dict/object -> normalize_parser_output(...) -> build_intake_record(...)
```

The parser should answer what the document appears to say. It must not decide whether a load is a match, block, review-once candidate, reload-watch candidate, or booking recommendation.

## Required Extraction Fields

The future parser should attempt to extract:

- broker name
- broker MC
- rate
- pickup location
- pickup date
- pickup time
- delivery location
- delivery date
- delivery time
- commodity
- weight
- reference/load number
- equipment
- special requirements

These fields should map to the current intake record shape:

- `broker_name`
- `broker_mc`
- `rate`
- `pickup_location`
- `pickup_date`
- `pickup_time`
- `delivery_location`
- `delivery_date`
- `delivery_time`
- `commodity`
- `weight`
- `reference_id`
- `equipment`
- `special_requirements`

## Mandatory Dispatch Fields

The current intake record model treats these fields as mandatory for dispatch review:

- broker name
- broker MC
- rate
- pickup location
- pickup date
- delivery location
- delivery date
- commodity
- weight
- reference/load number
- equipment

Missing mandatory fields should appear in `missing_fields`.

Pickup and delivery times are useful but not mandatory in the first intake record foundation. If a time is absent or ambiguous, the parser should preserve the blank field and add confidence/context rather than guessing.

## Optional Fields To Capture

These fields may not be mandatory in the current record, but should be captured when visible:

- pickup appointment window
- delivery appointment window
- detention terms
- layover terms
- lumper fees
- TONU terms
- tracking requirements
- tarp requirements
- Conestoga-specific requirements
- contact-heavy notes
- accessorial notes
- multi-stop notes

The current normalized target for these is usually `special_requirements`, plus future parser evidence/context fields if added later.

## Missing Fields Policy

Trigger `missing_fields` when a mandatory field cannot be extracted with usable value:

- broker name missing
- broker MC missing
- rate missing
- pickup location missing
- pickup date missing
- delivery location missing
- delivery date missing
- commodity missing
- weight missing
- reference/load number missing
- equipment missing

If broker name exists but broker MC is missing, both the record model and parser audit should treat `broker_mc` as missing and needing human verification.

If broker MC exists but broker name is missing, `broker_name` should be missing and needing human verification.

If pickup location exists but pickup date is missing, `pickup_date` should be missing. Same rule applies to delivery location and delivery date.

## Needs-check Policy

Trigger `needs_check_fields` when a value exists but may be incomplete, inferred, contradictory, low-confidence, or operationally sensitive.

Likely needs-check cases:

- broker identity is partial
- MC number is present but label is unclear
- rate appears in multiple places with conflicting amounts
- total charges differ from linehaul plus accessorials
- pickup or delivery date is inferred from appointment text
- pickup or delivery time is a window, not an exact appointment
- commodity is vague, such as "FAK" or "material"
- weight is approximate or appears only in notes
- reference ID appears under unusual labels
- equipment appears only in notes
- special requirements include unclear tarp, OD, escort, permit, or Conestoga language
- document has multiple pickups or deliveries
- scanned/low-quality source later reduces confidence

The parser should not hide uncertainty. A field with low confidence is more useful as "needs check" than as a silent best guess.

## Confidence Tracking

These fields should carry confidence when possible:

- broker name
- broker MC
- rate
- pickup location
- pickup date
- pickup time
- delivery location
- delivery date
- delivery time
- commodity
- weight
- reference/load number
- equipment
- special requirements

Confidence should describe extraction certainty, not business quality.

Examples:

- high confidence: value appears beside a clear label
- medium confidence: value is inferred from nearby label or table layout
- low confidence: value is guessed from notes or ambiguous text
- unknown confidence: value missing or parser cannot evaluate confidence

Future confidence data should fit under `field_confidence` in the intake record.

Accepted confidence levels:

- `HIGH`
- `MEDIUM`
- `LOW`
- `UNKNOWN`

Convention:

- unknown or invalid confidence values normalize to `UNKNOWN`
- if a caller asks for expected fields, missing confidence entries should be represented as `UNKNOWN`
- if no expected field list is provided, absent confidence keys can stay absent
- low confidence fields can be reported for future human review, but this helper does not automatically change dispatch decisions

The focused helper for this policy lives in:

```text
app/market_intelligence/intake/parser_confidence.py
tests/test_parser_confidence.py
```

It is pure and does not implement document parsing.

## Expected Layout Problems

Common RateCon parser risks:

- broker name appears only in logo/header
- MC number is missing or hard to identify
- rate appears multiple times
- total charges may include linehaul, fuel, detention, layover, lumper, TONU, or other accessorials
- linehaul and total may conflict
- multiple pickups or deliveries may be represented as tables
- appointment windows can be broad or split across date/time fields
- timezone may be omitted or implied
- commodity can be missing, vague, or hidden in notes
- weight can be missing, approximate, or tied to commodity notes
- reference/load number can appear under labels such as load, shipment, confirmation, pro, order, or trip
- equipment can be hidden in notes instead of a field
- detention/layover/lumper/TONU terms can look like rate terms but are not base rate
- scanned/low-quality PDFs may require OCR later
- the same field can appear with conflicting values in header, table, and fine print

## Parser Must Never Decide

The parser must not decide:

- MATCH / BLOCK / REVIEW_ONCE
- whether a broker is buy/no-buy
- whether a driver should take a load
- whether a reload watch should start
- whether a chain is strong or weak
- whether a RateCon should create a DispatchCase
- whether missing fields are acceptable for booking

Those decisions belong to decision, market context, DispatchCase, or dispatcher review layers.

## Outside Parser Responsibility

The parser must not:

- send Telegram
- write Google Sheets
- create DispatchCase events
- contact broker by email
- call Gmail/email APIs
- write event logs
- write JSON repository records directly
- call DAT/API
- call Google Maps
- run scheduler/background loops
- mutate legacy `app/load_intake`
- store real RateCon PDFs in Git

## Connection To Current Contract

Current accepted contract:

```text
app/market_intelligence/intake/parser_contract.py
```

The future parser should return a dict/object with structured fields. The contract layer should normalize that output into:

```text
app/market_intelligence/intake/record.py
```

Then the existing summary/report/repository layers can dry-run or store normalized JSON-ready records without knowing how the document was parsed.

This keeps parser extraction separate from:

- intake record normalization
- missing/needs-check validation
- dry-run summaries
- local JSON repository
- DispatchCase linking
- Telegram presentation
- Google Sheets export

## Safe Next Step

The next implementation should not be PDF parsing.

Safer next candidates:

1. parser expected output synthetic examples
2. parser confidence policy/helper
3. manual pasted-text parser adapter design

Any real private RateCon work must stay local under `data/private_ratecons/` and should begin with a small 10-15 document batch after this audit is accepted.

## Synthetic Expected Outputs

Synthetic parser expected-output fixtures exist in:

```text
tests/fixtures/parser_expected_outputs.py
tests/test_parser_expected_outputs.py
```

They describe fake future parser outputs for clean RateCons, missing fields, multi-stop structure, accessorial notes, low-confidence fields, appointment windows, special requirements, and Conestoga-specific language.

These fixtures do not parse files and do not use real RateCon data. They only prove that future parser-shaped output can normalize through the intake parser contract and produce intake summaries.
