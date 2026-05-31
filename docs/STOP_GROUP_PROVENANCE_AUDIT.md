# Stop Group Provenance Audit

This document defines the root-cause-first block for stop grouping. It is a
measurement and refactor planning block, not a production automation block.

## Why Provenance Comes First

The latest safe private rerun showed:

- documents measured: 18;
- layout attempted: 6;
- raw stop groups: 112;
- normalized stops: 112;
- duplicate / noise removed: 0 / 0;
- date candidates attached: 10;
- time candidates attached: 9;
- missing date fields: 102;
- fusion worsened fields: none;
- OCR-needed unchanged: 4.

`raw_stop_groups == normalized_stops` means the normalizer is effectively a
passthrough. A normalization layer should usually reduce or consolidate at least
some raw provider evidence: table cells into rows, lines into sections,
duplicate headers into one group, and terms/billing/signature noise into skipped
groups. When the counts are identical, the pipeline is probably normalizing
objects after they have already been over-split, or the merge/dedupe keys are
not aligned with how raw groups are created.

`112` raw groups across 6 layout-attempted documents is suspicious because it is
far above a plausible stop count for normal load confirmations. It suggests one
or more of these behaviors:

- one group per table cell;
- one group per line;
- one group per stop label;
- repeated header/footer groups;
- unmerged pickup/delivery section fragments;
- non-core terms, billing, or signature content reaching stop grouping.

`duplicate_removed == 0` and `noise_removed == 0` are also suspicious. Real
RateCon packets regularly include repeated labels, footers, terms, remittance
sections, and signature blocks. If no duplicates/noise are ever removed, either
the filters are not seeing the right metadata or the metadata is too weak to
make safe decisions.

Date/time attachment improved, but 10 attached dates and 9 attached times
across 112 groups is still too low. The system needs to know whether date/time
evidence is absent, split into separate groups, filtered by scope, or attached
to the wrong grouping stage.

Adding more generic heuristics before this audit would be low signal. The next
change must expose where each group came from and why existing merge/noise
rules do not fire.

## Provenance Definition

Stop group provenance is safe metadata about how a raw group was produced. It
must not include raw text or private values.

Required provenance fields:

- source generator;
- source type;
- page number;
- section role;
- table id;
- row index;
- cell index;
- line id;
- block id;
- trigger label category;
- stop type evidence;
- field count;
- candidate field names;
- grouping key.

Source type examples:

- table row;
- table cell;
- table header;
- section block;
- line cluster;
- single line;
- label-value pair;
- text regex;
- layout signal;
- unknown.

Trigger label categories:

- pickup;
- delivery;
- stop;
- date;
- time;
- location;
- reference;
- unknown.

## Root-Cause Categories

The provenance audit should classify safe root causes into these buckets:

- `ONE_GROUP_PER_CELL`: table cells create separate groups instead of one row
  group.
- `ONE_GROUP_PER_LINE`: lines create separate groups instead of one section or
  line-cluster group.
- `ONE_GROUP_PER_LABEL`: labels create groups even when no usable stop fields
  are present.
- `TABLE_ROW_NOT_MERGED`: multiple groups share page/table/row metadata but are
  not merged.
- `SECTION_LINES_NOT_CLUSTERED`: same-page, same-section lines are not clustered
  into one stop.
- `DUPLICATE_HEADERS_NOT_MERGED`: repeated header/footer-like groups survive.
- `TERMS_BILLING_NOISE_NOT_FILTERED`: non-core terms, billing, quick-pay, or
  signature content reaches stop normalization.
- `DATE_TIME_SPLIT_FROM_LOCATION`: date/time candidates exist but are separated
  from location candidates.
- `SCOPE_FILTER_MISMATCH`: relevant stop/date evidence is excluded by page or
  section scope.
- `NORMALIZER_PASSTHROUGH`: normalized count equals raw count after all stages.

## Audit Outputs

The local-only provenance report should contain only aliases, counts, status
flags, source categories, grouping keys, and suspected root causes. It must not
include:

- raw text;
- private values;
- filenames;
- broker names;
- MC numbers;
- rates;
- addresses;
- dates/times;
- references;
- local paths.

## Safe Provenance Audit Result

The local-only provenance audit reported:

- raw stop groups: 112;
- normalized stops: 112;
- source types: `single_line=70`, `table_row=42`;
- trigger labels: pickup 45, delivery 37, stop 30;
- suspected root causes:
  - `NORMALIZER_PASSTHROUGH`: 6 aliases;
  - `ONE_GROUP_PER_LINE`: 6 aliases;
  - `DATE_TIME_SPLIT_FROM_LOCATION`: 6 aliases;
- table row merge candidates: 0;
- section cluster merge candidates: 0;
- duplicate candidates: 0;
- noise candidates: 0.

The audit did not confirm one-group-per-cell on the private run. It showed that
four attempted aliases were entirely `single_line` groups, while two attempted
aliases were mostly `table_row` groups from one provider table each. The table
issue is therefore not cell splitting; it is likely overclassification of
provider table rows as stop rows.

## Provenance-Based Refactor Result

The first provenance-based refactor added explicit provenance metadata,
local-only provenance reports, synthetic provenance fixtures, section line
cluster scaffolding, structural dedupe hardening, date/time candidate retargeting
after merge, and normalized stop stage counts.

The safe rerun after this refactor reported:

- raw stop signals/groups: 112 / 112;
- premerge groups: 112;
- post row merge groups: 112;
- post section merge groups: 112;
- post noise filter groups: 112;
- post dedupe groups: 112;
- normalized stops: 112;
- duplicate / noise removed: 0 / 0;
- date generated / attached: 10 / 10;
- time generated / attached: 9 / 9.

This means the current grouping changes did not reduce private stop
fragmentation. The next block should be a deeper provider-line clustering and
stop-line classification rewrite. The stage counts are still valuable because
they prove where the current algorithm is a passthrough.

## Process Gate

Implementation fixes must wait until a safe provenance audit has been run and a
safe root-cause summary has been printed. If the first provenance metadata is
insufficient, add more instrumentation and rerun diagnostics before changing the
grouping algorithm.

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
