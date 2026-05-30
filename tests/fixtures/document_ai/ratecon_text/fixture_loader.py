"""Helpers for loading fake RateCon text fixtures."""

from pathlib import Path

from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


FIXTURE_DIR = Path(__file__).resolve().parent

FIXTURE_NAMES = (
    "simple_clean_ratecon.txt",
    "multi_amount_ratecon.txt",
    "ambiguous_references_ratecon.txt",
    "multi_stop_ratecon.txt",
    "missing_core_fields_ratecon.txt",
    "conflict_rate_ratecon.txt",
)


def fixture_path(name):
    return FIXTURE_DIR / name


def load_fixture_text(name):
    return fixture_path(name).read_text(encoding="utf-8")


def build_fixture_text_artifact(name):
    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{name.replace('.txt', '').upper()}",
        document_id=f"DOC-{name.replace('.txt', '').upper()}",
        source_name=name,
        full_text=load_fixture_text(name),
        source_method="synthetic_fixture",
    )
