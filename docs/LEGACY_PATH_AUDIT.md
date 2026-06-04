# Legacy RateCon Extraction Path Audit

This audit checks whether any older RateCon, PDF, parser, Telegram, or
DispatchCase path bypasses the current candidate/template/resolver/validation
architecture.

Current official RateCon extraction path:

1. PDF triage produces safe document metadata.
2. Extraction artifacts describe readiness without raw text.
3. Safe text artifacts feed candidate extraction.
4. Generic field candidates are generated with evidence and confidence.
5. Broker templates can adjust candidate confidence.
6. The conservative resolver selects, marks missing, or marks review/conflict.
7. `RateConfirmationIntake` drafts are built from resolved fields only.
8. Validation gates readiness.

Parsers, PDF helpers, broker templates, scripts, and Telegram adapters must not
create DispatchCases, write DispatchCase events, make accept/reject decisions,
or hide low-confidence/missing critical fields.

## Audit Scope

Searches covered:

- direct `parse_ratecon` / `read_ratecon` / `import_ratecon` paths
- direct PDF extraction and regex-to-final-field assignment
- raw text logging/saving
- Google Sheets writes
- DispatchCase creation or linking from extraction
- Telegram modules calling parser/resolver directly
- DecisionEngine imports inside `app/document_ai`
- `ACCEPT` / `REJECT` emissions inside parser/template/resolver modules
- real broker names in fake template fixtures
- docs that describe older parser-first flows

## Findings

| File or module | Current behavior | Risk | Action | Priority |
| --- | --- | --- | --- | --- |
| Legacy direct RateCon PDF/regex prototypes | `scripts/import_ratecon.py` and `scripts/read_ratecon.py` were removed after import graph proof showed zero non-test dependents. | Recreating them would bypass candidate/template/resolver/validation. | Do not recreate direct PDF-to-Google-Sheets or direct regex-to-final-field scripts. See `docs/archive/LEGACY_RATECON_REGEX_PROTOTYPES.md`. | Critical |
| `app/market_intelligence/intake/pasted_text_parser_adapter.py` | Uses label/regex heuristics to produce parser-shaped fields for dry-run/manual intake helpers. | It performs direct field assignment and can be mistaken for the official production extraction layer. Current usage is dry-run/testing oriented and does not create cases. | Keep temporarily as a compatibility/manual dry-run adapter. Document as superseded for production by candidate/template/resolver flow. Future work should route digital text artifacts through `app/document_ai` candidate extraction instead. | Medium |
| `app/market_intelligence/intake/ratecon_text_dry_run.py` | Runs pasted text through the legacy parser adapter, normalizes to intake, builds summaries, and optionally creates link candidates. | It can produce `READY_FOR_REVIEW` status from dry-run parser output, but does not create/link cases or write events. | Keep as manual dry-run only. Docs and help text should continue to emphasize no private text storage and no DispatchCase creation. | Medium |
| `app/market_intelligence/intake/ratecon_pdf_dry_run.py` | Extracts local PDF text with the local helper, feeds text into the text dry-run pipeline, and returns safe summaries. | It still depends on the legacy pasted-text adapter after extraction; not an official production RateCon extraction path. | Keep as local/private dry-run only. Do not use it as the canonical production parser. Future private reruns should compare it with the candidate/template path after that path is wired for local measurement. | Medium |
| `app/market_intelligence/intake/pdf_text_extraction.py` | Local-only `pypdf` extraction helper returns text to caller and metadata, with `private_text_saved=False`. | It returns raw text in memory by design for local dry-runs. If misused, callers could print or persist private text. | Keep local-only. Do not expose through fake CLIs or official candidate pipeline without safe artifact handling. | Medium |
| `scripts/run_private_ratecon_pdf_dry_run.py` | Local private PDF dry-run prints anonymized summaries only and does not print raw text. | Reads private PDFs locally; still uses the old pasted-text dry-run path after extraction. | Keep as private/local measurement script. It is not production extraction and should not be imported by fake-only scripts. | Low |
| `scripts/export_private_ratecon_value_review_csv.py` | Writes local private extracted values to an ignored CSV for user visual review. | Intentionally may contain private values locally. Risk is accidental commit or misuse as shared report. | Keep local-only with gitignored default output. Do not print values in chat/docs/tests. | Medium |
| `scripts/export_ratecon_dry_run_csv.py` | Exports safe dry-run summaries and imports the private PDF dry-run report builder. | Safe summary path, but it couples export to private dry-run helpers. | Keep for current local workflow. Consider later refactor to accept safe summary JSON from either dry-run path. | Low |
| `scripts/run_private_ratecon_redacted_diagnostics.py` | Local private PDF diagnostics that print safe signal counts only. | Reads private PDFs locally but avoids raw text output. | Keep as local diagnostic only. | Low |
| `scripts/run_private_ratecon_layout_diagnostics.py` | Local private PDF layout diagnostics with sanitized placeholders only. | Reads private PDFs locally but avoids raw text output. | Keep as local diagnostic only. | Low |
| `scripts/run_private_ratecon_pdf_extraction_inventory.py` | Local private PDF extraction inventory prints extraction metadata only. | Reads private PDFs locally but avoids raw text output. | Keep as local diagnostic only. | Low |
| `scripts/run_fake_ratecon_candidate_extraction.py` | Fake/anonymized candidate and template pipeline CLI. | No private path found. | Keep as the safe demonstration CLI. | Low |
| `app/document_ai/*` | Candidate, template, resolver, PDF triage, and artifact contracts do not import Telegram, DecisionEngine, DispatchCase, event writers, or Google Sheets. | No bypass found. | Keep and continue protecting with architecture boundary tests. | Low |
| `tests/fixtures/document_ai/broker_templates/*` | Fake broker templates use mock names and fake MC numbers. | No real broker templates found in fixture scan. | Keep. | Low |
| `README.md` and older docs | Some sections still mention historical scripts, Google Sheets, `data/ratecons/`, or parser dry-run commands. | Could confuse future work about the official pipeline. | Reconcile in the doc consistency mini-block so the current pipeline doc is the source of truth. | Medium |

