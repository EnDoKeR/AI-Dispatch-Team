# Next Candidate Coverage Target Plan

Selected target: `stop_span_date_candidate_generation`

## Supporting Counts

Current local candidate coverage selected this target from safe count/status
artifacts:

- affected field records: 8
- affected aliases: 2
- supporting fields: `delivery_date`, `pickup_date`
- failure stage: `span_field_candidate`
- gap reason: `candidate_not_generated`
- total `candidate_not_generated`: 22

This selection is data-driven. It does not repeat broad datetime hardening. It
targets the exact point where date evidence has reached stop-span processing but
no date field candidate is emitted.

## Fixture Plan

Add fake fixtures under:

`tests/fixtures/document_ai/candidate_coverage/stop_span_date/`

Required fixture patterns:

- TQL-like pickup/delivery rows with date and time columns inside stop spans.
- McLeod-like PU/SO sections with dates on the right side.
- Landstar-like target-window lines inside stop spans.
- SPI/Integrity-like expected date plus shipping/receiving hours.
- Header date outside stop span ignored.
- Billing/terms date ignored.

Fixtures must use fake values only. They must not contain private broker names,
real addresses, private dates/rates/references, screenshots, PDFs, raw private
text, or local paths.

## Tests Required

- fixture manifest loads and all fixture files exist;
- no banned private/screenshot/PDF/path tokens;
- date feature and stop span exist in the selected fixture patterns;
- missing date candidate is generated only from safe in-span lines;
- header and terms/billing dates remain ignored;
- focused stop-span candidate generation tests pass without changing review
  gates or production readiness claims.

## Expected Metric

Primary metric after rerun:

- selected target `candidate_not_generated` count should decrease.

Secondary metrics:

- total `candidate_not_generated` should not increase;
- readiness may remain unchanged;
- OCR_NEEDED should remain unchanged;
- no new passthrough behavior should appear.

## Non-Goals

No Google sync, OCR, Vision, cloud document AI, DispatchCase, DecisionEngine,
Telegram, Event Timeline writes, or production automation claims.
