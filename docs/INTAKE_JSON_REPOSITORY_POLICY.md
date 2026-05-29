# Intake JSON Repository Policy

Date: 2026-05-29

This audit decides whether intake records should be persisted locally before any parser, Telegram upload, Gmail/email, Google Sheets, or DispatchCase integration exists.

Scope is design-only. This document does not implement storage, file writes, parser behavior, DispatchCase wiring, Telegram behavior, OCR, Google Maps, DAT/API, or scheduler/background processing.

## Recommendation

Add a small local JSON repository for dry-run intake records.

It should store only JSON-ready intake records produced by:

```text
build_intake_record(...)
normalize_parser_output(...)
```

It must not store source PDFs, OCR text, email bodies, Telegram file bytes, Google Sheet rows, or DispatchCase events.

## Storage Format

Use a JSON list file, not JSONL, for the first foundation version.

Reasons:

- records are small during dry-run
- list round-trips are easy to inspect manually
- upsert by `intake_id` is simpler
- tests can use temp JSON files with no append-log semantics

JSONL may be useful later for immutable audit trails, but that belongs to a separate event/audit layer.

## Runtime Path

Default runtime path:

```text
data/intake_records.json
```

This file must be gitignored before the repository writes to it.

Tests must use temp files, not the runtime path.

## Record Identity

Primary key:

```text
intake_id
```

Repository upsert should replace a record with the same non-empty `intake_id`.

If `intake_id` is missing, the first repository version may append the record. Future service/CLI layers should provide a stable `intake_id` before saving.

The repository should not generate IDs in the first version. ID policy should remain in the caller/service layer.

## Status Policy

Initial statuses:

```text
READY_FOR_REVIEW
MISSING_FIELDS
NEEDS_CHECK
```

Status is a classification of the intake record, not a dispatch decision.

The repository should not decide status. It may filter records by an existing `status` field if present. A separate pure status helper can classify records before a CLI/service saves them.

## Source File Names

It is acceptable to store `source_file_name` when it is safe and useful, especially for synthetic or local dry-run records.

Do not store:

- full private filesystem paths
- PDF bytes
- OCR text dumps
- email body text
- broker/customer/driver private contact details beyond already-normalized intake fields
- real private documents

If future parser/upload code receives a private path, it should store only a safe basename or a redacted label.

## Repository Responsibilities

The repository may:

- load a JSON list of intake records
- save a JSON list of intake records
- return `[]` for missing files
- return `[]` for invalid or non-list JSON
- create a parent directory when saving
- upsert by `intake_id`
- get by `intake_id`
- filter by `status` if records contain status

The repository must not:

- parse PDFs
- read source documents
- write source documents
- send Telegram
- call Gmail/email APIs
- write Google Sheets
- write DispatchCase events
- call event logger
- use DAT/API or Google Maps
- run schedulers/background loops
- import legacy `app/load_intake`

## Tests Needed Before Implementation

- missing file returns `[]`
- invalid JSON returns `[]`
- non-list JSON returns `[]`
- save/load round-trip
- save creates parent folder
- upsert appends new `intake_id`
- upsert replaces existing `intake_id`
- get by `intake_id`
- filter by existing `status`
- repository does not mutate input records/lists
- repository has no parser/integration imports
- tests use temp files only

## Decision

Approved next mini-block:

```text
Intake JSON repository foundation
```

Keep it small and boring. It is local JSON storage only, not parser/storage service orchestration and not a live integration.
