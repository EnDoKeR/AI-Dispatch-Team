"""Generate local-only private broker template draft skeletons."""

import json
from pathlib import Path

from app.document_ai.broker_templates import TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT


DEFAULT_PRIVATE_TEMPLATE_DRAFT_DIR = Path(
    ".local_outputs/private_ratecon_measurement/private_template_drafts"
)


def _text(value):
    return str(value or "").strip()


def _safe_list(values):
    result = []
    for value in values or []:
        text = _text(value)
        if text and text not in result:
            result.append(text)
    return result


def build_private_template_draft_skeleton(family, index=1):
    family_alias = _text((family or {}).get("family_alias", f"TEMPLATE_FAMILY_{index:03d}"))
    draft_id = f"PRIVATE_TEMPLATE_DRAFT_{index:03d}"
    rate_labels = _safe_list((family or {}).get("likely_rate_labels_redacted", []))
    stop_labels = _safe_list((family or {}).get("likely_stop_labels_redacted", []))
    reference_labels = _safe_list((family or {}).get("likely_reference_labels_redacted", []))
    markers = _safe_list((family or {}).get("common_redacted_markers", []))

    return {
        "template_id": draft_id,
        "broker_key": draft_id.lower(),
        "display_name": draft_id,
        "version": "local_draft_v1",
        "active": False,
        "source": TEMPLATE_SOURCE_PRIVATE_LOCAL_DRAFT,
        "is_private_local": True,
        "description": f"Local-only draft skeleton from {family_alias}",
        "match_rules": [
            {
                "keywords": markers[:10],
                "aliases": [],
                "exclude_keywords": [],
                "mc_numbers": [],
                "email_domains": [],
                "min_keyword_hits": 1,
                "confidence_boost": 0.1,
                "confidence_penalty": 0.0,
            }
        ],
        "field_label_rules": [
            {
                "field_name": "rate",
                "labels": rate_labels,
                "negative_labels": [],
                "section_labels": [],
                "regex_patterns": [],
                "confidence_boost": 0.1,
                "confidence_penalty": 0.0,
                "notes": "Local draft only; manually review before use.",
            }
        ],
        "stop_section_rules": [
            {
                "pickup_labels": stop_labels,
                "delivery_labels": stop_labels,
                "generic_stop_labels": stop_labels,
                "appointment_labels": [],
                "location_patterns": [],
                "date_patterns": [],
                "time_patterns": [],
            }
        ],
        "reference_type_rules": [
            {
                "reference_type": "unknown_reference",
                "labels": reference_labels,
                "negative_labels": [],
                "confidence_boost": 0.05,
            }
        ],
        "known_accessorial_labels": [],
        "known_rate_labels": rate_labels,
        "known_equipment_labels": [],
        "known_special_requirement_labels": [],
        "warnings": [
            "local_private_template_draft_only",
            "manual_review_required_before_use",
            "do_not_commit_if_filled_with_real_broker_data",
        ],
        "created_for_testing": False,
        "source_family_alias": family_alias,
        "source_aliases": _safe_list((family or {}).get("aliases", [])),
    }


def write_private_template_draft_skeletons(families, output_dir=None):
    directory = Path(output_dir) if output_dir else DEFAULT_PRIVATE_TEMPLATE_DRAFT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    paths = []

    for index, family in enumerate(families or [], start=1):
        skeleton = build_private_template_draft_skeleton(family, index=index)
        family_alias = _text(family.get("family_alias", f"TEMPLATE_FAMILY_{index:03d}"))
        path = directory / f"{family_alias}.template_skeleton.json"
        path.write_text(json.dumps(skeleton, indent=2, sort_keys=True), encoding="utf-8")
        paths.append(path)

    return paths
