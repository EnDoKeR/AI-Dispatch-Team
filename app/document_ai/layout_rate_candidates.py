"""Layout-aware rate and payment candidate generation."""

import re

from app.document_ai.layout_artifacts import (
    EVIDENCE_LABEL_VALUE,
    EVIDENCE_TABLE_CELL,
    build_layout_evidence_ref,
)
from app.document_ai.layout_candidate_adapter import build_field_candidate_from_layout_value
from app.document_ai.layout_proximity import (
    PROXIMITY_SAME_ROW_RIGHT,
    PROXIMITY_TABLE_ROW,
    build_label_value_candidate,
)
from app.document_ai.ratecon_candidates import (
    CANDIDATE_CONFIDENCE_HIGH,
    CANDIDATE_CONFIDENCE_LOW,
    CANDIDATE_CONFIDENCE_MEDIUM,
    FIELD_ACCESSORIAL_TERM,
    FIELD_RATE,
    SOURCE_TABLE_PATTERN_FUTURE,
)
from app.document_ai.ratecon_rate_money_safety import get_layout_accessorial_label_types

LAYOUT_RATE_EXTRACTOR_VERSION = "layout_rate_candidates_v1"

MONEY_PATTERN = re.compile(
    r"(?P<amount>\$\s?\d{1,6}(?:,\d{3})*(?:\.\d{2})?|"
    r"\bUSD\s?\d{1,6}(?:,\d{3})*(?:\.\d{2})?|"
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b|"
    r"\b\d{4,6}(?:\.\d{2})?\b)",
    re.IGNORECASE,
)

MAIN_RATE_SECTIONS = {"RATE_SUMMARY", "RATE_BREAKDOWN", "PAYMENT_SUMMARY"}
TERMS_PAYMENT_SECTIONS = {
    "LEGAL_TERMS",
    "DEDUCTIONS_PENALTIES",
    "PAYMENT_TERMS",
    "QUICK_PAY",
    "BILLING_INSTRUCTIONS",
}

MAIN_RATE_LABELS = (
    ("total carrier pay", "total_carrier_pay"),
    ("carrier freight pay", "carrier_freight_pay"),
    ("carrier pay", "total_carrier_pay"),
    ("linehaul", "linehaul"),
    ("line haul", "linehaul"),
    ("total charge", "total_charge"),
    ("agreed amount", "agreed_amount"),
    ("agreed rate", "agreed_amount"),
    ("total rate", "total_carrier_pay"),
)

ACCESSORIAL_LABELS = get_layout_accessorial_label_types()


def _text(value):
    return str(value or "").strip()


def _lower(value):
    return _text(value).lower()


def normalize_money(value):
    text = _text(value).upper().replace("USD", "").replace("$", "").strip()
    return text.replace(",", "").replace(" ", "")


def _skip_non_money_number(context_text, match):
    amount = match.group("amount")
    lower = _lower(context_text)
    starts_with_money_symbol = amount.strip().startswith("$") or amount.strip().upper().startswith("USD")

    if starts_with_money_symbol:
        return False

    before = context_text[match.start() - 1] if match.start() > 0 else ""
    after = context_text[match.end()] if match.end() < len(context_text) else ""
    if before == "-" or after == "-":
        return True

    if "weight" in lower and ("lb" in lower or "pound" in lower):
        return True

    if any(term in lower for term in ["pickup", "delivery", "stop", "date", "appt"]):
        return True

    if any(term in lower for term in ["freight bill", "load number", "order id", "reference", "ref"]):
        return True

    return False


def _page_roles(page):
    return [str(role) for role in page.get("page_roles", [])]


def _page_role_text(page):
    return ",".join(_page_roles(page))


def _contains_label(text, labels):
    lower = _lower(text)
    for label, value_type in labels:
        if label in lower:
            return value_type
    return ""


def _classify_money_context(context_text, section_role):
    lower = _lower(context_text)

    accessorial_type = _contains_label(lower, ACCESSORIAL_LABELS)
    if accessorial_type == "TONU_pay" or section_role == "TONU_PAYMENT":
        return {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": "TONU_pay",
            "confidence": CANDIDATE_CONFIDENCE_HIGH,
            "warnings": ["tonu_payment_not_normal_linehaul"],
            "reasons": ["tonu_payment_context"],
        }

    if section_role in {"QUICK_PAY", "BILLING_INSTRUCTIONS"} or accessorial_type == "quick_pay_discount":
        return {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": "quick_pay_discount",
            "confidence": CANDIDATE_CONFIDENCE_LOW,
            "warnings": ["payment_terms_not_main_rate"],
            "reasons": ["quick_pay_or_billing_context"],
        }

    if section_role in {"LEGAL_TERMS", "DEDUCTIONS_PENALTIES", "PAYMENT_TERMS"} or accessorial_type:
        return {
            "field_name": FIELD_ACCESSORIAL_TERM,
            "value_type": accessorial_type or "accessorial",
            "confidence": CANDIDATE_CONFIDENCE_LOW,
            "warnings": ["not_final_rate_candidate"],
            "reasons": ["accessorial_or_terms_context"],
        }

    main_type = _contains_label(lower, MAIN_RATE_LABELS)
    if section_role in MAIN_RATE_SECTIONS and main_type:
        return {
            "field_name": FIELD_RATE,
            "value_type": main_type,
            "confidence": CANDIDATE_CONFIDENCE_HIGH,
            "warnings": [],
            "reasons": ["layout_rate_summary_context", f"rate_label:{main_type}"],
        }

    if section_role in MAIN_RATE_SECTIONS:
        return {
            "field_name": FIELD_RATE,
            "value_type": "unknown_money",
            "confidence": CANDIDATE_CONFIDENCE_MEDIUM,
            "warnings": ["rate_label_weak_layout_context"],
            "reasons": ["money_in_rate_section"],
        }

    return {
        "field_name": FIELD_RATE,
        "value_type": "unknown_money",
        "confidence": CANDIDATE_CONFIDENCE_LOW,
        "warnings": ["money_context_unknown"],
        "reasons": ["money_without_strong_layout_context"],
    }


