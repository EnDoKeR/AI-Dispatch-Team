# RateCon / Document Intake Workflow

Date: 2026-05-29

Scope:

- design only
- no parser behavior changes
- no OCR
- no Gmail/email integration
- no Google Sheets export
- no Telegram file upload handling
- no DispatchCase writes
- no DAT/API, Google Maps, scheduler, or live automation

## Product Goal

Future RateCon / broker document intake should turn a broker document into structured dispatch evidence.

It should not become a hidden decision engine.

The system should eventually help the dispatcher answer:

- What did the document say?
- What fields were confidently extracted?
- What fields are missing?
- What fields need human verification?
- Which existing DispatchCase does this document belong to?
- What should the dispatcher ask the broker before moving forward?

## Future Workflow

Accepted future direction:

```text
dispatcher provides document
  -> system records source metadata
  -> parser extracts candidate fields
  -> normalizer builds a JSON-ready intake record
  -> validator marks missing / needs-check fields
  -> system shows human-readable summary
  -> later links to DispatchCase
  -> later optional export or broker follow-up
```

Document sources can be added later, one at a time:

- manual CLI / local file path
- Telegram upload
- email/Gmail attachment
- broker portal download

Only manual/local dry-run should be considered first.

## Fields To Extract

Target fields:

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

Useful source metadata:

- intake id
- source type
- source file name
- source file path
- received timestamp
- parser version
- confidence / extraction status

## MVP Boundary

First implementation should be:

```text
manual local file or synthetic input
  -> JSON-ready intake record
  -> missing / needs-check field lists
  -> console or dry-run text summary
```

The first implementation should not:

- send Telegram messages
- read Telegram uploads
- read Gmail/email
- write Google Sheets
- write DispatchCase events
- make dispatch decisions
- call OCR services
- expand the existing PDF parser

The safest first implementation target after this design is a pure JSON-ready record helper, not a parser.

## Mandatory Fields

The record can exist without all mandatory fields, but missing mandatory fields must be flagged.

Mandatory for dispatch review:

- broker name or broker MC
- rate
- pickup location
- delivery location
- pickup date or appointment window
- delivery date or appointment window
- reference/load number

Mandatory for safe physical compatibility:

- equipment
- weight

If any mandatory field is missing, the record should be created with a clear missing-field warning instead of failing silently.

## Needs-Check Fields

Some extracted fields may exist but still require review.

Examples:

- broker name extracted but broker MC missing
- rate extracted as text with unclear currency/format
- pickup or delivery location missing state
- date extracted without time
- weight appears as multiple line items
- equipment says Flatbed/Step Deck while driver is Conestoga
- special requirements mention tarps, OD, permits, escorts, hazmat, TWIC, or tracking
- reference id is present but generic or duplicated

These should be placed in `needs_check_fields`, not treated as hard parser failure.

## First Output Policy

Recommended first output:

```text
JSON-ready intake record + dry-run human-readable summary
```

Why:

- JSON record gives stable tests and future storage shape.
- Dry-run summary lets dispatcher inspect extraction quality.
- It avoids live Telegram, Google Sheets, and DispatchCase coupling too early.

Later outputs:

- Telegram summary after upload handling is designed
- DispatchCase linkage after matching rules are designed
- Google Sheet export after field quality and schema are stable
- broker email/request draft after missing-field workflow is accepted

## DispatchCase Link Later

Future DispatchCase matching should use structured fields, not document text.

Likely match keys:

- reference/load number
- broker MC
- broker name
- pickup location
- delivery location
- rate

If no confident case match exists, the document should remain an unlinked intake record until a dispatcher links it or a later match appears.

## Test Scenarios Needed Before Live Use

Future tests should cover:

- complete clean RateCon
- missing broker MC
- missing rate
- missing appointment time
- multi-stop or multiple weight lines
- different broker document layouts
- unclear pickup/delivery state
- equipment mismatch / Conestoga verification
- duplicate reference id
- document linked to existing DispatchCase
- document not linked because confidence is low

## What Must Not Be Built Yet

Do not build yet:

- live Telegram upload handling
- Gmail/email ingestion
- Google Sheets export
- OCR service integration
- parser expansion
- DispatchCase event writes
- automatic broker follow-up email
- DAT/API or Google Maps integration

## Recommended Next Target

Next safe target:

```text
Intake structured record model proposal
```

That record model now lives in:

```text
docs/INTAKE_RECORD_MODEL.md
```

It defines the JSON-ready record shape before any helper, storage, parser, or integration work.
