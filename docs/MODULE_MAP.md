# Project Module Map

This map is an initial ownership/status inventory for high-risk and cleanup-relevant
modules. It is not yet exhaustive. Use `scripts/analyze_module_graph.py` to
compare this committed map against the current Python module graph before
deleting, moving, or refactoring code.

Status values:

- `active`: current supported runtime, workflow, or test infrastructure.
- `local_only`: explicit local/audit/review tooling. It must write generated
  artifacts only to ignored local paths such as `.local_outputs/` and must never
  commit private outputs.
- `test_only`: fixture or unittest support only.
- `compatibility`: legacy bridge or compatibility surface. Compatibility modules
  should not receive new product logic.
- `deprecated`: known old path. Deprecated does not mean removed immediately;
  prove replacement coverage and import safety first.
- `experimental`: gated/shadow/design surface. Experimental does not mean
  production-ready.

Cleanup notes:

- Deprecated modules require a separate removal PR with import graph proof.
- The old RateCon regex prototypes were removed after import graph proof; see
  `docs/archive/LEGACY_RATECON_REGEX_PROTOTYPES.md`.
- Local-only modules must not commit private values, raw extracted text, model
  outputs, PDFs, OCR artifacts, or audit packets.
- Compatibility modules should stay thin and should not become owners for new
  extraction, readiness, or decision logic.
- OCR and model-provider modules are visibility/design surfaces here, not
  approval to run OCR or any model.

