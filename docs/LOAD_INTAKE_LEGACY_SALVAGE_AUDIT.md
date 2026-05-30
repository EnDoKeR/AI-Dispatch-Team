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

## Safe Legacy Parser Label Candidates

The legacy parser contains useful label concepts, but not reusable implementation. These candidates may inform synthetic examples and redacted diagnostics only.

Do not copy private document text into tests. Do not wire legacy parser code into runtime. Do not reuse old parser-to-decision behavior.

### Broker Label Candidates

Safe label ideas:

- `TRUCKLOAD RATE CONFIRMATION`;
- `Broker`;
- `Broker Name`;
- header/title area before carrier or contact details.

Notes:

- broker identity may appear in a header rather than a clean `Broker:` field;
- future parser examples should use fake names such as `FAKE BROKER LLC`;
- diagnostics should count label/header signals, not return broker names.

### Broker MC Label Candidates

Safe label ideas:

- `MC`;
- `MC #`;
- `MC Number`;
- `Broker MC`;
- `Motor Carrier`.

Notes:

- legacy code did not robustly extract broker MC;
- this should be represented with synthetic examples before parser changes.

### Shipper / Pickup Label Candidates

Safe label ideas:

- `Shipper Information`;
- `Pickup`;
- `Pick Up`;
- `Pickup Location`;
- `Address`;
- `Origin`.

Notes:

- legacy parser used `Shipper Information` plus `Address` concepts;
- new diagnostics should count label signals only, never addresses.

### Consignee / Delivery Label Candidates

Safe label ideas:

- `Consignee Information`;
- `Delivery`;
- `Deliver To`;
- `Delivery Location`;
- `Address`;
- `Destination`.

Notes:

- legacy parser used `Consignee Information` plus `Address` concepts;
- new diagnostics should count label signals only, never addresses.

### Total / Rate Label Candidates

Safe label ideas:

- `TOTAL`;
- `Total Rate`;
- `Rate`;
- `USD`;
- `Linehaul`;
- `Fuel Surcharge`;
- `Accessorials`.

Notes:

- accessorial and linehaul labels should not automatically become total rate;
- parser changes should distinguish total/rate from accessorial notes with synthetic examples.

### Pickup / Delivery Time Label Candidates

Safe label ideas:

- `Pick Up Time`;
- `Pickup Time`;
- `Pickup Date`;
- `Pickup Window`;
- `Delivery Time`;
- `Delivery Date`;
- `Delivery Window`;
- `Appointment`.

Notes:

- appointment windows should usually require review until parser confidence is clear.

### Load / Reference Label Candidates

Safe label ideas:

- `Load #`;
- `Load Number`;
- `Reference`;
- `Reference #`;
- `Shipment ID`;
- `Order #`;

Notes:

- reference values must never be printed in diagnostics;
- parser tests should use fake values such as `FAKE-REF-001`.

### Carrier Label Candidates

Safe label ideas:

- `Carrier Name`;
- `Carrier`;
- `Truck`;
- `Driver`.

Notes:

- current intake records do not need carrier/driver identity as mandatory fields;
- private carrier/driver names should not be committed.

### Trailer / Equipment Label Candidates

Safe label ideas:

- `Trailer Type/Size`;
- `Trailer Type`;
- `Equipment`;
- `Flatbed`;
- `Conestoga`;
- `Step Deck`;

Notes:

- equipment labels are useful for parser coverage and future synthetic tests.

### Commodity / Weight Label Candidates

Safe label ideas:

- `Commodity Description`;
- `Commodity`;
- `Product`;
- `Description`;
- `Total Weight`;
- `Weight`;
- `WT`;
- `LBS`;

Notes:

- legacy code had a narrow commodity pattern; do not reuse that pattern directly;
- create synthetic examples for generic commodity/weight labels first.

## Salvage Policy

Safe to salvage:

- label vocabulary;
- generic label families;
- structural lesson that real RateCons may place values after section headers rather than one-line `Label: Value` pairs.

Not safe to salvage:

- raw regex implementation without tests;
- private text snippets;
- PDF reader logic;
- old mileage, zone, broker, reload, score, or final decision behavior;
- Google Sheets writer behavior;
- direct parser-to-`MarketLoad` construction.

## Deletion Impact Audit

This section documents what would break if `app/load_intake/` were deleted today. This is an audit only; no files are deleted in this block.

## Imports That Would Break

