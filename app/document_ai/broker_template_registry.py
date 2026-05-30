"""JSON broker template registry for fake/anonymized extraction templates."""

import json
from pathlib import Path

from app.document_ai.broker_templates import (
    TEMPLATE_SOURCE_PRIVATE_LOCAL,
    TEMPLATE_SOURCE_PUBLIC_FIXTURE,
    build_broker_template,
)


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


def load_broker_template(path, source=TEMPLATE_SOURCE_PUBLIC_FIXTURE):
    template_path = Path(path)

    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateRegistryError(f"Invalid broker template JSON: {template_path}") from exc

    if source:
        payload["source"] = source
        if source == TEMPLATE_SOURCE_PRIVATE_LOCAL:
            payload["is_private_local"] = True

    return validate_broker_template(build_broker_template(payload))


def load_broker_templates_from_directory(
    path,
    source=TEMPLATE_SOURCE_PUBLIC_FIXTURE,
    missing_ok=False,
):
    directory = Path(path)
    if not directory.exists():
        if missing_ok:
            return []
        raise TemplateRegistryError(f"Broker template directory not found: {directory}")

    return [
        load_broker_template(template_path, source=source)
        for template_path in sorted(directory.glob("*.json"))
    ]


class BrokerTemplateRegistry:
    def __init__(self, templates=None):
        self._templates = {}

        for template in templates or []:
            self.add_template(template)

    @classmethod
    def from_directory(cls, path, source=TEMPLATE_SOURCE_PUBLIC_FIXTURE):
        return cls(load_broker_templates_from_directory(path, source=source))

    @classmethod
    def from_directories(
        cls,
        public_dirs,
        private_dirs=None,
        allow_private_override=False,
    ):
        registry = cls()

        for directory in public_dirs or []:
            for template in load_broker_templates_from_directory(
                directory,
                source=TEMPLATE_SOURCE_PUBLIC_FIXTURE,
                missing_ok=False,
            ):
                registry.add_template(template)

        for directory in private_dirs or []:
            for template in load_broker_templates_from_directory(
                directory,
                source=TEMPLATE_SOURCE_PRIVATE_LOCAL,
                missing_ok=True,
            ):
                registry.add_template(
                    template,
                    allow_override=allow_private_override,
                    require_private_for_override=True,
                )

        return registry

    def add_template(
        self,
        template,
        allow_override=False,
        require_private_for_override=False,
    ):
        safe_template = validate_broker_template(build_broker_template(template))
        template_id = safe_template["template_id"]

        if template_id in self._templates:
            if not allow_override:
                raise TemplateRegistryError(f"Duplicate broker template_id: {template_id}")
            if require_private_for_override and not safe_template.get("is_private_local"):
                raise TemplateRegistryError(
                    f"Only private local templates can override template_id: {template_id}"
                )

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
