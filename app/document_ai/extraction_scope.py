"""Extraction scope selection for classified document text artifacts."""

from app.document_ai.document_classification import (
    CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED,
    DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED,
    EXTRACTION_SCOPE_NON_RATECON_SKIP,
    EXTRACTION_SCOPE_OCR_REQUIRED,
    PAGE_ROLE_BILLING,
    PAGE_ROLE_BOL,
    PAGE_ROLE_CARRIER_INFO,
    PAGE_ROLE_CERTIFICATE_SIGNATURE,
    PAGE_ROLE_DRIVER_INFO,
    PAGE_ROLE_INSURANCE_CERTIFICATE,
    PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_MAIN_TENDER,
    PAGE_ROLE_PAYMENT_SUMMARY,
    PAGE_ROLE_SIGNATURE,
    PAGE_ROLE_STOP_DETAILS,
    PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS,
    PAGE_ROLE_TERMS,
    SECTION_ROLE_BILLING_INSTRUCTIONS,
    SECTION_ROLE_CERTIFICATE_SIGNATURE_BLOCK,
    SECTION_ROLE_DEDUCTIONS_PENALTIES,
    SECTION_ROLE_DELIVERY_SECTION,
    SECTION_ROLE_LEGAL_TERMS,
    SECTION_ROLE_PAYMENT_TERMS,
    SECTION_ROLE_PICKUP_SECTION,
    SECTION_ROLE_QUICK_PAY,
    SECTION_ROLE_RATE_BREAKDOWN,
    SECTION_ROLE_RATE_SUMMARY,
    SECTION_ROLE_SIGNATURE_BLOCK,
    SECTION_ROLE_SPECIAL_INSTRUCTIONS,
    SECTION_ROLE_STOP_TABLE,
    SECTION_ROLE_TONU_PAYMENT,
)


SKIPPED_PAGE_ROLES = {
    PAGE_ROLE_BOL,
    PAGE_ROLE_CERTIFICATE_SIGNATURE,
    PAGE_ROLE_INSURANCE_CERTIFICATE,
    PAGE_ROLE_CARRIER_INFO,
    PAGE_ROLE_DRIVER_INFO,
    PAGE_ROLE_SIGNATURE,
}

CORE_PAGE_ROLES = {
    PAGE_ROLE_MAIN_RATECONF,
    PAGE_ROLE_MAIN_LOAD_CONFIRMATION,
    PAGE_ROLE_MAIN_TENDER,
}

STOP_SECTION_ROLES = {
    SECTION_ROLE_STOP_TABLE,
    SECTION_ROLE_PICKUP_SECTION,
    SECTION_ROLE_DELIVERY_SECTION,
}

RATE_SECTION_ROLES = {
    SECTION_ROLE_RATE_SUMMARY,
    SECTION_ROLE_RATE_BREAKDOWN,
    SECTION_ROLE_TONU_PAYMENT,
}

PAYMENT_SECTION_ROLES = {
    SECTION_ROLE_PAYMENT_TERMS,
    SECTION_ROLE_BILLING_INSTRUCTIONS,
    SECTION_ROLE_QUICK_PAY,
    SECTION_ROLE_DEDUCTIONS_PENALTIES,
    SECTION_ROLE_LEGAL_TERMS,
    SECTION_ROLE_TONU_PAYMENT,
}

REQUIREMENT_SECTION_ROLES = {
    SECTION_ROLE_SPECIAL_INSTRUCTIONS,
}


def _page_map(artifact):
    pages = artifact.get("pages", []) if isinstance(artifact, dict) else []
    return {
        int(page.get("page_number", index) or index): page
        for index, page in enumerate(pages or [], start=1)
        if isinstance(page, dict)
    }


def _page_results(classification_result):
    return [
        page
        for page in (classification_result or {}).get("page_results", [])
        if isinstance(page, dict)
    ]


def _roles(page_result):
    return set(page_result.get("page_roles", []) or [])


def _primary_role(page_result):
    return page_result.get("primary_page_role", "")


def _section_roles(page_result):
    return {
        section.get("section_role", "")
        for section in page_result.get("section_summaries", [])
        if isinstance(section, dict)
    }


def _selected_pages(classification_result, artifact, predicate):
    pages_by_number = _page_map(artifact)
    selected = []

    for page_result in _page_results(classification_result):
        page_number = int(page_result.get("page_number", 0) or 0)
        page = pages_by_number.get(page_number)
        if page and predicate(page_result):
            selected.append(page)

    return selected