The following tests directly import `app/load_intake` modules:

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
```

These tests would fail immediately if the folder were deleted.

`tests/test_load_intake_imports.py` currently imports:

```text
app.load_intake.broker_engine
app.load_intake.decision_engine
app.load_intake.importer
app.load_intake.market_models
app.load_intake.mileage
app.load_intake.parser
app.load_intake.reload_engine
app.load_intake.sheet_writer
app.load_intake.zone_engine
```

It also protects the current lazy Google Sheets behavior in `sheet_writer.py`.

`tests/test_load_intake_parser_import.py` imports:

```text
app.load_intake.parser
```

It verifies that `parser.Load` still points to the active `MarketLoad` compatibility constructor.

## Scripts Impact

`scripts/import_ratecon.py` does not import `app/load_intake`, but it contains a separate legacy manual PDF-to-Google-Sheets flow with hardcoded local paths and external dependencies. Deleting `app/load_intake/` would not directly break this script, but this script should remain outside the new intake architecture and should be audited separately before use.

`scripts/manual_test_sheet_connection.py` does not depend on `app/load_intake/`; it is a separate manual Google Sheets connectivity check.

## Documentation Impact

Current docs that mention `app/load_intake/` would need updates if the folder is deleted:

```text
docs/ARCHITECTURE_AUDIT.md
docs/FOUNDATION_NEXT_TARGET_DECISION.md
docs/LOAD_INTAKE_BOUNDARY_REVIEW.md
docs/LEGACY_CANDIDATES.md
docs/INTAKE_RECORD_MODEL.md
docs/PRIVATE_RATECON_PARSER_AUDIT.md
docs/PRIVATE_RATECON_SAMPLE_CHECKLIST.md
docs/MANUAL_PASTED_TEXT_PARSER_ADAPTER_DESIGN.md
docs/INTAKE_JSON_REPOSITORY_POLICY.md
docs/LOAD_INTAKE_LEGACY_SALVAGE_AUDIT.md
```

Many newer tests mention `load_intake` only as a forbidden import string. Those tests should remain because new intake modules must not import the legacy path.

## Google Sheets Manual Docs And Tests

Google Sheets behavior is still represented in:

```text
app/load_intake/sheet_writer.py
scripts/manual_test_sheet_connection.py
tests/test_manual_sheet_connection_script.py
tests/test_load_intake_imports.py
```

Deleting `app/load_intake/` would require removing or rewriting the `sheet_writer.py` compatibility checks in `tests/test_load_intake_imports.py`. It would not remove the separate manual sheet connection script.

No active intake foundation should depend on Google Sheets. If Google Sheets work returns later, it should be an adapter/integration design block, not a legacy reuse.

## Runtime Impact

Current active runtime and foundation modules do not import `app/load_intake/`.

Deletion should not affect:

- current `app/market_intelligence/intake/` helpers;
- redacted RateCon diagnostics;
- private PDF dry-run CLIs;
- DecisionEngine helpers/reports;
- Event Timeline helpers/reports;
- Telegram runtime behavior;
- DispatchCase runtime behavior.

Deletion would affect:

- legacy import compatibility tests;
- docs that describe legacy state;
- any untracked/manual local use of `app/load_intake/importer.py` or `app/load_intake/parser.py`.

## Recommended Deletion Steps If Approved Later

Deletion should be a dedicated cleanup block, not mixed with parser improvements.

Suggested deletion sequence:

1. Confirm no active runtime imports:

```powershell
rg -n "app\.load_intake|from app.load_intake|import app.load_intake" app scripts tests docs README.md
```

2. Decide whether to keep a short archived note in docs.
3. Remove or rewrite:

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
```

4. Delete:

```text
app/load_intake/
```

5. Update docs:

```text
docs/LEGACY_CANDIDATES.md
docs/LOAD_INTAKE_BOUNDARY_REVIEW.md
docs/FOUNDATION_NEXT_TARGET_DECISION.md
docs/ROADMAP.md
docs/LOAD_INTAKE_LEGACY_SALVAGE_AUDIT.md
```

6. Run compileall, full unittest discovery, `git diff --check`, and `git status`.

## Deletion Recommendation

Do not delete yet.

Recommended next safe step:

```text
migrate only safe label aliases into synthetic diagnostics/parser tests first, then plan deletion
```

Why:

- useful label ideas exist;
- deletion would break current legacy import tests;
- the deletion cleanup is safe but should be explicit and focused;
- parser improvements should happen through synthetic/fake examples, not legacy runtime reuse.

## Closeout Decision

Options evaluated:

1. delete `app/load_intake/` in a dedicated cleanup block;
2. keep folder but mark archived/legacy;
3. migrate only safe label aliases into new redacted diagnostics/parser tests;
4. run private redacted diagnostics locally and share safe summary;
5. anonymized synthetic RateCon scenario expansion from observed issues.

Decision:

```text
keep temporarily, salvage label aliases through synthetic examples, then plan deletion cleanup
```

Why:

- safe label vocabulary exists and has already started moving into synthetic diagnostics examples;
- legacy runtime behavior is unsafe for reuse;
- active intake architecture does not depend on the legacy folder;
- deletion would currently break two legacy import tests;
- deleting the folder should be a later focused cleanup with test/docs updates.

Recommended next target:

```text
anonymized synthetic RateCon scenario expansion from observed parser gaps and safe legacy label ideas
```

Recommended later target:

```text
parser field extraction improvements based on synthetic/fake patterns
```

Recommended later cleanup:

```text
app/load_intake deprecation/deletion block
```

Deletion cleanup should include:

