# Next Block: Safe Private RateCon Measurement Plan

## Objective

Measure the current deterministic RateCon pipeline against the local private test
documents without committing, printing, or saving raw private text in tracked
files.

The measurement goal is not production extraction. The goal is to compare field
status before and after the fake/anonymized candidate, template, resolver, and
hard-layout hardening work.

## What Will Be Measured

For each local private document, the next block should measure only safe summary
categories:

- triage route;
- page count;
- character count;
- candidate counts by field;
- template match status;
- selected template ID only if safe/anonymized or generic;
- template scoring applied or limited;
- resolved field names;
- missing field names;
- needs-check field names;
- conflict field names;
- result category;
- generic warning categories.

## Safe To Share

The user or Codex may share:

- anonymized labels such as `RATECON_001`;
- `TEXT_EXTRACTED`, `EMPTY_TEXT`, or PDF triage route;
- page and character counts;
- field status only: resolved, missing, needs-check, conflict, low confidence;
- candidate counts by field;
- template status;
- generic warning codes;
- whether local CSV or safe JSON summaries were created.

## Must Stay Local And Private

Do not share or commit:

- private filenames;
- raw extracted text;
- broker/customer/contact names;
- MCs;
- addresses;
- phone numbers;
- emails;
- reference numbers;
- appointment details;
- document snippets;
- local private CSV outputs;
- private value-review rows.

## Prior Safe Comparison Baseline

Known safe prior results:

- `RATECON_001`: `TEXT_EXTRACTED`, 4636 chars, 2 pages, still missing core fields.
- `RATECON_002`: `EMPTY_TEXT`, 0 chars, 2 pages.
- `RATECON_003`: `TEXT_EXTRACTED`, 10694 chars, 3 pages, low-confidence rate and special requirements.

The next measurement should compare:

- whether `TEXT_EXTRACTED` documents now produce more candidates;
- whether template matching is unknown, matched, conflict, or low confidence;
- whether missing core fields decreased;
- whether conflicts are visible instead of silently resolved;
- whether accessorial amounts are prevented from becoming rate;
- whether `EMPTY_TEXT` remains an extraction-route issue rather than a parser issue.

## Expected Output Shape

Safe console/report output should look like:

```text
RATECON_001
  triage_route: DIGITAL_TEXT
  page_count: 2
  char_count: 4636
  candidate_counts_by_field: {rate: 2, pickup_location: 1, ...}
  template_status: unknown|matched|conflict|low_confidence
  resolved_fields: [...]
  missing_fields: [...]
  needs_check_fields: [...]
  conflict_fields: [...]
  warnings: [...]
```

Values must remain absent from the report.

## Success Criteria

The measurement block succeeds if:

- private text is not printed or committed;
- private outputs remain ignored/local only;
- `TEXT_EXTRACTED` documents show safer field status than prior runs;
- missing fields remain explicit;
- low-confidence fields remain explicit;
- conflicts remain explicit;
- `EMPTY_TEXT` documents are identified as triage/OCR-route blockers;
- no DispatchCase is created;
- no events are written;
- no Telegram output is sent.

## Non-Goals

Do not implement:

- OCR;
- Vision AI;
- cloud extraction APIs;
- private raw text reporting;
- private fixtures;
- real broker templates;
- DispatchCase creation;
- Event Timeline writes;
- Telegram formatting for extraction output;
- production extraction claims.

## Recommended Command Direction

The next block may add or reuse a local-only private measurement command. It
should default to a small limit and write only ignored safe summaries or local
private value-review CSVs.

Any tracked tests must use fake/anonymized fixtures only.

## Decision After Measurement

After safe private measurement:

1. If `TEXT_EXTRACTED` documents improve and `EMPTY_TEXT` remains the main blocker,
   consider a local OCR design block.
2. If `TEXT_EXTRACTED` documents still miss table/layout fields, consider a
   layout-aware digital extraction design block.
3. If unknown, scanned, or table-heavy documents remain weak after deterministic
   extraction, consider a gated Vision fallback design block.
4. Do not jump to OCR or Vision without measurement.
