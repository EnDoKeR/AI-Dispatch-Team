import argparse
import json
import sys
from collections import Counter
from pathlib import Path


DEFAULT_PRIVATE_RATECON_DIR = Path("data/private_ratecons/originals")
DRY_RUN_WARNING = (
    "LOCAL ONLY - private RateCon inventory, no document contents read"
)


def extension_for(path):
    suffix = path.suffix.lower().strip()
    return suffix if suffix else "[no_extension]"


def list_private_ratecon_files(directory=DEFAULT_PRIVATE_RATECON_DIR):
    root = Path(directory)

    if not root.exists():
        return []

    return sorted(
        [path for path in root.iterdir() if path.is_file()],
        key=lambda path: path.name.lower(),
    )


def build_private_ratecon_inventory(directory=DEFAULT_PRIVATE_RATECON_DIR):
    files = list_private_ratecon_files(directory)
    extension_counts = Counter(extension_for(path) for path in files)
    labels = []

    for index, path in enumerate(files, start=1):
        labels.append(
            {
                "label": f"RATECON_{index:03d}",
                "extension": extension_for(path),
            }
        )

    return {
        "directory": str(Path(directory)),
        "total_files": len(files),
        "extension_counts": dict(sorted(extension_counts.items())),
        "labels": labels,
        "privacy_warning": DRY_RUN_WARNING,
        "contents_read": False,
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Local-only private RateCon inventory. Does not read contents."
    )
    parser.add_argument(
        "--directory",
        default=str(DEFAULT_PRIVATE_RATECON_DIR),
        help="Local private RateCon originals folder.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON inventory without private filenames.",
    )
    return parser


def format_counts(counts):
    if not counts:
        return "none"

    return ", ".join(
        f"{extension}: {count}"
        for extension, count in sorted(counts.items())
    )


def format_inventory(inventory):
    lines = [
        "PRIVATE RATECON INVENTORY",
        DRY_RUN_WARNING,
        f"Directory: {inventory['directory']}",
        f"Total files: {inventory['total_files']}",
        f"Extension counts: {format_counts(inventory['extension_counts'])}",
        "Anonymized labels:",
    ]

    for item in inventory["labels"]:
        lines.append(f"- {item['label']} ({item['extension']})")

    if not inventory["labels"]:
        lines.append("- none")

    lines.append("")
    lines.append("Do not commit private PDFs, extracted text, or dry-run outputs.")

    return "\n".join(lines)


def main(argv=None):
    args = build_parser().parse_args(argv)
    inventory = build_private_ratecon_inventory(args.directory)

    if args.json:
        print(json.dumps(inventory, indent=2, sort_keys=True))
    else:
        print(format_inventory(inventory))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
