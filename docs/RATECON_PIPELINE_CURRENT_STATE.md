# RateCon Pipeline Current State

This document records the official current Rate Confirmation extraction pipeline
as implemented. It is a control checkpoint, not a new feature.

## Official Implemented Flow

```text
PDF triage
-> extraction artifact
-> safe text artifact
-> generic candidates
-> broker template matching
-> template-aware scoring
-> conservative resolver
-> RateConfirmationIntake draft
-> validation
```

The pipeline is evidence-first and review-gated. It does not create DispatchCases,
write events, call Telegram, call DecisionEngine, or decide accept/reject/review.

## Step Owners

| Step | Owner modules | Current status |
| --- | --- | --- |
| PDF triage | `app/document_ai/pdf_triage.py`, `app/document_ai/pdf_triage_contract.py` | Implemented safe metadata route |
| Extraction artifact | `app/document_ai/extraction_artifacts.py`, `app/document_ai/pdf_extraction_artifact.py` | Implemented safe metadata artifact |
| Local PDF text extraction | `app/market_intelligence/intake/pdf_text_extraction.py` | Local dry-run helper only |
| Safe text artifact | `app/document_ai/text_artifacts.py` | Implemented for fake/anonymized candidate extraction |
| Generic candidates | `app/document_ai/ratecon_candidates.py`, `app/document_ai/ratecon_candidate_generators.py`, `app/document_ai/ratecon_candidate_extraction.py` | Implemented for fake/anonymized text artifacts |
| Broker template contract/registry | `app/document_ai/broker_templates.py`, `app/document_ai/broker_template_registry.py` | Implemented for fake/anonymized JSON templates |
| Private broker template overlay | `app/document_ai/broker_template_registry.py`, `scripts/run_private_ratecon_measurement.py` | Implemented as explicit local-only overlay support |
| Redacted pattern collection | `app/document_ai/private_template_pattern_collector.py`, `app/document_ai/private_template_pattern_families.py`, `scripts/run_private_ratecon_template_pattern_collection.py` | Implemented for safe local pattern grouping |
| Broker template matching | `app/document_ai/broker_template_matcher.py` | Implemented deterministic fake-template matcher |
| Template-aware scoring | `app/document_ai/broker_template_scoring.py`, `app/document_ai/broker_template_candidate_extraction.py` | Implemented candidate adjustment layer |
| Conservative resolver | `app/document_ai/ratecon_field_resolution.py` | Implemented generic and template-aware resolution |
| Intake draft | `app/document_ai/ratecon_intake_draft.py` | Implemented draft builder from resolved fields |
| Intake validation | `app/market_intelligence/intake/rate_confirmation_validation.py`, `app/market_intelligence/intake/rate_confirmation_intake.py` | Implemented validation and status gating |

## Implemented

- PDF triage contract and safe route selection.
- ExtractionArtifact metadata contract without raw text by default.
- Safe text artifact contract for fake/anonymized text.
- FieldCandidate and CandidateExtractionResult contracts.
- Generic candidate generators for:
  - money/rate vs accessorials;
  - broker identity and broker MC;
  - load number and typed references;
  - pickup/delivery location/date/time;
  - equipment, weight, commodity, special requirements, accessorial terms.
- BrokerTemplate contract, fake JSON fixtures, registry, matcher, and template-aware scoring.
- Conservative field resolver and template-aware resolver wrapper.
- Hard-layout resolver guards for multi-page terms, accessorial rate traps,
  table-like stops, header-only broker identity, typed references, conflicting
  appointment times, and buried special requirements.
- RateConfirmationIntake draft builder from resolved fields.
- Validation that computes missing and needs-check fields.
- Fake-only candidate/template dry-run CLI.
- Local-only private measurement harness that reports safe aliases, counts,
  field statuses, blocker categories, and aggregate summaries.
- Local-only private broker template overlay loading with safe template aliases.
- Redacted template pattern collection and local-only template draft skeletons.

## Scaffolding Only

- PDF triage route values for future OCR/Vision decisioning.
- ExtractionArtifact method values for future `pdfplumber`, OCR, or Vision.
- Broker template structure for future real broker templates.
- Event Timeline append points described in docs only.
- DispatchCase creation from validated intake is not implemented.

## Not Implemented Yet

- OCR.
- Vision AI.
- Cloud extraction APIs.
- Production private RateCon parser path.
- Real broker templates.
- Production real broker templates.
- Broker template privacy review workflow beyond local-only overlay measurement.
- Candidate field resolver for difficult layout pairing beyond current fake fixtures.
- DispatchCase creation from RateCon extraction.
- Event writes from document extraction.
- Telegram business logic for RateCon extraction.
- Live DAT/API integration.

