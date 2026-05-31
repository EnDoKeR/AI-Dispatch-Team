# Stop Span Candidate Generation Audit

This block audits why true intake-core fields still have no candidates after
the core field policy cleanup. It is a local-first diagnostic workflow, not a
production automation change.

## Why This Exists

The policy cleanup changed the problem shape. Optional fields are no longer
misclassified as core blockers:

- `optional_field_misclassified_as_core=0`;
- optional missing fields remain visible for review and dispatch decisioning;
- true intake blockers now focus on required broker/load/rate and stop fields.

The current true blockers include delivery date, broker name, pickup date, load
number, rate, delivery location, and pickup location. The cleaned root-cause
signal is mostly `no_candidate`, not unresolved or conflict.

`no_candidate` is materially different from `conflict` or
`candidate_exists_but_unresolved`. If no candidate exists, the resolver cannot
fix the field by choosing better. The pipeline has to show where evidence was
lost before resolution.

## Selected Target

The selected next target is `stop_span_candidate_generation_audit`.

The raw analyzer still points at stop-span mapping because stop fields dominate,
but the policy-cleaned reason is mostly missing candidate generation. This block
must not keep stacking datetime or span-to-core mapping heuristics unless the
coverage data proves that exact stage is failing.

## Pipeline Stages To Audit

For each required stop-related intake field, the audit traces whether evidence
survives these stages:

1. layout line exists;
2. line feature detected;
3. stop anchor detected;
4. stop span built;
5. span field candidate generated inside span;
6. normalized stop field created;
7. core field mapped;
8. review workbook row emitted.

The audit is count/status based. It must not store or print private values, raw
text, private filenames, local paths, broker names, rates, addresses,
references, or snippets.

## Failure Categories

Coverage gaps are classified into safe buckets:

- `line_feature_missing`;
- `anchor_missing`;
- `span_missing`;
- `span_boundary_excluded_line`;
- `candidate_not_generated`;
- `candidate_generated_but_not_normalized`;
- `normalized_but_not_core_mapped`;
- `scope_filtered`;
- `non_applicable`;
- `ocr_needed`;
- `policy_excluded`;
- `unknown`.

These categories are designed to separate extraction coverage failures from
readiness policy and resolver failures.

## Local Outputs

Coverage reports are local-only ignored artifacts under:

```text
.local_outputs/private_ratecon_measurement/
```

Expected report names:

- `candidate_coverage.json`;
- `candidate_coverage.md`;
- `candidate_coverage_analysis.json`;
- `candidate_coverage_analysis.md`.

The console may print aliases, field names, stage names, counts, statuses,
gap reasons, and recommended fix buckets only.

## Decision Gate

After coverage analysis, select exactly one candidate generation fix:

- date candidates missing inside spans -> stop span date candidate generation;
- location candidates missing inside spans -> stop span location candidate
  generation;
- value lines excluded from spans -> stop span boundary expansion;
- span candidates exist but normalized fields are absent -> normalized stop
  field mapping;
- normalized fields exist but core fields are absent -> normalized-to-core
  mapping;
- load number, broker, or rate candidates dominate -> select that one target;
- OCR-needed dominates -> queue OCR design later, do not add OCR in this block.

If coverage shows stop candidates are absent because evidence lines never enter
the spans, the fix belongs in span boundaries or candidate coverage, not in the
resolver.

## Non-Goals

This block does not:

- run Google Sheets sync;
- require Google credentials;
- add OCR;
- add Vision AI;
- add cloud document AI;
- add PyMuPDF, Camelot, Tesseract, or PaddleOCR;
- create DispatchCase records;
- call DecisionEngine;
- call Telegram;
- write Event Timeline events;
- make production readiness claims.

All tests must use fake or synthetic fixtures only.
