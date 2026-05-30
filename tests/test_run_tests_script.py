import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_tests


class RunTestsScriptTests(unittest.TestCase):
    def test_tests_directory_exists_and_contains_test_files(self):
        test_files = sorted(run_tests.DEFAULT_TEST_DIR.glob("test_*.py"))

        self.assertTrue(run_tests.DEFAULT_TEST_DIR.exists())
        self.assertTrue(test_files)

    def test_discovery_from_tests_directory_finds_real_suite(self):
        suite = run_tests.discover_test_suite()

        self.assertGreater(run_tests.count_tests(suite), 0)

    def test_zero_test_discovery_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            code = run_tests.main(["--start-dir", temp_dir])

        self.assertEqual(code, 2)

    def test_main_does_not_use_bare_root_discovery(self):
        observed = {}

        def fake_discover(start_dir, pattern):
            observed["start_dir"] = Path(start_dir)
            observed["pattern"] = pattern
            return unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])

        with patch.object(run_tests, "discover_test_suite", side_effect=fake_discover):
            code = run_tests.main([])

        self.assertEqual(code, 0)
        self.assertEqual(observed["start_dir"], run_tests.DEFAULT_TEST_DIR)
        self.assertEqual(observed["pattern"], run_tests.DEFAULT_PATTERN)


if __name__ == "__main__":
    unittest.main()
