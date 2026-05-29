# Manual RateCon Text Dry-run Protocol

Date: 2026-05-29

This protocol describes how to manually test a few real private RateCon texts later without committing private text or adding parser/PDF/OCR behavior.

This is design/protocol only. It does not change code, parser behavior, intake repository behavior, DispatchCase behavior, Telegram behavior, or integrations.

## Purpose

The goal is to test the existing dry-run foundation against a small number of private documents while keeping all private content local.

The protocol checks whether manually pasted or summarized document text can flow through:

```text
pasted text -> parser-output dry run -> IntakeRecord -> summary -> link candidate review
```

This should validate shape and review workflow only. It should not validate production parser accuracy yet.

## Execution Pipeline

The manual text dry-run pipeline should stay local and side-effect free:

1. User manually copies text locally from a private RateCon.
2. Text is passed through a CLI argument or safe stdin.
3. Pasted-text parser adapter extracts only obvious fields.
4. Parser output normalizes through the parser contract.
5. IntakeRecord is built.
6. Intake summary shows `missing_fields`, `needs_check_fields`, and confidence.
7. Optional case-like evidence can build an IntakeCaseLinkCandidate.
8. Output is printed locally only.
9. No private text is saved by default.
10. No case is created or linked.

The pipeline should expose review evidence only. It should not mutate runtime repositories, DispatchCases, event logs, Telegram state, or private source documents.

## Input And Save Modes

Supported or planned modes:

| Mode | Input | Safety rule |
| --- | --- | --- |
| sample mode | built-in fake RateCon-like text | synthetic only |
| text mode | `--text "..."` | local pasted text, not saved |
| stdin mode | `--stdin` if implemented safely | reads terminal stdin only, not a file path |
| save mode | disabled by default | no private text saved by default |

File input is intentionally not part of this protocol. Do not add a `--file`, `--pdf`, or private folder scan mode for this dry-run.

## Scope

Allowed later under this protocol:

- choose 3-5 private RateCons locally;
- manually copy text locally or manually summarize fields;
- run existing dry-run commands locally;
- inspect extracted fields, missing fields, needs-check fields, confidence, and candidate recommendations;
- discuss anonymized snippets if needed.

Not allowed:

- committing full private RateCon text;
- committing private document excerpts;
- reading private RateCon PDFs from tests;
- PDF extraction;
- OCR;
- automated Telegram upload;
- Gmail/email ingestion;
- Google Sheets export;
- DispatchCase creation;
- DispatchCase linking;
- DispatchCase event writes.

## Step-by-step Protocol

### 1. Select Local Private Documents

Choose 3-5 documents from:

```text
data/private_ratecons/
```

Prefer variety:

- one clean/simple RateCon;
- one missing field example;
- one appointment window example;
- one accessorial or linehaul split example;
- one contact-heavy or hard-to-read example if available.

### 2. Confirm Privacy Boundary

Before copying or typing anything:

```powershell
git status
```

Confirm private files are not shown.

Do not create tracked files containing private RateCon text.

### 3. Prepare Local Manual Text

Use one of these approaches:

1. Manually copy a small text sample locally for a dry-run command.
2. Manually summarize fields into JSON locally.
3. Create an anonymized/synthetic version if a committed fixture is needed later.

Do not paste full private document text into committed docs or tests.

If asking for help in chat, paste only selected anonymized snippets or manually rewritten structural examples.

### 4. Run Pasted-text Dry-run

For short local text:

```powershell
py scripts/run_pasted_text_parser_dry_run.py --text "Broker: FAKE BROKER LLC ..."
```

For private text, replace real values before sharing or committing anything. If running locally only, keep the command in the terminal and do not save the output to a tracked file.

Check output for:

- extracted fields;
- field confidence;
- missing fields;
- needs-check fields;
- final intake status.

### 5. Run Manual JSON Dry-run If Needed

If the pasted-text adapter is too conservative, manually create a local JSON object from the RateCon fields and run:

```powershell
py scripts/run_intake_record_dry_run.py --json "{...}"
```

Do not commit JSON containing real private values.

Check:

- IntakeRecord shape;
- `missing_fields`;
- `needs_check_fields`;
- `field_confidence`;
- summary status.

### 6. Compare Against Link Candidate Expectations

For public synthetic scenarios, use:

```powershell
py scripts/run_intake_case_link_candidate_report.py
```

For private local review, do not create runtime cases or events. If a link candidate needs to be discussed, anonymize the intake/case evidence first.

Check:

- recommended action;
- match reasons;
- mismatch reasons;
- approval required;
- no runtime link/create action.

## Expected Result Format

Each private dry-run review should produce local notes like:

```text
file_label: 01_clean_simple
dry_run_method: pasted_text or manual_json
extracted_fields: reviewed locally
missing_fields: [...]
needs_check_fields: [...]
field_confidence: reviewed locally
intake_status: READY_FOR_REVIEW / MISSING_FIELDS / NEEDS_CHECK
link_candidate_recommendation: LINK_EXISTING / CREATE_CASE_REVIEW / KEEP_UNLINKED / NEEDS_REVIEW
approval_required: true
notes: structure-only notes, no private text in Git
```

If these notes contain real values, keep them local/private and out of Git.

## Safety Rules

- no full RateCon PDF in repo;
- no private text fixtures yet;
- no OCR/PDF extraction;
- no automated upload;
- no DispatchCase creation;
- no event writes;
- no Google Sheets/Gmail/Telegram integration;
- no accounting/factoring action.

## When To Stop

Stop the dry-run and return to design if:

- the adapter guesses fields too aggressively;
- private text would need to be committed for a test;
- PDF/OCR is needed to continue;
- extracted fields create dispatch ambiguity;
- link candidate behavior would require runtime case changes;
- private data appears in `git status`.

## After 3-5 Manual Dry-runs

After the first few private local checks:

1. summarize only structural lessons;
2. create synthetic/anonymized scenarios if useful;
3. update parser difficulty notes;
4. decide whether a PDF extraction strategy audit is ready;
5. keep runtime linking/event writes out of scope until separately approved.