- removing or rewriting `tests/test_load_intake_imports.py`;
- removing or rewriting `tests/test_load_intake_parser_import.py`;
- updating legacy docs;
- confirming no active runtime imports;
- running full validation.

Still forbidden:

- reusing legacy parser directly;
- reusing old decision, reload, zone, mileage, broker, or Google Sheets behavior;
- committing private text;
- improving parser patterns from private text directly;
- creating/linking DispatchCases or writing events.

## Pre-deletion Import/Reference Audit

This section records the final reference audit before deleting `app/load_intake/`.

Searches run:

```powershell
rg -n "app\.load_intake|app/load_intake|load_intake|parse_ratecon|import_ratecon|append_load|test_load_intake" app scripts tests docs README.md
```

## References Found

### Active legacy package references

```text
app/load_intake/parser.py
app/load_intake/importer.py
app/load_intake/sheet_writer.py
```

These are internal references inside the legacy package and will be removed when the package is deleted.

### Legacy-only tests to remove

```text
tests/test_load_intake_imports.py
tests/test_load_intake_parser_import.py
```

These tests exist only to protect old import compatibility. They should be removed in the deletion block.

### Tests to keep

Many current intake tests include `load_intake` only as a forbidden import string. These should stay because they protect new modules from importing the deleted legacy path.

Examples:

```text
tests/test_intake_package_boundaries.py
tests/test_intake_record_repository.py
tests/test_intake_record_status.py
tests/test_intake_record_report.py
tests/test_parser_confidence.py
tests/test_pasted_text_parser_adapter.py
tests/test_ratecon_field_diagnostics.py
tests/test_ratecon_parser_coverage.py
```

These are not dependencies on the legacy package.

### Manual Google Sheets script to keep

```text
scripts/manual_test_sheet_connection.py
tests/test_manual_sheet_connection_script.py
```

This manual script does not import `app/load_intake/`. It should remain unless a separate Google Sheets cleanup block is approved.

### Legacy standalone script outside package

```text
scripts/import_ratecon.py
```

This script does not import `app/load_intake/`, but it is old manual PDF-to-Google-Sheets logic with hardcoded paths and external dependencies. Deleting `app/load_intake/` does not break it. It should remain untouched in this cleanup unless a separate manual-script cleanup is approved.

### Docs to update after deletion

Docs with legacy-retained wording include:

```text
docs/ARCHITECTURE_AUDIT.md
docs/FOUNDATION_NEXT_TARGET_DECISION.md
docs/LOAD_INTAKE_BOUNDARY_REVIEW.md
docs/LEGACY_CANDIDATES.md
docs/ROADMAP.md
docs/LOAD_INTAKE_LEGACY_SALVAGE_AUDIT.md
```

Other docs mention legacy `app/load_intake` as a forbidden import or historical boundary. Those can remain if they still describe architectural guardrails accurately.

## Active Runtime Import Finding

No active `app/market_intelligence/intake/` module imports `app/load_intake/`.

No current private PDF/text dry-run helper imports `app/load_intake/`.

No DecisionEngine, Event Timeline, Telegram, DispatchCase, or reload-watch foundation module should need a code change for this deletion.

## Final Deletion Checklist

Before deletion:

- safe label ideas preserved in docs;
- synthetic legacy label examples exist;
- redacted diagnostics tests cover preserved labels;
- no private text is committed;
- no runtime imports depend on the legacy package.

Deletion block should:

1. delete `app/load_intake/`;
2. delete `tests/test_load_intake_imports.py`;
3. delete `tests/test_load_intake_parser_import.py`;
4. keep `tests/test_manual_sheet_connection_script.py`;
5. keep current `app/market_intelligence/intake/`;
6. keep current private RateCon docs/templates and ignore rules;
7. run compileall, focused import/search checks, full unittest discovery, diff check, and status.

Post-deletion docs cleanup should:

- state that the legacy package was removed;
- state that useful label vocabulary was preserved in synthetic examples;
- state that old Google Sheets, parser-to-`MarketLoad`, and scoring flows are intentionally not part of the architecture.

## Safe Label Preservation Verification

Safe label knowledge is preserved outside `app/load_intake/` in:

```text
tests/fixtures/legacy_ratecon_label_examples.py
tests/test_legacy_ratecon_label_examples.py
docs/RATECON_REDACTED_FIELD_DIAGNOSTICS.md
```

The synthetic fixture/test coverage includes the required legacy label styles:

```text
TRUCKLOAD RATE CONFIRMATION
Shipper Information
Consignee Information
TOTAL: USD $
Pick Up Time
Delivery Time
Load #
Carrier Name
Trailer Type/Size
Commodity Description
Total Weight
```

The examples use fake values only, including:

```text
FAKE BROKER LLC
MC000000
FAKE-REF-001
Fake City, ST
```

The redacted diagnostics tests verify:

- synthetic label fixtures import;
- fixture text contains legacy label styles;
- diagnostics recognizes expected label categories;
- diagnostics output does not return fake values, which also protects against returning private values later.

This means legacy label knowledge is safe to keep even after the legacy package is deleted.