## Direct DispatchCase and Decision Bypass Review

No current `app/document_ai` module creates a DispatchCase, writes case events,
imports Telegram modules, imports the DecisionEngine, or emits dispatch
recommendations such as `ACCEPT` or `REJECT`.

The only DispatchCase-related intake helper found in the current RateCon area is
`app/market_intelligence/intake/case_link_candidate.py`, which is report-only and
produces link candidates instead of mutations.

## Parser Status Review

The old intake status helpers still support `READY_FOR_REVIEW`, `MISSING_FIELDS`,
and `NEEDS_CHECK` for manual/dry-run intake summaries. This is acceptable for
existing dry-run tools, but it is not a replacement for the newer
`RateConfirmationIntake` validation gate. Production RateCon extraction should
use candidate/template/resolver output plus validation, not parser status alone.

## Raw Text and Private Data Review

Safe current patterns:

- `app/document_ai` extraction artifacts do not store raw text by default.
- PDF triage results do not include raw text.
- Fake candidate extraction CLI does not print full fixture text.
- Private PDF dry-run scripts print anonymized summaries.

Legacy or local-only risk areas:

- The old direct RateCon PDF/regex prototypes were removed; see
  `docs/archive/LEGACY_RATECON_REGEX_PROTOTYPES.md`.
- `scripts/export_private_ratecon_value_review_csv.py` writes private values to a
  gitignored local CSV by design.

## Actions

Immediate small actions:

1. Do not recreate direct RateCon PDF/regex prototypes.
2. Add or preserve help text on private/local scripts that says local-only,
   ignored outputs only, and no raw text in reports.

Later refactor actions:

1. Replace parser-adapter-based private dry-run measurement with a candidate
   extraction measurement path once fake/anonymized candidate coverage is stronger.
2. Refactor safe CSV export to accept safe summary input from either old dry-run
   or new candidate/template measurement.
3. Update docs so `docs/RATECON_PIPELINE_CURRENT_STATE.md` is the canonical
   implementation map.

## Conclusion

The new `app/document_ai` pipeline is not currently bypassing architectural
boundaries. The remaining risks are old standalone scripts and manual dry-run
helpers that predate candidate/template/resolver validation. They should remain
clearly marked as non-production or local-only until they are replaced by a
measured candidate-based private rerun path.
