# Private RateCon Field Inventory Plan

Date: 2026-05-29

This plan defines a local-only manual process for inventorying the first private RateCons before any parser, PDF extraction, OCR, Telegram upload, Gmail/email, Google Sheets, DispatchCase writes, DAT/API, Google Maps, accounting/factoring, or reload-chain work.

## Purpose

The inventory is meant to answer:

- which fields are consistently visible on real RateCons;
- which fields are missing or ambiguous;
- which fields require human review;
- which document layouts are difficult for a future parser;
- which synthetic/anonymized scenarios should be created later.

The inventory is not parser output. It is a human review aid for future dry-run parser work.

## Storage And Privacy Rules

Private RateCon files stay local under:

```text
data/private_ratecons/
```

This folder is gitignored.

Do not commit:

- real RateCon PDFs, screenshots, scans, or images;
- copied private RateCon text;
- extracted private text;
- real broker/customer/driver/company/contact data;
- real phone numbers, emails, signatures, addresses, appointment notes, or reference numbers;
- local inventory files containing private operational details.

Only anonymized or synthetic examples may enter the repository.

## First Batch Size

Start with:

```text
10-15 private RateCons
```

Do not start with 100+ documents. A small varied batch is safer and easier to inspect while parser behavior is still not implemented.

## What To Review Manually

For each private RateCon, the dispatcher or reviewer should manually inspect:

- where the broker name appears;
- whether broker MC is present and clearly labeled;
- where the total rate appears;
- whether rate is split into linehaul/accessorials;
- pickup and delivery locations;
- pickup and delivery dates/times;
- appointment windows;
- commodity;
- weight;
- reference/load number labels;
- equipment requirements;
- special requirements;
- detention/layover/lumper/accessorial notes;
- whether there are multiple pickups or deliveries;
- which fields are missing;
- which fields need human check;
- which fields would be hard for a parser.

## Required Inventory Fields

Use these fields for each private document review:

```text
file_label / local filename reference
broker_name
broker_mc
rate
pickup_location
pickup_date
pickup_time
delivery_location
delivery_date
delivery_time
commodity
weight
reference_id / load number
equipment
special_requirements
detention/layover/lumper/accessorial notes if present
appointment windows
number of pickups/deliveries
missing_fields
needs_check_fields
confidence_notes
parser difficulty notes
```

If keeping local notes, store them outside Git or in a gitignored local file. Do not paste private operational values into committed docs.

## First Batch Categories

Try to collect 10-15 documents covering these categories. One document may satisfy more than one category.

1. clean/simple RateCon
2. missing weight
3. missing commodity
4. missing broker MC
5. unusual reference/load number placement
6. multiple pickups/deliveries
7. appointment windows
8. detention/layover/lumper/accessorials
9. Conestoga-specific
10. flatbed-specific
11. hard-to-read or scan-like
12. rate with linehaul/accessorial split
13. broker/contact-heavy format
14. revised rate confirmation if available
15. unusual special requirements

## Suggested Local Workflow

1. Put private files in `data/private_ratecons/`.
2. Confirm `git status` does not show private files.
3. Choose 10-15 varied documents.
4. Assign each a local `file_label`, such as `01_clean_simple`.
5. Manually review the required fields.
6. Mark missing fields and needs-check fields.
7. Add confidence notes for ambiguous fields.
8. Add parser difficulty notes.
9. Convert only structural lessons into synthetic/anonymized fixtures later.

## Local Inventory Command

Use the local-only inventory command to count private files and assign anonymized labels:

```powershell
py scripts/private_ratecon_inventory.py
```

The command scans:

```text
data/private_ratecons/originals/
```

It prints:

- total file count;
- extension counts;
- anonymized labels such as `RATECON_001`;
- privacy warning.

It does not read document contents, extract text, write files, create fixtures, create DispatchCases, or print private filenames by default.

## How To Use Inventory Results Later

The inventory can inform future work:

- pasted-text dry-run checks;
- parser confidence rules;
- missing/needs-check field expectations;
- synthetic fixture expansion;
- future PDF extraction strategy audit;
- future IntakeCaseLinkCandidate scenario refinement.

It must not directly create DispatchCases, write events, send Telegram, write Google Sheets, contact brokers, or trigger accounting/factoring flows.

## Stop Conditions

Stop before parser work if:

- private files appear in `git status`;
- local notes contain private text in a tracked file;
- extracted private text would need to be committed;
- fields are too ambiguous to map safely;
- the workflow would require PDF/OCR, email, Telegram upload, Google Sheets, DAT/API, Google Maps, or DispatchCase writes.
