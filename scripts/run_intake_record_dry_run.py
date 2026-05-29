import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.market_intelligence.intake_record_summary import (
    build_intake_record_summary,
    format_intake_record_summary,
)


SAMPLE_SOURCE = {
    "source_type": "manual_dry_run",
    "source_file_name": "synthetic_ratecon_sample.pdf",
    "broker_name": "Synthetic Broker",
    "broker_mc": "123456",
    "rate": 3200,
    "pickup_location": "Dallas, TX",
    "pickup_date": "2026-05-30",
    "pickup_time": "08:00",
    "delivery_location": "Denver, CO",
    "delivery_date": "2026-05-31",
    "delivery_time": "09:00",
    "commodity": "Steel coils",
    "weight": 42000,
    "reference_id": "SYNTH-RC-001",
    "equipment": "Conestoga",
    "special_requirements": ["TARPS", "APPOINTMENT_REQUIRED"],
}


def main():
    summary = build_intake_record_summary(
        SAMPLE_SOURCE,
        received_at_utc="2026-05-29T10:00:00Z",
        intake_id="DRY-RUN-INTAKE-1",
    )

    print(format_intake_record_summary(summary))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
