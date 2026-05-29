from copy import deepcopy

from app.market_intelligence.decision_engine.approval_modes import (
    MODE_COPILOT,
    normalize_approval_mode,
)


SIGNAL_GROUPS = (
    "load_facts",
    "notes_facts",
    "driver_profile",
    "broker_memory",
    "market_context",
    "dispatch_memory",
    "intake_evidence",
    "approval_context",
)


def value_from(source, key, default=None):
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def json_safe(value):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): json_safe(item)
            for key, item in value.items()
        }

    if hasattr(value, "__dict__"):
        return {
            str(key): json_safe(item)
            for key, item in vars(value).items()
            if not str(key).startswith("_")
        }

    return str(value)


def normalize_signal_group(value):
    if value is None:
        return {}

    if isinstance(value, dict):
        return json_safe(deepcopy(value))

    if hasattr(value, "__dict__"):
        return json_safe(value)

    return {}


def normalize_approval_context(value):
    context = normalize_signal_group(value)
    context["approval_mode"] = normalize_approval_mode(
        context.get("approval_mode", MODE_COPILOT)
    )
    return context


def build_decision_signal_bundle(source=None, **overrides):
    source = source or {}
    values = {}

    for group in SIGNAL_GROUPS:
        values[group] = value_from(source, group, None)

    for key, value in overrides.items():
        if key in SIGNAL_GROUPS:
            values[key] = value

    bundle = {}

    for group in SIGNAL_GROUPS:
        if group == "approval_context":
            bundle[group] = normalize_approval_context(values[group])
        else:
            bundle[group] = normalize_signal_group(values[group])

    return bundle
