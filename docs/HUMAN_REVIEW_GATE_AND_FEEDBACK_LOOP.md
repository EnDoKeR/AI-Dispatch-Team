# Human Review Gate And Feedback Loop

## Purpose

Deterministic hardening is paused for the current RateCon review workflow until
local human feedback identifies the next repair target. Recent forensics showed
that several tempting targets do not currently have a shared deterministic root
cause in the private corpus:

- `load_identifier_candidate_generation` was deferred after source-line
  forensics found no shared code-fixable cause across enough aliases.
- Rate conflict forensics found remaining review cases, but did not prove an
  allowed shared arbitration fix.
- Generic stop datetime and stop-span mapping hardening improved synthetic
  coverage earlier, but did not improve the private corpus enough to justify
  more generic rules.

The next repair block should be selected from completed review feedback, not
from another round of broad extraction heuristics.

## Review Terms

- **Predicted value**: the value extracted by the local deterministic pipeline.
  It is useful for review, but it is not final truth.
- **Reviewed value**: a local human decision that the predicted value is correct,
  wrong, unknown, or not applicable.
- **Corrected value**: a local-only value entered by the reviewer when the
  prediction is wrong or missing. Corrected values must not be pasted into chat,
  docs, tests, commits, or console output.
- **Trusted intake field**: a field that can be trusted only after the local
  review workflow marks it correct or provides a reviewed correction.

The review packet is a triage aid. It is not a production source of truth, and
it does not create dispatch cases, decisions, or events.

## Local Review Modes

1. **Status-only safe packet**: includes aliases, statuses, field names, issue
   categories, counts, and review columns. Predicted value columns are blank.
2. **Local-private values packet**: includes predicted values for local-only
   review. It must stay in ignored local output folders.
3. **Completed feedback CSV**: a local reviewer-edited CSV with `User Correct?`,
   `User Issue Type`, and optional local-only expected values or notes.

Generate the simplified packet locally:

```powershell
py scripts/generate_ratecon_review_packet_v2.py --include-private-values-local-only --natural-sort-inputs
```

This writes ignored local artifacts named `ratecon_review_v2_*`. Console output
reports row counts and basenames only.

Import completed feedback after review:

```powershell
py scripts/import_ratecon_review_feedback.py
```

If completed feedback CSVs are missing or contain no review decisions, the
import returns `no_completed_feedback_found` and the next action remains local
human review.

## Recommended Review Order

1. `Document_Summary`: confirm document type, OCR status, extraction relevance,
   readiness, and top blockers.
2. `Core_Field_Review`: review the intake-critical fields first.
3. `Stop_Review`: review pickup/delivery location, date, and time rows.
4. `Rate_Review`: review main rate/payment rows and conflict reasons.
5. `Load_ID_Review`: review typed load identifiers and rejected references.

## Issue Type Taxonomy

Use these issue types in completed local feedback:

- `correct`
- `wrong_value`
- `missing_value`
- `extra_value`
- `duplicate_stop`
- `extra_stop`
- `missing_stop`
- `wrong_stop_type`
- `wrong_pickup`
- `wrong_delivery`
- `wrong_date`
- `wrong_time`
- `wrong_rate`
- `accessorial_confused_as_rate`
- `rate_conflict_true`
- `load_id_missing`
- `wrong_load_id`
- `broker_missing`
- `wrong_broker`
- `OCR_needed`
- `document_not_ratecon`
- `unclear_document`
- `other`

## Next Repair Selection

Completed feedback is summarized into issue counts by field, alias, and issue
type. The next repair target should be selected from those reviewed counts.
Deferred targets remain skipped unless feedback proves they are the dominant
reviewed issue type.

Current deterministic hardening is review-gated for:

- `load_identifier_candidate_generation`
- `rate_conflict_review_routing`
- `generic_stop_datetime_mapping`
- `generic_stop_span_mapping`

Safe summaries may include issue counts, field names, aliases, readiness counts,
and status categories. They must not include predicted values, expected values,
money amounts, raw text, local paths, private filenames, or service account
keys.

## Non-Goals

- No OCR, Vision, or cloud document AI.
- No Google Sheets sync while credentials are unavailable.
- No DispatchCase creation.
- No DecisionEngine or Telegram calls.
- No production automation claims.
