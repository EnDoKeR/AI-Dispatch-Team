# Private RateCon Measurement CLI Responsibility Audit v1

This audit exists to decide whether further splitting of
`scripts/run_private_ratecon_measurement.py` is justified after the focused
measurement CLI cleanup series. It is visibility tooling only. It does not move
behavior and it is not a request to change extraction, measurement, output
schemas, filenames, workbook layout, audit metrics, Google sync semantics, or
CLI flag behavior.

## Completed Cleanup Phases

- Phase 1: `app/document_ai/measurement_cli/ratecon_private_args.py`,
  `ratecon_private_config.py`, and `ratecon_private_safety.py` own CLI parsing,
  parsed config, and local/private safety validation.
- Phase 2: `ratecon_private_output_paths.py` owns stable local output path and
  filename construction.
- Phase 3A: `ratecon_private_report_writers.py` owns safe JSON, CSV, Markdown,
  and value-review report writers.
- Phase 3B: `ratecon_private_review_exports.py` owns simple local review/export
  artifacts.
- Phase 3C: `ratecon_private_audit_orchestration.py` owns optional audit and
  diagnostic export orchestration wrappers.
- Phase 3D: `ratecon_private_review_workbook.py` owns review workbook wrapper
  orchestration.
- Phase 3E: `ratecon_private_google_sync.py` owns Google Sheets sync wiring.

## What Remains

The public CLI wrapper still owns the top-level sequence that ties the private
measurement command together:

- PDF discovery and safe alias selection.
- Private template registry loading.
- Safe output policy construction.
- The private measurement call for each document.
- Aggregate construction.
- Optional layout/table profile comparison hook.
- Console summary formatting.
- Top-level sequencing and expected-error handling.
- Delegated calls into output, review, audit, workbook, and Google sync helper
  modules.

Those responsibilities should not be moved casually. The current script is the
explicit public local-only entrypoint, and its remaining behavior coordinates
private document selection, measurement execution, and safety-gated side effects.
Moving that orchestration without a clear boundary risks changing private run
semantics or output timing.

## Running The Audit

Use the local-only command:

```powershell
python scripts/audit_private_ratecon_measurement_cli_responsibilities.py `
  --repo-root . `
  --output-dir .local_outputs/private_ratecon_measurement_cli_responsibility_audit `
  --confirm-local-audit-run
```

The audit refuses to run without `--confirm-local-audit-run` and refuses output
outside `.local_outputs`. It uses static AST/text analysis only and does not
import project modules, execute measurement, process PDFs, run OCR, call Google,
or call AI/model/cloud services.

Generated files are local-only and must not be committed:

- `measurement_cli_responsibility_summary.json`
- `measurement_cli_responsibility_report.md`
- `measurement_cli_responsibility_sections.csv`
- `measurement_cli_remaining_imports.csv`
- `measurement_cli_remaining_direct_calls.csv`
- `measurement_cli_recommendations.csv`

## Interpreting Output

- `line_count`, `function_count`, and `top_level_statement_count` show the size
  of the remaining wrapper.
- `delegated_modules` confirms which helper layers are already imported by the
  CLI wrapper.
- `remaining_responsibilities` identifies static signals for PDF discovery,
  template loading, measurement sequencing, formatting, audit wiring, workbook
  wiring, Google sync wiring, and path construction.
- `remaining_direct_calls` separates delegated helper calls from remaining
  direct calls such as measurement execution, registry loading, or layout
  profile comparison.
- `recommendations` should be treated as cleanup decision inputs, not automatic
  approval to split more code.

## Never Commit

Do not commit `.local_outputs`, private PDFs, raw extracted text, gold labels,
filled hybrid templates, benchmark outputs, audit JSONL with private values,
evaluation reports with private values, OCR artifacts, local debug files, model
outputs, Google credentials, token files, service account JSON, private
spreadsheet IDs, or sync logs containing private values.

## Decision Points

- Stop splitting and keep `scripts/run_private_ratecon_measurement.py` as the
  public orchestration wrapper.
- Split PDF discovery/input selection only if ownership is still unclear and
  fixture-only tests prove behavior remains unchanged.
- Split console summary formatting only after snapshotting current safe output
  text.
- Split measurement sequencing only with a separate reviewed plan and tests
  that prove output schemas, filenames, CLI semantics, audit metrics, workbook
  layout, and Google sync behavior are unchanged.
- Leave the file as a public orchestration wrapper if the audit shows remaining
  responsibilities are cohesive.
