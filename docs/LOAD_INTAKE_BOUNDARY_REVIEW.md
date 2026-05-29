# Load Intake Boundary Review

Date: 2026-05-29

Scope:

- audit only
- no file deletion or moves
- no runtime behavior changes
- no parser expansion
- no Gmail/email, Google Sheets, Telegram upload, OCR, DAT/API, Google Maps, or scheduler work

## Current Files

`app/load_intake/` currently contains:

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

## Current Activity

`app/load_intake/` appears to be a legacy/prototype intake path, not the active Foundation Hardening runtime path.

Current active architecture is still centered in:

```text
app/market_intelligence/
```

Import scan findings:

- `app/load_intake/importer.py` imports `parse_ratecon(...)` and `append_load(...)`.
- `app/load_intake/parser.py` imports the main `MarketLoad` as `Load` for compatibility.
- `app/load_intake/sheet_writer.py` lazy-imports `gspread` only when a sheet write is requested.
- Current tests import `app/load_intake` modules to protect import safety.
- No current `market_intelligence` production flow imports `app/load_intake`.
- `scripts/import_ratecon.py` is a standalone manual script and does not use `app/load_intake/importer.py`.

Relevant protection tests:

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
tests/test_manual_sheet_connection_script.py
```

## Responsibility Mixing

`app/load_intake/parser.py` currently mixes several responsibilities:

- PDF text extraction through `pypdf`
- broker document field extraction
- mileage lookup
- delivery zone scoring
- broker score lookup
- RPM score calculation
- final dispatch decision calculation
- reload score adjustment
- `MarketLoad` creation

`app/load_intake/importer.py` adds another mixed boundary:

- scans `data/ratecons`
- tracks imported files in `data/imported_loads.txt`
- parses documents
- writes loads to Google Sheets

`app/load_intake/sheet_writer.py` is intentionally safer than before because it uses environment settings and delays external imports, but it is still a manual integration boundary.

## Boundary Decision

For now, `app/load_intake/` should stay isolated.

It should not be deleted yet because:

- it documents an early RateCon/manual intake idea
- tests protect safe import behavior
- it may contain useful parsing examples for future design
- manual Google Sheets workflows still exist as legacy candidates

It should not be expanded yet because:

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

That should remain design-only and define:

- future document receipt flow
- mandatory fields
- missing fields
- needs-check fields
- first safe output
- future DispatchCase connection points

Do not implement parser/storage/integration behavior until the workflow and record shape are accepted.
