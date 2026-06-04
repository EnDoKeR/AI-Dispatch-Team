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

Future phases may move review workbook generation, Google sync wiring, and
pipeline orchestration into smaller owners. Each phase must preserve CLI flag
names, output schemas, output filenames, metric definitions, safety gates, and
measurement behavior unless a separate behavior-change PR explicitly approves
and tests that change.

Private outputs remain local-only. Generated reports, audits, review workbooks,
OCR artifacts, model outputs, raw extracted text, gold labels, and local audit
outputs must stay out of git.
