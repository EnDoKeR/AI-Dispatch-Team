# RateCon Hybrid Document Understanding Evaluation Plan v1

Date: 2026-06-03

Scope: planning, benchmark design, and local-only evaluation scaffolding for a
hybrid Rate Confirmation document-understanding path. This plan does not
implement AI extraction, cloud calls, OCR changes, production behavior changes,
selected stop changes, resolver threshold changes, broker-specific regexes, or
gold-label edits.

## Executive Summary

The full root-cause audit concluded that the current direction is only
partially correct. The deterministic shadow pipeline is useful for safe
measurement, load-number extraction, rate extraction, validation, provenance,
and review gates. It is not sufficient as the dominant stop-extraction strategy.

The next 30 days should evaluate hybrid document understanding for stops:

- keep deterministic extraction for scalar fields where it is already useful;
- move pickup/delivery stops to review-first hybrid drafts;
- compare local/open-source, OCR-plus-model, commercial document-AI, and manual
  fallback approaches without sending private documents anywhere by default;
- require auditable evidence for every proposed field;
- keep every hybrid stop review-required in phase 1.

Current baseline:

| Area | Baseline |
|---|---:|
| Load number | 25 correct / 1 wrong / 5 missing |
| Total carrier rate | 26 correct / 3 wrong / 2 missing |
| Pickup selected stops | 0 exact / 17 partial / 5 wrong / 3 missing |
| Delivery selected stops | 0 exact / 12 partial / 5 wrong / 4 missing |
| Stop production auto-accept | Not allowed |

The goal is not to replace the current pipeline immediately. The goal is to
measure whether a document-understanding path can produce safer, more complete
review drafts for stops than the current deterministic stop stack.

## Why Incremental Stop Extraction Is Frozen

Incremental stop extraction is frozen because the diagnostics are conclusive:

- stop exact selected matches remain zero;
- stop dispatch-usable selected matches remain effectively unavailable;
- current stop gold/evaluator issues are zero;
- patch template rows are zero;
- trusted-source fusion still has zero safe opportunities;
- row/block proof remains zero proven;
- main blockers are visual association, conflicting clusters, source
  unavailability, and legacy/noisy evidence.

More regexes, broader fusion, or lower thresholds would increase complexity and
risk without proving row/block understanding. Future stop work should be
review-first and document-understanding oriented.

## Deterministic Fields To Keep

These fields remain deterministic-first because the current system is already
producing measurable shadow value:

| Field | Current direction |
|---|---|
| `load_number` | Keep deterministic candidates, OCR fill-missing policy, and strict resolver gates. |
| `total_carrier_rate` | Keep money context gating and rate abstention policies. |
| Broker/carrier identity | Keep only where safe and evidence-backed; do not overfit broker-specific regexes. |
| Document classification | Keep deterministic RC vs supplemental/non-RC routing as the first gate. |

These fields can later consume hybrid evidence as a secondary signal, but the
30-day plan should not replace their current deterministic shadow path.

## Hybrid / Review-First Fields

These fields move to hybrid/review-first evaluation:

- pickup stops;
- delivery stops;
- facility;
- address;
- city;
- state;
- ZIP;
- date;
- time;
- appointment window.

Hybrid stop output must be review-required by default. It must not change
selected stop output, production output, or legacy output.

## Validation Gates

### 1. Document Classification Gate

Every document must be classified before extraction:

- rate confirmation;
- BOL/POD or supplemental document;
- unknown/manual review.

Non-RC BOL/POD documents must not be counted as failed RateCon extraction.

### 2. Critical Field Gate

The critical fields remain:

- load number;
- total carrier rate;
- pickup stops;
- delivery stops.

Hybrid output should be compared against current deterministic selected output,
candidate-best groups, and gold labels where local gold is available.

### 3. Stop Consistency Gate

Validators must check:

- pickup/delivery role separation;
- pickup before delivery when dates are available;
- no payment, instruction, footer, or legal text as location;
- no reference/contact-only rows as stop location;
- no cross-role fusion;
- no multiple conflicting locations/dates/times without review.

### 4. Evidence Gate

Every proposed field needs evidence:

- page number when available;
- source type;
- bounding box when available;
- redacted excerpt or source region reference;
- model/provider identity;
- confidence.

Fields without evidence are invalid as hybrid results.

### 5. Confidence / Review Gate

Any stop with uncertainty goes to human review. In phase 1, all stops go to
human review regardless of model confidence.

### 6. No-Auto-Accept Gate

