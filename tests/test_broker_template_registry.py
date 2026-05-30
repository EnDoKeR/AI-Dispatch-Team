import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.broker_template_registry import (
    BrokerTemplateRegistry,
    TemplateRegistryError,
    load_broker_template,
    load_broker_templates_from_directory,
)
from tests.fixtures.document_ai.broker_templates.fixture_loader import (
    FIXTURE_DIR,
    load_template_fixture,
)


class BrokerTemplateRegistryTests(unittest.TestCase):
    def test_load_one_fake_template(self):
        template = load_broker_template(FIXTURE_DIR / "alpha_freight_mock_v1.json")

        self.assertEqual(template["template_id"], "alpha_freight_mock_v1")
        self.assertTrue(template["created_for_testing"])

    def test_load_all_fake_templates_from_directory(self):
        templates = load_broker_templates_from_directory(FIXTURE_DIR)

        self.assertGreaterEqual(len(templates), 4)
        self.assertTrue(all(template["created_for_testing"] for template in templates))

    def test_registry_get_by_template_id(self):
        registry = BrokerTemplateRegistry.from_directory(FIXTURE_DIR)

        template = registry.get_template("northstar_logistics_mock_v1")

        self.assertEqual(template["broker_key"], "northstar_logistics_mock")

    def test_registry_filters_inactive_templates(self):
        active = load_template_fixture("alpha_freight_mock_v1.json")
        inactive = dict(load_template_fixture("northstar_logistics_mock_v1.json"))
        inactive["template_id"] = "inactive_template"
        inactive["active"] = False
        registry = BrokerTemplateRegistry([active, inactive])

        self.assertEqual(len(registry.list_templates(active_only=True)), 1)
        self.assertEqual(len(registry.list_templates(active_only=False)), 2)

    def test_invalid_json_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.json"
            path.write_text("{not-json", encoding="utf-8")

            with self.assertRaises(TemplateRegistryError):
                load_broker_template(path)

    def test_missing_required_fields_fails_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing.json"
            path.write_text(json.dumps({"template_id": "missing"}), encoding="utf-8")

            with self.assertRaises(TemplateRegistryError):
                load_broker_template(path)

    def test_duplicate_template_id_fails(self):
        template = load_template_fixture("alpha_freight_mock_v1.json")

        with self.assertRaises(TemplateRegistryError):
            BrokerTemplateRegistry([template, template])


if __name__ == "__main__":
    unittest.main()
