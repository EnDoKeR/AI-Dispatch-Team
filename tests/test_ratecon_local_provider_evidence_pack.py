import json
import unittest
from pathlib import Path

from app.document_ai.ratecon_local_provider_evidence_pack import (
    artifact_index_row,
    build_artifact_index,
    build_evidence_pack,
    validate_evidence_pack,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
READINESS_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_readiness"
PROVIDER_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_model_provider"
EVIDENCE_FIXTURES = REPO_ROOT / "tests" / "fixtures" / "ratecon_local_provider_evidence_pack"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class RateConLocalProviderEvidencePackTests(unittest.TestCase):
    def _valid_readiness(self) -> dict:
        return _json(READINESS_FIXTURES / "valid_fixture_only_readiness.json")

    def _valid_provider_config(self) -> dict:
        return _json(PROVIDER_FIXTURES / "valid_stub_provider_config.json")

    def _valid_smoke(self) -> dict:
        return _json(EVIDENCE_FIXTURES / "valid_evidence_inputs" / "fixture_smoke_summary.json")

    def test_valid_fixture_only_evidence_pack_validates(self):
        pack = build_evidence_pack(
            readiness_payload=self._valid_readiness(),
            provider_config=self._valid_provider_config(),
            smoke_summary=self._valid_smoke(),
        )

        self.assertTrue(validate_evidence_pack(pack).valid)
        self.assertFalse(pack["model_execution_attempted"])
        self.assertFalse(pack["pdf_processing_attempted"])
        self.assertFalse(pack["ocr_attempted"])
        self.assertFalse(pack["external_call_attempted"])

    def test_valid_fixture_only_pack_recommends_separate_design_pr(self):
        pack = build_evidence_pack(
            readiness_payload=self._valid_readiness(),
            provider_config=self._valid_provider_config(),
            smoke_summary=self._valid_smoke(),
        )

        self.assertEqual(pack["recommendation"], "ready_for_separate_local_provider_design_pr")
        self.assertIn("does not approve model implementation", pack["recommendation_note"])

    def test_missing_smoke_outputs_recommend_fixture_only_continue(self):
        pack = build_evidence_pack(
            readiness_payload=self._valid_readiness(),
            provider_config=self._valid_provider_config(),
            smoke_summary=None,
        )

        self.assertEqual(pack["recommendation"], "fixture_only_continue")
        self.assertIn("fixture smoke outputs are missing", pack["warnings"])

    def test_model_execution_attempted_rejects(self):
        smoke = _json(EVIDENCE_FIXTURES / "invalid_model_execution_attempted" / "fixture_smoke_summary.json")
        pack = build_evidence_pack(
            readiness_payload=self._valid_readiness(),
            provider_config=self._valid_provider_config(),
            smoke_summary=smoke,
        )

        self.assertEqual(pack["recommendation"], "reject")
        self.assertTrue(any("model_execution_attempted" in blocker for blocker in pack["blockers"]))

    def test_pdf_ocr_external_and_private_data_flags_reject(self):
        for key in ("pdf_processing_attempted", "ocr_attempted", "external_call_attempted", "private_data_used"):
            with self.subTest(key=key):
                smoke = self._valid_smoke()
                smoke[key] = True
                pack = build_evidence_pack(
                    readiness_payload=self._valid_readiness(),
                    provider_config=self._valid_provider_config(),
                    smoke_summary=smoke,
                )
                self.assertEqual(pack["recommendation"], "reject")

    def test_unsafe_provider_config_rejects(self):
        pack = build_evidence_pack(
            readiness_payload=self._valid_readiness(),
            provider_config=_json(PROVIDER_FIXTURES / "invalid_external_calls_config.json"),
            smoke_summary=self._valid_smoke(),
        )

        self.assertEqual(pack["recommendation"], "reject")
        self.assertTrue(any("allow_external_calls" in blocker for blocker in pack["blockers"]))

    def test_local_and_cloud_execution_requests_reject(self):
        for fixture_name in ("invalid_private_execution_approved.json", "invalid_cloud_approved.json"):
            with self.subTest(fixture_name=fixture_name):
                pack = build_evidence_pack(
                    readiness_payload=_json(READINESS_FIXTURES / fixture_name),
                    provider_config=self._valid_provider_config(),
                    smoke_summary=self._valid_smoke(),
                )
                self.assertEqual(pack["recommendation"], "reject")

    def test_artifact_index_marks_local_outputs_not_safe_to_commit(self):
        row = artifact_index_row(
            artifact_name="local_output",
            artifact_type="summary",
            path=REPO_ROOT / ".local_outputs" / "ratecon_local_provider_evidence_pack" / "summary.json",
        )

        self.assertFalse(row["safe_to_commit"])
        self.assertFalse(row["contains_private_values"])

    def test_artifact_index_detects_private_path_risk(self):
        row = artifact_index_row(
            artifact_name="private_output",
            artifact_type="summary",
            path=REPO_ROOT / ".local_outputs" / "private_ratecon_local_provider_evidence_pack" / "summary.json",
        )

        self.assertFalse(row["safe_to_commit"])
        self.assertTrue(row["contains_private_values"])

    def test_build_artifact_index_has_expected_columns(self):
        rows = build_artifact_index(
            readiness_file=READINESS_FIXTURES / "valid_fixture_only_readiness.json",
            provider_config=PROVIDER_FIXTURES / "valid_stub_provider_config.json",
            smoke_dir=EVIDENCE_FIXTURES / "valid_evidence_inputs",
            readiness_report_dir=EVIDENCE_FIXTURES / "valid_evidence_inputs",
            include_fixture_benchmark=True,
        )

        self.assertGreaterEqual(len(rows), 5)
        self.assertIn("safe_to_commit", rows[0])
        self.assertIn("contains_private_values", rows[0])


if __name__ == "__main__":
    unittest.main()
