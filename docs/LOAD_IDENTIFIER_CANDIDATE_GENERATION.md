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
- `Confirmation #`;
- `Booking #`.

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

The console and committed docs must never include private identifier values,
raw text, private filenames, local paths, screenshots, service account keys, or
generated private outputs.

## Non-Goals

This workflow does not add OCR, Vision, cloud document AI, Google sync, broker
template implementation, DispatchCase creation, DecisionEngine calls, Telegram
calls, Event Timeline writes, or production automation claims.