No pickup or delivery stop may be auto-accepted during the hybrid evaluation.
The evaluation measures draft quality only.

## 30-Day Evaluation Plan

### Week 1 - Benchmark and Contract Setup

1. Finalize the hybrid extraction contract.
2. Define document-shape benchmark groups without private values.
3. Add local-only stub output and tests.
4. Decide the evaluation denominator and reporting schema.
5. Freeze selected stop extraction behavior.

### Week 2 - Candidate Approach Selection

Evaluate feasibility and privacy posture for:

- local open-source VLM/document model;
- OCR plus local LLM/VLM;
- commercial document AI;
- commercial OCR plus deterministic validator;
- manual-review-only fallback.

No private documents should be sent to external services during this planning
phase.

### Week 3 - Local Private Pilot

Run only local/manual-safe experiments:

- use existing private gold/eval summaries;
- generate hybrid result templates;
- manually inspect a small private sample locally if needed;
- validate whether evidence capture is possible for each benchmark group.

### Week 4 - Decision Report

Produce a decision report:

- approach comparison;
- stop draft coverage;
- unsafe draft rate;
- evidence completeness;
- review burden;
- estimated cost;
- privacy risk;
- recommendation for prototype or rejection.

## 90-Day Architecture Plan

### Days 31-60

- Prototype one selected hybrid approach.
- Keep model output review-only.
- Add deterministic validators around hybrid stops.
- Compare hybrid drafts against current selected/candidate-best output.
- Build human-review feedback capture.

### Days 61-90

- Decide whether to continue with low-cost hybrid or move to production-grade
  document AI.
- Define field-specific acceptance policies.
- Keep stops review-required until measured evidence proves otherwise.
- Retire or quarantine stop modules that only create noisy fragments.
- Keep deterministic load/rate extraction as the stable validation baseline.

## Model / Service Candidate Categories

| Category | What to test | Strength | Risk |
|---|---|---|---|
| Local open-source VLM/document model | Local model reads rendered pages and returns structured JSON. | Strong privacy if local; can reason over visual layout. | Hardware, latency, model quality, validation burden. |
| OCR plus local LLM/VLM | Use local OCR/layout plus local model for association. | Keeps source control local; can reuse current OCR/layout artifacts. | OCR errors and prompt/schema brittleness. |
| Commercial document AI | Custom extractor or layout/form processor. | Mature OCR/layout/classification/review tooling. | Cost, vendor/privacy review, data retention. |
| Commercial OCR plus deterministic validator | Use paid OCR/layout only, keep extraction deterministic. | Less model hallucination; better OCR/layout than local. | May still fail semantic stop association. |
| Manual-review-only fallback | Human reviews all uncertain stops. | Safest and lowest implementation risk. | Higher labor cost; slower throughput. |

No one vendor is mandatory. Any external service must be explicitly reviewed and
opted into before private documents are sent.

## Privacy Options

| Option | Privacy posture | Notes |
|---|---|---|
| Fully local | Best privacy | Local OCR/model only; may require GPU or slower CPU inference. |
| Local OCR + redacted model prompt | Medium | Only safe if redaction preserves required stop semantics. |
| External OCR/document AI with opt-in | Vendor-dependent | Requires retention, logging, and compliance review. |
| Human-only local review | Strong | No model risk; higher manual workload. |

Private raw values, raw broker text, PDFs, OCR text/TSV, and model outputs must
remain under ignored local-only directories.

## Cost / Complexity Matrix

| Path | Cost estimate | Complexity | Expected stop lift | Notes |
|---|---:|---|---|---|
| Existing deterministic only | $0 | Medium | Low | Useful for load/rate, unlikely to solve stops. |
| Local open-source model | $0-$200/month equivalent | High | Medium | Depends on hardware and model quality. |
| OCR + local LLM/VLM | $0-$200/month equivalent | Medium-high | Medium | Good pilot path if local inference is practical. |
| Commercial OCR/document AI | $50-$500/month pilot estimate | Medium | Medium-high | Must verify pricing and privacy before use. |
| Production-grade commercial + review | $500+/month estimate | High | Highest | Best quality path, not a quick patch. |
| Manual-review-only fallback | Labor cost | Low-medium | High safety, low automation | Good interim stop workflow. |

These cost numbers are estimates for planning only. Real costs depend on page
volume, model size, GPU availability, vendor pricing, and review workload.

## Success Metrics

Baseline:

- load number: 25 correct / 1 wrong / 5 missing;
- total carrier rate: 26 correct / 3 wrong / 2 missing;
- pickup stops: 0 exact / 17 partial / 5 wrong / 3 missing;
- delivery stops: 0 exact / 12 partial / 5 wrong / 4 missing.

