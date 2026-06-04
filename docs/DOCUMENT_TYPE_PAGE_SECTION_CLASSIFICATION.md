# Document Type, Page Role, and Section Classification

## Why This Layer Exists

The RateCon extraction pipeline now has deterministic candidate generation, broker template matching, template-aware scoring, conservative resolution, safe private measurement, and private template overlay support. The next measured issue is not OCR or Vision. The safer next step is to decide which parts of a document are actually eligible for Rate Confirmation extraction before candidates are generated.

A single PDF packet may contain a primary Rate Confirmation page, supplemental terms, billing instructions, signature pages, carrier information sheets, certificate pages, or Bill of Lading-like pages. Treating every page as a primary RateCon source pollutes rate, stop, broker identity, and reference candidates. Terms pages can contain money values that are not carrier pay. Signature pages can contain driver and carrier information that is not broker identity. BOL pages can contain shipper and consignee labels that should not become missing RateCon fields when the document is not a RateCon.

The classification layer creates an explicit gate:

```text
DocumentType
-> PageRole
-> SectionRole
-> ExtractionScope
-> RateCon eligibility decision
-> candidate extraction from allowed scopes only
-> resolver
-> validation / REVIEW_REQUIRED
```

Unknown or ambiguous classification routes to review. It does not create extraction confidence.

## Measurement Context

The safe private measurement run found that most measured documents had extractable digital text, but every document had unknown template status:

- 14 of 18 documents had digital text.
- 4 of 18 documents were OCR-needed or empty-text.
- 18 of 18 documents had unknown template status.
- 14 of 14 text documents had a template gap.
- 13 of 14 text documents had a resolver gap.

The private redacted pattern collection then found mostly single-alias, low-confidence template families. That suggests mixed page and section types, not one stable broker template family. Before adding OCR, Vision, or more private overlay logic, the pipeline needs to stop treating every page as a primary RateCon page.

## Generic Layout Families Observed

The classifier should support fake/anonymized equivalents of these structure types. These names describe layout and document behavior only, not real brokers.

1. Rate/load confirmation with shipper and consignee blocks.
2. Carrier tender or route details confirmation.
3. Table-heavy broker confirmation.
4. Load/order confirmation layout with pickup and stop-off sections.
5. Blue-table broker confirmation.
6. Multi-page confirmation with terms and signature pages.
7. Carrier/driver information sheet.
8. Billing, remittance, or quick-pay page.
9. Carrier rate agreement or legal terms page.
10. Scanned BOL or BOL-like document.
11. Certificate of signature page.
12. Truck order not used or TONU confirmation.
13. Supplemental instructions page.

Committed fixtures must mimic structure only. They must not use private screenshots, private PDF text, real broker names, real MC numbers, real customer data, real carrier data, or real driver data.

## Core Concepts

### DocumentType

`DocumentType` describes the overall document packet after reviewing page roles. Examples include `RATE_CONFIRMATION`, `CARRIER_LOAD_TENDER`, `BILL_OF_LADING`, `CARRIER_RATE_AGREEMENT`, `CERTIFICATE_OF_SIGNATURE`, and `UNKNOWN`.

This is not broker memory. It does not describe broker risk, payment history, or dispatcher experience.

### PageRole

`PageRole` describes what a page is doing. A document can have multiple pages with different roles:

- Main RateCon or load confirmation pages can feed core load extraction.
- Terms pages should not feed main rate or stop extraction by default.
- Billing and quick-pay pages can feed payment terms, but not pickup/delivery fields.
- Signature and certificate pages should not feed core RateCon fields.
- BOL pages should not create missing RateCon fields.

### SectionRole

`SectionRole` describes what a page region or line group is doing. A single page can contain a header, rate summary, stop table, pickup section, delivery section, special instructions, billing instructions, and signature block.

The first implementation is deterministic text-based classification. It does not require coordinates or layout dependencies. Later layout-aware extraction can add word/block/table evidence.

### ExtractionScope

`ExtractionScope` tells downstream extraction which fields may be generated from a page or section:

- `RATECON_CORE_ALLOWED` for primary RateCon/load/tender content.
- `RATE_ONLY_ALLOWED` for rate summaries or approved payment sections.
- `STOP_EXTRACTION_ALLOWED` for pickup/delivery/stop sections.
- `REQUIREMENTS_ONLY_ALLOWED` for notes and special instructions.
- `PAYMENT_TERMS_ONLY_ALLOWED` for terms, deductions, detention, quick pay, or billing terms.
- `BILLING_ONLY`, `SIGNATURE_ONLY`, and `SUPPLEMENTAL_ONLY` for non-core content.
- `NON_RATECON_SKIP`, `OCR_REQUIRED`, and `REVIEW_REQUIRED` for content that should not feed normal RateCon extraction.

## Why Terms Pages Need Care

Terms pages often include money values for detention, layover, quick pay, deductions, penalties, accessorials, TONU, late fees, or other policies. Those values must not become the main carrier rate.

Terms pages can still be useful for:

