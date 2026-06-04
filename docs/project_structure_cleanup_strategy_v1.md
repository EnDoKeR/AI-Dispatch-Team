# Project Structure Cleanup Strategy v1

This cleanup track is visibility-first and behavior-preserving. Each PR should
move one ownership boundary at a time, keep public entrypoints stable, and avoid
production extraction changes.

## Private RateCon Measurement CLI Split

`scripts/run_private_ratecon_measurement.py` remains the public private
measurement CLI. Phase 1 extracts only the command surface:

- argument definitions and help text;
- parsed command configuration;
- local/private preflight safety validation.

The extracted modules live under `app/document_ai/measurement_cli/` and must not
own measurement business logic. They must not process PDFs, invoke OCR, call
models or cloud services, write reports, sync Google Sheets, or read private
document content.

Future phases may move report writers, review exporters, audit orchestration,
Google sync wiring, and pipeline orchestration into smaller owners. Each phase
must preserve CLI flag names, output schemas, safety gates, and measurement
behavior unless a separate behavior-change PR explicitly approves and tests that
change.

Private outputs remain local-only. Generated reports, audits, review workbooks,
OCR artifacts, model outputs, raw extracted text, gold labels, and local audit
outputs must stay out of git.
