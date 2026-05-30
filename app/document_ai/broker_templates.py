"""Broker template contracts for document extraction.

BrokerTemplate describes fake/anonymized document layout and label vocabulary.
It is not broker memory, broker risk, payment history, or dispatch policy.
"""


BROKER_TEMPLATE_CONTRACT_VERSION = "broker_template_contract_v1"
TEMPLATE_SOURCE_PUBLIC_FIXTURE = "public_fixture"
TEMPLATE_SOURCE_PUBLIC_GENERIC = "public_generic"
TEMPLATE_SOURCE_PRIVATE_LOCAL = "private_local"
TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT = "private_local_draft"


def _text(value):
    return str(value or "").strip()


def _number(value, default=0.0):
    if value in [None, ""]:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_list(value):
    if value is None:
        return []

    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        _text(item)
        for item in values
        if _text(item)
    ]


def _normalize_rule_list(value, builder):
    return [
        builder(item) if isinstance(item, dict) else builder({})
        for item in value or []
    ]


def build_broker_template_version(
    template_id="",
    broker_key="",
    display_name="",
    version="",
    active=True,
    description="",
):
    return {
        "template_id": _text(template_id),
        "broker_key": _text(broker_key),
        "display_name": _text(display_name),
        "version": _text(version),
        "active": bool(active),
        "description": _text(description),
    }


def build_broker_template_match_rule(source=None):
    source = source or {}

    return {
        "keywords": _normalize_list(source.get("keywords", [])),
        "aliases": _normalize_list(source.get("aliases", [])),
        "exclude_keywords": _normalize_list(source.get("exclude_keywords", [])),
        "mc_numbers": _normalize_list(source.get("mc_numbers", [])),
        "email_domains": _normalize_list(source.get("email_domains", [])),
        "min_keyword_hits": int(source.get("min_keyword_hits", 1) or 1),
        "confidence_boost": _number(source.get("confidence_boost", 0.0)),
        "confidence_penalty": _number(source.get("confidence_penalty", 0.0)),
    }


def build_field_label_rule(source=None):
    source = source or {}

    return {
        "field_name": _text(source.get("field_name", "")),
        "labels": _normalize_list(source.get("labels", [])),
        "negative_labels": _normalize_list(source.get("negative_labels", [])),
        "section_labels": _normalize_list(source.get("section_labels", [])),
        "regex_patterns": _normalize_list(source.get("regex_patterns", [])),
        "confidence_boost": _number(source.get("confidence_boost", 0.0)),
        "confidence_penalty": _number(source.get("confidence_penalty", 0.0)),
        "notes": _text(source.get("notes", "")),
    }


def build_stop_section_rule(source=None):
    source = source or {}

    return {
        "pickup_labels": _normalize_list(source.get("pickup_labels", [])),
        "delivery_labels": _normalize_list(source.get("delivery_labels", [])),
        "generic_stop_labels": _normalize_list(source.get("generic_stop_labels", [])),
        "appointment_labels": _normalize_list(source.get("appointment_labels", [])),
        "location_patterns": _normalize_list(source.get("location_patterns", [])),
        "date_patterns": _normalize_list(source.get("date_patterns", [])),
        "time_patterns": _normalize_list(source.get("time_patterns", [])),
    }


def build_reference_type_rule(source=None):
    source = source or {}

    return {
        "reference_type": _text(source.get("reference_type", "")),
        "labels": _normalize_list(source.get("labels", [])),
        "negative_labels": _normalize_list(source.get("negative_labels", [])),
        "confidence_boost": _number(source.get("confidence_boost", 0.0)),
    }


def build_broker_template(source=None):
    source = source or {}
    template_source = _text(source.get("source", TEMPLATE_SOURCE_PUBLIC_FIXTURE))
    version = build_broker_template_version(
        template_id=source.get("template_id", ""),
        broker_key=source.get("broker_key", ""),
        display_name=source.get("display_name", ""),
        version=source.get("version", ""),
        active=source.get("active", True),
        description=source.get("description", ""),
    )

    return {
        **version,
        "match_rules": _normalize_rule_list(
            source.get("match_rules", []),
            build_broker_template_match_rule,
        ),
        "field_label_rules": _normalize_rule_list(
            source.get("field_label_rules", []),
            build_field_label_rule,
        ),
        "stop_section_rules": _normalize_rule_list(
            source.get("stop_section_rules", []),
            build_stop_section_rule,
        ),
        "reference_type_rules": _normalize_rule_list(
            source.get("reference_type_rules", []),
            build_reference_type_rule,
        ),
        "known_accessorial_labels": _normalize_list(source.get("known_accessorial_labels", [])),
        "known_rate_labels": _normalize_list(source.get("known_rate_labels", [])),
        "known_equipment_labels": _normalize_list(source.get("known_equipment_labels", [])),
        "known_special_requirement_labels": _normalize_list(
            source.get("known_special_requirement_labels", [])
        ),
        "warnings": _normalize_list(source.get("warnings", [])),
        "created_for_testing": bool(source.get("created_for_testing", False)),
        "source": template_source,
        "is_private_local": bool(source.get("is_private_local", False))
        or template_source in [TEMPLATE_SOURCE_PRIVATE_LOCAL, TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT],
        "contract_version": _text(
            source.get("contract_version", BROKER_TEMPLATE_CONTRACT_VERSION)
            or BROKER_TEMPLATE_CONTRACT_VERSION
        ),
    }


def build_template_match_result(
    template_id="",
    broker_key="",
    confidence=0.0,
    matched_keywords=None,
    excluded_keywords=None,
    reasons=None,
    warnings=None,
):
    return {
        "template_id": _text(template_id),
        "broker_key": _text(broker_key),
        "confidence": _number(confidence),
        "matched_keywords": _normalize_list(matched_keywords),
        "excluded_keywords": _normalize_list(excluded_keywords),
        "reasons": _normalize_list(reasons),
        "warnings": _normalize_list(warnings),
    }
