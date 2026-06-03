# RateCon Hybrid Extraction Contract v1

Date: 2026-06-03

Scope: schema and validation contract for future local/private hybrid document
understanding evaluation. This contract does not implement model calls or change
production behavior.

## Contract Goals

The hybrid result contract must make model or document-AI output auditable,
reviewable, and safe to compare against existing deterministic output.

Required properties:

- private/local by default;
- explicit provider identity;
- field-level evidence;
- field-level confidence;
- deterministic validator results;
- stops review-required by default;
- no stop auto-accept in phase 1;
- no raw private values in committed artifacts.

## Top-Level Hybrid Result Schema

```json
{
  "schema_version": "ratecon_hybrid_extraction_result_v1",
  "document_id": "RATECON_001",
  "document_type": "rate_confirmation",
  "model_provider": "local_stub",
  "model_name": "no_model_stub",
  "private_local_only": true,
  "fields": {
    "load_number": {
      "value": null,
      "confidence": 0.0,
      "requires_human_review": true,
      "evidence_ids": []
    },
    "total_carrier_rate": {
      "value": null,
      "currency": "USD",
      "confidence": 0.0,
      "requires_human_review": true,
      "evidence_ids": []
    },
    "pickup_stops": [],
    "delivery_stops": []
  },
  "evidence": [
    {
      "evidence_id": "evidence_001",
      "field": "pickup_stops[0]",
      "page": 1,
      "bbox": null,
      "text_excerpt_redacted": "<redacted>",
      "source": "model"
    }
  ],
  "confidence": {
    "overall": 0.0,
    "load_number": 0.0,
    "total_carrier_rate": 0.0,
    "pickup_stops": 0.0,
    "delivery_stops": 0.0
  },
  "requires_human_review": true,
  "review_reasons": [
    "phase_1_no_auto_accept"
  ],
  "validator_results": {}
}
```

## Allowed Document Types

`document_type` must be one of:

- `rate_confirmation`;
- `bol_pod`;
- `unknown`.

Non-RateCon documents should not be treated as failed RateCon extraction.

## Allowed Model Providers

`model_provider` must be one of:

- `local_stub`;
- `local_vlm`;
- `commercial_doc_ai`;
- `manual`.

The current scaffold only supports `local_stub`. The other provider names are
contract placeholders for future opt-in evaluation.

## Stop Object Schema

```json
{
  "role": "pickup",
  "stop_index": 1,
  "facility": null,
  "address": null,
  "city": null,
  "state": null,
  "zip": null,
  "date": null,
  "time": null,
  "appointment_window": null,
  "raw_text_local_only": null,
  "evidence_page": 1,
  "evidence_bbox": null,
  "confidence": 0.0,
  "requires_human_review": true,
  "auto_accept": false,
  "evidence_ids": []
}
```

Rules:

- `role` must be `pickup` or `delivery`.
- `stop_index` must be a positive integer.
- `requires_human_review` must be `true` in phase 1.
- `auto_accept` must be `false` in phase 1.
- Missing components must be `null`, not string placeholders.
- `raw_text_local_only` may contain private text only in ignored local outputs.
- Evidence page or equivalent source reference is required when available.

## Evidence Contract

Every extracted field should point to one or more evidence objects.

Evidence fields:

| Field | Meaning |
|---|---|
| `evidence_id` | Stable ID unique within one hybrid result. |
| `field` | Field path such as `pickup_stops[0].city`. |
| `page` | 1-based page number when available. |
| `bbox` | Bounding box when available, otherwise `null`. |
| `text_excerpt_redacted` | Safe excerpt placeholder by default. |
| `source` | `native_text`, `OCR`, `image`, or `model`. |

Committed docs and safe reports must not include raw private excerpts.

## Confidence Contract

Confidence is diagnostic only in phase 1. It must not be used to auto-accept
stops.

Expected levels:

- field-level confidence;
- stop-level confidence;
- overall confidence;
- validator-derived risk status.

## Validator Results

Validators should report:

- document classification result;
- load/rate consistency;
- pickup/delivery role separation;
- pickup before delivery when dates are available;
- payment/instruction/footer leakage;
- reference/contact-only location rejection;
- missing evidence;
- human-review reasons.

Example:

```json
{
  "document_classification_gate": {
    "status": "passed"
  },
  "stop_consistency_gate": {
    "status": "review_required",
    "reasons": [
      "phase_1_no_auto_accept"
    ]
  },
  "evidence_gate": {
    "status": "passed"
  }
}
```

## Review Policy

Hybrid stops are always review-required in phase 1.

Stop auto-accept is explicitly prohibited until:

- stop exact and dispatch-usable draft metrics improve materially;
- unsafe wrong draft rate is below the agreed threshold;
- every accepted field has evidence;
- human review feedback supports the field policy;
- production acceptance is approved in a separate ADR.

## Privacy Rules

- Private raw values may exist only in ignored local outputs.
- Raw broker document text must not be committed.
- Private PDFs must not be committed.
- Hybrid model outputs containing private values must not be committed.
- Safe reports should use aliases, counts, status labels, and redacted
  placeholders.

## Minimal Valid Result

A minimal valid hybrid result can contain no extracted values, but it must still
include:

- schema version;
- document ID alias;
- document type;
- provider/model identity;
- `private_local_only=true`;
- `requires_human_review=true`;
- fields object;
- evidence list;
- confidence object;
- review reasons;
- validator results.

This allows the benchmark harness to test contracts before any model is
integrated.
