import csv


BROKER_FILE = "data/brokers.csv"


def get_broker_data(broker_name):
    try:
        with open(
            BROKER_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                if (
                    row["broker"].strip().lower()
                    == broker_name.strip().lower()
                ):
                    return (
                        row.get("score", "50"),
                        row.get("status", "UNKNOWN"),
                    )

    except:
        pass

    return (
        "50",
        "UNKNOWN",
    )