## Test Coverage

Current relevant tests include:

- PDF triage and artifacts:
  - `tests/test_pdf_triage_contract.py`
  - `tests/test_pdf_triage.py`
  - `tests/test_pdf_extraction_artifact.py`
  - `tests/test_fake_pdf_triage_dry_run_cli.py`
- Text artifacts and generic candidates:
  - `tests/test_text_artifacts.py`
  - `tests/test_ratecon_candidates_contract.py`
  - `tests/test_ratecon_candidate_extraction.py`
  - `tests/test_ratecon_money_candidates.py`
  - `tests/test_ratecon_identity_reference_candidates.py`
  - `tests/test_ratecon_stop_candidates.py`
  - `tests/test_ratecon_operational_detail_candidates.py`
- Broker templates:
  - `tests/test_broker_templates_contract.py`
  - `tests/test_broker_template_fixtures.py`
  - `tests/test_broker_template_registry.py`
  - `tests/test_broker_template_matcher.py`
  - `tests/test_broker_template_scoring.py`
  - `tests/test_broker_template_candidate_extraction.py`
  - `tests/test_broker_template_resolver_context.py`
  - `tests/test_broker_template_intake_context.py`
  - `tests/test_broker_template_regression_matrix.py`
  - `tests/test_ratecon_hard_layout_regression_matrix.py`
- Intake and validation:
  - `tests/test_ratecon_intake_draft.py`
  - `tests/test_rate_confirmation_intake.py`
  - `tests/test_rate_confirmation_validation.py`
- Boundaries:
  - `tests/architecture/test_architecture_boundaries.py`

## Fake-Only Scripts

- `py scripts/run_fake_pdf_triage_dry_run.py`
- `py scripts/run_fake_ratecon_candidate_extraction.py`

These scripts use fake/anonymized fixtures and should not be pointed at private
RateCons.

## Local Private Dry-Run Scripts

The following scripts exist for local-only private testing and must not commit or
print raw private text:

- `py scripts/private_ratecon_inventory.py`
- `py scripts/run_private_ratecon_pdf_extraction_inventory.py --limit 3`
- `py scripts/run_private_ratecon_pdf_dry_run.py --limit 3`
- `py scripts/run_private_ratecon_redacted_diagnostics.py --limit 3`
- `py scripts/run_private_ratecon_layout_diagnostics.py --limit 3`
- `py scripts/export_ratecon_dry_run_csv.py --limit 3`
- `py scripts/export_private_ratecon_value_review_csv.py --limit 3`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\path\to\private\ratecons" --confirm-private-local-run --write-json --write-csv --write-md`
- `py scripts/run_private_ratecon_template_pattern_collection.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --write-pattern-json --write-family-md --write-template-drafts`
- `py scripts/run_private_ratecon_measurement.py --input-dir "C:\Users\YOUR_NAME\Documents\RateCons" --confirm-private-local-run --limit 3 --private-template-dir ".local_private\broker_templates" --allow-private-template-overlay --write-json --write-csv --write-md`

Private value-review CSV output is local-only and ignored.

## Safety Rules

- Do not commit private PDFs.
- Do not commit private extracted text.
- Do not commit private field values.
- Do not create tracked fixtures from private documents.
- Do not add OCR or Vision AI without a separate approved block.
- Do not add cloud extraction APIs in this pipeline.
- Do not create DispatchCases from extraction output.
- Do not write DispatchCase events from extraction output.
- Do not call DecisionEngine from document extraction.
- Do not put extraction logic in Telegram modules.
- BrokerTemplate is not BrokerProfile or broker memory.
- Private broker templates must stay in ignored local paths and must not be
  committed.

## Known Limitations

- Some PDFs have no text layer and need future OCR/PDF route handling.
- Template-specific fixtures are fake and do not prove real broker coverage.
- Hard-layout behavior is tested on fake fixtures only and still needs safe
  private measurement before production claims.
- More fake layouts may be needed for unusual table extraction, repeated
  headers, and multi-page terms once safe measurement shows the next gaps.
- Template scoring adjusts candidates but does not guarantee final field resolution.
- Validation still gates readiness when fields are missing, low confidence, or conflicting.

## Next Recommended Block

Next safe block after private template overlay support:

```text
Run redacted private pattern collection, create local private template drafts, and compare safe baseline vs overlay measurement.
```

That block should still avoid OCR/Vision unless measurement shows deterministic
template/layout routes are insufficient.
