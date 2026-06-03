# RateCon Full Root-Cause Audit v1

Date: 2026-06-03

Scope: independent architecture and root-cause audit of the current Rate
Confirmation processing path. This report is sanitized. It uses aggregate
metrics, document-shape descriptions, and public source links only. It does not
include private document text, private PDF content, private addresses, private
money values, private load identifiers, gold labels, audit JSONL, OCR TSV/text,
or review packet values.

## Executive Summary

Verdict: partially. The current direction is right for safe measurement,
load-number diagnostics, rate diagnostics, evaluator cleanup, and conservative
review gates. It is not right for stop extraction. The stop work is now
optimizing layers that cannot reliably recover the visual relationships needed
for high-accuracy pickup and delivery extraction.

The measured state is decisive:

- Load number shadow result: 25 correct, 1 wrong, 5 missing.
- Total carrier rate shadow result: 26 correct, 3 wrong, 2 missing.
- High-confidence wrong load/rate: 1 / 0.
- Pickup selected stops: 0 exact, 17 partial, 5 wrong, 3 missing, denominator
  25.
- Delivery selected stops: 0 exact, 12 partial, 5 wrong, 4 missing, denominator
  21.
- Stop evaluator/gold blocker count: 0 code/evaluator issues, 0 true gold
  review rows, 0 patch rows.
- Trusted-source fusion safety: 0 safe opportunities after provenance repair
  and trusted-source filtering.

The load/rate path is producing useful shadow diagnostics because those fields
are often scalar values with context gates. Stops are different. They require
visual grouping: role, location, date, time, facility/address/city fragments,
stop index, and section boundaries must be linked as one semantic row or block.
The current rule/candidate/resolver stack can describe why that is hard, but it
has not proved it can solve it.

The blunt answer: continuing to add stop regexes, threshold tweaks, broad
fusion, or more resolver tuning is not the right direction. The next serious
architecture move should be a hybrid document-understanding and human-review
path, with the existing deterministic stack retained as validation,
provenance, audit, and low-risk scalar extraction infrastructure.

## Current Measured System State

| Area | Current result | Interpretation |
|---|---:|---|
| Load number | 25 correct / 1 wrong / 5 missing | Good enough for continued shadow hardening, not production auto-accept. |
| Total carrier rate | 26 correct / 3 wrong / 2 missing | Useful shadow result; remaining wrongs are money-context issues. |
| High-confidence wrong load/rate | 1 / 0 | Gates are useful, but load still has one risky case. |
| Pickup stops | 0 exact / 17 partial / 5 wrong / 3 missing | No exact or dispatch-usable selected stops. |
| Delivery stops | 0 exact / 12 partial / 5 wrong / 4 missing | Better partial coverage, still not safe. |
| Stop evaluator issues | 0 | The current stop problem is not evaluator serialization. |
| True gold review | 0 | Current gold labels are not the blocker. |
| Patch template rows | 0 | No gold-label patch should be applied. |
| All-source fusion safety | 0 safe / 35 risky / 6 unsafe / 17 not possible | Broad fusion is unsafe. |
| Trusted-source fusion safety | 0 safe / 35 risky / 0 unsafe / 23 not possible | Noise filtering removed unsafe sources, but did not create safe fusion. |
| Row/block proof | 0 proven / 12 probable / 17 not proven | The system still cannot prove visual stop rows. |

## Stage 1 - Document Ingestion Audit

### What Is Working

The ingestion stack has the correct privacy posture and a mostly correct routing
shape:

- PDF triage separates digital text, OCR-needed, unsupported, encrypted, and
  manual-review cases.
- Private measurement is local-only and aggregate-first.
- Shadow audit flow avoids raw private values by default.
- Supplemental and non-RateCon classification prevents every PDF from inflating
  RateCon missing-field counts.
- OCR is optional and explicit, not a mandatory production dependency.

### Findings

1. Document types are identified well enough for measurement, but not well
   enough to make field extraction safe. Classification prevents obvious
   denominator pollution. It does not solve the harder problem: many valid
   RateCons are visually structured in ways native text cannot preserve.

2. Scanned and image-based PDFs are handled at the right routing stage.
   Triage correctly treats empty text as an OCR/manual-review routing problem,
   not as a worthless document. OCR is now measurable and helped scalar fields.

3. Some PDFs are fundamentally incompatible with native-text parsing for stop
   extraction. A text layer can contain the right words while losing row,
   column, role, and boundary relationships. Native text may be sufficient for
   load IDs or rates, but insufficient for stops.

4. Information is lost before extraction begins when the pipeline collapses
   visual structure into linear text. The later provenance repair fixed metadata
   retention, but it cannot restore visual relationships that were never
   captured as rows or blocks.

