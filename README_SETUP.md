# Setup Notes

## Current Dependency Position

The active Foundation Hardening flow currently runs on the Python standard library.

`requirements.txt` intentionally has no project-wide third-party runtime dependency yet. This keeps the core test suite, intake dry-runs, DispatchCase helpers, Telegram metadata foundations, reload-watch dry-runs, and parser-contract work install-light and easy to verify.

## Observed Optional Dependencies

Repository audit found optional or legacy/manual imports for:

- `pypdf` in old/manual RateCon parsing paths;
- `gspread` and `google.oauth2.service_account` in manual Google Sheets scripts;
- `geopy` in legacy intake mileage helpers.

These are not required for the standard foundation checks. Do not add them to project-wide requirements until the corresponding workflow is explicitly accepted as active.

## Standard Verification

From the project root:

```powershell
py -m compileall app scripts main.py
py -m unittest discover -s tests -p "test_*.py"
git --no-pager diff --check
git status
```

In the Codex desktop runtime, use the bundled Python if `py` is not available.

## Local Configuration

`.env` is local-only and should not be committed.

Telegram environment variables are only needed when running live Telegram scripts:

```text
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

Private RateCons and local runtime records must stay out of GitHub. Use the documented ignored folders and local JSON paths.

## Formatter And Linter Position

Do not add `black`, `ruff`, or a repo-wide formatting pass casually.

If formatting/linting is added later, it should be a separate accepted mini-block with:

- selected tools and versions;
- focused configuration;
- no unrelated business behavior changes;
- full test verification.