def _line_label_before_money(text, match):
    return text[: match.start()].strip(" :-\t") or "money"


def _table_row_cells(table, row_index):
    return [
        cell
        for cell in table.get("cells", [])
        if int(cell.get("row_index") or 0) == int(row_index or 0)
    ]


def _nearest_left_label(row_cells, money_cell):
    money_col = int(money_cell.get("col_index") or 0)
    left_cells = [
        cell
        for cell in row_cells
        if int(cell.get("col_index") or 0) < money_col
        and _text(cell.get("text_redacted"))
    ]
    if not left_cells:
        return "money"
    return sorted(left_cells, key=lambda cell: int(cell.get("col_index") or 0))[-1]["text_redacted"]


def _table_section_role(page, table):
    table_id = table.get("table_id", "")
    table_box = table.get("bbox", {})
    for block in page.get("blocks", []):
        block_box = block.get("bbox", {})
        if table_id and table_id.lower().endswith(str(block.get("block_id", "")).lower()):
            return block.get("section_role", "")
        if (
            abs(float(block_box.get("x0", 0)) - float(table_box.get("x0", 0))) <= 1
            and abs(float(block_box.get("y0", 0)) - float(table_box.get("y0", 0))) <= 1
            and block.get("section_role")
        ):
            return block["section_role"]
    return ""


def _candidate_from_money(
    field_context,
    amount,
    label,
    bbox,
    page_number,
    proximity_type,
    evidence_ref,
    section_role,
    page_role,
):
    label_value = build_label_value_candidate(
        label=label,
        value_text_redacted=amount,
        label_bbox=bbox,
        value_bbox=bbox,
        page_number=page_number,
        proximity_type=proximity_type,
        distance_score=0.9 if field_context["confidence"] == CANDIDATE_CONFIDENCE_HIGH else 0.55,
        confidence=field_context["confidence"],
        reasons=field_context["reasons"],
        evidence_ref=evidence_ref,
        source_field=field_context["field_name"],
    )
    return build_field_candidate_from_layout_value(
        field_name=field_context["field_name"],
        label_value_candidate=label_value,
        normalized_value=normalize_money(amount),
        confidence=field_context["confidence"],
        confidence_reasons=field_context["reasons"],
        source=SOURCE_TABLE_PATTERN_FUTURE,
        value_type=field_context["value_type"],
        warnings=field_context["warnings"],
        section_role=section_role,
        page_role=page_role,
    )


def generate_layout_rate_candidates(layout_artifact):
    candidates = []

    for page in layout_artifact.get("pages", []):
        page_number = int(page.get("page_number") or 0)
        page_role = _page_role_text(page)

        for line in page.get("lines", []):
            text = _text(line.get("text_redacted"))
            section_role = line.get("section_role", "")
            for match in MONEY_PATTERN.finditer(text):
                if _skip_non_money_number(text, match):
                    continue
                amount = match.group("amount")
                label = _line_label_before_money(text, match)
                context = _classify_money_context(text, section_role)
                candidates.append(
                    _candidate_from_money(
                        context,
                        amount,
                        label,
                        line.get("bbox", {}),
                        page_number,
                        PROXIMITY_SAME_ROW_RIGHT,
                        build_layout_evidence_ref(
                            page_number=page_number,
                            bbox=line.get("bbox", {}),
                            line_id=line.get("line_id", ""),
                            label=label,
                            evidence_type=EVIDENCE_LABEL_VALUE,
                        ),
                        section_role,
                        page_role,
                    )
                )

        for table in page.get("tables", []):
            section_role = _table_section_role(page, table)
            for cell in table.get("cells", []):
                text = _text(cell.get("text_redacted"))
                money_match = MONEY_PATTERN.search(text)
                if not money_match:
                    continue
                row_cells = _table_row_cells(table, cell.get("row_index", 0))
                label = _nearest_left_label(row_cells, cell)
                row_text = " ".join(_text(row_cell.get("text_redacted")) for row_cell in row_cells)
                if _skip_non_money_number(text, money_match):
                    continue
                if section_role in {"STOP_TABLE", "PICKUP_SECTION", "DELIVERY_SECTION"} and not (
                    money_match.group("amount").strip().startswith("$")
                    or money_match.group("amount").strip().upper().startswith("USD")
                ):
                    continue
                context = _classify_money_context(row_text, section_role)
                candidates.append(
                    _candidate_from_money(
                        context,
                        money_match.group("amount"),
                        label,
                        cell.get("bbox", {}),
                        page_number,
                        PROXIMITY_TABLE_ROW,
                        build_layout_evidence_ref(
                            page_number=page_number,
                            bbox=cell.get("bbox", {}),
                            table_id=table.get("table_id", ""),
                            cell_ref=f"r{cell.get('row_index')}c{cell.get('col_index')}",
                            label=label,
                            evidence_type=EVIDENCE_TABLE_CELL,
                        ),
                        section_role,
                        page_role,
                    )
                )

    return candidates
