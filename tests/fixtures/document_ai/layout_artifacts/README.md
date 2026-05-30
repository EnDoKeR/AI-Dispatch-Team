# Synthetic Layout Artifact Fixtures

These fixtures are synthetic JSON layout artifacts. They are not generated from
private PDFs, screenshots, or real broker templates.

Fixture policy:

- no private PDFs;
- no screenshots;
- no raw private text;
- no real broker names;
- no real MC numbers;
- no real addresses;
- no real contacts;
- no private rates, load numbers, references, or stop details;
- fake values may be used only to exercise deterministic layout logic.

The fixtures mimic document structure only:

- table-heavy confirmations;
- PU/SO-style load confirmations;
- carrier tender route details;
- multi-stop order confirmations;
- terms, billing, and signature pages;
- TONU/payment confirmations.

They are intended to test dependency-free layout contracts, layout indexing,
label-value proximity, candidate generation, and resolver readiness before any
real PDF layout provider is added.
