import csv
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analyze_module_graph.py"
FIXTURE = ROOT / "tests" / "fixtures" / "module_graph" / "fake_project"


def _run_analyzer(repo_root, output_dir=None, *extra_args):
    command = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(repo_root),
        "--output-dir",
        str(output_dir or (repo_root / ".local_outputs" / "module_graph")),
        *extra_args,
    ]
    return subprocess.run(
        command,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path):
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


class AnalyzeModuleGraphTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.temp_dir.name) / "fake_project"
        shutil.copytree(FIXTURE, self.repo_root)
        self.output_dir = self.repo_root / ".local_outputs" / "module_graph"
        self.private_token = "PRIVATE_FIXTURE_VALUE_SHOULD_NOT_APPEAR"
        ignored_output_dir = self.repo_root / ".local_outputs"
        ignored_output_dir.mkdir(parents=True, exist_ok=True)
        (ignored_output_dir / "ignored_module.py").write_text(
            "def broken_python(",
            encoding="utf-8",
        )
        private_dir = self.repo_root / "data" / "private_ratecons"
        private_dir.mkdir(parents=True, exist_ok=True)
        (private_dir / "ignored_private_module.py").write_text(
            "def broken_private_python(",
            encoding="utf-8",
        )
        (private_dir / "private_note.txt").write_text(
            self.private_token,
            encoding="utf-8",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run_confirmed(self, *extra_args):
        result = _run_analyzer(
            self.repo_root,
            self.output_dir,
            "--confirm-local-audit-run",
            "--include-tests",
            *extra_args,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return result

    def test_refuses_without_confirm_flag(self):
        result = _run_analyzer(self.repo_root, self.output_dir)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--confirm-local-audit-run", result.stdout)

    def test_refuses_output_outside_local_outputs(self):
        result = _run_analyzer(
            self.repo_root,
            self.repo_root / "module_graph",
            "--confirm-local-audit-run",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".local_outputs", result.stdout)

    def test_writes_expected_outputs_and_detects_graph_features(self):
        self._run_confirmed("--max-rows", "1000")

        expected = {
            "module_graph_summary.json",
            "module_graph_report.md",
            "module_inventory.csv",
            "import_edges.csv",
            "entrypoints.csv",
            "orphan_module_candidates.csv",
            "script_only_modules.csv",
            "test_only_modules.csv",
            "deprecated_references.csv",
            "import_cycles.csv",
            "unclassified_modules.csv",
        }
        self.assertEqual(
            expected,
            {path.name for path in self.output_dir.iterdir() if path.is_file()},
        )

        summary = _read_json(self.output_dir / "module_graph_summary.json")
        self.assertGreaterEqual(summary["total_modules"], 10)
        self.assertGreater(summary["total_import_edges"], 0)
        self.assertGreaterEqual(summary["entrypoint_count"], 3)
        self.assertGreaterEqual(summary["orphan_candidate_count"], 1)
        self.assertGreaterEqual(summary["script_only_count"], 1)
        self.assertGreaterEqual(summary["test_only_count"], 1)
        self.assertEqual(summary["import_cycle_count"], 1)
        self.assertGreaterEqual(summary["unclassified_module_count"], 1)
        self.assertEqual(summary["deprecated_reference_count"], 1)
        self.assertEqual(summary["project_modules_imported"], False)
        self.assertEqual(summary["pdf_processing_attempted"], False)
        self.assertEqual(summary["ocr_attempted"], False)
        self.assertEqual(summary["network_or_model_calls_attempted"], False)
        self.assertIn("app/missing_module.py", summary["module_map_listed_missing"])

    def test_ignores_private_and_local_output_dirs(self):
        self._run_confirmed()

        inventory = _read_csv(self.output_dir / "module_inventory.csv")
        paths = {row["module_path"] for row in inventory}
        self.assertNotIn(".local_outputs/ignored_module.py", paths)
        self.assertNotIn("data/private_ratecons/ignored_private_module.py", paths)

        output_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in self.output_dir.iterdir()
            if path.is_file()
        )
        self.assertNotIn(self.private_token, output_text)

    def test_detects_imports_entrypoints_cycles_orphans_and_status_checks(self):
        self._run_confirmed()

        edges = _read_csv(self.output_dir / "import_edges.csv")
        internal_edges = {
            (row["importer_path"], row["imported_path"])
            for row in edges
            if row["is_internal"] == "true"
        }
        self.assertIn(("app/active.py", "app/deprecated_mod.py"), internal_edges)
        self.assertIn(("app/active.py", "app/experimental_mod.py"), internal_edges)

        entrypoints = {
            row["module_path"]
            for row in _read_csv(self.output_dir / "entrypoints.csv")
        }
        self.assertIn("main.py", entrypoints)
        self.assertIn("scripts/run_cli.py", entrypoints)

        cycles = _read_csv(self.output_dir / "import_cycles.csv")
        self.assertTrue(any("app/cycle_a.py" in row["modules"] for row in cycles))

        orphans = {
            row["module_path"]
            for row in _read_csv(self.output_dir / "orphan_module_candidates.csv")
        }
        self.assertIn("app/orphan.py", orphans)

        scripts = {
            row["module_path"]
            for row in _read_csv(self.output_dir / "script_only_modules.csv")
        }
        self.assertIn("scripts/script_only.py", scripts)

        test_only = {
            row["module_path"]
            for row in _read_csv(self.output_dir / "test_only_modules.csv")
        }
        self.assertIn("tests/helper_only.py", test_only)

        deprecated_refs = _read_csv(self.output_dir / "deprecated_references.csv")
        self.assertEqual("app/active.py", deprecated_refs[0]["importer_path"])
        self.assertEqual(
            "app/deprecated_mod.py",
            deprecated_refs[0]["deprecated_module_path"],
        )

        unclassified = {
            row["module_path"]
            for row in _read_csv(self.output_dir / "unclassified_modules.csv")
        }
        self.assertIn("app/orphan.py", unclassified)
        self.assertIn("app/side_effect_module.py", unclassified)

    def test_does_not_import_or_execute_fixture_modules(self):
        marker = self.repo_root / "module_graph_should_not_exist.txt"
        self.assertFalse(marker.exists())

        self._run_confirmed()

        self.assertFalse(marker.exists())

    def test_default_output_contains_no_private_values(self):
        self._run_confirmed()

        for path in self.output_dir.iterdir():
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(self.private_token, text)
            self.assertNotIn("ignored_private_module", text)


if __name__ == "__main__":
    unittest.main()
