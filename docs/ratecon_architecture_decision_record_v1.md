# Architecture Decision Record: RateCon Extraction Direction v1

Date: 2026-06-03

Status: accepted for planning. This ADR does not implement extraction changes.

## Context

The current Rate Confirmation pipeline has added substantial shadow-only
diagnostic infrastructure:

- candidate/provenance architecture;
- gold-label evaluator;
- pdfplumber layout provider;
- optional local OCR;
- OCR candidate policies;
- stop block, geometry, TSV column, and source inventory diagnostics;
- stop sidecar and evaluator cleanup;
- known-absent gold classification;
- provenance repair;
- trusted-source stop disambiguation.

Current measured state:

| Area | Metric |
|---|---:|
| Load number | 25 correct / 1 wrong / 5 missing |
| Total carrier rate | 26 correct / 3 wrong / 2 missing |
| High-confidence wrong load/rate | 1 / 0 |
| Pickup selected stops | 0 exact / 17 partial / 5 wrong / 3 missing |
| Delivery selected stops | 0 exact / 12 partial / 5 wrong / 4 missing |
| Stop evaluator/code issues | 0 |
| True gold review rows | 0 |
| Patch template rows | 0 |
| Trusted-source fusion safe opportunities | 0 |

The evidence shows that load/rate extraction is improving in shadow mode, while
stop extraction remains weak. Stop failures are no longer primarily caused by
gold labels, evaluator serialization, or missing provenance. They are caused by
visual document-understanding limits: row/block proof, multiple location
clusters, date/time conflicts, legacy fallback noise, source unavailability, and
insufficient geometry for some sources.

## Decision

Stop treating RateCon stop extraction as an incremental rule/candidate/resolver
optimization problem.

Continue using the deterministic pipeline for:

- PDF triage;
- document classification;
- safe private measurement;
- load/rate shadow extraction;
- validation;
- review gating;
- provenance;
- auditability.

Move the future stop strategy toward a hybrid document-understanding and
human-review architecture. Current stop outputs remain shadow-only and
review-required. No current stop candidate, fused stop, OCR stop, or legacy
fallback stop should be production auto-accepted.

## Accepted Direction

The accepted architecture direction is:

```text
PDF triage and classification
-> OCR/layout/document-understanding extraction
-> deterministic normalization and validation
-> field-level confidence and risk gates
-> review-only stop drafts for uncertain or visual fields
-> human correction capture
-> private benchmark evaluation
-> selective production acceptance only after measured proof
```

The current deterministic codebase remains useful, but its role changes:

- scalar extraction where evidence is strong;
- candidate and provenance audit;
- validation and conflict detection;
- privacy-safe measurement;
- review packet generation;
- guardrails around model or commercial document-AI output.

## Rejected Paths

| Rejected path | Reason |
|---|---|
| Pure regex/rule parsing as dominant stop strategy | Cannot prove visual stop rows across broker variation. |
| More broker-specific stop regexes | Scales poorly and increases brittle maintenance. |
| Resolver threshold lowering | Would turn ambiguity into wrong output. |
| Blind confidence boosting | Hides risk without improving evidence. |
| Broad stop fusion | Current fusion_safe is zero. |
| Auto-accepting fused stops | No safe measured basis. |
| Removing legacy fallback globally | It may still be useful as coverage/debug evidence. |
| Trusting legacy fallback for stop disambiguation | It is a major ambiguity source. |
| Auto-editing gold labels | Current patch rows are zero; gold is not the blocker. |
| Cloud-only architecture without privacy review | Private PDFs and values require explicit controls. |
| AI direct-to-production output | Needs deterministic validation and human review first. |

## What Remains Shadow-Only

- OCR stop candidates.
- OCR geometry and TSV stop candidates.
- Stop column reconstruction output.
- Candidate-best stop groups.
- Dispatch-usable review drafts.
- Review-only fusion drafts.
- Trusted-source disambiguation reports.
- Source inventory and provenance reports.
- Private review packets.
- Any stop output derived from legacy fallback.

## What Is Safe To Merge

The following are safe to merge because they do not change production or
selected extraction behavior:

- sanitized documentation;
- aggregate-only diagnostics;
- safe local measurement harness updates;
- evaluator/gold completeness reporting;
- known-absent classification;
- provenance and source inventory reports;
- review packet tooling that writes only ignored local outputs;
- strict review gates.

## What Must Never Be Production Auto-Accepted Yet

- Current selected pickup/delivery stops.
- Fused stops.
- OCR-only stop candidates.
- Legacy fallback stop candidates.
- Candidate-best stop groups.
- Structurally complete candidates labeled as dispatch-capable before they are
  proven correct against gold and source evidence.

## Risks

| Risk | Mitigation |
|---|---|
| Continuing incremental stop parser work burns time | Freeze selected stop changes and move to architecture evaluation. |
| AI/VLM output may hallucinate | Use deterministic validation, schema checks, review-only output, and no auto-accept. |
| Commercial document AI may leak private data | Require explicit vendor/privacy review and local-only evaluation first. |
| Human review cost may rise | Review only low-confidence or stop-specific fields; keep scalar auto-diagnostics separate. |
| Existing diagnostic stack becomes hard to maintain | Quarantine dead-end modules and document ownership. |
| Load/rate improvements may be overstated | Keep shadow-only until larger labeled evidence proves stability. |

## Migration Plan

### 0-30 Days

1. Freeze selected stop extraction behavior.
2. Keep load/rate shadow diagnostics under current strict profiles.
3. Produce a private benchmark protocol for RateCon document families.
4. Select a small private labeled evaluation set with trusted gold.
5. Evaluate low-cost AI-assisted and commercial document-understanding options.
6. Define a review-only stop draft schema and validation contract.
7. Quarantine legacy fallback from trusted stop association.

### 30-60 Days

1. Prototype hybrid stop draft extraction with one selected document-AI/VLM path.
2. Store model/source evidence only in ignored local/private outputs.
3. Validate draft stops with deterministic role, date/time, location, and
   section-boundary checks.
4. Add human review workflow for stop drafts.
5. Compare model drafts against current selected/candidate-best groups.

### 60-90 Days

1. Decide whether Option B or Option C is justified by measured lift.
2. Build field-specific acceptance policies.
3. Keep stops review-required until exact and dispatch-usable quality improves
   materially.
4. Retire or quarantine stop modules that only add noisy fragments.
5. Keep the deterministic pipeline as validation, fallback, and audit layer.

## Success Criteria

The next architecture should be considered successful only if it produces:

- higher dispatch-usable stop draft quality without increasing unsafe selected
  output;
- explicit source evidence for each stop component;
- lower manual review burden for stops;
- stable or improved load/rate metrics;
- zero private-data leakage in committed artifacts;
- no production auto-accept of stops until metrics justify it.

## Current Decision Summary

The current deterministic architecture is useful but mispositioned. It should
remain the safety, validation, scalar-field, and audit layer. It should not be
the dominant stop extraction strategy. Future stop work should move to hybrid
document understanding plus human review, with deterministic validation around
all model or commercial document-AI output.
