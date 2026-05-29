# Legacy Candidates

This document tracks files that look like legacy, prototype, or manual-integration code.

The goal is not to delete them quickly. The goal is to keep the current Foundation Hardening work honest by naming code paths that may not follow the current architecture.

Current rule:

```text
Do not remove legacy candidates until imports, runtime behavior, and replacement paths are understood.
```

---

## Current Status

The main active architecture is in:

```text
app/market_intelligence/
```

The current direction is documented in:

```text
docs/ARCHITECTURE.md
docs/FOUNDATION_HARDENING.md
docs/ROADMAP.md
docs/DEVELOPMENT_RULES.md
```

Latest verified baseline:

```powershell
py -m compileall app scripts main.py test_sheet_connection.py
py -m unittest discover -s tests -p "test_*.py"
```

Recent full test discovery passed with 545 tests.

---

## 1. `app/load_intake/`

Candidate status:

```text
LEGACY / PROTOTYPE CANDIDATE
```

Files:

```text
app/load_intake/broker_engine.py
app/load_intake/decision_engine.py
app/load_intake/importer.py
app/load_intake/market_models.py
app/load_intake/mileage.py
app/load_intake/parser.py
app/load_intake/reload_engine.py
app/load_intake/sheet_writer.py
app/load_intake/zone_engine.py
```

Why this is flagged:

- `app/load_intake/market_models.py` has a separate simple `MarketLoad` model.
- `app/market_intelligence/market_models.py` has the current main `MarketLoad` model.
- `app/load_intake/parser.py` mixes PDF parsing, mileage, zone scoring, broker scoring, final decision logic, reload scoring, and model creation.
- Current architecture says raw intake should parse and normalize data, not own final dispatch decisions.
- Several `load_intake` modules depend on optional/manual integrations such as `pypdf`, `gspread`, and Google credentials.

Recent safety work already done:

- `app/load_intake/parser.py` now imports `MarketLoad` safely as `Load`.
- `app/load_intake/mileage.py` no longer fails to import when `geopy` is not installed.
- `tests/test_load_intake_parser_import.py` protects parser import compatibility.

Do not do yet:

- Do not delete `app/load_intake/`.
- Do not merge this code into `market_intelligence` without a separate design step.
- Do not add new dependencies only to support this path unless the workflow is confirmed active.

Safe next steps:

1. Add import tests for each `app/load_intake` module.
2. Identify which scripts still depend on `app/load_intake`.
3. Decide whether the ratecon parser should become a clean intake-only parser.
4. Keep decision logic in the decision layer, not in raw intake.

---

## 2. Google Sheets Manual Integration Files

Candidate status:

```text
MANUAL INTEGRATION / MOVE CANDIDATE
```

Files:

```text
test_sheet_connection.py
scripts/append_document_test_load.py
scripts/import_ratecon.py
app/load_intake/sheet_writer.py
```

Why this is flagged:

- These files import `gspread`.
- They use Google service-account credentials.
- They can write to a real Google Sheet.
- `test_sheet_connection.py` is named like a test but behaves like a manual integration script.
- These files should not run as unit tests.

Do not do yet:

- Do not add `gspread` to `requirements.txt` only because these files exist.
- Do not run these scripts unless the dispatcher explicitly wants a manual integration check.
- Do not commit credentials, spreadsheet IDs, or runtime output.

Safe next steps:

1. Move `test_sheet_connection.py` to `scripts/manual_test_sheet_connection.py`.
2. Keep the standard compile command updated after the move.
3. Add a clear `if __name__ == "__main__":` entry point if missing.
4. Read spreadsheet IDs and credentials paths from environment/config where practical.

---

## 3. Optional External Dependencies

Candidate status:

```text
OPTIONAL DEPENDENCY REVIEW
```

Observed imports:

```text
gspread
google.oauth2.service_account
pypdf
geopy
```

Current recommendation:

```text
Do not expand requirements.txt until these workflows are confirmed active.
```

Reason:

- The current Foundation Hardening phase should avoid broadening runtime dependencies.
- Manual or legacy workflows can be isolated before dependencies are made project-wide.

Safe next steps:

1. Keep core unit tests independent from Google credentials.
2. Keep optional dependency imports from breaking core import checks.
3. Document any manual dependency setup separately if a manual workflow is retained.

---

## 4. Encoding / Mojibake Cleanup

Candidate status:

```text
CONTROLLED CLEANUP CANDIDATE
```

Known examples:

```text
вЂ”
в†’
вњ…
РІ...
```

Why this is flagged:

- README and some Telegram formatter strings contain mojibake.
- Telegram formatter and outbox parser tests may depend on current text shapes.
- Bulk replacement could break message parsing if done without tests.

Do not do yet:

- Do not mass-replace encoding artifacts across the repo in one patch.
- Do not change Telegram message text and outbox parsing in the same untested move.

Safe next steps:

1. Add tests around Telegram output and outbox parsing for intended clean text.
2. Clean one formatter family at a time.
3. Update outbox parsing together with the formatter it parses.
4. Keep README/docs cleanup separate from runtime Telegram text cleanup.

---

## 5. `.gitignore`

Candidate status:

```text
LOW-RISK CLEANUP CANDIDATE
```

Why this is flagged:

- `.gitignore` appears to contain duplicate patterns.
- Some sent-state/runtime file names are similar.

Safe next steps:

1. Normalize `.gitignore` into grouped sections.
2. Preserve all sensitive/runtime exclusions.
3. Run `git status --ignored` or targeted checks before and after cleanup.

---

## Recommended Order

Use small documentation and safety blocks:

1. Document legacy candidates. Completed by this file.
2. Move `test_sheet_connection.py` to a manual script path.
3. Add import tests for remaining `app/load_intake` modules.
4. Decide whether `app/load_intake/parser.py` should become a pure ratecon intake parser.
5. Clean `.gitignore`.
6. Plan encoding cleanup with tests.

Do not add DAT/API, dashboard, auto-booking, Observer, or live automation as part of this cleanup.
