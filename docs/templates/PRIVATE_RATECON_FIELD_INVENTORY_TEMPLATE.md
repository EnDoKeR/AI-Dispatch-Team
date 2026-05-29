# Private RateCon Field Inventory Template

Do not paste real private document text into this file if committing to GitHub.

Use this template for local/private manual review only. If you fill it with real operational values, keep the filled copy outside Git or in a gitignored local path.

Safe placeholder examples may use fake values such as:

```text
FAKE BROKER LLC
MC000000
FAKE-REF-001
```

## Document Summary

| Field | Value | Confidence | Missing / needs-check | Notes |
| --- | --- | --- | --- | --- |
| file_label / local filename reference |  |  |  | Local label only; avoid broker/customer names |
| source category |  |  |  | Example: clean/simple, missing weight, accessorial split |
| broker_name |  |  |  |  |
| broker_mc |  |  |  |  |
| rate |  |  |  | Note if linehaul/accessorial split exists |
| pickup_location |  |  |  | City/state preferred for committed synthetic examples |
| pickup_date |  |  |  |  |
| pickup_time |  |  |  | Exact time or window |
| delivery_location |  |  |  | City/state preferred for committed synthetic examples |
| delivery_date |  |  |  |  |
| delivery_time |  |  |  | Exact time or window |
| commodity |  |  |  |  |
| weight |  |  |  |  |
| reference_id / load number |  |  |  | Use fake ID if creating synthetic fixture |
| equipment |  |  |  |  |
| special_requirements |  |  |  |  |
| detention/layover/lumper/accessorial notes |  |  |  | Do not paste full private clauses into committed files |
| appointment windows |  |  |  |  |
| number of pickups/deliveries |  |  |  |  |
| missing_fields |  |  |  | List field names only |
| needs_check_fields |  |  |  | List field names only |
| confidence_notes |  |  |  | Keep private details local |
| parser difficulty notes |  |  |  | Describe layout challenge, not private content |

## Checklist View

- [ ] File is stored under `data/private_ratecons/`.
- [ ] `git status` does not show the private file.
- [ ] Local label avoids broker/customer/driver/contact names.
- [ ] Missing fields are listed.
- [ ] Needs-check fields are listed.
- [ ] Confidence notes are recorded locally.
- [ ] Parser difficulty notes describe structure only.
- [ ] Any public fixture derived from this review is synthetic/anonymized.

## Optional Fake Example Row

| Field | Value | Confidence | Missing / needs-check | Notes |
| --- | --- | --- | --- | --- |
| broker_name | FAKE BROKER LLC | HIGH |  | Placeholder only |
| broker_mc | MC000000 | HIGH |  | Placeholder only |
| reference_id / load number | FAKE-REF-001 | HIGH |  | Placeholder only |

## Safety Reminder

This template is safe to commit only while blank or filled with fake placeholder values. Do not commit a completed copy containing real private RateCon fields, copied document text, broker/customer/driver/contact details, real reference numbers, or real appointment details.
