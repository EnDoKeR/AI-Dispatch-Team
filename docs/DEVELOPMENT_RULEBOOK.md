# Development Rulebook

This rulebook is the canonical engineering guide for AI Dispatch Team. It complements `docs/DEVELOPMENT_RULES.md` and should be used when adding architecture, contracts, parser logic, business rules, tests, or future adapters.

## File Size And Responsibility

- Prefer one focused module plus one focused test file.
- New modules should have a clear owner layer: adapter, intake, parser, domain core, decision engine, memory, persistence, event timeline, simulation, or future integration.
- Avoid new monolith files.
- Existing orchestrators may coordinate helpers but should not accumulate parsing, business rules, formatting, and persistence in one place.
- If a file grows because it owns multiple responsibilities, split by responsibility before adding more behavior.

## Business Logic Separation

- DecisionEngine owns recommendations.
- Parsers extract evidence and confidence only.
- Repositories store and retrieve data only.
- Telegram and other outputs format and transmit results only.
- Memory adds context and reasons, but hard safety rules and missing critical data must still win.

## Parser Design

- Parsers should return structured fields, candidate values, confidence, warnings, and evidence references.
- Parsers should not create DispatchCases.
- Parsers should not send Telegram or write Google Sheets.
- Parsers should not make MATCH/BLOCK/REVIEW decisions.
- Regex can be useful, but it is only one candidate source.
- Every parser improvement must use fake/anonymized fixtures unless a local private dry-run is explicitly allowed and kept out of tracked files.

## Broker-Specific Logic

- Broker-specific templates or aliases should be isolated.
- Broker logic should not leak into generic parser code without tests.
- Broker memory can add risk/context, but under-sampled memory must not silently block a load.
- Broker MC, contact, factoring, and payment signals should be evidence with confidence and source where possible.

## Driver-Specific Logic

- Driver preferences, hard constraints, and lane memory should stay in driver-focused helpers.
- Driver memory should be sample-size protected.
- Driver preference context should be explainable and replayable.
- Do not let Telegram formatting become the place where driver compatibility is calculated.

## Rate Confirmation Extraction

- The current core review table fields are documented in `docs/RATECON_CORE_FIELD_POLICY.md`.
- Missing critical fields must be explicit.
- Low-confidence critical fields must be explicit.
- Conflicting critical candidates must route to review.
- Loaded miles are deferred to a later Google Maps/mileage block.
- Broker MC and equipment are useful but not current core blockers by themselves.
- Private raw RateCon text, private values, and private PDFs must not be committed.

## Error Handling

- Fail safe with structured warnings.
- Missing inputs should return safe empty/default structures when possible.
- Local-only dry-runs should not write private text.
- CLI tools should print privacy warnings when touching local private data.
- External adapter failures should not corrupt core records.

## Confidence Scoring

- Critical fields should eventually have field-level confidence.
- LOW confidence on a critical field must prevent accept/ready outcomes.
- Conflicts between candidates must be visible.
- Confidence should be included in dry-run reports and future event evidence.

## Event Timeline Design

- The Event Timeline is the audit trail.
- Events should have stable event types, timestamps, source, payload, evidence references, and idempotency keys when available.
- Event writes should happen only in explicit wiring blocks.
- Reporting-only previews must stay report-only.
- Future document and accounting events require separate ownership policy before writes.

## SQLite And Database Design

- SQLite modules should follow IO, connection, schema, repository, summary, rebuild, and facade boundaries.
- Database code should not calculate dispatch recommendations.
- Migrations and schema changes need tests.
- JSONL remains useful for append-only audit/debug/replay when used.

## Testing Requirements

Every new business rule needs:

- positive test;
- negative test;
- missing-data test;
- low-confidence test where applicable;
- regression test if fixing a bug.

Every new parser/template needs:

- fake/anonymized fixture;
- expected structured output;
- missing fields;
- confidence/evidence expectations;
- no raw private text committed.

## Logging Requirements

- Log structured IDs and categories, not private raw document text.
- Do not log broker/customer/contact names from private documents in tracked outputs.
- Event/log payloads should be JSON-serializable.
- Local private value-review outputs must stay in ignored folders.

## Telegram Output Formatting

- Telegram is an adapter.
- Telegram output should show recommendation, missing fields, low-confidence fields, reasons, and next human action when relevant.
- Telegram formatters should not calculate business decisions.
- Telegram must not leak raw private RateCon text.

## Avoiding Duplicate Logic

- Prefer shared domain helpers over duplicating status, confidence, risk, or field policies.
- If duplicate status concepts exist, document the owner before adding another one.
- Keep compatibility wrappers thin.

## Adding New Business Rules Safely

- Add the rule in the correct layer.
- Add tests for allowed, blocked, missing, and review paths.
- Document whether the rule is hard-block, review-only, or context-only.
- Ensure output adapters merely display the result.

## Adding New Broker Formats Safely

- Start with fake/anonymized examples.
- Add label detection and field candidates before direct extraction shortcuts.
- Keep broker-specific parsing isolated or clearly named.
- Require confidence/evidence for critical fields.
- Route ambiguous results to review.

## Preventing Future Monolith Files

- Review file size before adding large features.
- Split extractors by document type, field group, or broker template.
- Split reports from core logic.
- Split adapters from domain helpers.

## Future DAT/API Integration

- DAT/API is an adapter, not core logic.
- Start read-only.
- Require duplicate and idempotency tests.
- Preserve simulator as a test data source.
- No autonomous booking.

## Future AI/OCR/PDF Vision Integration

- Add PDF triage before OCR/Vision.
- OCR/Vision should be fallback/gated, not called for every document.
- Store extraction artifacts and evidence references, not raw private text by default.
- External paid APIs require explicit approval and privacy review.