30-day evaluation targets:

- load/rate do not regress;
- at least 80% document classification accuracy on the private set;
- at least 80% stop draft coverage;
- at most 10% unsafe wrong stop drafts;
- 100% of hybrid stops are review-required;
- every proposed stop has page/source evidence;
- non-RC BOL/POD documents are filtered;
- 0 private data committed.

These thresholds are estimates. They should be revised after the first private
local benchmark run.

## Stop Conditions

Stop the hybrid evaluation path if:

- private values would need to be sent externally without explicit approval;
- the model cannot return page/source evidence;
- unsafe wrong stop drafts exceed the agreed threshold;
- output cannot be validated deterministically;
- review burden is not lower than manual-only;
- load/rate regress because the hybrid layer interferes with deterministic
  extraction;
- implementation requires production behavior changes during the evaluation
  phase.

## Recommended Implementation Order

1. Land planning docs, contract docs, benchmark design, and local stub.
2. Build schema validation around hybrid result objects.
3. Add local-only benchmark runner that compares template outputs to existing
   gold/eval summaries.
4. Pilot one fully local approach first.
5. Only after local evidence exists, evaluate a commercial option with explicit
   privacy approval.
6. Add human-review draft UI/packet integration.
7. Decide whether any field can progress beyond review-only.

## Local Benchmark Runner Workflow

Use the benchmark runner after a human or future local/model process has filled
hybrid result JSON files:

```powershell
python scripts/run_ratecon_hybrid_benchmark.py ^
  --hybrid-results-dir .local_outputs/private_ratecon_hybrid_results ^
  --gold-dir .local_outputs/private_ratecon_gold_labels ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_benchmark ^
  --confirm-private-local-run
```

The runner:

- validates each hybrid JSON result against the contract;
- compares load, rate, pickup stops, and delivery stops against local gold;
- writes aggregate reports under `.local_outputs`;
- counts evidence and review-policy violations;
- optionally writes a review packet with `--write-review-packets`;
- does not call AI, cloud services, OCR, local models, or PDF processing.

Default outputs:

- `hybrid_benchmark_summary.json`;
- `hybrid_benchmark_report.md`;
- `hybrid_field_metrics.csv`;
- `hybrid_document_metrics.csv`;
- `hybrid_error_cases.csv`;
- `hybrid_schema_errors.csv`.

These outputs are private/local and must not be committed.

## Manual Template Workflow

Create blank hybrid result templates with:

```powershell
python scripts/create_ratecon_hybrid_result_templates.py ^
  --audit .local_outputs/private_ratecon_measurement/ratecon_shadow_document_pipeline_audit.jsonl ^
  --output-dir .local_outputs/private_ratecon_hybrid_result_templates ^
  --confirm-private-local-run
```

The template generator:

- creates one blank `*.hybrid_result.json` file per audit document when an audit
  is supplied;
- creates one generic template when no audit is supplied;
- leaves private field values blank by default;
- sets all stop drafts to `requires_human_review=true`;
- sets all stop drafts to `auto_accept=false`;
- writes an index CSV and README under `.local_outputs`.

A human or future local/model pipeline may fill the templates. Filled templates
should then be submitted to `scripts/run_ratecon_hybrid_benchmark.py` for
validation and aggregate scoring.

## Future Output Submission Rules

Future local/model outputs must:

- use `ratecon_hybrid_extraction_result_v1`;
- remain under ignored local-only paths;
- include `private_local_only=true`;
- include auditable evidence for non-empty extracted fields;
- keep all stops review-required in phase 1;
- never set stop `auto_accept=true`;
- avoid raw private values in committed artifacts.

## Benchmark Success / Failure

A benchmark run is successful only if:

- contract validation errors are explainable and low;
- stop drafts have evidence;
- all stops remain review-required;
- unsafe wrong stop drafts stay at or below the agreed threshold;
- load/rate do not regress against deterministic baseline;
- no private data leaves ignored local-only output paths.

A benchmark run fails if:

- the runner needs AI/cloud/model/PDF processing to operate;
- outputs contain raw private values without explicit local/private flags;
- stop auto-accept appears;
- evidence is missing for proposed fields;
- non-RC/BOL/POD documents pollute RateCon denominators.

## Non-Goals

- No AI/cloud integration in this branch.
- No private document transmission.
- No selected stop changes.
- No production output changes.
- No broker-specific regexes.
- No gold-label edits.
- No production extraction improvement claims.
