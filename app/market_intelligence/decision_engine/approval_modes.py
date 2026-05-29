MODE_COPILOT = "COPILOT"
MODE_SUPERVISED = "SUPERVISED"
MODE_AUTOPILOT = "AUTOPILOT"

APPROVAL_MODES = (
    MODE_COPILOT,
    MODE_SUPERVISED,
    MODE_AUTOPILOT,
)

APPROVAL_MODE_ALIASES = {
    "AUTO_PILOT": MODE_AUTOPILOT,
}

SAFE_INFORMATIONAL_ACTIONS = {
    "NO_ACTION",
    "INFO_ONLY",
    "SHOW_RECOMMENDATION",
    "FORMAT_PREVIEW",
    "DRY_RUN_REPORT",
    "LOG_ONLY",
}

COMMITMENT_ACTIONS = {
    "BOOK_LOAD",
    "CONFIRM_BOOKING",
    "RATE_COMMITMENT",
    "RATE_NEGOTIATION",
    "SEND_RATE_CONFIRMATION",
    "SEND_FACTORING_PACKET",
    "SUBMIT_FACTORING",
    "LEGAL_COMMITMENT",
    "FINANCIAL_COMMITMENT",
}


def normalize_token(value):
    text = str(value or "").strip().upper()

    for old, new in [
        ("-", "_"),
        (" ", "_"),
        ("/", "_"),
    ]:
        text = text.replace(old, new)

    while "__" in text:
        text = text.replace("__", "_")

    return text.strip("_")


def normalize_approval_mode(value):
    mode = normalize_token(value)

    if mode in APPROVAL_MODE_ALIASES:
        return APPROVAL_MODE_ALIASES[mode]

    if mode in APPROVAL_MODES:
        return mode

    return MODE_COPILOT


def normalize_action_type(value):
    return normalize_token(value) or "NO_ACTION"


def is_commitment_action(action_type):
    return normalize_action_type(action_type) in COMMITMENT_ACTIONS


def is_safe_informational_action(action_type):
    return normalize_action_type(action_type) in SAFE_INFORMATIONAL_ACTIONS


def approval_required_for_action(mode, action_type):
    normalize_approval_mode(mode)
    action = normalize_action_type(action_type)

    if action in SAFE_INFORMATIONAL_ACTIONS:
        return False

    if action in COMMITMENT_ACTIONS:
        return True

    return True


def is_autonomous_action_allowed(mode, action_type):
    normalize_approval_mode(mode)
    action = normalize_action_type(action_type)

    if action in COMMITMENT_ACTIONS:
        return False

    if action in SAFE_INFORMATIONAL_ACTIONS:
        return True

    return False
