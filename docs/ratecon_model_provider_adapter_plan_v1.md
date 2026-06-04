# RateCon Model Provider Adapter Plan V1

## Purpose

The provider adapter interface prepares RateCon model-assisted filling for
future experiments without enabling any real model execution. It defines
provider descriptors, safe configuration validation, dry-run planning, and
registry metadata for future local-only or privacy-approved providers.

## Disabled By Default

Providers are disabled by default because the validated manual/hybrid workflow
is review-first and local-only. This PR does not call OpenAI, Claude, Gemini,
local VLMs, OCR, PDF readers, or any other model/runtime. The only runnable
provider is a stub that produces empty scaffold submissions.

## Provider Lifecycle

- `stub_empty_v1`: runnable stub-only provider for harness tests.
- `manual_baseline_reference_v1`: listable reference provider for local
  comparison metadata; it does not copy private values by default.
- `local_model_placeholder_v1`: blocked until a later explicit local-only
  provider PR.
- `cloud_model_placeholder_v1`: blocked until explicit privacy approval and a
  later PR with clear opt-in gates.

## Safety Gates

All provider configs must satisfy:

- `private_local_only=true`;
- `allow_external_calls=false`;
- `allow_pdf_processing=false`;
- `allow_ocr_processing=false`;
- `allow_raw_text_input=false`;
- `allow_image_input=false`;
- `allow_private_value_copy=false`;
- `output_redaction_default=true`;
- no config keys containing `api_key`, `token`, `secret`, or `password`.

Cloud and local model placeholders are blocked. Any provider output with
`external_call_made=true`, stop `auto_accept=true`, or stop
`requires_human_review=false` fails validation.

## Config Schema

```json
{
  "schema_version": "ratecon_model_provider_config_v1",
  "provider_name": "stub_empty_v1",
  "run_id": "local_stub_run",
  "private_local_only": true,
  "allow_external_calls": false,
  "allow_pdf_processing": false,
  "allow_ocr_processing": false,
  "allow_raw_text_input": false,
  "allow_image_input": false,
  "allow_private_value_copy": false,
  "output_redaction_default": true
}
```

## List Providers

```powershell
python scripts/ratecon_model_provider_cli.py list-providers
```

## Validate Config

```powershell
python scripts/ratecon_model_provider_cli.py validate-config ^
  --config tests/fixtures/ratecon_model_provider/valid_stub_provider_config.json ^
  --confirm-private-local-run
```

## Dry Run

```powershell
python scripts/ratecon_model_provider_cli.py dry-run ^
  --config tests/fixtures/ratecon_model_provider/valid_stub_provider_config.json ^
  --templates-dir tests/fixtures/ratecon_model_assisted ^
  --output-dir .local_outputs/ratecon_model_provider_dry_run_fixture ^
  --confirm-private-local-run
```

Dry-run writes:

- `provider_dry_run_plan.json`;
- `provider_dry_run_report.md`;
- `provider_safety_gates.csv`.

It counts templates only. It does not execute a provider, read PDFs, OCR, call a
model, or send data anywhere.

## Production Output

No production output changes are allowed in this stage. Legacy output, selected
stop output, resolver thresholds, and broker-specific parsers remain unchanged.

## Stop Review Policy

All stops remain review-required. `auto_accept` must remain `false`, including
for future model-assisted outputs that match the manual baseline.

## Never Commit

Do not commit `.local_outputs`, private PDFs, private gold labels, private
benchmark outputs, filled hybrid templates, model outputs containing private
values, prompts/responses containing private values, API keys, or provider
configs containing secrets.

## Future Local-Only Provider Path

A future local-only provider PR can add an adapter behind explicit config gates.
It should first prove dry-run safety, then use sanitized fixtures, then run on a
small private local-only batch with user confirmation. This plan does not
implement that provider.

## Readiness Gates

Before any local provider implementation is proposed, run the readiness-gate
workflow in `docs/ratecon_local_provider_readiness_gates_v1.md`. The readiness
file, provider config, and fixture smoke report must show that execution remains
disabled, outputs are review-first, no model/PDF/OCR work occurred, and the
provider registry still blocks local/cloud placeholders. Readiness gates cannot
override registry blockers in this phase.
