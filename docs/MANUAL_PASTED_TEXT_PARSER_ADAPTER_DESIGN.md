# Manual Pasted-text Parser Adapter Design

Date: 2026-05-29

This document designs a possible future pasted-text parser adapter. It does not implement parsing, regex extraction, PDF parsing, OCR, file reading, private RateCon processing, Gmail/email intake, Google Sheets, Telegram upload handling, Telegram sending, DispatchCase writes, DAT/API, Google Maps, scheduler/background processing, or legacy `app/load_intake` changes.

## Should The Next Parser Step Accept Pasted Text?

Yes, but only after the design is accepted.

Pasted text is safer than PDF parsing because:

- it avoids file handling
- it avoids OCR complexity
- it avoids private document storage in tests
- it can be tested with synthetic text only
- it lets the project validate parser output shape before real documents are processed

The adapter should remain dry-run only.

## Input Boundary

Future input should be a single manually supplied text string:

```text
raw pasted RateCon-like text
```

Possible future CLI shape:

```powershell
py scripts/run_pasted_text_parser_dry_run.py --text "...synthetic RateCon-like text..."
```

or:

```powershell
py scripts/run_pasted_text_parser_dry_run.py --stdin
```

The first implementation should use synthetic text in tests. It should not read PDFs, images, emails, Telegram uploads, or private files.

## Output Boundary

The adapter should output a parser-shaped dict/object only.

Target shape:

```python
{
    "source_type": "manual_pasted_text",
    "source_file_name": "",
    "broker_name": "",
    "broker_mc": "",
    "rate": "",
    "pickup_location": "",
    "pickup_date": "",
    "pickup_time": "",
    "delivery_location": "",
    "delivery_date": "",
    "delivery_time": "",
    "commodity": "",
    "weight": "",
    "reference_id": "",
    "equipment": "",
    "special_requirements": [],
    "field_confidence": {},
}
```

The adapter should then connect to:

```text
normalize_parser_output(...)
```

The normalized output can flow into the existing intake summary and dry-run report layers.

## Connection To Parser Contract

Accepted flow:

```text
pasted text
  -> pasted-text parser adapter returns structured parser output
  -> normalize_parser_output(...)
  -> build_intake_record(...)
  -> build_intake_record_summary(...)
```

The adapter should not bypass `normalize_parser_output(...)`.

## What It Must Not Do

The pasted-text adapter must not:

- make MATCH/BLOCK/REVIEW decisions
- choose whether a dispatcher should book a load
- send Telegram
- write Google Sheets
- create DispatchCase events
- write event logs
- contact broker
- call Gmail/email APIs
- read PDFs or images
- run OCR
- read private RateCon files
- write repository records unless a separate CLI option is later approved
- call DAT/API
- call Google Maps
- run scheduler/background loops

## Fields To Attempt First

First extraction attempts should focus on fields with common explicit labels:

- broker name
- broker MC
- rate
- pickup location
- pickup date
- delivery location
- delivery date
- reference/load number
- equipment

These should be attempted only from clear labels or simple synthetic patterns in the first implementation.

## Fields That Should Stay Needs-check Early

These fields should remain conservative:

- pickup time
- delivery time
- commodity
- weight
- special requirements
- accessorial terms
- multiple pickup/delivery structure
- detention/layover/lumper/TONU terms
- Conestoga-specific notes
- flatbed-only or no-Conestoga language

If these are extracted from free text rather than clear labels, they should receive lower confidence and be surfaced for human review.

## Confidence Policy

The adapter should use:

- `HIGH`: clear label and clean value
- `MEDIUM`: nearby label or simple table-like structure
- `LOW`: guessed from notes/free text
- `UNKNOWN`: missing or not evaluated

Confidence should be stored in `field_confidence` and normalized by:

```text
app/market_intelligence/intake/parser_confidence.py
```

Low confidence should not silently become a dispatch decision. It should remain review context.

## Tests Required Before Implementation

Before implementing the adapter, add tests with synthetic text only:

1. clean labeled synthetic text
2. missing broker MC
3. missing rate
4. missing pickup/delivery dates
5. reference number with unusual label
6. rate with accessorial text
7. appointment window text
8. Conestoga-specific synthetic text
9. ambiguous equipment text
10. adapter output normalizes through `normalize_parser_output(...)`
11. output is JSON-serializable
12. no forbidden imports
13. no file reading
14. no private data

Synthetic pasted-text fixtures now exist in:

```text
tests/fixtures/pasted_text_ratecon_examples.py
tests/test_pasted_text_ratecon_examples.py
```

They contain fake RateCon-like text only. No real RateCon text, private broker/customer/driver/contact data, PDFs, OCR output, or private files are committed.

## Recommended First Implementation Shape

If accepted later, implement a small pure helper:

```text
app/market_intelligence/intake/pasted_text_parser_adapter.py
```

Potential function:

```python
parse_pasted_text_to_parser_output(text, source_type="manual_pasted_text")
```

The first implementation should stay intentionally conservative. It should return blanks and low/unknown confidence rather than overfitting to one document style.

Implementation status:

```text
app/market_intelligence/intake/pasted_text_parser_adapter.py
tests/test_pasted_text_parser_adapter.py
```

The adapter extracts only obvious label/value fields from synthetic or manually pasted text. It does not parse PDFs, read files, process private RateCons, run OCR, or call integrations.

## Stop Conditions

Stop and redesign if:

- extraction requires broad brittle regex logic
- tests need real RateCon text
- the adapter starts making dispatch decisions
- the adapter needs PDF/OCR/file handling
- the adapter needs Telegram, Gmail, Google Sheets, or DispatchCase integration
