# Manual RateCon Dry-run Result Checklist

Date: 2026-05-29

Use this checklist after each manual RateCon text dry-run.

This is documentation only. It does not add PDF/OCR extraction, file reading, parser behavior changes, DispatchCase writes, Telegram behavior, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, replay, or reload-chain work.

## Result Categories

Use one category per dry-run:

```text
PASS_FOR_DRY_RUN
NEEDS_FIELD_FIX
NEEDS_PARSER_FIX
BAD_TEXT_EXTRACTION
NOT_READY_FOR_PDF
```

### PASS_FOR_DRY_RUN

Use when the dry-run output is good enough for manual review:

- key fields extracted correctly;
- missing fields are expected;
- needs-check fields are understandable;
- confidence values make sense;
- no private text was saved;
- no case was linked or created.

### NEEDS_FIELD_FIX

Use when the user should manually correct or provide fields before review:

- important field is missing from the copied text;
- manual JSON dry-run would be clearer;
- source document is missing a dispatch-required field;
- missing/needs-check list is accurate but work remains.

### NEEDS_PARSER_FIX

Use when pasted text contains clear labeled fields but the adapter misses them:

- obvious label variant was not recognized;
- confidence is too low for a clear field;
- special requirement is missed;
- parser output shape needs a narrow synthetic scenario.

### BAD_TEXT_EXTRACTION

Use when manually copied text is too messy:

- PDF copy/paste order is broken;
- columns are mixed together;
- labels and values are separated;
- text contains fragments only;
- too much contact/legal noise hides load fields.

### NOT_READY_FOR_PDF

Use when the issue points to future PDF/OCR strategy instead of current manual text support:

- scan quality prevents text copy;
- PDF text extraction is required;
- OCR is required;
- table layout cannot be represented by pasted text safely;
- private sample would require file processing.

## Field Verification Checklist

After each dry-run, verify:

- [ ] Did broker name extract?
- [ ] Did broker MC extract?
- [ ] Did rate extract?
- [ ] Did pickup location extract?
- [ ] Did delivery location extract?
- [ ] Did pickup date/time extract?
- [ ] Did delivery date/time extract?
- [ ] Did commodity extract?
- [ ] Did weight extract?
- [ ] Was reference ID found?
- [ ] Were special requirements detected?
- [ ] Were appointment windows represented?
- [ ] Were detention/layover/lumper/accessorial notes represented as review context?

## Missing And Needs-check Review

Check:

- [ ] Which fields are missing?
- [ ] Which fields need check?
- [ ] Are missing fields actually absent from the source?
- [ ] Are needs-check fields reasonable?
- [ ] Did the output avoid inventing values?
- [ ] Did linehaul/accessorial split avoid becoming a false total rate?
- [ ] Did ambiguous broker/contact-heavy text stay review-only?

## Confidence Review

Check:

- [ ] Which confidence values are `LOW`?
- [ ] Which confidence values are `UNKNOWN`?
- [ ] Are high-confidence values truly obvious labeled fields?
- [ ] Are medium-confidence values explainable label variants?
- [ ] Should any low-confidence field become a synthetic parser test later?

## Link Candidate Review

If a link candidate is produced, verify:

- [ ] Did link candidate recommend a safe action?
- [ ] Was `approval_required` true?
- [ ] Were match reasons understandable?
- [ ] Were mismatch reasons visible?
- [ ] Did missing fields prevent unsafe linking?
- [ ] Did low confidence force review?
- [ ] Did the system avoid creating a case?
- [ ] Did the system avoid linking a case?
- [ ] Did the system avoid setting `linked_dispatch_case_id`?
- [ ] Did the system avoid writing events?

## Privacy And Side-effect Review

Before closing the dry-run:

- [ ] Did the system avoid saving private text?
- [ ] Did no private file appear in `git status`?
- [ ] Did no generated output with private text get committed?
- [ ] Did no PDF/OCR extraction run?
- [ ] Did no Telegram, Gmail/email, Google Sheets, DAT/API, or Google Maps integration run?
- [ ] Did no DispatchCase or event write occur?

## Recommended Follow-up

For each dry-run, record only local/private notes unless the content is fully anonymized.

Suggested local summary:

```text
file_label:
result_category:
missing_fields:
needs_check_fields:
low_confidence_fields:
parser_gap:
text_extraction_gap:
safe_to_create_synthetic_fixture:
notes:
```

Only commit a follow-up fixture if all real broker/customer/driver/contact/reference/address/date details are replaced with synthetic values.
