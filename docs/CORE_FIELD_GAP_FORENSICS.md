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

The first core-field gap pass found that the broad blocker names were hiding
several different causes:

- optional/review-only fields were still visible as gaps, but should not drive
  intake-core readiness by themselves;
- stop-span fields had structured date/time/location evidence that was not
  always surfaced in top-level field review statuses;
- existing conflicts in pickup/delivery locations, dates, and rates remain the
  dominant blockers for readiness;
- broker identity and load identifiers remain separate measured targets.

The selected target for this pass was `stop_span_field_mapping`, not another
date/time regex expansion. The implemented hardening maps resolved provider-line
span stop fields into top-level pickup/delivery review statuses when the
top-level status is missing or not applicable. It also treats resolved
appointment windows as pickup/delivery time review evidence. Existing conflicts
are preserved and not overwritten.

Missing appointment-window stop rows are not double-counted as core time gaps in
the core-field gap analysis. Conflicting appointment-window rows remain mapped
to pickup/delivery time because they are actionable review issues.

Private rerun result: readiness and span counts did not materially improve.
The mapped statuses make the local workbook more reviewable, but corpus-level
blockers still come from unresolved stop-level gaps, broker identity gaps, load
identifier gaps, and rate conflicts.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or make production automation
claims.
