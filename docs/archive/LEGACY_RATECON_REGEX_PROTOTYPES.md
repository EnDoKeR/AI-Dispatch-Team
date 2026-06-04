# Legacy RateCon Regex Prototypes

This archive note records the intentional removal of two deprecated standalone
RateCon prototype scripts:

- `scripts/read_ratecon.py`
- `scripts/import_ratecon.py`

They were removed because they were old direct PDF/regex prototypes and were no
longer part of the official RateCon extraction path. The import graph audit
showed zero non-test dependents before removal.

## Historical Purpose

`scripts/read_ratecon.py` read a PDF with `pypdf`, applied direct regexes, and
printed extracted field values when explicitly allowed.

`scripts/import_ratecon.py` read a PDF with `pypdf`, applied similar direct
regexes, and could write a row to Google Sheets when explicitly allowed.

Both scripts bypassed the current candidate/template/resolver/validation
architecture and duplicated legacy helper logic.

## Replacement Paths

Use these current paths instead:

- Document AI candidate/template/resolver/validation pipeline for official
  RateCon extraction development.
- `scripts/run_private_ratecon_measurement.py` for explicit local-only private
  measurement runs.
- Hybrid/manual benchmark workflow for review-required model-assisted or manual
  validation work.

## Do Not Recreate

Do not reintroduce direct PDF-to-Google-Sheets scripts or direct regex-to-final
RateCon extraction scripts. New work should route through the current document
AI pipeline and review/validation contracts.

Do not commit private PDFs, raw extracted document text, gold labels, filled
hybrid templates, benchmark outputs, local audit outputs, OCR artifacts, model
outputs, secrets, or anything under `.local_outputs/` or `data/private_ratecons/`.
