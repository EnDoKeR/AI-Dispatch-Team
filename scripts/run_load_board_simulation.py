import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


TIMELINE_FILE = Path("data/simulation/load_board_timeline.json")
CURRENT_SIMULATED_LOADS_FILE = Path("data/simulation/current_simulated_loads.json")
SIMULATION_EVENTS_FILE = Path("data/simulation/load_board_simulation_events.jsonl")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_json_file(file_path, default):
    file_path = Path(file_path)

    if not file_path.exists():
        return default

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(file_path, data):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def append_jsonl(file_path, record):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def normalize_load(load_id, load_data):
    load = dict(load_data)
    load["simulation_load_id"] = load_id
    return load


def apply_event(active_loads_by_id, event):
    event_type = event.get("event_type", "")
    load_id = event.get("load_id", "")

    if event_type == "LOAD_APPEARED":
        active_loads_by_id[load_id] = normalize_load(
            load_id=load_id,
            load_data=event.get("load", {}),
        )

    elif event_type == "LOAD_UPDATED":
        if load_id in active_loads_by_id:
            updates = event.get("updates", {})
            active_loads_by_id[load_id].update(updates)
        else:
            print(f"Warning: update ignored, load not active: {load_id}")

    elif event_type == "LOAD_REMOVED":
        if load_id in active_loads_by_id:
            del active_loads_by_id[load_id]
        else:
            print(f"Warning: remove ignored, load not active: {load_id}")

    else:
        print(f"Warning: unknown event type ignored: {event_type}")

    append_jsonl(
        SIMULATION_EVENTS_FILE,
        {
            "timestamp_utc": utc_now_iso(),
            "simulation_step": event.get("step", ""),
            "event_time": event.get("event_time", ""),
            "event_type": event_type,
            "load_id": load_id,
            "reason": event.get("reason", ""),
            "payload": event,
        },
    )


def build_simulation_state(step):
    timeline = read_json_file(TIMELINE_FILE, [])

    if not isinstance(timeline, list):
        raise ValueError("Timeline file must contain a JSON list.")

    active_loads_by_id = {}

    events_to_apply = [
        event for event in timeline
        if int(event.get("step", 0)) <= step
    ]

    events_to_apply = sorted(
        events_to_apply,
        key=lambda event: int(event.get("step", 0)),
    )

    for event in events_to_apply:
        apply_event(active_loads_by_id, event)

    active_loads = list(active_loads_by_id.values())
    write_json_file(CURRENT_SIMULATED_LOADS_FILE, active_loads)

    return {
        "step": step,
        "events_applied": len(events_to_apply),
        "active_loads": len(active_loads),
        "active_load_ids": list(active_loads_by_id.keys()),
    }


def reset_simulation():
    if CURRENT_SIMULATED_LOADS_FILE.exists():
        CURRENT_SIMULATED_LOADS_FILE.unlink()

    if SIMULATION_EVENTS_FILE.exists():
        SIMULATION_EVENTS_FILE.unlink()

    print("Simulation reset.")
    print(f"Removed: {CURRENT_SIMULATED_LOADS_FILE}")
    print(f"Removed: {SIMULATION_EVENTS_FILE}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--step",
        type=int,
        help="Build active simulated load board state up to this step.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear current simulated load board state and simulation event log.",
    )

    args = parser.parse_args()

    if args.reset:
        reset_simulation()
        return

    if args.step is None:
        print("Use:")
        print("py scripts/run_load_board_simulation.py --step 1")
        print("py scripts/run_load_board_simulation.py --reset")
        return

    result = build_simulation_state(args.step)

    print("Load board simulation state built.")
    print(f"Step: {result['step']}")
    print(f"Events applied: {result['events_applied']}")
    print(f"Active simulated loads: {result['active_loads']}")
    print("Active load IDs:")

    for load_id in result["active_load_ids"]:
        print(f"- {load_id}")

    print("")
    print(f"Saved to: {CURRENT_SIMULATED_LOADS_FILE}")


if __name__ == "__main__":
    main()