| module_path | package_area | owner_layer | status | entrypoints | imported_by_summary | imports_summary | remove_after | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `main.py` | root | runtime entrypoint | active | direct app startup | invoked directly | `app/market_intelligence/market_snapshot.py` |  | Thin startup wrapper. |
| `app/market_intelligence/market_snapshot.py` | market_intelligence | market runtime | active | called by `main.py` | root entrypoint and market reports | market scoring, route fallback, opportunity helpers |  | Current market snapshot workflow owner. |
| `scripts/run_tests.py` | scripts | test infrastructure | active | CLI | developers and CI-equivalent local runs | unittest discovery only |  | Canonical local unittest runner. |
| `scripts/run_private_ratecon_measurement.py` | scripts | private RateCon local audit | local_only | CLI with explicit confirmation | manual private audit only | measurement orchestration, Google sync | keep shrinking | Public CLI wrapper. Parser/config/safety/output paths/safe report writer/review export/audit orchestration/review workbook helpers now live under `app/document_ai/measurement_cli/`; do not add new report/audit/review-export/workbook logic here. |
| `app/document_ai/measurement_cli/ratecon_private_args.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI | `scripts/run_private_ratecon_measurement.py`, tests | argparse definitions and CLI choices only | after measurement split is stable | Owns CLI parsing only. Must not own measurement business logic, PDF processing, OCR, model calls, report writers, or Google sync. |
| `app/document_ai/measurement_cli/ratecon_private_config.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI | `scripts/run_private_ratecon_measurement.py`, tests | parsed command value wrapper only | after measurement split is stable | Owns parsed command config only. Must not touch PDFs, write files, or run measurement. |
| `app/document_ai/measurement_cli/ratecon_private_safety.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI | `scripts/run_private_ratecon_measurement.py`, tests | preflight safety validation and optional provider dependency check | after measurement split is stable | Owns local/private safety validation only. Must not process PDFs, call OCR/model/cloud, write artifacts, or approve private outputs outside explicit local-only paths. |
| `app/document_ai/measurement_cli/ratecon_private_output_paths.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI and local writers | private measurement output writers, CLI wrapper, tests | path dataclass, stable filenames, local-only output path validation | after measurement split is stable | Owns output path and filename construction only. Must not write files, process PDFs, run measurement, call OCR/model/cloud, or own report/audit logic. |
| `app/document_ai/measurement_cli/ratecon_private_report_writers.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI and local writers | private measurement output compatibility wrapper, CLI wrapper, tests | safe JSON/CSV/Markdown/value-review report writers | after measurement split is stable | Owns safe report/export writer implementation only. Must preserve filenames/schemas, use centralized output paths, and must not run measurement, process PDFs, call OCR/model/cloud, sync Google Sheets, or own audit/review workbook logic. |
| `app/document_ai/measurement_cli/ratecon_private_review_exports.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI and local review exports | stop review packet compatibility wrapper, CLI wrapper, tests | simple review/export artifact writers and label helpers | after measurement split is stable | Owns simple local-only review/export artifact helpers only. Must preserve filenames/schemas, use centralized output paths, and must not run measurement, process PDFs, call OCR/model/cloud, sync Google Sheets, generate workbooks, or own full audit orchestration. |
| `app/document_ai/measurement_cli/ratecon_private_audit_orchestration.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI and local audits | CLI wrapper, audit writer modules, tests | optional audit/diagnostic task planning and writer orchestration | after measurement split is stable | Owns optional audit/diagnostic orchestration only. Must not own metric definitions, run measurement, process PDFs, call OCR/model/cloud, sync Google Sheets, generate workbooks, or change output filenames/schemas. |
| `app/document_ai/measurement_cli/ratecon_private_review_workbook.py` | document_ai | local_private_measurement_cli | local_only | library for private measurement CLI and local review workbook exports | CLI wrapper, review workbook writer, tests | review workbook export task planning, delegation, and console-safe labels | after measurement split is stable | Owns review workbook generation orchestration only. Must preserve workbook filename/layout/sheets/columns/styles, use centralized output paths, and must not run measurement, process PDFs, call OCR/model/cloud, sync Google Sheets, or change audit metrics. |
| `app/document_ai/ratecon_core_field_policy.py` | document_ai | readiness policy | active | library | measurement, benchmark, readiness, review flows | no external service imports | promote as single readiness policy owner | Count/status policy owner for RateCon field readiness. |
| `app/document_ai/ratecon_candidates.py` | document_ai | candidate model | active | library | candidate extraction and resolver flows | canonical field/schema helpers |  | Candidate schema/constants used by current pipeline. |
| `app/document_ai/ratecon_candidate_*` | document_ai | candidate pipeline | active | library | candidate extraction and context flows | candidate context and extraction helpers | consolidate candidate/status logic | RateCon candidate helper family. |
| `app/document_ai/field_candidate_provenance.py` | document_ai | candidate provenance | active | library | candidate generators and resolver tests | provenance and candidate builders |  | Provenance normalization owner. |
| `app/document_ai/field_candidate_generators.py` | document_ai | candidate generation | active | library | fake and private candidate workflows | candidate policies and stop/rate helpers | consolidate with candidate status cleanup | Current generator registry/profile owner. |
| `app/document_ai/field_candidate_resolver.py` | document_ai | candidate resolution | active | library | document pipeline, tests, review workflows | resolver policies, stop/rate/load helpers |  | Resolution and review-required status owner. Do not lower thresholds casually. |
| `app/document_ai/ratecon_rate_money_safety.py` | document_ai | rate money safety | active | library | resolver and rate candidate flows | money normalization and safety guards | consolidate rate-money logic | Central rate money safety helper. |
| `app/document_ai/load_identifier_candidates.py` | document_ai | load identifier candidates | active | library | generators and audits | candidate provenance | consolidate load identifier logic | Current load identifier candidate helper. |
| `app/document_ai/ratecon_load_table_safety.py` | document_ai | load table safety | active | library | resolver and table candidate flows | load table safety heuristics | consolidate load identifier logic | Safety checks for table-derived load identifiers. |
| `app/document_ai/ratecon_canonical_fields.py` | document_ai | field constants | active | library | candidate/resolver/policy modules | no external services |  | Canonical field naming surface. |
| `app/document_ai/ratecon_schema.py` | document_ai | schema | active | library | parser and review flows | standard library only |  | Structured RateCon payload schema helpers. |
| `app/document_ai/ratecon_document_pipeline.py` | document_ai | document extraction pipeline | active | library | architecture tests, private measurement | candidates, templates, resolver, artifacts |  | Current document AI pipeline assembly. |
| `app/document_ai/ratecon_field_resolution.py` | document_ai | field resolution bridge | active | library | document pipeline | resolver and canonical fields |  | Bridge around candidate resolution output. |
| `app/document_ai/ratecon_review_workbook.py` | document_ai | local review exports | local_only | library | private measurement, Sheets review sync | CSV review row builders |  | Local review workbook row generation. |
| `app/document_ai/ratecon_gold_labels.py` | document_ai | benchmark labels | local_only | library | benchmark and review tooling | JSON label parsing |  | Local benchmark label helper. Never auto-edit gold labels. |
| `app/document_ai/ratecon_hybrid_contract.py` | document_ai | hybrid/manual contract | local_only | library | hybrid benchmark and manual workflow | schema validation only |  | Manual/hybrid result contract. Not production extraction. |
| `app/document_ai/ratecon_model_assisted_contract.py` | document_ai | model-assisted contract | experimental | library | stub/eval wrappers | hybrid contract validation | after provider-governance decision | Contract only. No live model provider. |
| `app/document_ai/ratecon_model_provider_*` | document_ai | provider governance | experimental | library | disabled provider registry and CLI | provider config validation | after provider-governance decision | Disabled-by-default provider scaffolding. Not runtime approval. |
| `app/document_ai/ratecon_local_provider_*` | document_ai | provider governance | experimental | library | fixture readiness/evidence/design tooling | contracts and sanitized fixtures | after provider-governance decision | Governance/review scaffolding only. Cannot unblock providers. |
| `app/document_ai/ocr_provider_contract.py` | document_ai | OCR contract | experimental | library | shadow OCR diagnostics | standard library only | after OCR status decision | Contract for optional local OCR diagnostics. Not production approval. |
| `app/document_ai/tesseract_ocr_provider.py` | document_ai | OCR provider | experimental | library | optional local shadow diagnostics | optional local OCR dependencies | after OCR status decision | Optional local OCR provider. Do not run on private PDFs without explicit approval. |
| `app/document_ai/ratecon_ocr_candidate_policy.py` | document_ai | OCR candidate policy | experimental | library | private measurement OCR candidate controls | policy constants | after OCR status decision | Shadow OCR candidate policy surface. |
| `app/document_ai/ocr_stop_*` | document_ai | OCR stop reconstruction | experimental | library | shadow OCR stop diagnostics | geometry/table reconstruction helpers | after OCR status decision | Shadow OCR reconstruction helpers. |
| `app/document_ai/layout_*` | document_ai | layout pipeline | experimental | library | private measurement, fake layout demos, diagnostics | layout providers, adapters, proximity, candidates | after layout status decision | Shadow/layout candidate pipeline. Not a production migration. |
| `app/document_ai/pdfplumber_layout_*` | document_ai | layout provider | experimental | library | optional local layout diagnostics | optional pdfplumber dependency | after layout status decision | Optional local layout provider/settings. |
| `app/document_ai/private_measurement.py` | document_ai | private local audit policy | local_only | library | private measurement orchestrator | output policy helpers | split private measurement orchestrator | Local-only safe measurement policy helper. |
| `app/document_ai/private_measurement_*` | document_ai | private local audit | local_only | library | private measurement orchestrator | input/output/report/pipeline helpers | split private measurement orchestrator | Private local audit family. Never commit generated outputs. |
| `app/document_ai/private_template_*` | document_ai | private template local audit | local_only | library | private template review workflows | redaction, overlay, pattern helpers | after template governance decision | Private template helpers. Never commit private templates. |
| `app/document_ai/broker_templates.py` | document_ai | broker templates | active | library | document pipeline and private measurement | template parsing and scoring contracts |  | Public sanitized template registry model. |
| `app/document_ai/broker_template_*` | document_ai | broker templates | active | library | candidate extraction and registry flows | template matching/scoring/extraction |  | Broker-template support family. Avoid broker-specific regex additions without separate review. |
| `app/document_ai/candidate_fusion.py` | document_ai | candidate fusion | active | library | private measurement and document pipeline | candidate provenance | consolidate candidate/status logic | Candidate merge/fusion helper. |
| `app/document_ai/operational_fusion.py` | document_ai | candidate fusion | active | library | document pipeline | operational candidate helpers | consolidate candidate/status logic | Operational field fusion helper. |
| `app/document_ai/normalized_stops.py` | document_ai | stop normalization | active | library | resolver and stop helpers | stop normalization policies | consolidate stop status logic | Stop normalization owner. |
| `app/document_ai/structured_stop_values.py` | document_ai | stop normalization | active | library | resolver and tests | structured stop value helpers | consolidate stop status logic | Structured stop comparison surface. |
| `app/document_ai/stop_*` | document_ai | stop pipeline | active | library | candidate/resolver/review flows | stop association, provenance, spans, review helpers | consolidate stop status logic | Stop pipeline family. Some files are review/local helpers. |
| `app/document_ai/rate_candidate_*` | document_ai | rate candidates | active | library | candidate extraction, forensics | rate equivalence and forensics | consolidate rate-money logic | Rate candidate helper family. |
| `app/document_ai/rate_conflict_audit.py` | document_ai | rate review audit | local_only | library | private measurement audit scripts | rate candidate helpers | consolidate rate-money logic | Local-only rate conflict audit. |
| `app/document_ai/rate_fusion.py` | document_ai | rate candidates | active | library | candidate flows | rate candidate helpers | consolidate rate-money logic | Rate candidate fusion helper. |
| `app/document_ai/ratecon_shadow_audit.py` | document_ai | shadow audit | local_only | library | private measurement shadow reports | document pipeline output summaries |  | Local-only shadow audit reporting. |
| `app/document_ai/ratecon_shadow_root_cause_analysis.py` | document_ai | shadow audit | local_only | library | tests and local diagnostics | resolver and provenance helpers |  | Local-only root-cause diagnostics. |
| `app/document_ai/candidate_coverage_*` | document_ai | local coverage audit | local_only | library | private measurement and coverage scripts | candidate coverage helpers | after measurement split | Local-only coverage audit helper family. |
| `app/document_ai/classification_audit.py` | document_ai | local coverage audit | local_only | library | private measurement reports | classification counts | after measurement split | Local-only classification audit helper. |
| `app/document_ai/core_field_gap_analysis.py` | document_ai | local coverage audit | local_only | library | private measurement reports | core field policy helpers | after field policy promotion | Local-only field gap analysis. |
| `app/document_ai/load_identifier_coverage_audit.py` | document_ai | local coverage audit | local_only | library | private measurement reports | load identifier helpers | consolidate load identifier logic | Local-only load identifier coverage audit. |
| `app/document_ai/load_identifier_source_line_audit.py` | document_ai | local coverage audit | local_only | library | private measurement reports | load identifier helpers | consolidate load identifier logic | Local-only load identifier source-line audit. |
| `app/document_ai/load_identity_forensics.py` | document_ai | local coverage audit | local_only | library | private measurement reports | load identifier helpers | consolidate load identifier logic | Local-only load identity forensics. |
| `app/document_ai/dispatcher_review_table.py` | document_ai | local review exports | local_only | library | review table scripts/tests | review row builders |  | Review CSV/table output helper. |
| `app/document_ai/local_review_analysis.py` | document_ai | local review analysis | local_only | library | review output analysis | local review parsers |  | Local-only review output analysis. |
| `app/document_ai/review_feedback_*` | document_ai | review feedback | local_only | library | feedback import/target scripts | review issue taxonomy |  | Local feedback workflow support. |
| `app/document_ai/review_issue_taxonomy.py` | document_ai | review feedback | active | library | review and feedback flows | constants only |  | Shared review issue taxonomy. |
| `app/document_ai/measurement_integrity.py` | document_ai | measurement audit | local_only | library | private measurement reports | count/status checks |  | Local-only measurement integrity checks. |
| `app/document_ai/pdf_triage.py` | document_ai | PDF triage | active | library | fake tests and private measurement | PDF triage contract/artifact helpers | after OCR status decision | Triage only. Private PDF processing remains local-only and explicit. |
| `app/document_ai/pdf_triage_contract.py` | document_ai | PDF triage | active | library | triage and OCR contracts | constants only | after OCR status decision | Route/status constants for triage. |
| `app/document_ai/pdf_extraction_artifact.py` | document_ai | PDF artifact | active | library | document artifact extraction | PDF artifact helpers | after OCR status decision | Artifact container helper. Does not approve private PDF processing. |
| `app/document_ai/text_artifacts.py` | document_ai | text artifacts | active | library | document artifact flows | standard library only |  | Text artifact helper. |
| `app/integrations/google_sheets_review.py` | integrations | local review sync | local_only | library | explicit review sync scripts | review workbook and local config | after review-sync governance decision | Review sync adapter. Must not own business decisions or secrets. |
| `app/integrations/google_sheets_review_preflight.py` | integrations | local review sync | local_only | library | review sync preflight scripts | Sheets review config checks | after review-sync governance decision | Local preflight helper. |
| `app/market_intelligence/intake/ratecon_pdf_dry_run.py` | market_intelligence | legacy intake dry-run | compatibility | library | old dry-run scripts | intake PDF text extraction | after document_ai migration proof | Compatibility path. Do not add new extraction logic. |
| `app/market_intelligence/intake/ratecon_text_dry_run.py` | market_intelligence | legacy intake dry-run | compatibility | library | old dry-run scripts | intake parser contracts | after document_ai migration proof | Compatibility path. Do not add new extraction logic. |
| `app/market_intelligence/intake/pdf_text_extraction.py` | market_intelligence | legacy PDF text extraction | compatibility | library | old intake dry-runs | PDF text extraction dependency | after document_ai migration proof | Compatibility path only. |
| `tests/*` | tests | test suite | test_only | unittest | test discovery | test fixtures and assertions |  | Test files are not production modules. |
