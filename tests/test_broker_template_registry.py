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
from app.document_ai.broker_templates import (
    TEMPLATE_SOURCE_PRIVATE_LOCAL,
    TEMPLATE_SOURCE_PUBLIC_FIXTURE,
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
        self.assertEqual(template["source"], TEMPLATE_SOURCE_PUBLIC_FIXTURE)

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

    def test_missing_private_overlay_directory_is_okay(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-private-overlay"

            registry = BrokerTemplateRegistry.from_directories(
                [FIXTURE_DIR],
                private_dirs=[missing],
            )

        self.assertGreaterEqual(len(registry), 4)

    def test_private_overlay_template_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            overlay_dir = Path(temp_dir)
            private_template = dict(load_template_fixture("alpha_freight_mock_v1.json"))
            private_template["template_id"] = "private_overlay_template_v1"
            private_template["broker_key"] = "private_overlay_template"
            private_template["display_name"] = "PRIVATE OVERLAY TEMPLATE"
            private_template["created_for_testing"] = True
            (overlay_dir / "private_overlay_template_v1.json").write_text(
                json.dumps(private_template),
                encoding="utf-8",
            )

            registry = BrokerTemplateRegistry.from_directories(
                [FIXTURE_DIR],
                private_dirs=[overlay_dir],
            )

        template = registry.get_template("private_overlay_template_v1")
        self.assertEqual(template["source"], TEMPLATE_SOURCE_PRIVATE_LOCAL)
        self.assertTrue(template["is_private_local"])

    def test_private_overlay_duplicate_template_id_fails_without_override(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            overlay_dir = Path(temp_dir)
            private_template = dict(load_template_fixture("alpha_freight_mock_v1.json"))
            private_template["created_for_testing"] = True
            (overlay_dir / "alpha_freight_mock_v1.json").write_text(
                json.dumps(private_template),
                encoding="utf-8",
            )

            with self.assertRaises(TemplateRegistryError):
                BrokerTemplateRegistry.from_directories(
                    [FIXTURE_DIR],
                    private_dirs=[overlay_dir],
                )

    def test_private_overlay_duplicate_template_id_can_override_when_explicit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            overlay_dir = Path(temp_dir)
            private_template = dict(load_template_fixture("alpha_freight_mock_v1.json"))
            private_template["display_name"] = "PRIVATE OVERRIDE TEMPLATE"
            private_template["created_for_testing"] = True
            (overlay_dir / "alpha_freight_mock_v1.json").write_text(
                json.dumps(private_template),
                encoding="utf-8",
            )

            registry = BrokerTemplateRegistry.from_directories(
                [FIXTURE_DIR],
                private_dirs=[overlay_dir],
                allow_private_override=True,
            )

        template = registry.get_template("alpha_freight_mock_v1")
        self.assertEqual(template["source"], TEMPLATE_SOURCE_PRIVATE_LOCAL)
        self.assertTrue(template["is_private_local"])
        self.assertEqual(template["display_name"], "PRIVATE OVERRIDE TEMPLATE")


if __name__ == "__main__":
    unittest.main()
