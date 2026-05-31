# Google Sheets Review Sync

This document defines the Google Sheets sync workflow for RateCon value
correctness review. The sync publishes review packets to dedicated tabs. It is
not final truth, not intake approval, and not dispatch automation.

## Purpose

The RateCon local workbook/CSV export lets a reviewer inspect extracted values
without programming. Google Sheets sync makes the same review packet available
in a shared spreadsheet so the user can mark fields as correct, incorrect, or
unknown and assign issue types.

The synced sheet remains a review surface only:

- extracted candidate: deterministic or layout-derived signal;
- resolved field: current resolver output and status;
- reviewed field: user-marked row in the review sheet;
- corrected field: user-provided expected value in local/private review data;
- trusted intake field: a later validated field after feedback import and
  policy checks.

## Dedicated Tabs

The sync uses dedicated review tabs instead of overwriting the operational
sheet. This prevents review/testing rows from modifying live load operations.

The review tabs are:

- `RC_Document_Summary`
- `RC_Stop_Review`
- `RC_Field_Review`
- `RC_Rate_Review`
- `RC_Instructions`
- `RC_Feedback_Summary`

Only those tabs are created or updated by the review sync. Existing operational
tabs are not touched unless a future block explicitly changes that policy.

## Service Account

Expected service account email:

```text
ai-dispatch-sheet@ai-dispatch-team.iam.gserviceaccount.com
```

Share the target spreadsheet with this email before running sync. The service
account JSON key must remain local and ignored. Do not commit it, paste it into
docs, or print it to console.

## Credential Safety

Supported local config sources:

- environment variables:
  - `AI_DISPATCH_GOOGLE_SHEETS_CONFIG`
  - `AI_DISPATCH_GOOGLE_CREDENTIALS_JSON`
  - `AI_DISPATCH_GOOGLE_SPREADSHEET_ID`
- ignored local config file:
  - `.local_private/google_sheets_review_config.json`
- explicit CLI flags:
  - `--google-config`
  - `--credentials-json`
  - `--spreadsheet-id`

The local config contains:

- `spreadsheet_id`
- `credentials_json_path`
- `worksheet_prefix`, default `RC_`
- `service_account_email`, optional
- `default_sync_mode`, default `status_only`
- `allow_private_review_value_sync`, default `false`

The repo may include a fake example config only. Real spreadsheet IDs and JSON
keys must remain local.

Initialize ignored local config with:

```powershell
python scripts/init_google_sheets_review_config.py --spreadsheet-id "YOUR_SPREADSHEET_ID" --credentials-json ".local_private\google-service-account.json"
```

The initializer prints only safety booleans. It does not print the credential
path, spreadsheet ID, or JSON key content. If a config already exists, pass
`--overwrite` intentionally.

Place the service account JSON in `.local_private\google-service-account.json`
or pass another ignored local credential path. Do not commit the JSON key and do
not paste it into chat.

If the credential is not already local, import a full service account JSON with:

```powershell
python scripts/import_google_service_account_local.py --from-file "C:\path\to\service-account.json"
```

The helper also supports `AI_DISPATCH_GOOGLE_SERVICE_ACCOUNT_JSON`,
`AI_DISPATCH_GOOGLE_SERVICE_ACCOUNT_JSON_B64`, and `--from-stdin`. The input
must be the complete Google service account JSON with `private_key`,
`client_email`, and `token_uri`; a one-line `private_key_id`, hash, or API key
is not sufficient for Google Sheets writes.

To permit the controlled private-values test sync, set the local-only config
field `allow_private_review_value_sync` to `true` by passing:

```powershell
python scripts/init_google_sheets_review_config.py --spreadsheet-id "YOUR_SPREADSHEET_ID" --credentials-json ".local_private\google-service-account.json" --allow-private-review-value-sync --overwrite
```

## Sync Modes

`status_only` is the default. It excludes predicted private values and uploads
aliases, statuses, counts, field names, evidence types, readiness levels, and
review columns.

`private_values_test_only` is explicit test mode. It may upload predicted
private values to the review tabs, but only when the user passes the explicit
private-value flag. Private values still must not be printed to console or
committed.

Google sync always requires explicit confirmation:

```text
--confirm-google-review-sync
```

## Commands

Create the local review CSVs/workbook first:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "<local-folder>" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --layout-diagnostics --compare-layout-to-text-baseline --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-review-workbook --write-review-csvs --natural-sort-inputs
```

Status-only Google sync:

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --confirm-google-review-sync --status-only
```

Explicit private-values test sync:

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --confirm-google-review-sync --include-private-review-values-google-test-only
```

The private-values mode is for controlled local review only. It still prints
only tab names, row counts, and sync mode.

Preflight local review CSVs before a sync:

```powershell
py scripts/sync_ratecon_review_to_google_sheet.py --preflight-only
```

Preflight checks expected headers, row counts, and raw-text columns by basename
only. If generated review CSVs are stale, rerun the local review export before
syncing. A typical stale-schema failure is a missing review column after the
exporter has changed; regenerate the review workbook/CSVs, then rerun
`--preflight-only`.

Feedback download:

```powershell
py scripts/download_ratecon_review_feedback_from_google_sheet.py --confirm-google-feedback-download
```

The measurement CLI can also sync immediately after writing review artifacts:

```powershell
py scripts/run_private_ratecon_measurement.py --input-dir "<local-folder>" --confirm-private-local-run --layout-provider pdfplumber --enable-layout-candidates --enable-layout-fusion --enable-no-regression-fusion --enable-stop-span-extractor --compare-stop-span-to-stop-group-pipeline --write-review-csvs --sync-review-google-sheet --confirm-google-review-sync --natural-sort-inputs
```

Optional config flags:

- `--google-config`
- `--spreadsheet-id`
- `--credentials-json`
- `--worksheet-prefix`

## Review Flow

The user reviews the Google Sheet tabs in this order:

1. `RC_Document_Summary`
2. `RC_Stop_Review`
3. `RC_Field_Review`
4. `RC_Rate_Review`

Review fields:

- `User Correct? yes/no/unknown`
- `User Expected Value LOCAL ONLY`
- `User Issue Type`
- `User Notes Local Only`

Completed review feedback is later downloaded from the review tabs into ignored
local CSVs, then summarized by the local feedback import tool. Feedback import
reports counts and issue types only; it does not create DispatchCases or write
production corrections in this block.

Downloaded local filenames:

- `google_feedback_stop_review.csv`
- `google_feedback_field_review.csv`
- `google_feedback_rate_review.csv`

## Safe To Share

Safe to share:

- aliases;
- row counts;
- readiness counts;
- integrity issue counts;
- issue type counts;
- field names;
- review status counts.

Do not share:

- service account JSON key;
- private predicted or expected values;
- raw text;
- private filenames or local paths;
- broker names;
- MC numbers;
- rates;
- addresses;
- references.

## Non-Goals

This block does not add OCR, Vision AI, cloud document AI, PyMuPDF, Camelot,
Tesseract, PaddleOCR, DispatchCase creation, DecisionEngine calls, Telegram
calls, Event Timeline writes, operational sheet overwrites, or production
automation claims.
