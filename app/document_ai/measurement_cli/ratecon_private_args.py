"""Argument parser for the private RateCon measurement CLI."""

import argparse
from pathlib import Path

from app.document_ai.field_candidate_generators import (
    LOAD_CANDIDATE_PROFILES,
    STOP_CANDIDATE_PROFILES,
)
from app.document_ai.field_candidate_resolver import (
    LOAD_RANKING_PROFILES,
    RANKING_PROFILES,
    RATE_RANKING_PROFILES,
    STOP_RANKING_PROFILES,
)
from app.document_ai.layout_provider_contract import SHADOW_LAYOUT_PROVIDER_CHOICES
from app.document_ai.ocr_provider_contract import (
    OCR_PAGE_MODE_CHOICES,
    OCR_PROVIDER_CHOICES,
)
from app.document_ai.pdfplumber_layout_settings import PDFPLUMBER_TABLE_SETTING_PROFILES
from app.document_ai.measurement_cli.ratecon_private_output_paths import (
    DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR,
)
from app.document_ai.ratecon_ocr_candidate_policy import OCR_CANDIDATE_POLICIES
from app.document_ai.ratecon_stop_draft_profile import STOP_DRAFT_PROFILES
from app.document_ai.ratecon_stop_fusion_profile import STOP_FUSION_PROFILES


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TEMPLATE_DIR = (
    REPO_ROOT / "tests" / "fixtures" / "document_ai" / "broker_templates"
)