- payment terms
- deductions and penalties
- detention or layover policy
- TONU policy
- accessorial terms
- special requirements

That content should be scoped as payment or requirements evidence, not as primary RateCon core evidence.

## Why BOL-Like Pages Are Supplemental

A Bill of Lading can include shipper, consignee, carrier, commodity, quantity, weight, signatures, and reference numbers. Those labels overlap with RateCons but have a different purpose. A BOL should not produce missing RateCon fields just because it lacks broker MC, carrier pay, or load confirmation terms.

BOL-like pages should be classified as supplemental or non-RateCon for this pipeline. They may become useful in a future document packet workflow, but they do not currently create a DispatchCase or a RateConfirmationIntake.

## Why Carrier/Driver Info Sheets Are Supplemental

Carrier and driver information sheets can contain carrier names, driver names, truck numbers, trailer numbers, phone numbers, and signatures. Those values are not broker identity and should not contaminate broker-name extraction.

These pages are supplemental only. They should not count as failed RateCon extraction.

## Why Signature and Certificate Pages Are Supplemental

Signature pages, accepted-by pages, and certificate-of-signature pages may contain names, timestamps, emails, driver/truck/trailer lines, or legal completion text. They should not feed rate, stops, broker identity, or references. Their role is evidence or packet status, not RateCon extraction.

## TONU / Truck Order Not Used

Truck order not used documents can be rate or payment relevant, but they are not normal load movement documents. They may have TONU payment status without normal pickup/delivery fields. The classifier should identify them separately so missing stops do not look like failed normal RateCon extraction.

## Calibrated Eligibility Rules

The first private classification rerun found only 2 of 18 documents as
RateCon-eligible, which was too strict for a corpus containing carrier load
tenders, load tenders, order confirmations, and TONU payment confirmations.

Eligibility is now based on extraction relevance, not completeness. A document
can be eligible when it has a strong combination of load/order/tender identity,
route or stop details, and rate/payment/equipment context, even if the broker
template is unknown or the title is not exactly `Rate Confirmation`.

Extraction-relevant types are:

- `RATE_CONFIRMATION`
- `RATE_LOAD_CONFIRMATION`
- `LOAD_CONFIRMATION`
- `ORDER_CONFIRMATION`
- `CARRIER_LOAD_TENDER`
- `LOAD_TENDER`
- `TRUCK_ORDER_NOT_USED`

The calibrated safe rerun showed, without printing private values:

- total documents: 18
- extraction-relevant documents: 10
- normal load movement documents: 6
- TONU/payment confirmations: 4
- supplemental-only documents: 2
- non-RateCon or unknown-review documents: 6
- OCR-needed / empty-text documents: 4

Critical pickup/delivery/equipment/weight denominator reporting should use
normal load movement documents only. TONU documents remain extraction-relevant
for payment/status, but normal movement fields are non-applicable when absent.

## Relationship to Broker Templates

Broker templates describe document layout, labels, and extraction vocabulary. Classification decides whether a page or section is allowed to feed RateCon extraction at all.

Templates may improve candidate scoring inside allowed scopes. They must not override classification, validation, or review rules. Private local template overlays remain ignored and redacted in safe summaries.

## Relationship to Layout-Aware Extraction

Classification remains the gate before layout-aware extraction. Layout evidence
must not replace page and section eligibility.

The current layout-aware scaffold is dependency-free and synthetic. It adds
contracts and fake fixtures for:

- word, line, block, table, and cell artifacts;
- bounding boxes and reading-order variants;
- label-value proximity;
- table/section evidence;
- rate/payment, stop, and operational-detail candidates.

The intended sequence is:

```text
classification
-> extraction scopes
-> layout artifact
-> layout-aware candidates
-> conservative resolver
```

The scaffold proves candidate behavior with synthetic JSON fixtures only. A real
PDF layout provider remains a future block after dependency and licensing
review.

## Relationship to OCR and Vision

OCR may still be needed for empty-text or image-like documents, but production
OCR is not the first major block because most measured documents already had
digital text. Optional local/shadow OCR diagnostics are tracked separately in
`docs/ratecon_ocr_ownership_status_v1.md`.

Vision is not next by default. It should remain a gated fallback only after deterministic text, classification, templates, and layout-aware extraction are measured and found insufficient.

## Safety Rules

- Do not commit private PDFs, screenshots, raw text, or private measurement outputs.
- Do not use real broker names, MC numbers, customer data, carrier data, driver data, addresses, rates, or references in committed fixtures.
- Do not print raw private text or private values.
- Do not create `DispatchCase` from classification.
- Do not call `DecisionEngine`, Telegram, or Event Timeline code.
- Do not add OCR, Vision, cloud APIs, or heavy PDF/layout dependencies in this block.
- Unknown or ambiguous classification must route to review.

## Non-Goals

- No production OCR implementation in this block.
- No Vision AI implementation.
- No cloud APIs.
- No real broker templates.
- No private fixture commits.
- No production automation claim.
- No dispatch recommendation.
- No autonomous booking or DispatchCase creation.
