# Load Intake Legacy Salvage Audit

Date: 2026-05-30

This audit reviews the legacy `app/load_intake/` prototype now that the current intake architecture lives under `app/market_intelligence/intake/`. It does not delete files, change runtime behavior, process private RateCons, add OCR/PDF parsing behavior, add Google Sheets behavior, create/link DispatchCases, write events, or wire legacy code into active flows.

## Current Legacy Files

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

## Current Import Surface

Direct legacy import tests:

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
```

Current test purpose:

- verify legacy modules still import without immediate external side effects;
- verify `sheet_writer.py` uses environment settings and stops before external imports when no Sheet ID is configured;
- verify `parser.py` still exposes the current `MarketLoad` compatibility constructor as `Load`.

Current app/script imports:

- `app/load_intake/importer.py` imports `parse_ratecon(...)` and `append_load(...)` inside the legacy folder.
- `app/load_intake/parser.py` imports other legacy helper modules and current `app.market_intelligence.market_models.MarketLoad` as `Load`.
- No current `app/market_intelligence/intake/` module imports `app/load_intake`.
- `scripts/import_ratecon.py` does not import `app/load_intake`, but it contains a separate old manual PDF-to-Google-Sheets flow with similar regex ideas and live external dependencies.
- `scripts/manual_test_sheet_connection.py` is a separate manual Google Sheets connectivity script and does not depend on `app/load_intake`.

## File-by-File Audit

### `parser.py`

Responsibilities currently mixed together:

- reads PDFs with `pypdf.PdfReader`;
- extracts text;
- uses regex patterns for broker, pickup, delivery, dates, load number, carrier, trailer type, commodity, weight, and total rate;
- calculates miles/RPM;
- evaluates zones, broker score, reload score, final score, final decision, and adjusted decision;
- creates a `MarketLoad`;
- returns a load object rather than structured parser evidence.

Potentially reusable:

- a small set of label/regex concepts, documented separately before any implementation.

Must not be reused directly:

- direct PDF reading in active parser flow;
- parser-to-decision flow;
- score/RPM/reload/zone/broker logic;
- `MarketLoad` construction from parser output;
- private text examples or document snippets.

### `importer.py`

Responsibilities:

- scans `data/ratecons`;
- tracks imported filenames in `data/imported_loads.txt`;
- calls legacy parser;
- writes to Google Sheets via `append_load(...)`;
- prints file names and import results.

Reusable:

- none for active architecture.

Must not be reused:

- automatic folder import;
- filename tracking;
- Google Sheets write flow;
- parser-to-storage/write flow.

### `sheet_writer.py`

Responsibilities:

- reads Google Sheets settings from environment variables;
- lazy-imports `gspread` and Google credentials only when appending;
- writes a full row into a spreadsheet.

Reusable:

- the safe delayed-import pattern is a useful general idea, but no active intake code should write Google Sheets.

Must not be reused:

- spreadsheet writes;
- private RateCon data export;
- external Google integration.

### `decision_engine.py`

Responsibilities:

- RPM scoring;
- weighted final score;
- BOOK/REVIEW/PASS decision.

Reusable:

- none directly. The current DecisionEngine foundation has its own result/risk/signal model.

Must not be reused:

- old score thresholds;
- direct BOOK/PASS decisions;
- parser-coupled decision flow.

### `reload_engine.py`

Responsibilities:

- state-list based reload score;
- adjusted score;
- BOOK/REVIEW/PASS decision.

Reusable:

- none directly. Reload-watch and market-context foundations already exist separately.

Must not be reused:

- old reload scoring;
- final decision adjustment.

### `broker_engine.py`

Responsibilities:

- reads `data/brokers.csv`;
- returns score/status by broker name.

Reusable:

- none directly. Broker memory now has stronger boundaries under market intelligence.

Must not be reused:

- ad hoc CSV lookup as active broker memory;
- parser-coupled broker scoring.

### `mileage.py`

Responsibilities:

- optional `geopy` import;
- mock coordinate lookup for a tiny fixed set of locations;
- mileage estimate.

Reusable:

- none directly.

Must not be reused:

- mock coordinates as real mileage logic;
- Google Maps or external mileage behavior in intake.

### `zone_engine.py`

Responsibilities:

- state-list based zone scoring.

Reusable:

- none directly. Market context has stronger baseline/zone helpers.

Must not be reused:

- old zone scoring as active decision logic.

### `market_models.py`

Responsibilities:

- small separate `MarketLoad` prototype model;
- simple qualification/good-load helpers.

Reusable:

- none directly. Active market model logic now lives under `app/market_intelligence/`.

Must not be reused:

- old qualification rules;
- duplicate model shape.

## Unsafe Legacy Behavior

The legacy folder includes behavior that should not be carried into the new architecture:

- direct PDF parsing as a parser/decision pipeline;
- Google Sheets writing;
- parser-to-MarketLoad creation;
- dispatch decision scoring;
- reload scoring;
- mileage/zone scoring;
- broker score lookup;
- parser-to-decision flow;
- implicit file/folder imports;
- old BOOK/PASS terminology.

## Potential Salvage

Only parser label/regex ideas may be worth salvaging.

Safe candidates to document:

- broker label candidates;
- shipper/pickup label candidates;
- consignee/delivery label candidates;
- total/rate label candidates;
- pickup/delivery time label candidates;
- load/reference label candidates;
- carrier label candidates;
- trailer/equipment label candidates;
- commodity/weight label candidates.

These should be translated into synthetic/fake examples before any parser behavior changes.

## Recommendation

Recommended current state:

```text
keep temporarily, mark as archived/legacy, salvage label ideas into docs/tests only
```

Rationale:

- the folder is still covered by import compatibility tests;
- deletion would require test and docs cleanup;
- the old parser includes useful label hints, but the runtime flow is unsafe for reuse;
- the current intake architecture is stronger and should remain the source of future work.

Recommended later sequence:

1. Document safe label candidates from legacy parser patterns.
2. Create synthetic/fake label examples.
3. Use redacted diagnostics and synthetic examples to improve new parser behavior.
4. Create a deletion impact plan.
5. Delete or archive `app/load_intake/` only in a dedicated cleanup block after tests and docs are updated.
