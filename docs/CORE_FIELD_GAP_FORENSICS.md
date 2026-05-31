# Core Field Gap Forensics

This workflow breaks broad RateCon review blockers into concrete fields and
safe root-cause buckets before changing extraction logic.

## Why This Exists

The previous stop datetime hardening expanded deterministic format coverage for
synthetic fixtures, but the private aggregate did not improve:

- span date resolved / missing stayed at 8 / 21;
- span time resolved / missing stayed at 10 / 19;
- readiness stayed at `extraction_review_ready=14`, `not_ready=4`.

That means the next useful work is not more generic datetime heuristics. The
current top blockers, `missing_core_field` and `conflict_core_field`, are too
broad to fix directly. They must be broken down by exact field and safe
root-cause category.

## Gap Reasons

Core fields can fail for different reasons:

- `no_candidate`: the pipeline did not produce a candidate for the field.
- `candidate_exists_but_unresolved`: candidates exist, but the resolver cannot
  select one safely.
- `conflict`: multiple candidates or resolver paths disagree.
- `low_confidence`: a candidate exists but confidence is too weak.
- `scope_filtered`: the document or page was outside the extraction scope.
- `optional_field_misclassified_as_core`: a useful field is being treated as an
  intake blocker when it should only route to review or dispatch readiness.
- `non_applicable`: the field is not expected for this document type or status.
- `ocr_needed`: the document lacks usable digital text.
- `review_required`: the field needs human review even if it has evidence.

The analysis output must remain safe: aliases, field names, statuses, counts,
and warning buckets only. It must not include private values, filenames, paths,
raw text, rates, addresses, references, or broker identifiers.

## Readiness Policy

Readiness is not a single yes/no flag.

`not_ready` means there is not enough usable extraction or review structure.

`extraction_review_ready` means enough candidate/status data exists for human
review. Values may still be missing, conflicting, or wrong.

`intake_core_ready` should focus on load-identifying and operationally essential
fields:

- broker/customer candidate;
- load/order/pro/tender number or equivalent identifier;
- rate/payment candidate;
- pickup location candidate;
- delivery location candidate;
- pickup date candidate;
- delivery date candidate.

Unresolved fields may be allowed only when they are clearly reviewable. Missing
or unresolved core fields should keep the document out of intake-core-ready.

`dispatch_decision_ready` is stricter. It requires the intake core plus
dispatch-critical fields such as equipment, weight, commodity, special
requirements, appointment windows, broker identity/risk, and driver
compatibility inputs.

`broker_mc`, equipment, and loaded miles should not automatically block
`intake_core_ready` when absent. They should remain visible for review and
should block `dispatch_decision_ready` where relevant. Commodity and weight may
be `needs_review` for intake, but they must not be silently ignored.

## Local Loop

```text
local review CSVs
-> core field gap analysis
-> readiness policy check
-> one measured target
-> synthetic fixtures
-> focused deterministic hardening
-> local private rerun
-> regenerated workbook / CSVs
-> before/after delta
```

Only one major extraction target should be changed in a block. This keeps the
measurement interpretable.

## Current Forensics Result

The policy cleanup reconciled optional/review-only fields with readiness
blocking:

- `optional_field_misclassified_as_core` is now 0;
- optional missing fields remain visible as review/dispatch gaps but do not
  drive intake-core readiness;
- readiness remains `extraction_review_ready=14`, `not_ready=4`;
- supplemental, non-RateCon, unknown-review, OCR-needed, and TONU/payment-only
  rows do not become dispatch-decision-ready just because normal-load fields are
  non-applicable.

The cleaned analysis now reports true intake blockers separately from all review
gaps. Current safe counts:

- true intake blockers: 56;
- dispatch-decision blockers: 128;
- optional missing fields: 56;
- true intake blocker reasons: `no_candidate=39`, `conflict=17`.

Top true intake fields are delivery date, broker name, pickup date, load number,
rate, delivery location, and pickup location. Stop-related fields remain the
largest group, but the dominant reason is `no_candidate`, not a
candidate-mapping failure. That means the next stop-focused block should inspect
stop-span evidence/candidate generation and coverage rather than adding another
date/time regex or span-to-core mapping tweak.

The clean target-selection report is written locally as
`clean_target_selection.md`. It is ignored and contains counts/statuses only.

## Candidate Coverage Follow-Up

The follow-up coverage block added `app/document_ai/candidate_coverage_analysis.py`
and `scripts/analyze_candidate_coverage.py`. This separates true `no_candidate`
gaps by pipeline stage:

- line feature;
- stop anchor;
- stop span;
- span field candidate;
- normalized stop field;
- core field mapping;
- review row.

The first selected candidate-generation target was broker identity. It added
review-gated broker candidates from explicit broker/tender labels and
broker-context header/contact blocks while preserving carrier-name separation.
Safe local delta:

- broker-name candidate-not-generated: 10 -> 7;
- total candidate-not-generated: 27 -> 22;
- true intake blockers: 56 -> 53;
- dispatch-decision blockers: 128 -> 123;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`.

Remaining blockers should be chosen from the updated coverage reports, not from
the broad all-gap list.

The next coverage pass selected stop-span date candidate generation only after
stage evidence showed the date loss at `span_field_candidate`. The table-row
date fix reduced selected date `candidate_not_generated` from 8 to 0 and true
intake blockers from 53 to 49. Remaining no-candidate work is now led by
`load_number`, so the next selected target is
`load_identifier_candidate_generation`.

The load identifier pass added typed primary identifiers, typed reference
separation, load-number resolver mapping, load identifier coverage counters,
and review workbook columns. Safe local result: primary identifier candidates
3, typed references 11, rejected non-primary references 11, load-number
candidate gap 7 -> 8 under the more specific taxonomy, and load-number intake
blockers 7 -> 9. This is cleaner diagnostics rather than private-corpus
improvement. The next forensics step is missing identifier label and
load-identity section coverage.

The load identifier coverage audit then selected
`generic_header_reference_review_candidate` as one constrained root cause.
After implementing review-gated generic header reference candidates, the private
rerun remained unchanged: primary identifier candidates 3, typed references 11,
rejected non-primary references 11, and core load-number mappings 1. Core gap
analysis still shows `load_number` among true intake blockers. This keeps the
next useful step at label/section coverage inspection rather than resolver
mapping or relaxed PO/BOL promotion.

The label/section source-line forensics pass then confirmed there is no shared
code-fixable load identifier root cause in the current private corpus. It
counted 96 identifier-like source lines, 11 header/load-identity source lines,
73 stop/billing/terms source lines, 96 detected labels, 24 classified labels,
3 primary candidates, and 11 rejected non-primary references. The root causes
were split, with no code-fixable bucket reaching the required three-alias
threshold. The next load identifier action is local human review, while other
core blockers should continue to be selected from policy-cleaned coverage data.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or make production automation
claims.
