# Load Intake Boundary Review

Date: 2026-05-29

Status update: this is a historical boundary review. The legacy `app/load_intake/` package was later removed after a salvage/delete audit. Active intake work now lives under `app/market_intelligence/intake/`.

Scope:

- audit only
- no file deletion or moves
- no runtime behavior changes
- no parser expansion
- no Gmail/email, Google Sheets, Telegram upload, OCR, DAT/API, Google Maps, or scheduler work

## Historical Files

Before deletion, `app/load_intake/` contained:

```text
broker_engine.py
decision_engine.py
importer.py
market_models.py
mileage.py
parser.py
reload_engine.py
sheet_writer.py
zone_engine.py
```

Current line-count shape:

```text
parser.py          231
sheet_writer.py     88
market_models.py    81
reload_engine.py    75
decision_engine.py  57
zone_engine.py      47
importer.py         46
mileage.py          28
broker_engine.py    32
```

## Historical Activity

`app/load_intake/` was a legacy/prototype intake path, not the active Foundation Hardening runtime path.

Current active intake architecture is centered in:

```text
app/market_intelligence/intake/
```

Import scan findings:

- `app/load_intake/importer.py` imported `parse_ratecon(...)` and `append_load(...)`.
- `app/load_intake/parser.py` imported the main `MarketLoad` as `Load` for compatibility.
- `app/load_intake/sheet_writer.py` lazy-imported `gspread` only when a sheet write was requested.
- Legacy tests imported `app/load_intake` modules to protect import safety before deletion.
- No `market_intelligence` production flow imported `app/load_intake`.
- The old standalone RateCon PDF/regex Google Sheets prototype was removed; see
  `docs/archive/LEGACY_RATECON_REGEX_PROTOTYPES.md`.

Historical protection tests:

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
tests/test_manual_sheet_connection_script.py
```

The two legacy import tests were removed with the package. `tests/test_manual_sheet_connection_script.py` remains because it covers a separate manual script and does not depend on the deleted package.

## Responsibility Mixing

`app/load_intake/parser.py` mixed several responsibilities:

- PDF text extraction through `pypdf`
- broker document field extraction
- mileage lookup
- delivery zone scoring
- broker score lookup
- RPM score calculation
- final dispatch decision calculation
- reload score adjustment
- `MarketLoad` creation

`app/load_intake/importer.py` added another mixed boundary:

- scans `data/ratecons`
- tracks imported files in `data/imported_loads.txt`
- parses documents
- writes loads to Google Sheets

`app/load_intake/sheet_writer.py` was intentionally safer than before because it used environment settings and delayed external imports, but it was still a manual integration boundary.

## Boundary Decision

Deletion is complete. The old package should not be restored or reused.

Useful label ideas were preserved outside the deleted package in synthetic fixtures and redacted diagnostics docs. The following legacy behaviors are intentionally excluded from the current architecture:

- Google Sheets writing;
- parser-to-`MarketLoad` construction;
- dispatch decision scoring;
- reload scoring;
- mileage/zone scoring;
- broker scoring;
- direct parser-to-decision flow.

It should not be reintroduced because:

- raw intake should not own dispatch decisions
- PDF parsing should not write directly to Google Sheets
- future RateCon parsing should produce structured evidence, not final match decisions
- optional dependencies such as `pypdf`, `gspread`, and Google credentials should stay optional/manual until the workflow is explicitly accepted

## Future Boundary

Future intake should be split by responsibility:

```text
document source
  -> raw file receipt metadata
  -> parser/extractor
  -> normalized intake record
  -> missing/needs-check field report
  -> later DispatchCase link
  -> later optional export/integration
```

The raw intake layer should produce structured evidence only.

It should not:

- choose `BUY` / `NO BUY`
- override hard dispatch rules
- send Telegram messages
- write Google Sheets directly
- write DispatchCase events directly
- call Gmail/email APIs
- run OCR or PDF expansion without a focused design

## Recommended Next Target

Next safe target:

```text
RateCon / document intake workflow design
```

That design now lives in:

```text
docs/RATECON_INTAKE_WORKFLOW.md
```

It should remain design-only and define:

- future document receipt flow
- mandatory fields
- missing fields
- needs-check fields
- first safe output
- future DispatchCase connection points

Do not implement parser/storage/integration behavior until the workflow and record shape are accepted.
