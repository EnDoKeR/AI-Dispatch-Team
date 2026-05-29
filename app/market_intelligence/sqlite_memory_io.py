import json
from pathlib import Path


def load_jsonl(file_path):
    file_path = Path(file_path)

    if not file_path.exists():
        return []

    records = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return records


def json_text(value):
    return json.dumps(value, ensure_ascii=False)