5. BOL/POD/non-RC separation is directionally correct. The remaining issue is
   not document eligibility. It is semantic layout understanding inside
   extraction-relevant RateCons.

### Ingestion Verdict

Ingestion is not the main blocker. The major failure happens after route
selection, when visual documents are represented as candidate fragments instead
of document objects with reliable table/section semantics.

## Stage 2 - Text / OCR / Layout Extraction Audit

### Measured Facts

- OCR improved load/rate candidate evidence.
- OCR stop evidence increased structured stop candidate counts in prior runs.
- Stop exact/dispatch-usable selected output remains at zero.
- Trusted-source fusion still has zero safe opportunities.
- Row/block proof remains zero after OCR geometry, TSV column reconstruction,
  provenance repair, and trusted-source filtering.

### Findings

1. Extracted text is usable for some scalar fields. Load numbers and carrier
   rates benefited from OCR, layout, and stricter context gates.

2. Extracted text is not reliably usable for stops. Stop extraction requires
   association, not just detection. The system can see many words and many
   candidate fragments, but still cannot prove which location/date/time belongs
   to which pickup or delivery role.

3. Broker PDFs are often structurally incompatible with plain-text parsing.
   Pickup/delivery information is spread across tables, compact rows, PU/SO
   blocks, right-column date/time cells, and footers/instructions/payment
   sections that look similar in linear text.

4. OCR solved part of the scanned-PDF gap but created noisy candidates for
   stops. OCR adds text and geometry. It does not automatically create semantic
   stop rows.

5. Geometry improved observability more than extraction quality. OCR geometry,
   TSV columns, and row diagnostics made the failure measurable. They did not
   produce safe stop fusion.

6. Row/block proof remains zero because current logic is still reconstructing
   visual semantics from fragments. It lacks a strong document-understanding
   layer that can say, with evidence, "this role label, location cell, date
   cell, and time window are one stop row."

### Layout/OCR Verdict

OCR and layout are necessary but not sufficient. The current implementation is
still a deterministic fragment pipeline. For stops, that is the wrong dominant
representation.

## Stage 3 - Parsing / Candidate Generation Audit

### Field Failure Pattern

| Field group | Current status | Main failure mode |
|---|---|---|
| Load number | Mostly useful shadow result | Some gold values not generated; one wrong selection. |
| Carrier rate | Mostly useful shadow result | Wrong money context for a small number of cases. |
| Stops | Weak selected output | Visual association failure, noisy candidates, legacy fallback ambiguity. |

### Findings

1. Load/rate improved because their candidate spaces are smaller and easier to
   gate. Money context, header identity, and OCR fill-missing policies are
   coherent for scalar fields.

2. Stops did not improve enough because stop extraction is not scalar. A stop
   is a structured object with role, sequence, location, date, time, and
   optional facility/address/contact/reference components. Current parsers
   still often treat these as separable field candidates.

3. Several assumptions are wrong:
   - More stop candidates are not necessarily better.
   - More geometry is not enough without semantic row/block proof.
   - Legacy fallback coverage is not neutral; it actively pollutes
     disambiguation.
   - Resolver scoring cannot compensate for weak or ambiguous candidate
     generation.

4. Legacy fallback is useful as a diagnostic coverage source, but harmful as a
   trusted stop-disambiguation source. Current diagnostics show legacy fallback
   noise remains a major multiple-location blocker. It should be quarantined
   from any future stop fusion or auto-selection path.

5. The system is forcing semi-structured visual documents into a rigid parser
   architecture. That architecture is adequate for some scalar extraction. It is
   not adequate for high-accuracy stops.

### Candidate Verdict

Candidate generation is now less of a missing-evidence problem and more of a
document-understanding problem. More line-window parsing will add complexity
without solving row/block semantics.

## Stage 4 - Resolver / Review Gate / Evaluator Audit

### What Is Working

- Conservative resolver behavior prevents aggressive unsafe promotion.
- Review gates correctly keep risky stop evidence out of production-like
  selected output.
- Candidate-best, draft groups, and private sidecars are now useful diagnostic
  views.
- Stop usability tiers, known-absent handling, and gold completeness reporting
  make the evaluator trustworthy enough for decisions.

### Findings

1. Resolver tuning is no longer the high-leverage stop path. The selected stop
   output is weak because the underlying candidates cannot prove the required
   visual associations. Lowering thresholds would convert ambiguity into wrong
   output.

2. The system has been over-indexing on scoring. The blocker is document
   understanding, not candidate ranking.

