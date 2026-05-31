# Local RateCon Review Analysis

Google Sheets review sync is paused until a full Google service account JSON is
available locally. The local review workbook and CSV outputs are enough to keep
improving deterministic RateCon extraction without waiting for credentials.

## Review Artifacts

The local review export is a review packet, not final truth. It is written under
`.local_outputs/private_ratecon_measurement/` and remains ignored.

The review files are:

- `ratecon_review_document_summary.csv`: document status, readiness, stop
  counts, and high-level blockers.
- `ratecon_review_stop_review.csv`: stop fields, statuses, confidence buckets,
  evidence type, and review columns.
- `ratecon_review_field_review.csv`: core field statuses and review columns.
- `ratecon_review_rate_review.csv`: rate/payment candidate review rows.

Private values may exist in local-only outputs when explicitly generated for
local review. They must not be printed, committed, copied into tests, or pasted
into chat.

## What Can Be Analyzed

Without human review, local analysis can safely measure:

- missing, unresolved, conflict, and low-confidence field counts;
- stop review-required counts;
- span stop count anomalies;
- missing stop date/time patterns;
- field confidence and status distributions;
- readiness level counts;
- OCR-needed counts;
- integrity issue counts.

The output is safe because it reports aliases, counts, statuses, field names,
and issue categories only.

## What Requires Human Review

The local analysis cannot prove:

- whether a predicted private value is truly correct;
- whether a stop address exactly matches the source PDF;
- whether a rate is legally or operationally correct when conflicting;
- whether a human should accept the extracted intake as final truth.

Those questions require reviewing the workbook rows against the private source
documents.

## Hardening Loop

Use this loop:

```text
local analysis
-> top blockers
-> fake fixtures for generic failure patterns
-> targeted deterministic/layout hardening
-> private measurement rerun
-> workbook/CSV regeneration
-> local analysis delta
```

Only one major blocker should be fixed per block. This keeps the before/after
measurement interpretable and prevents unrelated heuristics from masking the
real effect.

## Current Local Analysis Result

The current local review analysis uses regenerated ignored review outputs only.
It reports safe counts and aliases, not private values.

Latest safe counts:

- documents analyzed: 18;
- readiness counts: `extraction_review_ready=14`, `not_ready=4`;
- OCR-needed count: 4;
- span-normalized stops: 29;
- span date resolved / missing: 8 / 21;
- span time resolved / missing: 10 / 19.

The first local hardening pass selected stop span date/time extraction because
missing stop date/time was a top blocker. Synthetic fixtures now cover dotted
dates, ISO dates, compact time ranges, right-side PU/SO date/time lines, target
windows, and shipping/receiving hours. The private rerun did not change the
aggregate date/time counts, so the improvement is regression coverage for
known deterministic formats rather than a measured private-corpus gain.

After the rerun, the top issue categories are:

- `missing_core_field`;
- `missing_stop_time`;
- `conflict_core_field`;
- `missing_stop_date`;
- `broker_identity_missing`;
- `rate_conflict`.

The next measured blocker should be chosen from those categories or by local
human review of the workbook rows.

## Core Field Gap Forensics

The broader core-field analysis is run with:

```powershell
py scripts/analyze_core_field_gaps.py --write-md --write-json --include-local-document-names-local-only
```

It writes ignored local reports:

- `core_field_gap_analysis.md`
- `core_field_gap_analysis.json`

This report breaks `missing_core_field` and `conflict_core_field` into field
names and root-cause buckets such as `no_candidate`, `conflict`,
`candidate_exists_but_unresolved`, and
`optional_field_misclassified_as_core`.

Latest safe result after policy-aware blocker cleanup:

- readiness remained `extraction_review_ready=14`, `not_ready=4`;
- span-normalized stops remained 29;
- `optional_field_misclassified_as_core=0`;
- optional missing fields are separated from true intake blockers;
- true intake blockers total 56;
- dispatch-decision blockers total 128;
- top true intake fields are delivery date, broker name, pickup date, load
  number, rate, delivery location, and pickup location.

The next target should be chosen from `top_true_intake_core_gaps`, not from the
broad all-gap list. Current stop-field blockers are mostly `no_candidate`, so
another datetime regex or span-to-core mapping tweak is not the clean next move.
The next stop-focused block should inspect stop-span evidence/candidate
generation and coverage before changing extraction behavior.

## Candidate Coverage Analysis

Candidate coverage analysis is run with:

```powershell
py scripts/analyze_candidate_coverage.py --write-md --write-json --include-local-document-names-local-only
```

It writes ignored local reports:

- `candidate_coverage.md`
- `candidate_coverage.json`
- `candidate_coverage_analysis.md`
- `candidate_coverage_analysis.json`

This report distinguishes `no_candidate` from resolver conflicts by identifying
where evidence disappears: line feature, stop anchor, stop span, span field
candidate, normalized stop field, core field mapping, or review row.

The first policy-cleaned coverage pass selected
`broker_identity_candidate_generation` because `broker_name` was the largest
concrete `candidate_not_generated` field. Synthetic fixtures cover broker
contact blocks, broker-like header/logo text, explicit `Load Tendered By`
labels, and carrier-name guard cases.

Safe measured delta after the focused fix:

- broker-name candidate-not-generated: 10 -> 7;
- total candidate-not-generated: 27 -> 22;
- readiness unchanged: `extraction_review_ready=14`, `not_ready=4`;
- remaining top true intake blockers: delivery date, pickup date, load number,
  rate, broker name, delivery location, and pickup location.

The next extraction target should be selected from the remaining candidate
coverage counts. Do not repeat datetime or mapping work unless the stage data
shows that exact loss point.

The second target-selection pass did prove a date candidate-generation loss:
eight pickup/delivery date records were at
`span_field_candidate/candidate_not_generated`. The focused table-row date fix
reduced that count to zero, improved span date resolved/missing from 8 / 21 to
10 / 19, and left readiness unchanged. The remaining next target from coverage
is `load_identifier_candidate_generation`.

The load identifier pass implemented typed primary identifiers and typed
references, then regenerated local review and coverage outputs. The review
workbook now includes load identifier status, primary candidate count, typed
reference count, rejected non-primary reference count, gap reason, and
needs-review flag. Safe local result: primary identifier candidates 3, typed
references 11, rejected non-primary references 11, load-number candidate gap
7 -> 8 under the more specific taxonomy, and load-number intake blockers
7 -> 9. This means the next useful work is a label/section coverage audit for
load identity, not another broad identifier regex pass.

The follow-up audit added safe load identifier artifacts and a CLI, then tested
a constrained generic header-reference review candidate fix. The private corpus
did not move: primary candidates stayed 3, typed references stayed 11, rejected
non-primary references stayed 11, and core mappings stayed 1. Treat this as an
honest negative measurement. The next local review step is to inspect safe
label/section coverage counts for documents with no primary load identifier
candidate.

That label/section source-line audit has now run. It counted 96
identifier-like source lines, 11 header/load-identity source lines, 73
stop/billing/terms source lines, 96 detected labels, 24 classified labels, 3
primary candidates, and 11 rejected non-primary references. Root causes were
split across unknown, OCR/weak text, absent source lines, only non-primary
references, and correctly non-primary labels. Because no code-fixable reason
hit the three-alias threshold, `fix_allowed=false` and no further load-id
hardening was added.

## Non-Goals

This workflow does not run Google sync, create DispatchCases, call
DecisionEngine or Telegram, write Event Timeline events, add OCR/Vision/cloud
document AI, or make production automation claims.
