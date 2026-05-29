# Product Strategy

## Positioning

AI Dispatch Team is evolving into a Dispatch Operating Intelligence System for small and mid-size trucking carriers.

The product is not a Telegram bot. Telegram is one adapter for dispatcher communication. The core system is the intelligence layer that turns load intake, decisions, dispatcher feedback, documents, and operational events into an explainable DispatchCase timeline.

## Target User

The first target user is a small or mid-size carrier that does not have a large operations department, but still needs disciplined dispatch memory, document tracking, and decision history.

Near-term workflows are focused on flatbed and Conestoga dispatch, where load fit, broker quality, reload risk, documentation, and timing can change the real value of a load.

## First Wedge

The first wedge is:

1. Rate confirmation / broker document intake.
2. Structured intake record.
3. DispatchCase creation or linking.
4. Decision and risk analysis.
5. Dispatcher approval or feedback.
6. Event timeline.
7. Document trail.

This keeps the foundation centered on operational memory instead of only alert delivery.

## Core Value

The durable value is the combination of:

- DispatchCase as the operational unit of work.
- Event Timeline as the audit and learning trail.
- Structured intake records as evidence.
- Decision/risk analysis as explainable context.
- Dispatcher feedback as memory.

The system should help the dispatcher understand:

- what happened;
- why a recommendation was shown;
- what was accepted, rejected, changed, or missed;
- which documents and notes belong to the case;
- what can be learned for future decisions.

## Interfaces And Adapters

Telegram, CLI tools, future dashboards, Gmail, Google Sheets, and other integrations are adapters. They should not own core business logic.

Core domain logic should remain interface-independent so the same DispatchCase, intake record, and decision context can be used from Telegram, manual CLI dry-runs, future dashboards, or future integrations.

## Future Modules

Future product layers may include:

- accounting and factoring packet preparation;
- replay and missed opportunity analysis;
- dispatcher approval modes;
- document packet assembly;
- broker and lane memory;
- search/session-level history;
- market and reload context over time.

These modules should be added only after the current foundation is stable and each module has a clear boundary.

## Not Building Now

The current foundation phase is not building:

- a full TMS;
- autonomous booking;
- live DAT/API integration;
- Google Maps integration;
- Gmail or Google Sheets live integration;
- real factoring submission;
- autonomous financial or legal commitments;
- live document ingestion from Telegram;
- expanded PDF/OCR parsing.

## Near-Term Foundation Direction

Near-term work should continue to harden:

- intake record and parser contracts;
- DispatchCase and Event Timeline behavior;
- DecisionEngine boundaries;
- adapter boundaries for Telegram and CLI;
- local dry-run tools and synthetic scenarios;
- setup and dependency documentation.

Every new layer should be small, tested, explainable, and easy to replace before it becomes live automation.
