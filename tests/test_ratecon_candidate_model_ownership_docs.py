import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RateconCandidateModelOwnershipDocsTests(unittest.TestCase):
    def _read(self, relative_path):
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_candidate_ownership_doc_names_canonical_and_compatibility_surfaces(self):
        source = self._read("docs/ratecon_candidate_model_ownership_v1.md")

        self.assertIn("field_candidate_provenance.py", source)
        self.assertIn("canonical candidate contract", source)
        self.assertIn("field_candidate_generators.py", source)
        self.assertIn("generator and orchestration", source)
        self.assertIn("field_candidate_resolver.py", source)
        self.assertIn("consumes candidate records", source)
        self.assertIn("ratecon_candidates.py", source)
        self.assertIn("legacy RateCon candidate compatibility surface", source)
        self.assertIn("boundary adapters", source)

    def test_candidate_ownership_doc_blocks_behavior_changes(self):
        source = self._read("docs/ratecon_candidate_model_ownership_v1.md")

        self.assertIn("does not change extraction behavior", source)
        self.assertIn("does not change extraction behavior", source.lower())
        self.assertIn("Do not change resolver thresholds", source)
        self.assertIn("Do not delete legacy candidate modules", source)
        self.assertIn("Do not change candidate shapes", source)
        self.assertIn("must not be committed", source)

    def test_candidate_ownership_doc_mentions_behavior_pinning_and_guardrails(self):
        source = self._read("docs/ratecon_candidate_model_ownership_v1.md")

        self.assertIn("Behavior Pinning Status", source)
        self.assertIn("tests/test_ratecon_candidate_compatibility_pinning.py", source)
        self.assertIn("same field names", source)
        self.assertIn("same source names", source)
        self.assertIn("same confidence values", source)
        self.assertIn("same candidate shapes", source)
        self.assertIn("same resolver outputs", source)
        self.assertIn("evaluation metrics", source)
        self.assertIn("New candidate constants must go through", source)

    def test_module_map_classifies_candidate_owners(self):
        source = self._read("docs/MODULE_MAP.md")

        self.assertIn("document_ai_candidate_contract", source)
        self.assertIn("document_ai_candidate_generation", source)
        self.assertIn("document_ai_candidate_resolution", source)
        self.assertIn("legacy_ratecon_candidate_contract", source)
        self.assertIn("legacy_ratecon_candidate_generation", source)
        self.assertIn("intake_boundary_contract", source)

    def test_cleanup_strategy_references_candidate_audit(self):
        source = self._read("docs/project_structure_cleanup_strategy_v1.md")

        self.assertIn("RateCon Candidate Model Ownership", source)
        self.assertIn("scripts/audit_ratecon_candidate_model_ownership.py", source)
        self.assertIn("field_candidate_provenance.py", source)
        self.assertIn("Do not delete candidate modules", source)
        self.assertIn("Do not change candidate shapes", source)

    def test_cleanup_strategy_references_candidate_compatibility_pinning(self):
        source = self._read("docs/project_structure_cleanup_strategy_v1.md")

        self.assertIn("RateCon Candidate Compatibility Pinning", source)
        self.assertIn("tests/test_ratecon_candidate_compatibility_pinning.py", source)
        self.assertIn("tests/test_ratecon_candidate_constant_guardrails.py", source)
        self.assertIn("Current duplicate constants are compatibility debt", source)
        self.assertIn("Do not consolidate duplicates without behavior-pinning tests", source)


if __name__ == "__main__":
    unittest.main()
