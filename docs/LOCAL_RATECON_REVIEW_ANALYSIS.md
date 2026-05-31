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

## Non-Goals

This workflow does not run Google sync, create DispatchCases, call
DecisionEngine or Telegram, write Event Timeline events, add OCR/Vision/cloud
document AI, or make production automation claims.