def build_private_ratecon_measurement_parser():
    """Build the private RateCon measurement parser without running measurement."""
    parser = argparse.ArgumentParser(
        description=(
            "Run safe local-only private RateCon measurement. Requires explicit "
            "confirmation and never prints raw text or private values."
        )
    )
    parser.add_argument("--input-dir", required=True, help="Local private PDF directory.")
    parser.add_argument(
        "--confirm-private-local-run",
        action="store_true",
        help="Required confirmation that this is a local private run.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_PRIVATE_MEASUREMENT_OUTPUT_DIR),
        help="Local-only output directory for safe summaries.",
    )
    parser.add_argument(
        "--template-dir",
        default=str(DEFAULT_TEMPLATE_DIR),
        help="Fake/anonymized broker template directory.",
    )
    parser.add_argument("--alias-prefix", default="RATECON")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--write-json", action="store_true")
    parser.add_argument("--write-csv", action="store_true")
    parser.add_argument("--write-md", action="store_true")
    parser.add_argument("--write-value-review-template", action="store_true")
    parser.add_argument("--private-template-dir", default="")
    parser.add_argument("--allow-private-template-overlay", action="store_true")
    parser.add_argument("--redact-private-template-names", action="store_true", default=True)
    parser.add_argument("--layout-provider", default="")
    parser.add_argument("--enable-layout-candidates", action="store_true")
    parser.add_argument("--enable-layout-fusion", action="store_true")
    parser.add_argument("--layout-diagnostics", action="store_true")
    parser.add_argument("--compare-pdfplumber-table-profiles", action="store_true")
    parser.add_argument(
        "--pdfplumber-table-profile",
        default="default",
        choices=PDFPLUMBER_TABLE_SETTING_PROFILES,
    )
    parser.add_argument("--enable-no-regression-fusion", action="store_true", default=True)
    parser.add_argument("--allow-layout-regression-for-debug", action="store_true")
    parser.add_argument("--compare-layout-to-text-baseline", action="store_true")
    parser.add_argument("--write-stop-review-packet", action="store_true")
    parser.add_argument("--write-stop-provenance-report", action="store_true")
    parser.add_argument("--write-google-sheet-export", action="store_true")
    parser.add_argument("--write-review-workbook", action="store_true")
    parser.add_argument("--write-review-csvs", action="store_true")
    parser.add_argument("--write-candidate-coverage", action="store_true")
    parser.add_argument("--write-load-identifier-audit", action="store_true")
    parser.add_argument("--write-load-identifier-source-line-audit", action="store_true")
    parser.add_argument("--write-load-generated-resolver-provenance-sidecars", action="store_true")
    parser.add_argument("--write-rate-forensics", action="store_true")
    parser.add_argument("--write-rate-conflict-audit", action="store_true")
    parser.add_argument("--ratecon-shadow-document-pipeline", action="store_true")
    parser.add_argument("--include-document-ai-debug", action="store_true")
    parser.add_argument("--write-ratecon-shadow-audit", action="store_true")
    parser.add_argument("--strict-ratecon-shadow-document-pipeline", action="store_true")
    parser.add_argument(
        "--ratecon-shadow-layout-provider",
        default="native_text",
        choices=SHADOW_LAYOUT_PROVIDER_CHOICES,
        help=(
            "Shadow-only document layout provider. Default native_text preserves "
            "existing behavior; auto/pdfplumber are diagnostic sidecars only."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-table-profile",
        default="default",
        choices=PDFPLUMBER_TABLE_SETTING_PROFILES,
        help="Shadow-only pdfplumber table profile when coordinate layout is requested.",
    )
    parser.add_argument(
        "--ratecon-shadow-ranking-profile",
        default="baseline",
        choices=sorted(RANKING_PROFILES),
        help=(
            "Shadow-only resolver ranking profile. Default baseline preserves "
            "current behavior; gold_diagnostic_v1 is an explicit local "
            "gold-evaluation experiment."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-load-candidate-profile",
        default="baseline",
        choices=sorted(LOAD_CANDIDATE_PROFILES),
        help=(
            "Shadow-only load candidate generation profile. Default baseline "
            "preserves current candidate generation; header_recall_v1 enables "
            "a local gold-recall experiment for generic document header/title "
            "load identifiers; header_recall_table_safety_v1 also applies "
            "generic table-neighbor safety metadata/penalties; "
            "header_recall_table_abstain_v1 conservatively abstains from "
            "ambiguous table-neighbor load selections."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-load-ranking-profile",
        default=None,
        choices=sorted(LOAD_RANKING_PROFILES),
        help=(
            "Shadow-only field-scoped load_number ranking/candidate profile. "
            "When set to a header_recall* profile, it also drives the "
            "corresponding load candidate generation profile. If omitted, "
            "the legacy broad --ratecon-shadow-ranking-profile behavior is "
            "preserved."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-rate-ranking-profile",
        default=None,
        choices=sorted(RATE_RANKING_PROFILES),
        help=(
            "Shadow-only field-scoped total_carrier_rate ranking profile. "
            "money_abstain_v1 applies local-only money-context abstention. "
            "If omitted, the legacy broad --ratecon-shadow-ranking-profile "
            "behavior is preserved."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-provider",
        default="none",
        choices=OCR_PROVIDER_CHOICES,
        help=(
            "Shadow-only optional local OCR provider. Default none preserves "
            "current behavior; auto/tesseract never use cloud services."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-pages",
        default="ocr_required",
        choices=OCR_PAGE_MODE_CHOICES,
        help="Shadow-only OCR page selection mode.",
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-dpi",
        default=200,
        type=int,
        choices=[150, 200, 300],
        help="Shadow-only OCR render DPI when local OCR is explicitly enabled.",
    )
    parser.add_argument(
        "--ratecon-shadow-ocr-candidate-policy",
        default="baseline",
        choices=sorted(OCR_CANDIDATE_POLICIES),
        help=(
            "Shadow-only OCR candidate selection policy. "
            "fill_missing_strict_v1 keeps OCR diagnostic and only lets safe OCR "
            "candidates fill missing load/rate fields."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-stop-candidate-profile",
        default="baseline",
        choices=sorted(STOP_CANDIDATE_PROFILES),
        help=(
            "Shadow-only pickup/delivery stop candidate assembly profile. "
            "ocr_block_assembly_v1 emits structured OCR stop block candidates "
            "without changing default behavior; ocr_geometry_block_v1 uses "
            "optional OCR TSV geometry when available; ocr_geometry_column_v1 "
            "uses TSV row/column bands for stop table reconstruction."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-stop-ranking-profile",
        default="baseline",
        choices=sorted(STOP_RANKING_PROFILES),
        help=(
            "Shadow-only pickup/delivery stop selection profile. "
            "stop_component_strict_v1 conservatively abstains from ambiguous "
            "or weakly role-scoped structured stop candidates; "
            "stop_alignment_strict_v1 additionally gates OCR stop block "
            "candidates by component alignment; stop_geometry_strict_v1 "
            "requires geometry role/boundary evidence for OCR geometry stops; "
            "stop_column_strict_v1 requires row/column evidence for OCR "
            "column-reconstructed stops."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-stop-draft-profile",
        default="none",
        choices=sorted(STOP_DRAFT_PROFILES),
        help=(
            "Shadow-only stop review draft profile. "
            "dispatch_usable_review_v1 serializes dispatch-usable stop "
            "candidates into a separate review-required draft group without "
            "changing selected shadow or legacy output."
        ),
    )
    parser.add_argument(
        "--ratecon-shadow-stop-fusion-profile",
        default="none",
        choices=sorted(STOP_FUSION_PROFILES),
        help=(
            "Shadow-only stop fusion review profile. review_safe_v1 emits "
            "only high-provenance review-required fused stop drafts into a "
            "separate private-eval group; selected shadow and legacy output "
            "remain unchanged."
        ),
    )
    parser.add_argument(
        "--strict-ratecon-shadow-ocr",
        action="store_true",
        help="Fail cleanly when explicit shadow OCR cannot run.",
    )
    parser.add_argument(
        "--ratecon-shadow-use-legacy-final-candidates",
        action="store_true",
        help=(
            "Explicitly enable diagnostic legacy-final FieldCandidate fallback "
            "in shadow mode. This is already enabled by default for private "
            "measurement diagnostics."
        ),
    )
    parser.add_argument(
        "--no-ratecon-shadow-legacy-final-candidates",
        action="store_true",
        help=(
            "Disable diagnostic legacy-final FieldCandidate fallback in shadow mode. "
            "Independent candidates are always counted separately."
        ),
    )
    parser.add_argument("--sync-review-google-sheet", action="store_true")
    parser.add_argument("--confirm-google-review-sync", action="store_true")
    parser.add_argument("--google-config", default="")
    parser.add_argument("--google-spreadsheet-id", default="")
    parser.add_argument("--google-credentials-json", default="")
    parser.add_argument("--google-worksheet-prefix", default="RC_")
    parser.add_argument("--natural-sort-inputs", action="store_true")
    parser.add_argument("--enable-stop-span-extractor", action="store_true")
    parser.add_argument("--compare-stop-span-to-stop-group-pipeline", action="store_true")
    parser.add_argument("--include-private-stop-values-local-only", action="store_true")
    parser.add_argument("--include-private-review-values-local-only", action="store_true")
    parser.add_argument("--include-private-review-values-google-test-only", action="store_true")
    parser.add_argument(
        "--include-private-eval-values",
        action="store_true",
        help=(
            "Local-only gold-evaluation mode: include comparable private legacy, "
            "shadow, and candidate values in the shadow audit. Outputs must stay "
            "under .local_outputs and must not be committed."
        ),
    )
    parser.add_argument("--include-filenames-local-only", action="store_true")
    parser.add_argument("--include-file-hash-prefix-local-only", action="store_true")
    parser.add_argument("--allow-custom-output-dir", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def parse_private_ratecon_measurement_args(argv=None):
    """Parse private RateCon measurement args without running measurement."""
    return build_private_ratecon_measurement_parser().parse_args(argv)
