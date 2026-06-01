"""Dependency-free settings for the optional pdfplumber layout provider."""

TABLE_PROFILE_DEFAULT = "default"
TABLE_PROFILE_LINES = "lines"
TABLE_PROFILE_TEXT = "text"
TABLE_PROFILE_LINES_STRICT = "lines_strict"
TABLE_PROFILE_TEXT_STRICT = "text_strict"
PDFPLUMBER_TABLE_SETTING_PROFILES = (
    TABLE_PROFILE_DEFAULT,
    TABLE_PROFILE_LINES,
    TABLE_PROFILE_TEXT,
    TABLE_PROFILE_LINES_STRICT,
    TABLE_PROFILE_TEXT_STRICT,
)


def normalize_pdfplumber_table_profile(value):
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return text if text in PDFPLUMBER_TABLE_SETTING_PROFILES else TABLE_PROFILE_DEFAULT


def get_pdfplumber_table_settings(profile_name=TABLE_PROFILE_DEFAULT):
    profile = normalize_pdfplumber_table_profile(profile_name)
    if profile == TABLE_PROFILE_DEFAULT:
        return None
    if profile == TABLE_PROFILE_LINES:
        return {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
        }
    if profile == TABLE_PROFILE_TEXT:
        return {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
        }
    if profile == TABLE_PROFILE_LINES_STRICT:
        return {
            "vertical_strategy": "lines_strict",
            "horizontal_strategy": "lines_strict",
            "snap_tolerance": 2,
            "join_tolerance": 2,
            "intersection_tolerance": 2,
        }
    if profile == TABLE_PROFILE_TEXT_STRICT:
        return {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "text_x_tolerance": 1,
            "text_y_tolerance": 1,
            "snap_tolerance": 1,
            "join_tolerance": 1,
            "intersection_tolerance": 1,
        }
    return None
