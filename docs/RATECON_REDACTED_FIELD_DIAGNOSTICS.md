# RateCon Redacted Field Diagnostics

Date: 2026-05-30

This document defines a safe local-only diagnostic process for private RateCon PDF text extraction. It exists because first-pass PDF text extraction works, but the pasted-text parser may not recognize the structure of real extracted text yet.

The diagnostic layer helps identify which field-label signals appear in extracted private text without exposing the private values behind those labels.

## Purpose

Redacted field diagnostics should answer:

- whether the extracted text contains recognizable label signals;
- which field categories have label-like evidence;
- which fields the current parser/intake dry-run still misses;
- which parser gaps should be represented later with anonymized synthetic examples.

It should not answer by showing the private text itself.

## Local Inspection Boundary

Diagnostics may inspect extracted text locally in memory only.

Allowed local inputs:

- a local private PDF under `data/private_ratecons/originals/`;
- extracted text returned in memory from the local PDF extraction helper;
- existing parser/intake dry-run output held in memory.

Diagnostics must not:

- save extracted text;
- write diagnostic output containing private values;
- create tracked fixtures from private documents;
- create or link DispatchCases;
- write DispatchCase events;
- send Telegram;
- use Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, OCR, or reload-chain metadata.

## Allowed Output

Safe diagnostic output may include:

- anonymized label such as `RATECON_001`;
- extraction status;
- character count;
- page count;
- count of detected label signals by field category;
- detected/missing signal categories;
- parser extracted/missing status by field category;
- suspected parser gap field names;
- generic warnings;
- result category.

## Forbidden Output

Diagnostics must never print or save:

- raw extracted text;
- document lines;
- matched values;
- document snippets;
- real broker/customer/company/contact names;
- MC numbers;
- addresses;
- phone numbers;
- emails;
- reference/load numbers;
- appointment details;
- detention, layover, lumper, or accessorial text copied from the document.

## Field Signal Categories

The first diagnostic pass should count label-like signals for:

- `broker_name`;
- `broker_mc`;
- `rate`;
- `pickup_location`;
- `delivery_location`;
- `pickup_date`;
- `delivery_date`;
- `weight`;
- `commodity`;
- `reference_id`;
- `equipment`;
- `special_requirements`;
- `accessorials`.

Signal detection should count generic labels only, not values. Examples of allowed label concepts include words such as `broker`, `pickup`, `delivery`, `rate`, `weight`, `commodity`, `reference`, `equipment`, `detention`, `layover`, and `lumper`.

Legacy `app/load_intake/` review found additional generic label concepts that may be useful for future synthetic examples:

- `TRUCKLOAD RATE CONFIRMATION`;
- `Shipper Information`;
- `Consignee Information`;
- `Address`;
- `TOTAL`;
- `USD`;
- `Pick Up Time`;
- `Delivery Time`;
- `Load #`;
- `Carrier Name`;
- `Trailer Type/Size`;
- `Commodity Description`;
- `Total Weight`.

These are label concepts only. Do not copy private lines, matched values, document snippets, or old parser regex behavior into active parser code without synthetic tests.

## Parser Coverage Comparison

After signal detection, the coverage diagnostic may compare:

- field-label signals detected;
- fields extracted by the existing parser/intake dry-run;
- missing fields;
- needs-check fields.

The comparison should report only field names and statuses:

```text
yes
no
partial
missing
```

It must not include extracted values.

## How This Improves Parser Safely

Safe diagnostics can show patterns like:

```text
broker_mc signal detected, parser did not extract broker_mc
reference_id signal detected, parser did not extract reference_id
accessorial signals detected, parser marked special_requirements missing
```

Those patterns can then be recreated with fake/anonymized synthetic text in tests. Parser improvements should be based on those synthetic examples, not on committed private text.

## Stop Conditions

Stop diagnostics and return to process review if:

- a CLI prints raw extracted text;
- a report includes private values;
- diagnostic output needs document snippets to be useful;
- private text would need to be committed;
- OCR is required;
- the next step would create/link DispatchCases or write events.

## Implementation Status

Implemented safe diagnostics:

```text
app/market_intelligence/intake/ratecon_field_diagnostics.py
app/market_intelligence/intake/ratecon_parser_coverage.py
scripts/run_private_ratecon_redacted_diagnostics.py
```

Current command:

```powershell
py scripts/run_private_ratecon_redacted_diagnostics.py --limit 1
```

The command uses local extraction, runs redacted signal diagnostics, compares the signal counts to parser/intake coverage, and prints safe summaries only.

Current safe output includes:

- anonymized label;
- extraction status;
- character count;
- page count;
- signal counts by category;
- parser field status by category;
- missing and needs-check field names;
- suspected parser gap field names;
- result category;
- generic warnings.

Recommended next step:

```text
user runs redacted diagnostics locally and shares safe summary
```

Recommended follow-up:

```text
create anonymized synthetic RateCon examples from observed parser gap categories
```

Parser improvements should be based on fake/synthetic examples derived from the safe summaries. Do not improve parser patterns by committing private text or snippets.
