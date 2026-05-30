# RateCon Redacted Layout-shape Diagnostics

Date: 2026-05-30

This document defines a safe local-only process for inspecting label/value layout shapes in extracted private RateCon text. It exists because the first private batch showed many field-label signals, but the parser still marked required fields missing. Signal counts prove labels exist; they do not explain whether values are on the same line, the next line, in a section block, or in a table-like layout.

## Purpose

Redacted layout-shape diagnostics should answer:

- which label/value structures appear in extracted text;
- whether values appear next to labels, after section headers, or in table-like rows;
- which safe synthetic examples should be created next;
- why parser coverage may fail even when label signals are detected.

It must not reveal the private values behind those labels.

## Allowed Output

Safe output may include:

- anonymized label such as `RATECON_001`;
- extraction status, page count, and character count;
- field category name;
- normalized label token;
- structural shape with values replaced by placeholders;
- counts by field category and shape;
- broad line position group such as `beginning`, `middle`, or `end`;
- generic warnings.

Allowed safe shape examples:

```text
TOTAL: USD $ <AMOUNT>
Load #: <ID>
Shipper Information -> Address: <LOCATION>
Consignee Information -> Address: <LOCATION>
Total Weight: <WEIGHT>
Trailer Type/Size: <EQUIPMENT>
```

## Forbidden Output

Diagnostics must never print, save, or commit:

- raw extracted text;
- raw lines;
- document snippets with private values;
- real broker/customer/company/contact names;
- MC numbers;
- addresses;
- phone numbers;
- emails;
- reference/load numbers;
- appointment details;
- detention, layover, lumper, or accessorial text copied from the document.

## Placeholder Rules

Any detected value-like text must be replaced before it leaves memory:

- dollar amounts become `<AMOUNT>`;
- IDs and reference numbers become `<ID>`;
- MC numbers become `<MC>`;
- locations and address-like text become `<LOCATION>`;
- dates become `<DATE>`;
- times become `<TIME>`;
- phone numbers, emails, and contact-like text become `<CONTACT>`;
- generic text after sensitive labels becomes `<VALUE>`;
- weight values become `<WEIGHT>`;
- equipment values become `<EQUIPMENT>`.

The diagnostic output should prefer a generic placeholder over a risky value. When uncertain, use `<VALUE>`.

## Field Categories

The first layout-shape detector should group shapes into:

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

## Diagnostic-only Boundary

This is diagnostic only.

It must not:

- improve parser behavior directly from private text;
- create tracked fixtures from private documents;
- save extracted text;
- write DispatchCase events;
- create or link DispatchCases;
- send Telegram;
- call Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, or OCR.

Parser improvements must be made only after a safe layout shape is represented by fake/synthetic examples.

## Safe Workflow

1. Extract text locally in memory with the existing private PDF dry-run helper.
2. Count redacted field signals.
3. Detect redacted layout shapes.
4. Print only anonymized labels, counts, placeholders, and generic warnings.
5. Create new fake/anonymized scenarios from the shapes if parser gaps remain.
6. Improve parser behavior only against those fake scenarios.

## Stop Conditions

Stop and return to process review if:

- a CLI prints raw extracted text or values;
- a shape requires a private snippet to be understandable;
- a tracked fixture would need private-derived text;
- OCR is required;
- the next step would add Google Sheets, Telegram upload, Gmail/email, DispatchCase writes, DAT/API, Google Maps, or accounting/factoring behavior.
