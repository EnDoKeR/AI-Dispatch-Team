# Stop Pipeline Wiring Audit

This document defines the stop pipeline wiring audit block. It is a
correctness/debugging block, not a feature expansion block.

## Why This Block Exists

The latest safe private rerun showed that stop normalization is still a
passthrough:

- raw stop signals/groups: 112 / 112;
- premerge groups: 112;
- post row merge groups: 112;
- post section merge groups: 112;
- post noise filter groups: 112;
- post dedupe groups: 112;
- normalized stops: 112;
- duplicate / noise removed: 0 / 0;
- date candidates attached: 10;
- time candidates attached: 9.

Unchanged stage counts prove that the current pipeline is not reducing
fragmented stop evidence. A normalized stop pipeline should reduce mergeable
fragments: line fragments should become section-level groups, row fragments
should become one table-row group, repeated header/footer groups should be
removed or merged, and date/time fragments should attach to the stop context
instead of remaining separate review records.

`normalized_stops == raw_stop_groups` is not acceptable for mergeable provider
artifacts. It means at least one of these is true:

- merge/dedupe functions are not wired into the real measurement pipeline;
- stage counts are measured before the actual merge output is used;
- grouping keys are missing or always unique;
- single-line groups bypass section clustering;
- normalized stop building receives raw groups instead of merged groups;
- dedupe/noise logic cannot match groups because provenance signatures are too
  unique;
- provider lines are not clustered into stop sections.

## Provenance Interpretation

The safe provenance audit reported:

- `single_line`: 70 groups;
- `table_row`: 42 groups;
- `NORMALIZER_PASSTHROUGH`: 6 aliases;
- `ONE_GROUP_PER_LINE`: 6 aliases;
- `DATE_TIME_SPLIT_FROM_LOCATION`: 6 aliases.

`single_line: 70` makes section clustering the main target. Those line-level
groups need to be clustered into pickup, delivery, or stop sections before
normalized stops are built.

`table_row: 42` means table extraction already creates row-level groups for the
private run. The confirmed table issue is not one group per cell. It may still
include overclassification of table rows as stops, but table/cell overgrouping
is not the primary confirmed cause for this block.

`duplicate_removed == 0` and `noise_removed == 0` remain suspicious. Real
RateCon packets commonly include repeated headers, footers, terms, billing
sections, and signature content. If the filters never remove anything, either
they are not wired into the active path or the provenance/grouping signatures
are too unique to match.

## Expected Pipeline

The active normalized stop path should be:

1. raw provider evidence;
2. raw stop signals;
3. premerge groups;
4. single-line section clustering;
5. table row grouping;
6. section clustering;
7. noise filtering;
8. structural dedupe;
9. date/time attachment;
10. normalized stop set.

The output of each stage must be the input to the next stage. Stage counts must
be recorded after the stage output is selected, not before the stage runs.

## Required Invariant Tests

The block must add tests that fail if the pipeline remains passthrough:

- a mergeable single-line fixture must reduce counts after single-line
  clustering;
- a two-section single-line fixture must become two normalized stops;
- a non-mergeable fixture must preserve distinct stops;
- a signature/footer noise fixture must remove noise;
- a passthrough fixture must fail if all stage counts remain unchanged.

These tests are not production accuracy claims. They are wiring invariants that
prove the pipeline consumes grouped output rather than raw input.

## Private Rerun Decision Rule

If a private safe rerun still reports unchanged counts across all stages, the
block must be reported as `NOT FIXED`. Do not claim stop normalization is fixed
unless the stage counts actually change.

The safe report should include only aliases, counts, status fields, stage names,
warning codes, and pattern categories. It must not include private values,
filenames, broker names, MC numbers, rates, addresses, dates/times, references,
local paths, screenshots, or PDFs.

## Google Sheets Review Export

This block may add a local-only Google Sheets-compatible export to support
manual review of measurement rows. The export must be written only under the
ignored local output directory. It must not use Google APIs, OAuth, cloud
services, or new dependencies.

The default export must be safe/status-oriented. Local document stems may be
included only in local-only output files and must never be printed to console.
Natural sorting should be available for local review workflows so names like
`LoadConfirmation1`, `LoadConfirmation2`, and `LoadConfirmation10` appear in
human order.

## Non-Goals

This block does not add:

- OCR;
- Vision AI;
- Camelot;
- PyMuPDF;
- cloud APIs;
- new dependencies;
- DispatchCase creation;
- DecisionEngine calls;
- Telegram calls;
- Event Timeline writes;
- production automation claims.