3. Review gates are accurately reflecting risk. They should remain strict.

4. Gold/evaluator metrics are now trustworthy enough to stop blaming the
   evaluator. Code/evaluator issues are zero, true gold review is zero, and
   patch rows are zero.

5. Current stop output must remain shadow-only. OCR stop candidates, structured
   stop candidates, draft stops, fusion drafts, candidate-best groups, and
   legacy fallback stop values should not become production auto-accept.

### Resolver Verdict

The resolver is doing the right conservative thing. Do not tune thresholds to
hide candidate weakness.

## Stage 5 - Architecture Review

### Bottlenecks

- Visual stop row/block understanding is missing.
- Candidate fragments outnumber reliable semantic stop objects.
- Legacy fallback is mixed into diagnostics and creates ambiguity unless
  explicitly tiered away.
- Multiple stop assemblers and reconstructors create overlapping partial
  evidence with inconsistent trust.
- Broad fusion remains unsafe because it cannot prove a single row/block.

### Complexity and Technical Debt

The stop stack has accumulated useful diagnostics, but also too many
incremental extraction layers:

- line-window stop parsing;
- block assembly;
- geometry assembly;
- TSV column reconstruction;
- sidecar serialization;
- source inventory;
- provenance repair;
- location disambiguation;
- trusted-source tiering.

Most of these are useful as audit tools. They are not proving a path to safe
automatic stop extraction.

### Useful Diagnostic Infrastructure

| Keep | Why |
|---|---|
| PDF triage and classification | Correct denominator and routing foundation. |
| Safe private measurement | Necessary to evaluate private corpora without leaking values. |
| Gold/evaluator tooling | Now trustworthy; prevents false engineering targets. |
| OCR dependency and provider checks | Useful local-only scanner path. |
| Load/rate ranking profiles | Producing measurable scalar-field gains. |
| Source inventory and provenance reports | Good diagnostic visibility. |
| Review packets and known-absent logic | Prevents unnecessary gold-label work. |
| Trust-tier diagnostics | Separates useful evidence from legacy/noisy evidence. |

### Quarantine or Stop Extending

| Quarantine / stop extending | Reason |
|---|---|
| Broad stop fusion | Zero safe opportunities after provenance and trusted-source work. |
| Legacy fallback for stop disambiguation | Useful for coverage, harmful for trusted association. |
| More stop regex passes | Adds fragments, not row/block proof. |
| Resolver threshold tuning | Would increase wrong selected stops. |
| Broker-specific stop regexes | Scales poorly and increases maintenance risk. |
| Production migration of current stops | Exact and dispatch-usable selected stops are zero. |

### Architecture Verdict

Rule-based parsing should no longer be the dominant strategy for stops. It can
remain the deterministic validation and low-risk scalar extraction layer.
Continuing to optimize stop candidate layers is now diminishing returns. The
system is becoming more complex without proportional stop accuracy gains.

## Stage 6 - Failure Contribution Estimate

These estimates are for the remaining extraction failures, especially stops.
They are estimates, not directly measured percentages.

| Failure source | Estimated contribution | Confidence | Evidence |
|---|---:|---|---|
| Table/geometry reconstruction failure | 25% | High | Row/block proof is 0 proven; trusted-source fusion_safe is 0. |
| Architecture limitation | 20% | Medium-high | Candidate/resolver layers expose ambiguity but do not recover visual semantics. |
| Parser/candidate generation failure | 15% | Medium | Stops remain partial/wrong/missing despite many candidate generators. |
| Legacy fallback noise | 10% | High | Legacy fallback noise is a named multiple-location blocker. |
| OCR failures/noise | 8% | Medium | OCR helps scalar fields but adds noisy stop candidates. |
| Native text extraction failure | 7% | Medium | Some PDFs lose row/column relationships in linear text. |
| Resolver/ranking failure | 5% | Medium | Load has one selection issue; stops are mainly candidate-quality limited. |
| Field taxonomy/mapping failure | 4% | Medium | Stop object components are not always represented as one semantic unit. |
| Bad/scanned PDFs | 4% | Medium | OCR-needed cases exist, but OCR is no longer the whole blocker. |
| Evaluator/gold issues | 2% | High | Current code/evaluator issues, true gold review, and patch rows are zero. |

## Stage 7 - Industry Approach Comparison

Web access was available. This comparison uses current public documentation and
papers:

