# RateCon Hybrid Sanitized Fixtures

These fixtures exercise the local-only hybrid benchmark workflow without using
private broker documents, private gold labels, OCR outputs, PDFs, or model
outputs.

## Scenarios

- `DOC_FIXTURE_PERFECT`: a rate confirmation with matching load, rate, pickup,
  and delivery stop drafts.
- `DOC_FIXTURE_MISSING_EVIDENCE`: a rate confirmation with correct stop values
  but missing stop evidence.
- `DOC_FIXTURE_UNSAFE_WRONG_STOP`: a rate confirmation with a materially wrong
  pickup stop.
- `DOC_FIXTURE_AUTO_ACCEPT`: a rate confirmation with a stop `auto_accept=true`
  policy violation.
- `DOC_FIXTURE_NON_RC`: a BOL/POD-style non-rate-confirmation document.
- `DOC_FIXTURE_PARTIAL_STOP`: a rate confirmation with useful partial stop
  drafts that still require human review.

All values are synthetic and intentionally generic. These files are safe to
commit; generated benchmark outputs still belong under `.local_outputs/`.