def _is_skipped_page(page_result):
    roles = _roles(page_result)
    primary = _primary_role(page_result)
    return primary in SKIPPED_PAGE_ROLES or bool(roles.intersection({PAGE_ROLE_BOL}))


def _is_main_core_page(page_result):
    return _primary_role(page_result) in CORE_PAGE_ROLES


def should_skip_ratecon_extraction(classification_result):
    result = classification_result or {}

    if result.get("classification_status") == CLASSIFICATION_STATUS_UNKNOWN_REVIEW_REQUIRED:
        return True

    if result.get("document_type") == DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED:
        return False

    if not result.get("ratecon_eligible"):
        return True

    return False


def select_pages_for_ratecon_core(classification_result, artifact):
    if should_skip_ratecon_extraction(classification_result):
        return []

    if (classification_result or {}).get("document_type") == DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED:
        return []

    return _selected_pages(
        classification_result,
        artifact,
        lambda page_result: _is_main_core_page(page_result) and not _is_skipped_page(page_result),
    )


def select_pages_for_rate_candidates(classification_result, artifact):
    if should_skip_ratecon_extraction(classification_result):
        return []

    def allowed(page_result):
        if _is_skipped_page(page_result):
            return False
        roles = _roles(page_result)
        sections = _section_roles(page_result)
        return (
            _is_main_core_page(page_result)
            or PAGE_ROLE_PAYMENT_SUMMARY in roles
            or bool(sections.intersection(RATE_SECTION_ROLES))
        )

    return _selected_pages(classification_result, artifact, allowed)


def select_pages_for_stop_candidates(classification_result, artifact):
    if should_skip_ratecon_extraction(classification_result):
        return []

    if (classification_result or {}).get("document_type") == DOCUMENT_TYPE_TRUCK_ORDER_NOT_USED:
        return []

    def allowed(page_result):
        if _is_skipped_page(page_result):
            return False
        roles = _roles(page_result)
        sections = _section_roles(page_result)
        return (
            _is_main_core_page(page_result)
            or PAGE_ROLE_STOP_DETAILS in roles
            or bool(sections.intersection(STOP_SECTION_ROLES))
        )

    return _selected_pages(classification_result, artifact, allowed)


def select_pages_for_requirements_candidates(classification_result, artifact):
    if should_skip_ratecon_extraction(classification_result):
        return []

    def allowed(page_result):
        if _is_skipped_page(page_result):
            return False
        roles = _roles(page_result)
        sections = _section_roles(page_result)
        return (
            _is_main_core_page(page_result)
            or PAGE_ROLE_SUPPLEMENTAL_INSTRUCTIONS in roles
            or bool(sections.intersection(REQUIREMENT_SECTION_ROLES))
        )

    return _selected_pages(classification_result, artifact, allowed)


def select_pages_for_payment_terms(classification_result, artifact):
    if should_skip_ratecon_extraction(classification_result):
        return []

    def allowed(page_result):
        if PAGE_ROLE_BOL in _roles(page_result):
            return False
        roles = _roles(page_result)
        sections = _section_roles(page_result)
        return (
            PAGE_ROLE_TERMS in roles
            or PAGE_ROLE_BILLING in roles
            or PAGE_ROLE_PAYMENT_SUMMARY in roles
            or bool(sections.intersection(PAYMENT_SECTION_ROLES))
        )

    return _selected_pages(classification_result, artifact, allowed)


def extraction_scope_warning_codes(classification_result):
    if not classification_result:
        return [EXTRACTION_SCOPE_OCR_REQUIRED]

    if should_skip_ratecon_extraction(classification_result):
        if classification_result.get("supplemental_only"):
            return [EXTRACTION_SCOPE_NON_RATECON_SKIP]
        return [EXTRACTION_SCOPE_OCR_REQUIRED]

    warnings = []
    for page in _page_results(classification_result):
        roles = _roles(page)
        if PAGE_ROLE_TERMS in roles and PAGE_ROLE_PAYMENT_SUMMARY in roles:
            warnings.append("terms_payment_summary_scope_limited")
        if PAGE_ROLE_BILLING in roles and PAGE_ROLE_PAYMENT_SUMMARY in roles:
            warnings.append("billing_payment_summary_scope_limited")
        if _is_skipped_page(page):
            warnings.append("supplemental_page_skipped_for_core_ratecon")

    return sorted(set(warnings))
