# Load Identifier Candidate Generation

This workflow improves deterministic candidate generation for RateCon load
identifiers. It is local-first and does not run Google sync or require Google
credentials.

## Why This Is The Next Target

Candidate coverage analysis selected `load_identifier_candidate_generation`
after the date target was fixed. The latest safe coverage output still shows
load-number records where no candidate is generated, and `load_number` remains
one of the true intake-core blockers.

Load identity is core for review and intake readiness because a reviewer needs
a reliable way to connect the RateCon to the broker load, order, tender, or
shipment being worked. A generic reference is useful, but it is not enough when
the document also contains PO, BOL, pickup, delivery, appointment, customer, or
carrier references that should not silently become the primary load ID.

## Identifier Types

Primary load identifier candidates are labels that can reasonably identify the
load, order, tender, shipment, or broker confirmation:

- load number;
- order number;
- tender ID;
- PRO number;
- freight bill number;
- shipment number;
- trip number;
- dispatch number;
- primary reference when it appears in a header or load identity context.

Typed references are preserved separately because they may matter for review but
should not automatically become `load_number`:

- PO number;
- BOL number;
- pickup number;
- delivery number;
- appointment number;
- customer reference;
- carrier reference;
- generic reference.

PO, BOL, customer, carrier, pickup, delivery, and appointment references are not
primary load identifiers by default. They may be review evidence, but promoting
them to `load_number` without stronger context would hide an honest missing
identifier behind a weaker reference.

## Supported Layout Families

The candidate generator should support generic RateCon layout families without
broker-specific templates:

- carrier tender or route details pages;
- load confirmation headers;
- order confirmation headers;
- blue-table rate confirmations;
- McLeod-style PU/SO confirmations;
- broker confirmations with header identifiers.

Template-specific broker rules are a separate future workflow. This block keeps
the implementation deterministic and generic.

## Data Flow

Typed identifier evidence should feed the existing pipeline without creating
dispatch automation:

1. A label/value pair becomes a typed field candidate.
2. Strong or context-supported primary identifiers are eligible for
   `load_number` or equivalent load identity mapping.
3. Non-primary references stay typed as review evidence.
4. The local review workbook shows identifier type, status, and review needs.
5. Core field gap analysis can distinguish missing primary load identity from
   preserved secondary references.
6. A later reviewed `RateConfirmationIntake` draft can use the resolved primary
   identifier and keep typed references available for manual review.

## Confidence And Evidence Rules

Strong primary labels:

- `Load #`, `Load Number`, `Load ID`;
- `Order #`, `Order Number`;
- `Tender #`, `Tender ID`;
- `Freight Bill #`, `Freight Bill Number`;
- `PRO #`, `PRO Number`;
- `Shipment #`, `Shipment Number`.

Medium labels are primary only when near a header, load identity section, route
details heading, tender heading, or confirmation title:

- `Trip #`;
- `Dispatch #`;
- `Ref #`;
- `Reference #`;
- `Reference No.`;
- `Confirmation #`;
- `Confirmation No.`;
- `Booking #`;
- `Tender Ref`.

Weak labels such as plain `Reference #` without load context should be
generated as review evidence, not silently resolved as `load_number`.

Negative labels for primary load identity:

- `PO #`;
- `BOL #`;
- `Pickup #`;
- `Delivery #`;
- `Appointment #`;
- `Customer Ref`;
- `Carrier Ref`.

The generator must not use broker names, carrier names, MC numbers, phone
numbers, email addresses, dates, times, rates, payment terms, billing addresses,
or stop-only references as primary load identifiers.

## Review And Coverage

Candidate coverage should report safe counts only:

- identifier label features;
- primary identifier candidates;
- typed reference candidates;
- rejected non-primary references;
- core load-number mappings;
- conflicts or weak generic references that require review.

The local review workbook and field review CSV include load-identifier-specific
columns:

- load identifier status;
- primary identifier candidate count;
- primary identifier candidate type counts;
- typed reference count;
- rejected non-primary reference count;
- load identifier gap reason;
- load identifier needs-review flag.

## Implemented Behavior

The generic identity/reference candidate generator now creates typed candidates
for strong primary load labels such as load, order, tender, freight bill, PRO,
and shipment labels. It preserves PO, BOL, pickup, delivery, appointment,
customer, carrier, and generic references as typed references instead of
silently promoting them to `load_number`.

It also recognizes inline generic header/load-context forms such as
`Reference No.`, `Confirmation #`, and `Tender Ref` as low-confidence,
review-required primary-reference candidates only when context supports that
interpretation and no stronger identifier is present. Stop, customer, PO, BOL,
pickup, delivery, and appointment references remain non-primary.

The resolver maps typed primary identifiers into the core load-number field,
routes multiple conflicting strong primary IDs to review, and keeps weak header
references review-required unless no stronger identifier exists.

Candidate coverage now tracks identifier label features, primary candidates,
typed references, rejected non-primary references, and core load-number mapping
counts.

## Latest Local Result

The private rerun regenerated local review workbook/CSV outputs and candidate
coverage artifacts. Safe measured result:

- documents measured: 18;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed unchanged: 4;
- primary identifier candidates observed: 3;
- typed references observed: 11;
- rejected non-primary references: 11;
- load-number candidate gap: 7 -> 8 under the more specific taxonomy;
- load-number intake blockers: 7 -> 9;
- total candidate gap count stayed 14;
- next selected target remains `load_identifier_candidate_generation`.

The implementation improved synthetic coverage and reporting, but it did not
improve the private corpus. The next useful step is to audit why the relevant
private documents lack identifier label features or load-identity section
coverage, not to add broader generic identifier regexes.

The follow-up load identifier audit selected the generic header reference
review-candidate root cause and implemented that constrained fix. The safe
private rerun did not move corpus counts: primary candidates stayed 3, typed
references stayed 11, rejected non-primary references stayed 11, and core
load-number mappings stayed 1. Candidate coverage still selects
`load_identifier_candidate_generation`, so the next target remains label and
section coverage rather than primary mapping or resolver changes.

The subsequent source-line forensics pass measured identifier visibility before
adding any more load-id rules. It found 96 identifier-like source lines, but
only 11 were in header/load-identity sections while 73 were in stop, billing,
or terms contexts. The reasons were split across unknown cases, OCR/weak text,
absent source lines, only non-primary references, and correctly non-primary
labels. No shared code-fixable root cause reached the three-alias threshold, so
no additional load identifier hardening was implemented.

The console and committed docs must never include private identifier values,
raw text, private filenames, local paths, screenshots, service account keys, or
generated private outputs.

## Non-Goals

This workflow does not add OCR, Vision, cloud document AI, Google sync, broker
template implementation, DispatchCase creation, DecisionEngine calls, Telegram
calls, Event Timeline writes, or production automation claims.
