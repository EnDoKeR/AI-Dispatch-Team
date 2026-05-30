import json
import tempfile
import unittest
from pathlib import Path

from app.document_ai.private_measurement_inputs import (
    PrivateMeasurementInputError,
    build_safe_aliases,
    discover_private_pdfs,
    load_alias_map,
    validate_private_input_dir,
)


class PrivateMeasurementInputTests(unittest.TestCase):
    def test_discover_private_pdfs_returns_pdfs_only_sorted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "b_ratecon.PDF").write_bytes(b"%PDF fake")
            (root / "a_ratecon.pdf").write_bytes(b"%PDF fake")
            (root / "notes.txt").write_text("not a pdf", encoding="utf-8")

            pdfs = discover_private_pdfs(root)

        self.assertEqual([path.name for path in pdfs], ["a_ratecon.pdf", "b_ratecon.PDF"])

    def test_empty_directory_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdfs = discover_private_pdfs(Path(temp_dir))

        self.assertEqual(pdfs, [])

    def test_missing_directory_raises_clear_error(self):
        missing = Path(tempfile.gettempdir()) / "missing-ratecon-measurement-dir"

        with self.assertRaises(PrivateMeasurementInputError):
            validate_private_input_dir(missing)

    def test_safe_aliases_are_stable_and_do_not_include_filenames_in_values(self):
        paths = [
            Path("Z_PRIVATE_NAME.pdf"),
            Path("A_PRIVATE_NAME.pdf"),
        ]

        aliases = build_safe_aliases(paths)

        self.assertEqual(aliases[Path("A_PRIVATE_NAME.pdf")], "RATECON_001")
        self.assertEqual(aliases[Path("Z_PRIVATE_NAME.pdf")], "RATECON_002")
        for alias in aliases.values():
            self.assertNotIn("PRIVATE_NAME", alias)

    def test_alias_prefix_customization(self):
        aliases = build_safe_aliases([Path("one.pdf")], prefix="DOC")

        self.assertEqual(aliases[Path("one.pdf")], "DOC_001")

    def test_load_alias_map_reads_json_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aliases.json"
            path.write_text(
                json.dumps({"local-key": "RATECON_099"}),
                encoding="utf-8",
            )

            aliases = load_alias_map(path)

        self.assertEqual(aliases, {"local-key": "RATECON_099"})

    def test_load_alias_map_rejects_non_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "aliases.json"
            path.write_text(json.dumps(["RATECON_001"]), encoding="utf-8")

            with self.assertRaises(PrivateMeasurementInputError):
                load_alias_map(path)


if __name__ == "__main__":
    unittest.main()
