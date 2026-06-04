# RateCon Load Identifier Cleanup Closeout Plan v1

This plan records the next safe path after the load identifier ownership and
baseline gate PR. It is not a behavior-changing load-number improvement plan.

Before any future load-number extraction, ranking, table/layout pairing, or
diagnostic behavior change, the project should have:

- a sanitized selected-load regression harness that pins current selected
  value/source/confidence/status behavior;
- a local-only private selected-load aggregate gate that compares existing
  evaluation outputs without printing private values by default;
- explicit known-debt fixture labels for table-neighbor, nearby-row, generic
  reference, and non-primary reference cases;
- private full-corpus aggregate comparison only when local private evaluation
  outputs already exist or are explicitly requested.

Future improvement targets can include:

- load identifier source-line evidence quality;
- table-neighbor pairing precision;
- nearby-row pairing precision;
- generic reference review routing;
- evaluator diagnosis mapping for load-number wrong/missing cases.

Do not process private PDFs, run OCR, run private measurement, call
Google/model/cloud services, edit gold labels, or change selected load-number
behavior as part of this closeout planning.
