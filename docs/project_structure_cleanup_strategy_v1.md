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

Phase 2 extracts only output path and filename construction. It centralizes
stable local artifact names and local-only output path validation so later
cleanup can move writers without accidentally changing filenames, directories,
or schemas. The output path module must not create directories, write files,
process PDFs, invoke OCR, call models or cloud services, sync Google Sheets, or
own report/audit generation.

Phase 3A extracts only safe report/export writer ownership for the local-only
private measurement summaries. The writer module owns safe JSON, CSV, Markdown,
and value-review template output generation while preserving existing filenames,
schemas, and local-only/private-redaction metadata. It must use the centralized
output path helpers and must not run measurement, process PDFs, invoke OCR, call
models or cloud services, sync Google Sheets, generate review workbooks, or own
full audit orchestration.

Phase 3B extracts only simple review/export artifact ownership for local-only
review packets and related labels. It must preserve existing filenames, schemas,
and local-only/private-redaction metadata, and it must not run measurement,
process PDFs, invoke OCR, call models or cloud services, sync Google Sheets,
generate review workbooks, or own full audit orchestration.

Phase 3C extracts only optional audit/diagnostic orchestration wrappers. The
orchestration module may decide which existing audit writer functions to call
from already-parsed flags, but it must not own metric definitions, audit
algorithms, filenames, schemas, measurement execution, review workbook
generation, or Google sync wiring.

Phase 3D extracts only review workbook generation ownership. The wrapper module
may decide whether to call the existing workbook artifact writer based on
already-parsed flags and may prepare console-safe result labels, but it must not
rewrite workbook internals, change sheet names, columns, styles, row semantics,
filenames, schemas, measurement execution, audit metrics, or Google sync wiring.

Phase 3E extracts only Google Sheets sync wiring. The wrapper module may plan
whether sync should run, apply the existing config override precedence, delegate
to the existing Google Sheets adapter, and prepare console-safe labels. It must
not change credential discovery, API scopes, worksheet semantics, sync modes,
output schemas, workbook layout, measurement execution, or audit metrics. Tests
must use fake clients and must not call Google.

Phase 3F is a responsibility audit, not another behavior split. Use
`scripts/audit_private_ratecon_measurement_cli_responsibilities.py` and
`docs/private_ratecon_measurement_cli_responsibility_audit_v1.md` to measure the
remaining responsibilities in `scripts/run_private_ratecon_measurement.py`
before deciding whether any further split is justified. The audit must remain
static/local-only and must not import project modules, run measurement, process
PDFs, invoke OCR, call Google, or call model/cloud services.

Future work should pause after the audit and make an explicit decision. Each
phase must preserve CLI flag names, output schemas, output filenames, workbook
layout, metric definitions, safety gates, credential behavior, sync semantics,
and measurement behavior unless a separate behavior-change PR explicitly
approves and tests that change.

Private outputs remain local-only. Generated reports, audits, review workbooks,
OCR artifacts, model outputs, raw extracted text, gold labels, Google
credentials, token files, sync logs with private values, and local audit outputs
must stay out of git.
