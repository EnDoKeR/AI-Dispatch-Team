# RateCon Test Readiness Checklist

Date: 2026-05-29

Use this checklist before running the first private RateCon text dry-run.

This checklist is documentation only. It does not add PDF parsing, OCR, private file reading, parser behavior changes, DispatchCase writes, Telegram behavior, Gmail/email, Google Sheets, DAT/API, Google Maps, accounting/factoring, replay, or reload-chain work.

## Foundation Readiness

- [ ] Intake record helper exists.
- [ ] Intake parser contract exists.
- [ ] Pasted-text parser adapter exists.
- [ ] Parser confidence helper exists.
- [ ] Intake repository exists for optional local dry-run JSON records.
- [ ] IntakeCaseLinkCandidate helper exists.
- [ ] Intake-to-case candidate report exists.
- [ ] Private RateCon folder is gitignored.
- [ ] Real RateCons are stored only under `data/private_ratecons/`.
- [ ] No private data is committed.
- [ ] Dry-run commands are documented.

## Local Private Sample Readiness

- [ ] User has selected 3-5 private RateCons locally.
- [ ] Selected files remain in `data/private_ratecons/`.
- [ ] `git status` does not show private files.
- [ ] No private text has been copied into tracked docs/tests.
- [ ] Missing-field expectations are clear.
- [ ] Needs-check expectations are clear.
- [ ] Confidence expectations are clear.
- [ ] Local notes, if any, are outside Git or gitignored.

## Commands

Pasted-text dry-run:

```powershell
py scripts/run_pasted_text_parser_dry_run.py
```

Manual JSON intake dry-run:

```powershell
py scripts/run_intake_record_dry_run.py
```

Synthetic intake-to-case candidate report:

```powershell
py scripts/run_intake_case_link_candidate_report.py
```

## What To Check In Dry-run Output

- extracted fields;
- missing fields;
- needs-check fields;
- field confidence;
- IntakeRecord shape;
- dry-run summary status;
- link candidate recommendation;
- approval required remains true;
- no case is created;
- no case is linked;
- no event is written.

## Not Ready If

Do not proceed if:

- private files appear in `git status`;
- private text would need to be committed for a test;
- PDF/OCR is needed;
- file upload handling is needed;
- Gmail/email or Google Sheets would be needed;
- DispatchCase creation/linking would be needed;
- parser output is too ambiguous to review manually.

## Still Not Allowed

- no PDF/OCR until later;
- no automated private file reading;
- no private text fixtures;
- no Telegram upload handling;
- no Gmail/email;
- no Google Sheets;
- no DispatchCase writes;
- no `linked_dispatch_case_id` updates;
- no accounting/factoring actions;
- no DAT/API or Google Maps;
- no synthetic 100-200 load dataset.

## Ready Definition

The project is ready for the first private manual text dry-run only when:

```text
foundation helpers exist
+ private samples are local and ignored
+ no private data is tracked
+ user has 3-5 selected docs
+ review expectations are clear
+ no PDF/OCR/file upload is required
```

Even when ready, the run remains manual, local, and dry-run only.
