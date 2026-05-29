# Private RateCon Dry-run Result Summary Template

Do not paste private RateCon text, real broker names, phone numbers, emails, addresses, MCs, reference numbers, appointment details, or copied document clauses into this tracked template.

Use this as a blank/safe template only. Filled summaries containing private operational values must stay local or gitignored.

## Summary Table

| Field | Value |
| --- | --- |
| anonymized_label |  |
| result_category |  |
| broker_name_extracted | yes / no / partial |
| broker_mc_extracted | yes / no / partial |
| rate_extracted | yes / no / partial |
| pickup_extracted | yes / no / partial |
| delivery_extracted | yes / no / partial |
| date_time_extracted | yes / no / partial |
| commodity_extracted | yes / no / partial |
| weight_extracted | yes / no / partial |
| reference_id_extracted | yes / no / partial |
| missing_fields |  |
| needs_check_fields |  |
| low_confidence_fields |  |
| parser_issue_notes | Structure-only notes, no private text |
| safe_next_action |  |

## Result Categories

Use one:

```text
PASS_FOR_DRY_RUN
NEEDS_FIELD_FIX
NEEDS_PARSER_FIX
BAD_TEXT_EXTRACTION
NOT_READY_FOR_PDF
```

## Safe Next Action Examples

Use safe structural notes like:

```text
create synthetic scenario for missing broker MC label
create synthetic scenario for linehaul/accessorial split
manual field review needed before parser expansion
PDF extraction strategy audit needed later
```

Do not include real document values in notes.

## Final Safety Check

- [ ] No private RateCon text pasted.
- [ ] No real broker/customer/driver/contact data pasted.
- [ ] No real phone numbers or emails pasted.
- [ ] No real addresses pasted.
- [ ] No real MC/reference/load numbers pasted.
- [ ] No private appointment details pasted.
- [ ] No PDF/OCR output pasted.
- [ ] No DispatchCase IDs from private workflow pasted unless anonymized.
