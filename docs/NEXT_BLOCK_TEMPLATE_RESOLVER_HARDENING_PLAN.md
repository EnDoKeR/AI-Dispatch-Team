# Next Block: Template Resolver Hardening Plan

## Objective

Harden the fake/anonymized RateCon broker-template resolver so it handles harder
document layouts before any private rerun or OCR/Vision decision.

This block should improve confidence, conflict handling, stop/date association,
and typed-reference association using fake/anonymized fixtures only.

## Why This Block Is Needed

The current pipeline is correctly layered:

```text
safe text artifact
-> generic candidates
-> broker template matching
-> template-aware candidate scoring
-> conservative resolver
-> RateConfirmationIntake draft
-> validation
```

The next weakness is not PDF triage or private extraction. It is resolver
behavior on realistic document structures where labels repeat, amounts compete,
or references appear near the wrong field. Hardening this layer with fake data
keeps private values out of the repo and makes later private measurement
meaningful.

## Problems To Simulate With Fake Fixtures

Add fake/anonymized fixtures for:

- multi-page terms where the same broker/header text repeats;
- repeated headers and footers around load details;
- multiple rate-like amounts, including linehaul, fuel, detention, lumper, quick
  pay, and fee amounts;
- table-like stops with pickup and delivery rows;
- missing broker MC with otherwise strong broker-template evidence;
- broker name in header only;
- references near the wrong stop or repeated in terms;
- pickup and delivery date association when dates are split from locations;
- conflicting appointment times for one stop;
- special requirements buried in notes;
- accessorial terms near rate labels;
- missing equipment or weight with otherwise complete core fields.

All fixture values must remain fake, such as:

- `FAKE BROKER LLC`
- `MC000000`
- `FAKE-LOAD-001`
- `FAKE-PO-001`
- `Fake City, ST 00000`
- `$0000.00`

## Expected New Fake Fixtures

Suggested files under `tests/fixtures/document_ai/ratecon_text/`:

- `multi_page_terms_ratecon.txt`
- `repeated_header_footer_ratecon.txt`
- `table_stop_date_association_ratecon.txt`
- `missing_broker_mc_template_match_ratecon.txt`
- `header_only_broker_ratecon.txt`
- `wrong_stop_reference_ratecon.txt`
- `conflicting_appointments_ratecon.txt`
- `notes_buried_requirements_ratecon.txt`
- `accessorials_near_rate_ratecon.txt`

If fixture files become too repetitive, add a small fixture builder helper, but
do not use private text or private-derived snippets.

## Expected Resolver Improvements

The resolver should:

- preserve all plausible candidates;
- select fields only when confidence and template evidence are strong enough;
- mark conflicts when multiple strong candidates disagree;
- keep rate unresolved if only accessorial or fee amounts are present;
- prefer template-specific carrier-pay labels over accessorial labels;
- associate pickup dates with pickup locations and delivery dates with delivery
  locations when labels/sections support it;
- avoid assigning a stop reference to the wrong stop;
- treat missing broker MC as optional when the current RateCon core policy allows
  it, while still preserving the missing optional field;
- preserve special requirements as evidence, not dispatch decisions;
- keep low-confidence template matches from overboosting candidates.

## Fields Affected

- broker_name
- broker_mc
- load_number
- typed references
- rate
- pickup_location
- pickup_date
- pickup_time
- delivery_location
- delivery_date
- delivery_time
- equipment
- weight
- commodity
- special_requirement
- accessorial_term

## Tests Required

Add focused tests for:

- fake fixtures load and contain no private/real broker data;
- template selection status for each hard layout;
- candidate counts by field;
- rate/accessorial separation;
- stop/date/time association;
- typed-reference preservation;
- missing broker MC optional behavior;
- conflict fields for conflicting appointments or conflicting rates;
- unknown/low-confidence template fallback;
- intake draft remains review-gated when critical fields are missing, low
  confidence, or conflicting;
- no DispatchCase creation;
- no `ACCEPT`/`REJECT` output;
- no raw private text in fixtures or reports.

Also extend the broker-template regression matrix so hard layouts become stable
fixtures before private measurement resumes.

## Docs Required

Update:

- `docs/RATECON_BROKER_TEMPLATES.md`
- `docs/RATECON_CANDIDATE_EXTRACTION.md`
- `docs/TESTING_ROADMAP.md`
- `docs/RATECON_PIPELINE_CURRENT_STATE.md` if the official flow changes

Docs should emphasize that templates are scoring aids, not final truth.

## Safety Rules

- Use fake/anonymized examples only.
- Do not touch private PDFs or private CSVs.
- Do not commit private text or private values.
- Do not add OCR.
- Do not add Vision AI.
- Do not add cloud APIs or network calls.
- Do not add real broker templates.
- Do not create DispatchCases.
- Do not write DispatchCase events.
- Do not call DecisionEngine from extraction.
- Do not call Telegram from extraction.
- Do not recreate the removed direct RateCon PDF/regex prototypes as official
  paths.

## Explicit Non-Goals

- no private PDF rerun in this block;
- no OCR or Vision;
- no Google Sheets API;
- no DAT/API integration;
- no autonomous booking;
- no broker memory or BrokerProfile scoring;
- no DispatchCase creation from extraction;
- no real broker names, MCs, customers, contacts, addresses, phone numbers,
  emails, reference numbers, or appointment details in tracked fixtures.

## Exit Criteria

The block is complete when:

1. Hard-layout fake fixtures exist and are covered by tests.
2. Template-aware resolver behavior improves on fake layouts.
3. Accessorial/rate conflicts remain review-safe.
4. Stop/date/reference association is tested.
5. Missing, low-confidence, and conflict fields remain explicit.
6. Intake drafts still pass through validation and do not create DispatchCases.
7. Architecture boundary tests remain green.
8. Full unittest discovery passes.
9. Git status is clean and only safe tracked files are committed.

After this block, the next safe step is a local private measurement harness that
reports only triage metrics, candidate counts, field statuses, missing fields,
conflicts, warnings, and result categories.
