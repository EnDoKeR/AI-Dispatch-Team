# RateCon Extraction Strategy

This document defines the target future Rate Confirmation extraction architecture. It does not implement OCR, Vision AI, external APIs, Google Sheets, DispatchCase writes, or parser behavior changes.

## Strategic Correction

The current RateCon extraction issue is architectural, not just a regex problem.

Observed safe summary:

- some PDFs have no extractable text and need triage plus OCR/Vision fallback later;
- some PDFs have extractable text and label signals, but the field parser does not reliably turn those signals into structured fields;
- endlessly patching one parser with regex will make the system brittle and hard to replay.

Future extraction should be candidate-based, evidence-based, confidence-aware, and review-gated.

## Target Hybrid Pipeline

```text
Document received
-> DocumentRecord created
-> PDF triage
-> digital extraction with PyMuPDF/pdfplumber later
-> OCR fallback later
-> broker/document classification
-> candidate extraction
-> broker templates
-> template-aware field resolution
-> optional Vision AI fallback later
-> normalization
-> validation
-> confidence/evidence
-> human review if needed
-> RateConfirmationIntake
-> DispatchCase draft
-> DecisionEngine
-> Event Timeline
```

## Current Position

Current project support:

- dependency-free document AI contracts;
- safe PDF triage metadata and fake-only triage CLI;
- extraction artifacts built from triage without raw text;
- safe text artifacts for fake/anonymized candidate extraction;
- candidate extraction contracts for RateCon field candidates;
- dependency-free candidate generators for money, identity/reference, stops, and operational details;
- conservative field resolution contracts and resolver;
- RateConfirmationIntake draft builder from resolved candidates;
- fake-only candidate extraction CLI;
- fake/anonymized broker template contracts, registry, matcher, template-aware scoring, and regression matrix;
- hard-layout resolver tests for repeated headers, rate/accessorial traps, table-like stops,
  header-only broker identity, typed references, conflicting appointments, and buried requirements;
- local-only `pypdf` extraction helper;
- private PDF extraction inventory CLI;
- private PDF dry-run CLI;
- redacted field diagnostics;
- redacted layout diagnostics;
- local private value-review CSV;
- synthetic/anonymized parser scenarios;
- RateCon core-field policy.

Current project does not yet have:

- OCR;
- Vision AI;
- real broker templates;
- typed evidence object for every production field;
- DispatchCase creation from RateCon intake;
- live document upload handling;
- external paid extraction calls.

## DocumentRecord

Future DocumentRecord should identify the document without storing raw private text by default.

Planned fields:

- `document_id`
- `document_type`
- `source`
- `received_at`
- `file_label`
- `sha256` or local fingerprint if needed
- `page_count`
- `privacy_classification`
- `storage_policy`
- `linked_case_id`
- `warnings`

Rules:

- private PDFs stay local and ignored unless a separate storage policy is approved;
- tracked docs/tests must use fake document records only;
- document records do not create cases by themselves.

## PDF Triage

PDF triage should decide the route before extraction is attempted.

Current triage behavior and thresholds are documented in `docs/PDF_TRIAGE.md`.

Triage output:

- `page_count`
- `char_count`
- `chars_per_page`
- `has_text_layer`
- `likely_image_based`
- `mixed_pdf`
- `encrypted`
- `broken`
- `recommended_route`

Recommended routes:

- `DIGITAL_TEXT`
- `OCR_NEEDED`
- `VISION_REVIEW_CANDIDATE`
- `UNSUPPORTED`
- `MANUAL_REVIEW`

If extraction returns empty text:

- do not pretend parsing failed;
- mark extraction as `EMPTY_TEXT`;
- route to PDF extraction refinement, OCR audit, or manual review;
- do not create parser fixtures from private PDFs.

## Extraction Artifacts

ExtractionArtifact should summarize how text or structure was obtained.

Planned fields:

- `artifact_id`
- `document_id`
- `method`
- `pages`
- `char_count`
- `text_summary`
- `word_count`
- `block_count`
- `table_count`
- `warnings`
- `artifact_version`

Rules:

- do not store raw private text by default;
- use local ignored output only for private value review;
- tracked fixtures should be fake/anonymized.

## Candidate Extraction

Extractors should produce candidates, not final truth immediately.

Canonical ownership: `app/document_ai/field_candidate_provenance.py` owns the
candidate contract for new document AI extraction candidates. Legacy
`ratecon_candidates.py` and related RateCon candidate modules remain
compatibility surfaces until a separate behavior-pinned cleanup proves safe.

FieldCandidate fields:

- `field_name`
- `raw_value`
- `normalized_value`
- `confidence`
- `confidence_reasons`
- `source`
- `evidence_ref`
- `warnings`

ExtractedFieldEvidence fields:

- `evidence_id`
- `document_id`
- `page`
- `source_method`
- `shape_or_label`
- `redacted_context`
- `confidence`

Rules:

- evidence can include safe/redacted shape, not raw private text;
- conflicting candidates should remain visible;
- low-confidence critical candidates should route to review.
- candidate extraction does not create DispatchCases;
- candidate extraction does not emit dispatch recommendations;
- regex is one candidate source, not final assignment.

Current fake/anonymized candidate extraction is documented in
`docs/RATECON_CANDIDATE_EXTRACTION.md`.

Run:

```powershell
py scripts/run_fake_ratecon_candidate_extraction.py
```

## Broker And Document Classification

Classification should happen before broker-specific extraction.

Examples:

- Rate Confirmation
- Revised Rate Confirmation
- BOL
- POD
- Lumper Receipt
- Invoice
- Detention Proof
- Layover Proof
- TONU Proof
- Unknown

Broker templates should:

- live in focused modules;
- use fake/anonymized tests;
- produce candidates and evidence;
- avoid direct dispatch decisions.

Current fake/anonymized broker template behavior is documented in
`docs/RATECON_BROKER_TEMPLATES.md`.

The exact implemented pipeline checkpoint is documented in
`docs/RATECON_PIPELINE_CURRENT_STATE.md`. If this strategy document and the
checkpoint ever disagree, update the checkpoint first because it is the
implementation map.

## Normalization And Validation

Normalization converts candidates into RateConfirmationIntake or a similar domain contract.

Validation must compute:

- missing critical fields;
- low-confidence critical fields;
- conflicting candidate fields;
- review-required reasons;
- field evidence coverage.

The validation layer must compute missing and needs-check fields from the
normalized intake shape. It must not trust caller-provided `missing_fields`,
`needs_check_fields`, or `status` alone.

Critical fields are defined by current policy in `docs/RATECON_CORE_FIELD_POLICY.md`, while future full RateConfirmationIntake may contain additional optional and document/accounting fields.

## Human Review Gate

Human review is required when:

- critical fields are missing;
- critical fields are low confidence;
- multiple critical candidates conflict;
- PDF triage says OCR/manual review is needed;
- extraction route is unsupported;
- case creation from intake is requested.

Low-confidence RateCon intake must not automatically create or finalize a DispatchCase.

## DecisionEngine And Event Timeline

DecisionEngine should consume normalized, validated evidence. It should not consume raw PDF text.

Future Event Timeline append points:

- `document_received`
- `pdf_triaged`
- `text_extracted`
- `ocr_fallback_needed`
- `rate_con_parsed`
- `rate_con_review_required`
- `field_corrected`
- `document_linked`
- `case_created`
- `ai_evaluated`

Event writes require a separate explicit implementation block.

## OCR And Vision AI Policy

No external OCR or Vision AI API is added in this mini-block.

Future OCR/Vision must be:

- gated by PDF triage;
- used only when deterministic/local extraction is insufficient;
- privacy-reviewed;
- cost-aware;
- testable with fake/anonymized artifacts;
- never called for every document by default.

## Privacy Rules

- Do not commit private PDFs.
- Do not commit raw extracted text.
- Do not commit private field values.
- Do not create tracked fixtures from private documents.
- Do not print broker/customer/contact names, MCs, addresses, emails, phone numbers, reference numbers, appointment details, or private snippets in reports.
- Local private value-review CSVs must stay in ignored folders.
