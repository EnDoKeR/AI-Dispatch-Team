"""Helpers for loading fake RateCon text fixtures."""

from pathlib import Path

from app.document_ai.text_artifacts import build_text_extraction_artifact_for_candidates


FIXTURE_DIR = Path(__file__).resolve().parent
HARD_LAYOUT_FIXTURE_DIR = FIXTURE_DIR / "hard_layouts"

FIXTURE_NAMES = (
    "simple_clean_ratecon.txt",
    "multi_amount_ratecon.txt",
    "ambiguous_references_ratecon.txt",
    "multi_stop_ratecon.txt",
    "missing_core_fields_ratecon.txt",
    "conflict_rate_ratecon.txt",
    "alpha_freight_mock_ratecon.txt",
    "northstar_logistics_mock_ratecon.txt",
    "tablelane_transport_mock_ratecon.txt",
    "unknown_broker_ratecon.txt",
    "template_conflict_ratecon.txt",
)

HARD_LAYOUT_FIXTURE_NAMES = (
    "repeated_headers_terms_ratecon.txt",
    "multi_page_rate_terms_ratecon.txt",
    "table_like_stops_ratecon.txt",
    "missing_broker_mc_header_only_ratecon.txt",
    "carrier_vs_broker_confusion_ratecon.txt",
    "references_near_wrong_stop_ratecon.txt",
    "conflicting_appointment_times_ratecon.txt",
    "buried_special_requirements_ratecon.txt",
    "revised_rate_conflict_ratecon.txt",
    "unknown_hard_layout_ratecon.txt",
)

ALL_FIXTURE_NAMES = FIXTURE_NAMES + HARD_LAYOUT_FIXTURE_NAMES


def fixture_path(name):
    direct_path = FIXTURE_DIR / name
    if direct_path.exists():
        return direct_path

    hard_layout_path = HARD_LAYOUT_FIXTURE_DIR / name
    if hard_layout_path.exists():
        return hard_layout_path

    return direct_path


def load_fixture_text(name):
    return fixture_path(name).read_text(encoding="utf-8")


def fixture_pages_from_text(text):
    pages = []
    current_lines = []

    for line in str(text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("--- PAGE ") and stripped.endswith("---"):
            if current_lines:
                pages.append("\n".join(current_lines).strip())
                current_lines = []
            continue

        current_lines.append(line)

    if current_lines:
        pages.append("\n".join(current_lines).strip())

    return [page for page in pages if page]


def build_fixture_text_artifact(name):
    text = load_fixture_text(name)
    pages = fixture_pages_from_text(text)

    return build_text_extraction_artifact_for_candidates(
        artifact_id=f"ART-{name.replace('.txt', '').upper()}",
        document_id=f"DOC-{name.replace('.txt', '').upper()}",
        source_name=name,
        pages=pages,
        full_text=text,
        source_method="synthetic_fixture",
    )
