# RateCon Core Field Policy

This policy defines how RateCon fields participate in review readiness,
intake-core readiness, and dispatch-decision readiness. It is local extraction
and review policy only. It does not create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, run Google sync, add OCR/Vision, or
make production automation claims.

## Readiness Levels

### Extraction Review Ready

Purpose: enough extraction, candidate, or status data exists for a human to
review. Values may still be wrong, incomplete, conflicting, or missing.

This level is not dispatch-ready and is not enough to create final intake data.

### Intake Core Ready

Purpose: enough core information exists to create a reviewed
`RateConfirmationIntake` draft after human review. It is not necessarily ready
for dispatch decisions or driver matching.

For normal load movement documents, intake-core readiness requires resolved or
reviewable evidence for:

- broker/customer identity candidate;
- load/order/pro/tender identifier or equivalent recognized load ID;
- rate/payment candidate;
- pickup location;
- pickup date;
- delivery location;
- delivery date.

### Dispatch Decision Ready

Purpose: enough reliable operational information exists for DecisionEngine,
driver matching, or dispatch review after explicit review/approval.

This level is stricter than intake-core readiness and includes equipment,
weight, commodity, special requirements, appointment windows, broker
identity/risk, and driver compatibility inputs.

## Field Matrix

### Broker / Customer Identity

`broker_name` or an equivalent broker/customer candidate:

- extraction review: useful;
- intake core: required as resolved or reviewable evidence;
- dispatch decision: high confidence or broker-memory/risk-resolvable.

`broker_mc`:

- extraction review: useful;
- intake core: not a hard blocker by itself;
- dispatch decision: review/risk blocker when broker identity is uncertain.

### Load Identity

`load_number`, `order_number`, `pro_number`, `tender_id`, or an equivalent typed
load identifier:

- extraction review: useful;
- intake core: required as resolved or reviewable evidence;
- dispatch decision: required or manually confirmed.

Generic `reference` values are useful review fields, but they are not enough by
themselves unless typed or recognized as the load identifier.

### Rate / Payment

`rate`, total carrier pay, agreed amount, or equivalent payment candidate:

- extraction review: useful;
- intake core: required as resolved or reviewable evidence;
- dispatch decision: required at high confidence or manually confirmed.

Accessorials, quickpay discounts, deductions, penalties, and line items are
review fields. They must not become the main rate unless the document labels
them as total/main agreed pay.

### Stops For Normal Load Movement

For normal load movement documents:

- `pickup_location`: intake-core required as resolved or reviewable evidence;
- `pickup_date`: intake-core required as resolved or reviewable evidence;
- `delivery_location`: intake-core required as resolved or reviewable evidence;
- `delivery_date`: intake-core required as resolved or reviewable evidence.

`pickup_time` and `delivery_time` are review/dispatch fields. They are not hard
intake-core blockers by themselves, but missing or conflicting appointment
windows should block dispatch-decision readiness or route to review.

### Operational Details

`equipment`:

- extraction review: useful;
- intake core: review field, not a hard blocker by itself;
- dispatch decision: blocker for driver matching if missing or unresolved.

`weight`:

- extraction review: useful;
- intake core: review field, not a hard blocker by itself;
- dispatch decision: blocker for driver/load compatibility if missing.

`commodity`:

- extraction review: useful;
- intake core: review field, not a hard blocker by itself;
- dispatch decision: blocker when safety, compatibility, or special handling
  could be impacted.

`special_requirements`:

- extraction review: useful;
- intake core: review field;
- dispatch decision: blocker if critical and unresolved.

### Non-Normal Documents

TONU/payment confirmations:

- normal pickup/delivery movement fields may be non-applicable;
- broker/load/rate/payment evidence can still be reviewable;
- missing normal stop fields should not be counted as normal-load extraction
  failures.

OCR-needed documents:

- do not count missing RateCon core fields as digital extraction failures;
- route to OCR queue / not-ready status until local OCR design exists.

Supplemental or non-RateCon documents:

- RateCon core fields are non-applicable;
- do not count missing RateCon fields as extraction blockers.

## Blocker Taxonomy

The same field can have different meaning at different levels:

- extraction review blocker: there is not enough structure to review;
- intake-core blocker: a required core intake group is not resolved or
  reviewable;
- dispatch-decision blocker: an operational or risk field is missing,
  conflicting, or low confidence;
- review-only field: useful for review but not hard intake-core gating;
- non-applicable field: not expected for the document context.

`optional_field_misclassified_as_core` should be near-zero after policy cleanup.
If it appears frequently, that is a policy/reporting bug, not an extraction
target.

## Measurement Rule

Readiness policy must be measured separately from extraction accuracy.

A document can be extraction-review-ready while still wrong or incomplete. A
document can be intake-core-ready while still missing dispatch-critical
operational details. A document should not become dispatch-decision-ready until
critical operational and risk fields are high-confidence or manually confirmed.

## Privacy Boundary

Tracked tests and docs must use fake values only. Do not commit private PDFs,
extracted text, real customer/broker/contact names, MCs, addresses, rates,
phone numbers, emails, reference numbers, appointment details, screenshots, or
document snippets.
