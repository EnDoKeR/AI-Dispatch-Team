# Target Deferral And Rate Forensics

Google Sheets sync remains paused until a valid local service account
credential exists. This workflow stays local-first and uses ignored local
measurement outputs, review CSVs, and safe analysis artifacts.

## Why Load Identifier Is Deferred

`load_identifier_candidate_generation` remains a real intake-core blocker, but
the latest source-line audit did not prove a shared code-fixable root cause.
Safe result:

- source-line audit ran on 18 documents;
- primary candidates stayed low;
- rejected non-primary references remained useful review evidence;
- root causes split across unknown, OCR/weak text, absent source lines, only
  non-primary references, and correctly non-primary labels;
- no code-fixable bucket reached the required three-alias threshold.

Continuing to add generic load-number rules would risk promoting PO, BOL,
pickup, delivery, appointment, customer, or carrier references into
`load_number`. That would hide an honest missing identifier behind weak
evidence. The target is therefore deferred until local human review or new
source-line evidence changes the root-cause distribution.

## Why Deferral Is Needed

Target selection loops are dangerous when a broad blocker stays high after a
negative audit. Without a disposition registry, the selector can keep returning
the same target even after the measured evidence says no further code change is
justified.

Deferral is a control mechanism, not a suppression mechanism. It records why a
target is paused and lets the selector move to the next actionable blocker.

## Target Disposition States

- `active`: selectable for the next hardening block.
- `completed`: already handled for the current evidence set.
- `deferred_until_review`: blocked until local human review adds new evidence.
- `no_shared_code_root_cause`: audited, but no shared code-fixable reason was
  found.
- `blocked_by_missing_credential`: blocked by missing local service account
  credential or local config.
- `blocked_by_ocr`: blocked by non-digital or weak text that belongs in a future
  OCR design block.
- `needs_human_review`: not enough safe deterministic evidence to proceed.

Deferred or blocked targets are skipped by default. An explicit override may
allow rerunning a deferred target when new evidence exists, but the default
selector must not loop.

## Next Measured Area

The next measured area is rate conflict and main-rate resolution. Rate is a true
intake-core field. Unlike `no_candidate`, rate conflicts usually mean money-like
candidates exist but disagree, come from the wrong section, or are ranked with
the wrong source priority.

Rate forensics should determine whether conflicts come from:

- `accessorial_as_main_rate`;
- `quickpay_discount_as_main_rate`;
- `deduction_or_penalty_as_main_rate`;
- `terms_page_money_noise`;
- `billing_page_money_noise`;
- `linehaul_vs_total_conflict`;
- `multiple_strong_totals_conflict`;
- `TONU_payment_non_normal_load`;
- `candidate_generated_but_not_resolved`;
- `normalized_rate_not_core_mapped`;
- `no_shared_root_cause`.

A rate fix is allowed only if a shared, code-fixable root cause is proven. If
the root causes split across aliases or require private judgment, the correct
outcome is local human review for rate fields.

## Safe Sharing Rules

Safe to share:

- aliases;
- counts;
- statuses;
- field names;
- issue categories;
- rate candidate categories;
- source section categories;
- selected target names.

Do not share:

- money values;
- private predicted or expected values;
- raw text or line text;
- private filenames or local paths;
- broker/customer identifiers;
- service account keys.

## Non-Goals

This workflow does not run Google sync, add OCR/Vision/cloud document AI, add
Camelot/PyMuPDF/Tesseract/PaddleOCR, create DispatchCases, call DecisionEngine,
call Telegram, write Event Timeline events, or make production automation
claims.