- [Google Cloud Document AI overview](https://docs.cloud.google.com/document-ai/docs/overview)
  describes document processing as OCR, layout extraction, classification,
  splitting, form parsing, custom extraction, pretrained processors, and
  prediction review.
- [Amazon Textract AnalyzeDocument](https://docs.aws.amazon.com/textract/latest/APIReference/API_AnalyzeDocument.html)
  exposes feature types for tables, forms, queries, signatures, and layout, and
  includes human-in-the-loop configuration.
- [Azure AI Document Intelligence model overview](https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/model-overview?preserve-view=true&view=doc-intel-4.0.0)
  separates OCR/read, layout, prebuilt models, custom extraction, and custom
  classification.
- [LayoutLM](https://arxiv.org/abs/1912.13318) and
  [LayoutLMv3](https://arxiv.org/abs/2204.08387) show the industry shift from
  text-only NLP toward joint text/layout/image document understanding.
- [Donut](https://arxiv.org/abs/2111.15664) is an OCR-free visual document
  understanding architecture that shows another path: direct document image to
  structured output.

### Approach Comparison

| Approach | What works | What is outdated or insufficient |
|---|---|---|
| Pure regex/rule parsing | Cheap, auditable, good for simple scalar fields. | Brittle on visual tables, multi-column pages, and broker variation. |
| Template-based extraction | Useful for stable document families and field labels. | Requires many templates and still needs layout association. |
| OCR plus layout parser | Necessary for scans and table evidence. | Still insufficient if layout output is not converted into semantic stop rows. |
| OCR plus visual document understanding | Better fit for variable visual docs. | Needs model evaluation, privacy controls, and validation. |
| LLM/VLM-assisted extraction | Handles variation and semantic grouping better. | Can hallucinate; must be constrained and review-gated. |
| Commercial Document AI | Provides OCR, layout, custom extraction, classification, and review tooling. | Costs money and requires privacy/vendor assessment. |
| Human-in-the-loop review | Essential for low-confidence or high-value exceptions. | Not free; must be designed so humans review only ambiguous cases. |

### Production-Grade Pattern

Production-grade document AI systems usually do not rely on one regex parser.
They combine:

1. Document classification and splitting.
2. OCR/read and layout extraction.
3. Custom or pretrained extraction models.
4. Deterministic validation and business-rule checks.
5. Confidence thresholds and review queues.
6. Human correction capture.
7. Continuous evaluation on labeled corpora.

For freight-tech RateCons, broker variation is the normal case. A scalable
system needs document-family understanding and visual association, not only
field regexes.

## Stage 8 - Three Solution Paths

### Option A - No Additional Cost

Use the existing codebase and open-source tools only.

What should change:

- Freeze selected stop extraction changes.
- Keep load/rate shadow hardening where risk is measurable.
- Quarantine legacy fallback from stop disambiguation/fusion.
- Build a smaller, explicit document-shape taxonomy from sanitized aggregate
  diagnostics.
- Use pdfplumber/Tesseract only for local measurement and high-trust row/table
  diagnostics.
- Add human review workflow for stops instead of trying to auto-accept.

What should be removed or quarantined:

- Broad stop fusion.
- Stop resolver threshold tuning.
- Broker-specific stop regex additions.
- Legacy fallback as a trusted source for stop association.

Expected success:

- Load/rate: realistic incremental gains may continue.
- Stops: high exact accuracy is unlikely. Expect useful partial/review-ready
  evidence, not reliable automated stop extraction.

Implementation difficulty: medium. It is mostly simplification, reporting, and
review workflow.

Risk: this path may never reach high stop extraction accuracy. It is the lowest
cost path, but it is also the most constrained.

### Option B - Low-Cost AI-Assisted Approach

Allow small monthly spend or local/open-source model experimentation.

Architecture:

- Keep current deterministic pipeline for triage, safety, validation, and
  scalar fields.
- Route hard/low-confidence stop documents to an AI-assisted extractor.
- Test local or low-cost visual document understanding models on private local
  corpora.
- Use model output only as review draft, never auto-accept.
- Validate extracted stops with deterministic checks: role consistency,
  date/time normalization, payment/instruction exclusion, and source evidence.

Cost estimate range: roughly tens to a few hundreds of dollars per month for
small private pilots, depending on local GPU availability, hosted model usage,
or low-volume document-AI API calls. This must be confirmed with actual usage
and vendor pricing before production.

Expected improvement: likely better review-usable stop drafts and fewer manual
blank reviews. Exact production auto-accept should still wait for measured
evidence.

Implementation complexity: medium-high. Requires privacy controls, prompt/schema
design or model integration, validation, and review UI/sidecar plumbing.

Privacy considerations:

- Prefer local models first for sensitive PDFs.
- If using hosted services, require explicit opt-in, redaction where possible,
  vendor review, retention controls, and audit logging.

### Option C - Production-Grade / Highest Accuracy

Assume budget is available.

Recommended architecture:

- Commercial or best-in-class OCR/document AI for layout and table extraction.
- Custom RateCon extraction model or VLM/document-understanding model tuned on
  labeled private examples.
- Deterministic validation layer from the current codebase.
- Human-in-the-loop review for low-confidence, conflicting, or high-impact
  fields.
- Feedback capture that updates training/evaluation sets.
- Audit trail with source snippets/regions stored privately, not in Git.
- Separate production acceptance thresholds by field type.

Expected accuracy:

- Scalar load/rate: high with enough data and validation.
- Stops: substantially better than current rule pipeline, but still review
  required for ambiguous broker layouts, damaged scans, multi-stop ambiguity,
  and missing source values.

Scalability:

- Better than rule-only if labels and review feedback are maintained.
- Requires ongoing model/vendor management and evaluation.

Maintenance model:

- Treat RateCon extraction as a document-AI product, not a parser script.
- Maintain a labeled benchmark, model versioning, review queues, and field-level
  acceptance policies.

## Stage 9 - Final Verdict

### 1. Verdict

Partially. The current work was correct up through measurement, OCR diagnostics,
load/rate gating, evaluator cleanup, and provenance analysis. It is now the
wrong direction for stops if it continues as incremental rule/geometry/fusion
optimization.

### 2. What We Got Right

- Privacy-safe local measurement.
- Classification-first denominators.
- Conservative resolver and review gates.
- OCR as optional/local, not mandatory production dependency.
- Gold/evaluator cleanup before blaming extraction.
- Source inventory and provenance repair.
- Trusted-source analysis that proved broad fusion is unsafe.

### 3. Where the Wrong Turn Happened

The wrong turn was continuing to treat stops as a candidate-ranking problem
after the diagnostics showed that the system could not prove row/block
relationships. Once fusion_safe stayed zero after provenance repair and
trusted-source filtering, the next step should have shifted from extraction
patches to architecture review.

### 4. What Should Stop Immediately

- Stop resolver threshold tuning.
- Broad stop fusion.
- More line-window stop regex passes.
- Broker-specific stop regexes.
- Treating legacy fallback as trusted stop evidence.
- Any production migration of current stop output.
- Asking users to patch gold labels when patch rows are zero.

### 5. What Should Continue

- Load/rate shadow hardening with strict gates.
- OCR dependency checks and optional local OCR measurement.
- Safe private measurement and aggregate reporting.
- Gold/evaluator and known-absent handling.
- Source inventory/provenance diagnostics as audit infrastructure.
- Human review packet/reporting, but focused on actual review needs.

### 6. What Should Replace The Current Strategy

A hybrid document-understanding architecture should replace rule-first stop
extraction:

- deterministic triage/classification;
- OCR/layout extraction;
- document-understanding model or commercial processor for visual stop rows;
- deterministic validation and safety gates;
- review-only drafts for uncertain stops;
- human-in-loop correction and continuous evaluation.

### 7. Recommended Next 30-Day Plan

1. Freeze selected stop extraction behavior.
2. Write a sanitized benchmark protocol for RateCon document families.
3. Pick a small private evaluation subset with labels already considered
   trustworthy.
4. Evaluate two low-cost document-understanding approaches and one commercial
   document-AI option on local/private data only.
5. Define a review-draft schema for model output with strict validation and no
   auto-accept.
6. Quarantine legacy fallback from any future trusted stop association logic.
7. Keep load/rate shadow work only where metrics remain stable and gates stay
   conservative.

### 8. Recommended 90-Day Architecture Plan

1. Build a hybrid extraction prototype: deterministic scalar fields plus
   document-understanding stop drafts.
2. Add a human review workflow for stop drafts with correction capture.
3. Maintain a private labeled benchmark and field-level acceptance dashboard.
4. Define production field policies:
   - load/rate may progress toward selective auto-accept only after more
     evidence;
   - stops remain review-required until exact and dispatch-usable metrics are
     materially better.
5. Retire or quarantine stop modules that only generate noisy fragments.
6. Keep the current deterministic system as validation, audit, fallback, and
   privacy-safe measurement infrastructure.

## Final Answer To The Core Question

Are we currently moving in the correct direction, or are we spending time
optimizing layers that will never achieve the extraction accuracy we need?

Answer: partially, and for stops the current incremental direction should stop.
The system is not one small rule or threshold away from high stop accuracy. It
has reached the point where more deterministic stop layers mostly improve
explainability, not extraction quality. The correct next direction is a hybrid
document-understanding and review-first architecture, with the current pipeline
kept for safe measurement, validation, provenance, and scalar-field extraction.
