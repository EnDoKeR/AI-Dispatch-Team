"""Candidate generators for fake/anonymized RateCon text artifacts."""

import re

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_BROKER_MC,
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_ACCESSORIAL_TERM,
    FIELD_LOAD_NUMBER,
    FIELD_REFERENCE,
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

BROKER_NAME_LABELS = (
    "broker",
    "broker name",
    "logistics company",
    "carrier rate confirmation from",
)

CARRIER_NAME_LABELS = (
    "carrier name",
    "carrier",
)

REFERENCE_LABELS = (
    ("load #", FIELD_LOAD_NUMBER, "broker_load_number", CANDIDATE_CONFIDENCE_HIGH),
    ("load number", FIELD_LOAD_NUMBER, "broker_load_number", CANDIDATE_CONFIDENCE_HIGH),
    ("load no", FIELD_LOAD_NUMBER, "broker_load_number", CANDIDATE_CONFIDENCE_HIGH),
    ("order #", FIELD_LOAD_NUMBER, "broker_load_number", CANDIDATE_CONFIDENCE_HIGH),
    ("shipment #", FIELD_LOAD_NUMBER, "broker_load_number", CANDIDATE_CONFIDENCE_HIGH),
    ("po #", FIELD_REFERENCE, "po_number", CANDIDATE_CONFIDENCE_HIGH),
    ("po number", FIELD_REFERENCE, "po_number", CANDIDATE_CONFIDENCE_HIGH),
    ("bol #", FIELD_REFERENCE, "bol_number", CANDIDATE_CONFIDENCE_HIGH),
    ("bol number", FIELD_REFERENCE, "bol_number", CANDIDATE_CONFIDENCE_HIGH),
    ("pickup number", FIELD_REFERENCE, "pickup_number", CANDIDATE_CONFIDENCE_HIGH),
    ("delivery number", FIELD_REFERENCE, "delivery_number", CANDIDATE_CONFIDENCE_HIGH),
    ("customer reference", FIELD_REFERENCE, "customer_reference", CANDIDATE_CONFIDENCE_HIGH),
    ("appointment number", FIELD_REFERENCE, "appointment_number", CANDIDATE_CONFIDENCE_MEDIUM),
    ("reference", FIELD_REFERENCE, "unknown_reference", CANDIDATE_CONFIDENCE_LOW),
)

MC_PATTERN = re.compile(
    r"\b(?P<label>broker\s+mc|mc\s*number|mc#?|mc)\s*[:#]?\s*(?P<value>MC?\s?\d{5,8}|\d{5,8})\b",
    re.IGNORECASE,
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


def _normalize_mc(value):
    text = str(value or "").upper().replace(" ", "").replace("#", "")

    if text.startswith("MC"):
        return text

    return f"MC{text}" if text else ""


def _split_label_value(line):
    if ":" in line:
        label, value = line.split(":", 1)
        return label.strip(), value.strip()

    return "", ""


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


def generate_identity_reference_candidates(artifact):
    candidates = []

    for page in _artifact_pages(artifact):
        page_number = page.get("page_number", "")
        lines = str(page.get("text", "") or "").splitlines()

        for line_index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            lower_line = stripped.lower()
            label, value = _split_label_value(stripped)
            lower_label = label.lower()
            context_before, context_after = _line_context(lines, line_index - 1)

            for match in MC_PATTERN.finditer(stripped):
                candidates.append(
                    build_field_candidate(
                        candidate_id=f"broker-mc-p{page_number}-l{line_index}",
                        field_name=FIELD_BROKER_MC,
                        raw_value=match.group("value"),
                        normalized_value=_normalize_mc(match.group("value")),
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                        confidence_reasons=["broker_mc_label"],
                        page_number=page_number,
                        line_number=line_index,
                        label=match.group("label"),
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="broker_mc",
                    )
                )

            if value:
                if lower_label in BROKER_NAME_LABELS:
                    candidates.append(
                        build_field_candidate(
                            candidate_id=f"broker-name-p{page_number}-l{line_index}",
                            field_name=FIELD_BROKER_NAME,
                            raw_value=value,
                            normalized_value=value,
                            confidence=CANDIDATE_CONFIDENCE_HIGH,
                            confidence_reasons=["broker_name_label"],
                            page_number=page_number,
                            line_number=line_index,
                            label=label,
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_LABEL_PATTERN,
                            value_type="name",
                        )
                    )

                if lower_label in CARRIER_NAME_LABELS:
                    candidates.append(
                        build_field_candidate(
                            candidate_id=f"carrier-name-p{page_number}-l{line_index}",
                            field_name=FIELD_CARRIER_NAME,
                            raw_value=value,
                            normalized_value=value,
                            confidence=CANDIDATE_CONFIDENCE_HIGH,
                            confidence_reasons=["carrier_name_label"],
                            page_number=page_number,
                            line_number=line_index,
                            label=label,
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_LABEL_PATTERN,
                            value_type="name",
                        )
                    )

                for label_text, field_name, reference_type, confidence in REFERENCE_LABELS:
                    if lower_label == label_text:
                        candidates.append(
                            build_field_candidate(
                                candidate_id=(
                                    f"reference-{reference_type}-p{page_number}-l{line_index}"
                                ),
                                field_name=field_name,
                                raw_value=value,
                                normalized_value=value,
                                confidence=confidence,
                                confidence_reasons=[f"{reference_type}_label"],
                                page_number=page_number,
                                line_number=line_index,
                                label=label,
                                context_before=context_before,
                                context_after=context_after,
                                source=SOURCE_LABEL_PATTERN,
                                value_type=reference_type,
                                warnings=(
                                    ["ambiguous_reference_label"]
                                    if reference_type == "unknown_reference"
                                    else []
                                ),
                            )
                        )

            elif "reference" in lower_line:
                candidates.append(
                    build_field_candidate(
                        candidate_id=f"reference-unknown-p{page_number}-l{line_index}",
                        field_name=FIELD_REFERENCE,
                        raw_value=stripped,
                        normalized_value=stripped,
                        confidence=CANDIDATE_CONFIDENCE_LOW,
                        confidence_reasons=["unstructured_reference_line"],
                        page_number=page_number,
                        line_number=line_index,
                        label="reference",
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="unknown_reference",
                        warnings=["ambiguous_reference_label"],
                    )
                )

    return candidates


def build_identity_reference_candidate_result(artifact):
    candidates = generate_identity_reference_candidates(artifact)
    missing = []
    warnings = []
    field_names = {candidate["field_name"] for candidate in candidates}

    if FIELD_BROKER_NAME not in field_names:
        missing.append(FIELD_BROKER_NAME)

    if FIELD_LOAD_NUMBER not in field_names:
        missing.append(FIELD_LOAD_NUMBER)

    if missing:
        warnings.append("identity_candidates_missing")

    return build_candidate_extraction_result(
        document_id=(artifact or {}).get("document_id", ""),
        artifact_id=(artifact or {}).get("artifact_id", ""),
        candidates=candidates,
        missing_candidate_fields=missing,
        warnings=warnings,
        extractor_version="identity_reference_candidates_v1",
    )
