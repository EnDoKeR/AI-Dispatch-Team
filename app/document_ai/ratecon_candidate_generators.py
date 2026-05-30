"""Candidate generators for fake/anonymized RateCon text artifacts."""

import re

from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_BROKER_MC,
    FIELD_BROKER_NAME,
    FIELD_CARRIER_NAME,
    FIELD_DELIVERY_DATE,
    FIELD_DELIVERY_LOCATION,
    FIELD_DELIVERY_TIME,
    FIELD_ACCESSORIAL_TERM,
    FIELD_COMMODITY,
    FIELD_EQUIPMENT,
    FIELD_LOAD_NUMBER,
    FIELD_PICKUP_DATE,
    FIELD_PICKUP_LOCATION,
    FIELD_PICKUP_TIME,
    FIELD_REFERENCE,
    FIELD_RATE,
    FIELD_SPECIAL_REQUIREMENT,
    FIELD_WEIGHT,
    SOURCE_SECTION_PATTERN,
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

MONEY_EXCLUSION_LABELS = (
    "weight",
    "gross weight",
    "total weight",
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
    ("pickup #", FIELD_REFERENCE, "pickup_number", CANDIDATE_CONFIDENCE_HIGH),
    ("pickup number", FIELD_REFERENCE, "pickup_number", CANDIDATE_CONFIDENCE_HIGH),
    ("pickup confirmation", FIELD_REFERENCE, "pickup_confirmation", CANDIDATE_CONFIDENCE_HIGH),
    ("delivery #", FIELD_REFERENCE, "delivery_number", CANDIDATE_CONFIDENCE_HIGH),
    ("delivery number", FIELD_REFERENCE, "delivery_number", CANDIDATE_CONFIDENCE_HIGH),
    ("delivery confirmation", FIELD_REFERENCE, "delivery_confirmation", CANDIDATE_CONFIDENCE_HIGH),
    ("customer ref", FIELD_REFERENCE, "customer_reference", CANDIDATE_CONFIDENCE_HIGH),
    ("customer reference", FIELD_REFERENCE, "customer_reference", CANDIDATE_CONFIDENCE_HIGH),
    ("appointment #", FIELD_REFERENCE, "appointment_number", CANDIDATE_CONFIDENCE_MEDIUM),
    ("appointment number", FIELD_REFERENCE, "appointment_number", CANDIDATE_CONFIDENCE_MEDIUM),
    ("ref #", FIELD_REFERENCE, "unknown_reference", CANDIDATE_CONFIDENCE_LOW),
    ("reference #", FIELD_REFERENCE, "unknown_reference", CANDIDATE_CONFIDENCE_LOW),
    ("reference", FIELD_REFERENCE, "unknown_reference", CANDIDATE_CONFIDENCE_LOW),
)

MC_PATTERN = re.compile(
    r"\b(?P<label>broker\s+mc|mc\s*number|mc#?|mc)\s*[:#]?\s*(?P<value>MC?\s?\d{5,8}|\d{5,8})\b",
    re.IGNORECASE,
)

LOCATION_PATTERN = re.compile(
    r"\b(?P<location>[A-Z][A-Za-z ]+,\s*[A-Z]{2}(?:\s+\d{5})?)\b"
)

DATE_PATTERN = re.compile(
    r"\b(?P<date>\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4})\b",
    re.IGNORECASE,
)

TIME_PATTERN = re.compile(
    r"\b(?P<time>FCFS|(?:PU\s+|DEL\s+)?Appt\s+\d{1,2}:\d{2}(?:\s?[AP]M)?"
    r"(?:\s*-\s*\d{1,2}:\d{2}(?:\s?[AP]M)?)?|"
    r"\d{1,2}:\d{2}(?:\s?[AP]M)?(?:\s*-\s*\d{1,2}:\d{2}(?:\s?[AP]M)?)?)\b",
    re.IGNORECASE,
)

WEIGHT_PATTERN = re.compile(
    r"\b(?P<weight>\d{1,3}(?:,\d{3})+|\d{4,6})\s*(?P<unit>lbs?|pounds)?\b",
    re.IGNORECASE,
)

