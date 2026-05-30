"""Helpers for loading fake broker template fixtures."""

import json
from pathlib import Path

from app.document_ai.broker_templates import build_broker_template


FIXTURE_DIR = Path(__file__).resolve().parent

TEMPLATE_FIXTURE_NAMES = (
    "alpha_freight_mock_v1.json",
    "northstar_logistics_mock_v1.json",
    "tablelane_transport_mock_v1.json",
    "conflict_mock_v1.json",
)


def template_fixture_path(name):
    return FIXTURE_DIR / name


def load_template_fixture_payload(name):
    return json.loads(template_fixture_path(name).read_text(encoding="utf-8"))


def load_template_fixture(name):
    return build_broker_template(load_template_fixture_payload(name))


def load_all_template_fixtures():
    return [
        load_template_fixture(name)
        for name in TEMPLATE_FIXTURE_NAMES
    ]
