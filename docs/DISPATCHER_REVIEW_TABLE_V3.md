# Dispatcher Review Table V3

## Purpose

The v2 local review packet is useful for developers because it exposes field
statuses, gap reasons, and evidence diagnostics. It is still too technical for
dispatcher review because a single document can span many rows across core,
stop, rate, and load-ID sheets.

V3 adds a dispatcher-style table: one document per row, with the extracted
values arranged like an operational dispatch sheet. The reviewer can edit the
visible values directly, or use correction columns, then provide the edited CSV
for local feedback import.

This table is review-only. It is not final truth, does not create a
DispatchCase, does not call DecisionEngine, does not write events, and does not
make production automation claims.

## Review Concepts

- **Predicted extracted value**: the current local pipeline prediction for a
  field. It may be blank, missing, conflicted, or wrong.
- **User corrected value**: a local reviewer edit in the dispatcher table or in
  a `User Corrected ...` helper column.
- **Imported feedback**: a safe summary produced by comparing edited values to
  the original predictions. It contains counts and issue types only.
- **Trusted intake field**: a field that can be trusted only after local review
  and a later correction/import policy. V3 does not create trusted production
  fields by itself.

Original predictions must be preserved in an audit sheet so edited values can be
compared later without relying on the user to remember what changed.

## Workbook Sheets

### Dispatcher_Review

User-friendly, one-row-per-document table. It should resemble the operational
dispatch sheet and include editable columns for broker, pickup, delivery, load
number, equipment, commodity, weight, rate, notes, blockers, review status, and
local notes.

### Extraction_Audit

Original predicted values and statuses. This sheet is used by the feedback
importer to infer changed fields and issue categories. It is not intended for
manual editing.

### Review_Instructions

Local-only instructions for how to review, what to edit, how to export feedback,
and what must not be shared.

### Feedback_Summary

Safe count-only summary after feedback import. It may contain changed field
counts, issue type counts, and the recommended next repair target. It must not
include predicted values, corrected values, raw text, private filenames, local
paths, money values, or service account keys.

## Generate V3

Run locally from the repository root:

```powershell
py scripts/generate_dispatcher_review_table_v3.py --include-private-values-local-only --natural-sort-inputs
```

Generated ignored outputs:

- `ratecon_review_v3_dispatcher_workbook.xlsx`
- `ratecon_review_v3_dispatcher_review.csv`
- `ratecon_review_v3_extraction_audit.csv`
- `ratecon_review_v3_instructions.csv`
- `ratecon_review_v3_feedback_summary.csv`

Open the workbook and review the `Dispatcher_Review` sheet first. The detailed
v2 packet remains available for debugging, but V3 is the intended user-facing
review table.

## Edit Modes

The reviewer can use either mode:

- **Direct edit mode**: edit the visible dispatch columns directly.
- **Corrected column mode**: leave predictions unchanged and fill
  `User Corrected ...` columns.

The feedback importer supports both. Corrected columns take priority when both
are present.

## Import Feedback

After review, save an edited CSV as:

```text
ratecon_review_v3_dispatcher_review_completed.csv
```

Then run:

```powershell
py scripts/import_dispatcher_review_feedback.py
```

If no completed/edited feedback is found, the importer reports
`no_completed_dispatcher_feedback_found` and recommends continuing local review.

## Safety

Google Sheets sync remains paused until credentials exist. Private predicted
values may appear only inside ignored local workbook/CSV outputs when generated
with an explicit local-only flag. Console output, docs, tests, commits, and
final reports may include only aliases, counts, statuses, field names, and issue
categories.

## Non-Goals

- No extraction hardening.
- No OCR, Vision, or cloud document AI.
- No Google Sheets live sync.
- No DispatchCase creation.
- No DecisionEngine or Telegram calls.
- No Event Timeline writes.
