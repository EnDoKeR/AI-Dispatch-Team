from app.market_intelligence.intake_record import RECORD_FIELDS, build_intake_record


def parser_output_value(raw_output, field_name):
    if raw_output is None:
        return ""

    if isinstance(raw_output, dict):
        value = raw_output.get(field_name, "")
    else:
        value = getattr(raw_output, field_name, "")

    if value is None:
        return ""

    return value


def parser_output_to_source(raw_output):
    source = {}

    for field_name in RECORD_FIELDS:
        source[field_name] = parser_output_value(raw_output, field_name)

    return source


def normalize_parser_output(
    raw_output=None,
    source_type="",
    source_file_name="",
    received_at_utc="",
    intake_id="",
):
    source = parser_output_to_source(raw_output)

    if source_type:
        source["source_type"] = source_type

    if source_file_name:
        source["source_file_name"] = source_file_name

    return build_intake_record(
        source,
        received_at_utc=received_at_utc,
        intake_id=intake_id,
    )
