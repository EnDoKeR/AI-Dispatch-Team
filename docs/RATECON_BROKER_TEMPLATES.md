# RateCon Broker Templates

Broker templates describe document layout and extraction vocabulary for Rate
Confirmations. They are not broker memory, broker risk, payment history, or
dispatch policy.

This layer is fake/anonymized only today. It does not process private RateCons,
run OCR, call Vision AI, call cloud APIs, create DispatchCases, write events, or
make accept/reject/review recommendations.

## Why Broker Templates Exist

Generic candidate extraction can find obvious labels and values, but real RateCon
layouts often use broker-specific vocabulary. Broker templates let the extractor
understand layout vocabulary without turning regex matches into final field truth.

Current flow:

```text
fake/anonymized text artifact
-> generic candidates
-> broker template match
-> template candidate scoring
-> conservative resolver
-> RateConfirmationIntake draft
-> validation / review gating
```

## BrokerTemplate vs BrokerProfile

BrokerTemplate:

- document layout vocabulary;
- label aliases;
- stop section labels;
- typed reference labels;
- confidence boosts/penalties for extraction candidates;
- explicit versioning.

BrokerProfile / broker memory:

- broker history;
- dispatcher experience;
- payment/factoring context;
- trust/risk context;
- negotiation behavior.

These concepts must stay separate. Broker templates must not contain credit
score, days-to-pay, factoring status, payment history, or business-risk fields.

## Template Matching

Template matching uses:

- fake/anonymized keyword hits;
- aliases;
- fake MC matches;
- broker name candidate matches;
- exclude keywords;
- field-label overlap.

Match statuses:

- `matched`: one template has enough evidence and wins clearly;
- `unknown`: no template has enough broker/layout identity evidence;
- `conflict`: two or more templates are too close;
- `low_confidence`: some evidence exists, but not enough to trust.

Unknown, conflict, and low-confidence matches must fall back to generic extraction
or review. They must not overboost candidates.

Template-aware scoring is now guarded by a trusted-match threshold. A template
can match for identification purposes while still being too weak to apply strong
candidate boosts. In that case the resolver records a template-match review
signal and uses generic candidates.

## Field Label Rules

Field label rules define labels for one candidate field.

Examples:

- `Carrier Pay` boosts `rate`;
- `Agreed Amount` boosts `rate`;
- `Docket MC` boosts `broker_mc`;
- `Gross Weight` boosts `weight`;
- `Trailer Type` boosts `equipment`.

Negative labels reduce confidence. For example, `Detention`, `Lumper`, `Quick
Pay`, and `Fee` must not become the main carrier-pay rate.

## Typed Reference Rules

Templates can map labels to reference types:

- broker load number;
- PO number;
- BOL number;
- pickup number;
- delivery number;
- customer reference;
- appointment number.

Typed references are evidence. They are not automatic case-link approval.

## Stop Section Rules

Stop rules describe pickup/delivery sections and appointment labels.

Examples:

- `Pickup`, `Shipper`, `Origin`;
- `Delivery`, `Consignee`, `Receiver`;
- `Stop 1`, `Stop 2`;
- `PU Appt`, `DEL Appt`.

Templates can boost stop candidates, but they do not build routing, calculate
miles, or call Google Maps.

## Confidence Boosts And Penalties

Template scoring adjusts candidate confidence; it does not resolve fields by
itself.

Rules:

- strong matching labels may increase candidate confidence;
- negative labels may decrease confidence;
- accessorial labels must not become main rate;
- low-confidence template matches do not get trusted boosts;
- conflicting templates do not get trusted boosts;
- matched-but-untrusted templates do not get trusted boosts;
- final resolution still goes through the conservative resolver.

## Validation Gate

Templates do not bypass RateConfirmationIntake validation.

Review is required when:

- critical fields are missing;
- critical fields are low confidence;
- critical fields conflict;
- template match is low confidence;
- template match conflicts;
- extraction route is uncertain.

## Fake Template Fixtures

Fake JSON templates live in:

```text
tests/fixtures/document_ai/broker_templates/
```

Fake text fixtures live in:

```text
tests/fixtures/document_ai/ratecon_text/
```

Run:

```powershell
py scripts/run_fake_ratecon_candidate_extraction.py
py scripts/run_fake_ratecon_candidate_extraction.py --include-hard-layouts
```

This prints safe summary fields only.

Hard-layout resolver behavior is documented in
`docs/RATECON_TEMPLATE_RESOLVER_HARDENING.md`.

## Rules For Adding New Fake Templates

1. Use fake broker names only.
2. Use fake MC numbers only.
3. Do not include private RateCon text.
4. Do not include real customer, carrier, driver, phone, email, address, or reference data.
5. Add a template JSON fixture.
6. Add at least one fake text fixture.
7. Add a matched-template test.
8. Add unknown/conflict fallback tests when labels overlap another template.
9. Add accessorial/rate safety tests if the template includes money labels.
10. Keep template version explicit.

## Rules For Adding Real Broker Templates Later

1. Never commit private RateCon text.
2. Use redacted/anonymized fixtures.
3. Every template must have tests.
4. Every template must have unknown and conflict fallback coverage.
5. Template must not encode business-risk status.
6. Template must not create DispatchCases.
7. Template must not decide accept/reject/review.
8. Template version must be explicit.
9. Real MC numbers should be handled carefully and not exposed in public fixtures.
10. Low-confidence template match must route to review/generic fallback.

Real broker templates require a separate privacy-reviewed implementation block.

## Private Local Overlay Workflow

Private broker template overlays are supported only for local measurement. They
must live in ignored paths such as:

```text
.local_private/broker_templates/
```

Collect redacted private template patterns first:

```powershell
py scripts/run_private_ratecon_template_pattern_collection.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-pattern-json --write-family-md --write-template-drafts
```

Then run safe measurement with the private overlay explicitly enabled:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --private-template-dir ".local_private\broker_templates" --allow-private-template-overlay --write-json --write-csv --write-md
```

Safe overlay summaries may show `PRIVATE_TEMPLATE_001`, template source,
confidence bucket, field names, statuses, blockers, and aliases. They must not
show private template display names, real broker names, MC numbers, rates,
addresses, references, raw text, filenames, or local paths.

Private templates cannot bypass validation, create DispatchCases, call
DecisionEngine, call Telegram, write events, or decide accept/reject.
