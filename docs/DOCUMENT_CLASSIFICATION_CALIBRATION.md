# Document Classification Calibration

## Why Calibration Is Needed

The first classification-first private measurement run found only 2 of 18
documents as RateCon eligible. That is suspicious for this corpus because the
safe page-role counts still showed many `MAIN_RATECONF`, `MAIN_LOAD_CONFIRMATION`,
`MAIN_TENDER`, `STOP_DETAILS`, and `PAYMENT_SUMMARY` signals.

The likely issue is not that most private documents are irrelevant. The likely
issue is that legitimate transportation confirmation documents use varied names
and mixed page sections:

- Rate Confirmation
- Rate & Load Confirmation
- Carrier Load Tender / Rate Confirmation
- Load Tender
- Load Confirmation
- Order Confirmation
- Dispatch Confirmation
- Truck Order Not Used / TONU payment confirmation
- route-details tender pages with agreed-rate sections
- system-style load/order confirmation pages
- table-heavy confirmations with payment summaries

Classification must remain conservative, but it should not require the exact
phrase `Rate Confirmation` or a known broker template before attempting
extraction.

## Extraction-Relevant Document Types

These document types should be considered extraction-relevant:

- `RATE_CONFIRMATION`
- `RATE_LOAD_CONFIRMATION`
- `LOAD_CONFIRMATION`
- `ORDER_CONFIRMATION`
- `CARRIER_LOAD_TENDER`
- `LOAD_TENDER`
- `TRUCK_ORDER_NOT_USED`

Extraction-relevant means the candidate/template/resolver pipeline may run on
allowed pages and sections. It does not mean the document is complete, accepted,
or dispatch-ready.

## Supplemental Or Non-RateCon Document Types

These document types should not be treated as normal RateCon extraction sources:

- `BILL_OF_LADING`
- `PROOF_OF_DELIVERY`
- `CERTIFICATE_OF_INSURANCE`
- `CERTIFICATE_OF_SIGNATURE`
- `DRIVER_CARRIER_INFO_SHEET`
- `TERMS_AND_CONDITIONS` only
- `CARRIER_RATE_AGREEMENT` only
- `BILLING_INSTRUCTIONS` only
- signature-only pages
- `UNKNOWN` unless a future review flag explicitly marks it as maybe eligible

Supplemental documents can still be useful in a broader packet workflow, but
they should not inflate missing RateCon field counts.

## Primary Confirmation Vs Related Documents

### Primary Rate Confirmation

A primary Rate Confirmation usually contains a load identity, broker or dispatch
header, carrier pay/rate, stop details, equipment, commodity, or weight. It
should be eligible even if the broker template is unknown.

### Carrier Load Tender / Load Tender

Tender documents can have route details, stop numbers, pickup/drop blocks,
freight bill or tender IDs, carrier blocks, and agreed rate sections. They are
extraction-relevant even when they do not use the exact title `Rate Confirmation`.

### Load Confirmation / Order Confirmation / Dispatch Confirmation

System-style confirmations may use `PU`, `SO`, `stop off`, `order number`,
`load number`, `pro number`, `total charge`, `freight pay`, or `carrier amount`.
They should be eligible when load identity, route/stops, and payment or equipment
signals are present.

### Truck Order Not Used / TONU

TONU documents are special. They are payment/status extraction relevant but not
normal load movement documents.

Rules:

- classify as `TRUCK_ORDER_NOT_USED`;
- allow payment/status extraction;
- do not require pickup/delivery/equipment/weight if absent;
- report normal movement fields as non-applicable where appropriate;
- never treat TONU as an automatic dispatch decision.

## Eligibility Must Not Require Completeness

Eligibility answers: should RateCon-style extraction be attempted?

It does not answer:

- are all critical fields present?
- is the rate correct?
- is the template known?
- is the load ready?
- should a DispatchCase be created?

Missing fields, low confidence, conflicts, unknown templates, and incomplete
candidate coverage remain resolver/validation concerns. They should route to
review, not suppress document eligibility.

## Strong Eligibility Signal Combinations

A document should become eligible when it has a strong combination of:

- load/order/pro/freight bill/tender identifier;
- carrier block;
- pickup/drop/PU/SO/stop details;
- rate/pay/freight pay/total charge/agreed amount;
- equipment/weight/commodity;
- route details;
- dispatch/load/tender/order confirmation title.

Terms, billing, and signature signals should not overpower these main
confirmation signals when both are present on the same page or packet.

## Safe Denominator Rules

Measurement reports should separate:

- total documents;
- extraction-relevant documents;
- normal load movement documents;
- TONU documents;
- supplemental-only documents;
- non-RateCon or unknown-review documents;
- OCR-needed documents.

Critical field denominators must be honest:

- pickup/delivery/equipment/weight denominators use normal load movement
  documents only;
- TONU documents are counted separately;
- supplemental, non-RateCon, and OCR-needed documents are excluded from missing
  RateCon critical-field failure rates;
- unknown documents remain visible as review-required classification gaps.

## Calibrated Safe Rerun Result

After calibration, the safe local private measurement rerun reported status-only
counts:

- total documents: 18
- digital-text documents: 14
- OCR-needed / empty-text documents: 4
- extraction-relevant documents: 10
- normal load movement documents: 6
- TONU/payment confirmations: 4
- supplemental-only documents: 2
- non-RateCon or unknown-review documents: 6

Document type counts were:

- `BILL_OF_LADING`: 1
- `CARRIER_LOAD_TENDER`: 2
- `DRIVER_CARRIER_INFO_SHEET`: 1
- `LOAD_CONFIRMATION`: 1
- `LOAD_TENDER`: 1
- `ORDER_CONFIRMATION`: 1
- `RATE_CONFIRMATION`: 1
- `TRUCK_ORDER_NOT_USED`: 4
- `UNKNOWN`: 6

The result confirms the original 2 of 18 eligible count was too strict. It also
shows that 6 normal movement digital-text documents still have missing,
low-confidence, or conflicting fields, so the likely next engineering checkpoint
is layout-aware digital extraction and field association after this calibrated
measurement baseline.

## Non-Goals

This calibration does not add OCR, Vision AI, cloud APIs, layout dependencies,
real broker templates, private fixtures, DispatchCase creation, DecisionEngine
calls, Telegram calls, Event Timeline writes, or production automation claims.
