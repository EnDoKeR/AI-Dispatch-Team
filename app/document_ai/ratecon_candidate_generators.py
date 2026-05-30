"""Candidate generators for fake/anonymized RateCon text artifacts."""

import re

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
    SOURCE_LABEL_PATTERN,
    build_candidate_extraction_result,
    build_field_candidate,
)


MONEY_PATTERN = re.compile(
    r"(?P<amount>\$\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?|"
    r"\bUSD\s?\d{1,6}(?:,\d{3})*(?:\.\d{2})?|"
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|"
    r"\b\d{4,6}(?:\.\d{2})?\b)",
    re.IGNORECASE,
)

STRONG_RATE_LABELS = (
    "carrier pay",
    "total rate",
    "agreed amount",
    "linehaul",
    "total carrier rate",
    "freight charge",
    "rate",
)

ACCESSORIAL_LABELS = (
    "detention",
    "layover",
    "lumper",
    "tonu",
    "quick pay",
    "fuel surcharge",
    "accessorial",
    "fee",
    "penalty",
    "deduction",
)


def _artifact_pages(artifact):
    if isinstance(artifact, dict):
        return artifact.get("pages", [])

    return getattr(artifact, "pages", [])


def _line_context(lines, index):
    before = lines[index - 1].strip() if index > 0 else ""
    after = lines[index + 1].strip() if index + 1 < len(lines) else ""

    return before, after


def _normalize_money(value):
    text = str(value or "").upper().replace("USD", "").replace("$", "").strip()
    return text.replace(",", "")


def _label_from_line(line, match_start):
    prefix = line[:match_start].strip(" :-\t")

    if not prefix:
        return ""

    return prefix[-80:]


def _classify_money_line(line):
    lower_line = line.lower()

    if any(label in lower_line for label in ACCESSORIAL_LABELS):
        return {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "confidence": CANDIDATE_CONFIDENCE_LOW,
            "confidence_reasons": ["accessorial_or_fee_label"],
            "warnings": ["not_final_rate_candidate"],
        }

    if any(label in lower_line for label in STRONG_RATE_LABELS):
        return {
            "field_name": FIELD_RATE,
            "confidence": CANDIDATE_CONFIDENCE_HIGH,
            "confidence_reasons": ["strong_rate_label"],
            "warnings": [],
        }

    return {
        "field_name": FIELD_RATE,
        "confidence": CANDIDATE_CONFIDENCE_MEDIUM,
        "confidence_reasons": ["money_amount_without_strong_label"],
        "warnings": ["needs_rate_context_review"],
    }


def generate_money_rate_candidates(artifact):
    candidates = []

    for page in _artifact_pages(artifact):
        page_number = page.get("page_number", "")
        lines = str(page.get("text", "") or "").splitlines()

        for line_index, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            for match_index, match in enumerate(MONEY_PATTERN.finditer(line), start=1):
                classification = _classify_money_line(line)
                context_before, context_after = _line_context(lines, line_index - 1)
                raw_value = match.group("amount")
                label = _label_from_line(line, match.start("amount"))
                candidate_id = f"money-p{page_number}-l{line_index}-{match_index}"

                candidates.append(
                    build_field_candidate(
                        candidate_id=candidate_id,
                        field_name=classification["field_name"],
                        raw_value=raw_value,
                        normalized_value=_normalize_money(raw_value),
                        confidence=classification["confidence"],
                        confidence_reasons=classification["confidence_reasons"],
                        page_number=page_number,
                        line_number=line_index,
                        label=label,
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        warnings=classification["warnings"],
                        value_type="money",
                    )
                )

    return candidates


def build_money_rate_candidate_result(artifact):
    candidates = generate_money_rate_candidates(artifact)
    warnings = []
    missing = []

    if not candidates:
        warnings.append("no_money_candidates_found")
        missing.append(FIELD_RATE)

    return build_candidate_extraction_result(
        document_id=(artifact or {}).get("document_id", ""),
        artifact_id=(artifact or {}).get("artifact_id", ""),
        candidates=candidates,
        missing_candidate_fields=missing,
        warnings=warnings,
        extractor_version="money_rate_candidates_v1",
    )
