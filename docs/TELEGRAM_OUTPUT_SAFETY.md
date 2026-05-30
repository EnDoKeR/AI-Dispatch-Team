# Telegram Output Safety

Telegram is an output adapter. It formats and sends information produced by the
domain and decision layers; it must not decide whether a load is acceptable,
rejected, or ready for dispatch.

## Required Output

Decision-oriented Telegram output should show:

- recommendation;
- confidence;
- approval-required state;
- missing critical fields;
- low-confidence fields;
- needs-check fields;
- risk flags;
- rules fired;
- reasons;
- next human action when review is required.

Low-confidence loads must not be described as good, ready, or safe unless an
upstream DecisionResult explicitly produced that recommendation and the message
also shows the confidence and missing/needs-check fields.

## Boundaries

Telegram formatters must not:

- import parser modules to make a dispatch decision;
- import case mutation code;
- write timeline events;
- hide missing critical fields;
- print raw private RateCon text;
- include private PDF snippets.

If an upstream result has no recommendation, formatter fallback should be
review-safe, not acceptance-oriented.

## Current Helper

`app/market_intelligence/telegram_decision_result_formatter.py` formats an
already-built DecisionResult-like dictionary. It is not wired into existing
runtime Telegram flows yet; it exists as a safe output contract for future
DecisionResult presentation.
