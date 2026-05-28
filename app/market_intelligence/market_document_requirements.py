def document_status(search_request, document_key):
    return getattr(search_request, document_key, None)


def require_driver_document(load, search_request, document_key, document_label):
    status = document_status(search_request, document_key)

    if status is True:
        load.match_reasons.append(
            f"{document_label} confirmed in driver profile."
        )
        return load

    if status is False:
        load.is_blocked = True
        load.block_reasons.append(
            f"{document_label} required, but driver profile says driver does not have it."
        )
        return load

    load.is_review_once = True
    load.review_reasons.append(
        f"{document_label} required; ask driver and save answer in driver profile."
    )

    return load


def require_one_of_driver_documents(
    load,
    search_request,
    document_options,
    requirement_label,
):
    confirmed_documents = []
    unknown_documents = []

    for document_key, document_label in document_options:
        status = document_status(search_request, document_key)

        if status is True:
            confirmed_documents.append(document_label)
        elif status is None:
            unknown_documents.append(document_label)

    if confirmed_documents:
        load.match_reasons.append(
            f"{requirement_label} confirmed in driver profile: {', '.join(confirmed_documents)}."
        )
        return load

    if unknown_documents:
        load.is_review_once = True
        load.review_reasons.append(
            f"{requirement_label} required; ask driver about: {', '.join(unknown_documents)} and save answer in driver profile."
        )
        return load

    load.is_blocked = True
    load.block_reasons.append(
        f"{requirement_label} required, but driver profile has no accepted document/status."
    )

    return load