EQUIPMENT_PATTERN = re.compile(
    r"\b(?P<equipment>dry\s+van|reefer|flatbed|conestoga|step\s*deck|"
    r"stepdeck|van|53\s*ft|48\s*ft)\b",
    re.IGNORECASE,
)

SPECIAL_REQUIREMENT_PATTERN = re.compile(
    r"\b(?P<requirement>tarp required|no tarp|straps required|chains required|"
    r"appointment required|driver assist|team required|temperature control|"
    r"load bars|no touch|hazmat)\b",
    re.IGNORECASE,
)

COMMODITY_LABELS = (
    "commodity",
    "commodity description",
    "product",
    "freight",
    "freight description",
    "description",
)

WEIGHT_LABELS = (
    "weight",
    "gross weight",
    "total weight",
)

EQUIPMENT_LABELS = (
    "equipment",
    "trailer type",
    "trailer type/size",
    "mode",
)

SPECIAL_REQUIREMENT_LABELS = (
    "special requirements",
    "requirements",
    "notes",
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


def _normalize_weight(value):
    return str(value or "").replace(",", "").strip()


def _split_label_value(line):
    if ":" in line:
        label, value = line.split(":", 1)
        return label.strip(), value.strip()

    return "", ""


def _section_from_line(line):
    lower_line = line.lower()
    confidence = CANDIDATE_CONFIDENCE_HIGH

    if any(text in lower_line for text in ["pickup", "pick up", "shipper", "origin"]):
        return "pickup", confidence

    if re.search(r"\bpu\b", lower_line):
        return "pickup", confidence

    if any(text in lower_line for text in ["delivery", "consignee", "destination", "receiver"]):
        return "delivery", confidence

    if re.search(r"\bdel\b", lower_line):
        return "delivery", confidence

    if "stop 1" in lower_line:
        return "pickup", CANDIDATE_CONFIDENCE_LOW

    if "stop 2" in lower_line:
        return "delivery", CANDIDATE_CONFIDENCE_LOW

    return "", CANDIDATE_CONFIDENCE_LOW


def _stop_field(section, field_kind):
    fields = {
        ("pickup", "location"): FIELD_PICKUP_LOCATION,
        ("pickup", "date"): FIELD_PICKUP_DATE,
        ("pickup", "time"): FIELD_PICKUP_TIME,
        ("delivery", "location"): FIELD_DELIVERY_LOCATION,
        ("delivery", "date"): FIELD_DELIVERY_DATE,
        ("delivery", "time"): FIELD_DELIVERY_TIME,
    }

    return fields.get((section, field_kind), "")


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


def _is_bare_number_amount(value):
    text = str(value or "").strip()
    return bool(re.fullmatch(r"\d{4,6}", text))


def _has_money_context(line):
    lower_line = line.lower()
    return any(label in lower_line for label in STRONG_RATE_LABELS + ACCESSORIAL_LABELS)


def _has_non_money_context(line):
    lower_line = line.lower()
    return any(label in lower_line for label in MONEY_EXCLUSION_LABELS)


def generate_money_rate_candidates(artifact):
    candidates = []

    for page in _artifact_pages(artifact):
        page_number = page.get("page_number", "")
        lines = str(page.get("text", "") or "").splitlines()

        for line_index, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            for match_index, match in enumerate(MONEY_PATTERN.finditer(line), start=1):
                raw_value = match.group("amount")
                if _has_non_money_context(line) and not _has_money_context(line):
                    continue

                if _is_bare_number_amount(raw_value) and not _has_money_context(line):
                    continue

                classification = _classify_money_line(line)
                context_before, context_after = _line_context(lines, line_index - 1)
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


def generate_stop_candidates(artifact):
    candidates = []

    for page in _artifact_pages(artifact):
        page_number = page.get("page_number", "")
        lines = str(page.get("text", "") or "").splitlines()
        current_section = ""
        current_confidence = CANDIDATE_CONFIDENCE_LOW

        for line_index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            section, section_confidence = _section_from_line(f" {stripped} ")
            if section:
                current_section = section
                current_confidence = section_confidence

            active_section = section or current_section
            active_confidence = section_confidence if section else current_confidence
            context_before, context_after = _line_context(lines, line_index - 1)

            for field_kind, pattern in [
                ("location", LOCATION_PATTERN),
                ("date", DATE_PATTERN),
                ("time", TIME_PATTERN),
            ]:
                field_name = _stop_field(active_section, field_kind)
                if not field_name:
                    continue

                for match_index, match in enumerate(pattern.finditer(stripped), start=1):
                    value = match.group(field_kind)
                    warnings = []
                    confidence_reasons = [f"{active_section}_{field_kind}_section"]

                    if active_confidence == CANDIDATE_CONFIDENCE_LOW:
                        warnings.append("ambiguous_stop_section")
                        confidence_reasons.append("generic_stop_label")

                    candidates.append(
                        build_field_candidate(
                            candidate_id=(
                                f"{field_name}-p{page_number}-l{line_index}-{match_index}"
                            ),
                            field_name=field_name,
                            raw_value=value,
                            normalized_value=value,
                            confidence=active_confidence,
                            confidence_reasons=confidence_reasons,
                            page_number=page_number,
                            line_number=line_index,
                            label=active_section,
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_SECTION_PATTERN,
                            warnings=warnings,
                            value_type=field_kind,
                        )
                    )

    return candidates


def build_stop_candidate_result(artifact):
    candidates = generate_stop_candidates(artifact)
    present_fields = {candidate["field_name"] for candidate in candidates}
    required_fields = [
        FIELD_PICKUP_LOCATION,
        FIELD_PICKUP_DATE,
        FIELD_DELIVERY_LOCATION,
        FIELD_DELIVERY_DATE,
    ]
    missing = [
        field_name for field_name in required_fields if field_name not in present_fields
    ]
    warnings = ["stop_candidates_missing"] if missing else []

    return build_candidate_extraction_result(
        document_id=(artifact or {}).get("document_id", ""),
        artifact_id=(artifact or {}).get("artifact_id", ""),
        candidates=candidates,
        missing_candidate_fields=missing,
        warnings=warnings,
        extractor_version="stop_candidates_v1",
    )


def generate_operational_detail_candidates(artifact):
    candidates = []

    for page in _artifact_pages(artifact):
        page_number = page.get("page_number", "")
        lines = str(page.get("text", "") or "").splitlines()

        for line_index, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            label, value = _split_label_value(stripped)
            lower_label = label.lower()
            lower_line = stripped.lower()
            context_before, context_after = _line_context(lines, line_index - 1)

            if value and lower_label in EQUIPMENT_LABELS:
                candidates.append(
                    build_field_candidate(
                        candidate_id=f"equipment-p{page_number}-l{line_index}",
                        field_name=FIELD_EQUIPMENT,
                        raw_value=value,
                        normalized_value=value,
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                        confidence_reasons=["equipment_label"],
                        page_number=page_number,
                        line_number=line_index,
                        label=label,
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="equipment",
                    )
                )
            elif any(text in lower_line for text in ["conestoga", "flatbed", "reefer"]):
                match = EQUIPMENT_PATTERN.search(stripped)
                if match:
                    candidates.append(
                        build_field_candidate(
                            candidate_id=f"equipment-pattern-p{page_number}-l{line_index}",
                            field_name=FIELD_EQUIPMENT,
                            raw_value=match.group("equipment"),
                            normalized_value=match.group("equipment"),
                            confidence=CANDIDATE_CONFIDENCE_MEDIUM,
                            confidence_reasons=["equipment_keyword"],
                            page_number=page_number,
                            line_number=line_index,
                            label="equipment keyword",
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_LABEL_PATTERN,
                            value_type="equipment",
                        )
                    )

            if value and lower_label in COMMODITY_LABELS:
                candidates.append(
                    build_field_candidate(
                        candidate_id=f"commodity-p{page_number}-l{line_index}",
                        field_name=FIELD_COMMODITY,
                        raw_value=value,
                        normalized_value=value,
                        confidence=CANDIDATE_CONFIDENCE_HIGH,
                        confidence_reasons=["commodity_label"],
                        page_number=page_number,
                        line_number=line_index,
                        label=label,
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="commodity",
                    )
                )

            if lower_label in WEIGHT_LABELS or re.search(r"\b(?:lbs?|pounds)\b", lower_line):
                for match_index, match in enumerate(WEIGHT_PATTERN.finditer(stripped), start=1):
                    raw_weight = match.group("weight")
                    unit = match.group("unit") or ""
                    candidates.append(
                        build_field_candidate(
                            candidate_id=(
                                f"weight-p{page_number}-l{line_index}-{match_index}"
                            ),
                            field_name=FIELD_WEIGHT,
                            raw_value=f"{raw_weight} {unit}".strip(),
                            normalized_value=_normalize_weight(raw_weight),
                            confidence=CANDIDATE_CONFIDENCE_HIGH,
                            confidence_reasons=["weight_label_or_unit"],
                            page_number=page_number,
                            line_number=line_index,
                            label=label or "weight",
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_LABEL_PATTERN,
                            value_type="weight",
                        )
                    )

            if value and lower_label in SPECIAL_REQUIREMENT_LABELS:
                for match_index, match in enumerate(
                    SPECIAL_REQUIREMENT_PATTERN.finditer(value),
                    start=1,
                ):
                    candidates.append(
                        build_field_candidate(
                            candidate_id=(
                                f"special-requirement-p{page_number}-l{line_index}-{match_index}"
                            ),
                            field_name=FIELD_SPECIAL_REQUIREMENT,
                            raw_value=match.group("requirement"),
                            normalized_value=match.group("requirement").lower(),
                            confidence=CANDIDATE_CONFIDENCE_HIGH,
                            confidence_reasons=["special_requirement_label"],
                            page_number=page_number,
                            line_number=line_index,
                            label=label,
                            context_before=context_before,
                            context_after=context_after,
                            source=SOURCE_LABEL_PATTERN,
                            value_type="special_requirement",
                        )
                    )

            for match_index, match in enumerate(
                SPECIAL_REQUIREMENT_PATTERN.finditer(stripped),
                start=1,
            ):
                if value and lower_label in SPECIAL_REQUIREMENT_LABELS:
                    continue

                candidates.append(
                    build_field_candidate(
                        candidate_id=(
                            f"special-requirement-pattern-p{page_number}-l{line_index}-{match_index}"
                        ),
                        field_name=FIELD_SPECIAL_REQUIREMENT,
                        raw_value=match.group("requirement"),
                        normalized_value=match.group("requirement").lower(),
                        confidence=CANDIDATE_CONFIDENCE_MEDIUM,
                        confidence_reasons=["special_requirement_keyword"],
                        page_number=page_number,
                        line_number=line_index,
                        label="special requirement keyword",
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="special_requirement",
                    )
                )

            if any(label_text in lower_line for label_text in ACCESSORIAL_LABELS):
                candidates.append(
                    build_field_candidate(
                        candidate_id=f"accessorial-term-p{page_number}-l{line_index}",
                        field_name=FIELD_ACCESSORIAL_TERM,
                        raw_value=stripped,
                        normalized_value=stripped,
                        confidence=CANDIDATE_CONFIDENCE_MEDIUM,
                        confidence_reasons=["accessorial_term_label"],
                        page_number=page_number,
                        line_number=line_index,
                        label="accessorial",
                        context_before=context_before,
                        context_after=context_after,
                        source=SOURCE_LABEL_PATTERN,
                        value_type="accessorial_term",
                    )
                )

    return candidates


def build_operational_detail_candidate_result(artifact):
    candidates = generate_operational_detail_candidates(artifact)
    present_fields = {candidate["field_name"] for candidate in candidates}
    required_fields = [
        FIELD_EQUIPMENT,
        FIELD_WEIGHT,
        FIELD_COMMODITY,
    ]
    missing = [
        field_name for field_name in required_fields if field_name not in present_fields
    ]
    warnings = ["operational_detail_candidates_missing"] if missing else []

    return build_candidate_extraction_result(
        document_id=(artifact or {}).get("document_id", ""),
        artifact_id=(artifact or {}).get("artifact_id", ""),
        candidates=candidates,
        missing_candidate_fields=missing,
        warnings=warnings,
        extractor_version="operational_detail_candidates_v1",
    )
