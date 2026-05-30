"""JSON broker template registry for fake/anonymized extraction templates."""

import json
from pathlib import Path

from app.document_ai.broker_templates import build_broker_template


class TemplateRegistryError(ValueError):
    """Raised when a broker template registry cannot load safely."""


REQUIRED_TEMPLATE_FIELDS = (
    "template_id",
    "broker_key",
    "display_name",
    "version",
)


def validate_broker_template(template):
    missing = [
        field_name
        for field_name in REQUIRED_TEMPLATE_FIELDS
        if not str(template.get(field_name, "")).strip()
    ]

    if missing:
        raise TemplateRegistryError(
            f"Broker template missing required fields: {', '.join(missing)}"
        )

    return template


def load_broker_template(path):
    template_path = Path(path)

    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateRegistryError(f"Invalid broker template JSON: {template_path}") from exc

    return validate_broker_template(build_broker_template(payload))


def load_broker_templates_from_directory(path):
    directory = Path(path)
    if not directory.exists():
        raise TemplateRegistryError(f"Broker template directory not found: {directory}")

    return [
        load_broker_template(template_path)
        for template_path in sorted(directory.glob("*.json"))
    ]


class BrokerTemplateRegistry:
    def __init__(self, templates=None):
        self._templates = {}

        for template in templates or []:
            self.add_template(template)

    @classmethod
    def from_directory(cls, path):
        return cls(load_broker_templates_from_directory(path))

    def add_template(self, template):
        safe_template = validate_broker_template(build_broker_template(template))
        template_id = safe_template["template_id"]

        if template_id in self._templates:
            raise TemplateRegistryError(f"Duplicate broker template_id: {template_id}")

        self._templates[template_id] = safe_template
        return safe_template

    def list_templates(self, active_only=True):
        templates = list(self._templates.values())
        if active_only:
            return [
                template
                for template in templates
                if template.get("active", True)
            ]

        return templates

    def get_template(self, template_id):
        template = self._templates.get(str(template_id or "").strip())
        if not template:
            raise TemplateRegistryError(f"Unknown broker template_id: {template_id}")

        return template

    def __len__(self):
        return len(self._templates)
