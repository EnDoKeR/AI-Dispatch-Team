# System Flow

AI Dispatch Team is intended to operate as a Dispatch Operating Intelligence System. Telegram, CLI scripts, and future dashboards are interfaces around the system, not the system itself.

## Main Flow

1. Intake / RateCon / simulated load input

   The system receives operational evidence from manual JSON, synthetic scenarios, future RateCon parsing, future broker documents, or simulated load inputs.

2. Parser contract / intake record

   Intake evidence is normalized into structured records. Parsers and manual adapters must produce structured fields only. They do not make dispatch decisions, create cases, send messages, or write integrations.

3. DispatchCase creation or linking

   Structured evidence can later be linked to a DispatchCase. A DispatchCase is the operational unit of work for a load opportunity, accepted load, dispatcher action, or related decision history.

4. DecisionEngine / risk analysis

   Decision logic evaluates load fit, notes, driver compatibility, market context, exit risk, duplicate/repost identity, and review/rate-check signals. Recommendations must remain explainable and interface-independent.

5. Interface adapter

   Telegram, CLI tools, future dashboards, and future integrations present the decision context to the dispatcher. Adapters format, preview, send, or collect input, but they must not own business logic.

6. Dispatcher approval / feedback

   Dispatcher actions and feedback are captured as operational evidence. They may approve, reject, mark loaded, stop search, request review, or add context.

7. Event Timeline

   Decisions, alerts, feedback, document events, state changes, and outcomes should become an auditable event timeline on the relevant DispatchCase or future search/session entity.

8. Documents

   Rate confirmations, broker documents, notes, and later proof/accounting documents should be associated with the operational record after document-intake policy is designed.

9. Accounting / factoring packet later

   Future accounting and factoring helpers may prepare packets from structured documents and case history, but they must not submit anything or create financial commitments without explicit dispatcher approval.

10. Replay / missed opportunity later

    Future replay can use structured timelines, outbox records, feedback, and market snapshots to explain missed opportunities, false positives, duplicate suppression, or decision drift.

## Core Domain Logic

Core domain logic includes:

- intake record normalization;
- parser output contracts;
- load identity and duplicate safety;
- market baseline and zone context;
- exit classification and chain scoring;
- DecisionEngine rules;
- DispatchCase and Event Timeline behavior.

Core logic must not depend on Telegram sender/notifier code, Gmail, Google Sheets, DAT/API, Google Maps, or UI-specific formatting.

## Adapters And Interfaces

Adapters include:

- Telegram message sending and formatting;
- CLI dry-run tools;
- future dashboards;
- future Gmail or Google Sheets integrations;
- future Telegram upload handling.

Adapters may call core helpers, but core helpers should not call adapters.

## Storage And Repositories

Repositories provide simple persistence boundaries, such as local JSON records for dry-run intake or reload-watch state. Repositories should read and write records only. They should not decide dispatch behavior, format Telegram text, parse documents, or create DispatchCase events.

## Future Integrations

Future integrations may include:

- DAT/API load boards;
- Google Maps road mileage;
- Gmail/email intake;
- Google Sheets export;
- PDF/OCR parsing;
- accounting/factoring packet workflows.

Each integration needs a separate accepted design before live behavior is added.

## Current Foundation Rule

Build the intelligence layer first. Keep each module small, tested, and replaceable. Do not let any adapter, parser, repository, or formatter become the center of the product.
