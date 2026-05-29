import tempfile
from pathlib import Path

from app.market_intelligence.chain_scoring import score_two_load_chain
from app.market_intelligence.market_baseline import build_market_baseline
from app.market_intelligence.market_exit_classifier import classify_load_exit_market
from app.market_intelligence.market_zone_snapshot import build_market_zone_snapshot
from app.market_intelligence.reload_watch_service import (
    handle_reload_watch_event,
    start_reload_watch,
)
from app.market_intelligence.telegram_watch_formatter import (
    format_reload_watch_message,
)


SCENARIO_NAME = "strong_inbound_weak_exit_then_clean_exit"


class ScenarioLoad:
    def __init__(
        self,
        reference_id,
        pickup,
        delivery,
        rate,
        loaded_miles,
        total_rpm,
        driver_match_status="MATCH",
        review_category="",
        pickup_date="2026-05-29",
        broker_mc="123456",
        posted_trailer_type="Flatbed",
        equipment="Flatbed",
        distances=None,
    ):
        self.reference_id = reference_id
        self.load_id = reference_id
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.gross = rate
        self.loaded_miles = loaded_miles
        self.total_miles = loaded_miles
        self.total_rpm = total_rpm
        self.driver_match_status = driver_match_status
        self._review_category = review_category
        self.pickup_date = pickup_date
        self.broker_mc = broker_mc
        self.posted_trailer_type = posted_trailer_type
        self.equipment = equipment
        self.driver_name = "Alex"
        self.distances = distances or {}

    def is_qualified(self):
        return self.driver_match_status in ["MATCH", "REVIEW_ONCE"]

    def review_category(self):
        return self._review_category

    def distance_between_known_cities(self, location_a, location_b):
        return self.distances.get((location_a, location_b))


def load_summary(load):
    return {
        "reference_id": getattr(load, "reference_id", ""),
        "pickup": getattr(load, "pickup", ""),
        "delivery": getattr(load, "delivery", ""),
        "rate": getattr(load, "rate", 0),
        "loaded_miles": getattr(load, "loaded_miles", 0),
        "total_rpm": getattr(load, "total_rpm", 0),
        "driver_match_status": getattr(load, "driver_match_status", ""),
    }


def build_strong_inbound_weak_exit_scenario():
    parent_load = ScenarioLoad(
        reference_id="INBOUND-1",
        pickup="Dade City, FL",
        delivery="Denver, CO",
        rate=3600,
        loaded_miles=1100,
        total_rpm=3.27,
        driver_match_status="MATCH",
        distances={("Denver, CO", "Denver, CO"): 0},
    )
    weak_denver_loads = [
        ScenarioLoad(
            reference_id="WEAK-DEN-1",
            pickup="Atlanta, GA",
            delivery="Denver, CO",
            rate=2200,
            loaded_miles=1000,
            total_rpm=2.2,
            driver_match_status="REVIEW_ONCE",
        ),
        ScenarioLoad(
            reference_id="WEAK-DEN-2",
            pickup="Chicago, IL",
            delivery="Denver, CO",
            rate=2100,
            loaded_miles=1000,
            total_rpm=2.1,
            driver_match_status="REVIEW_ONCE",
        ),
        ScenarioLoad(
            reference_id="WEAK-DEN-3",
            pickup="Kansas City, MO",
            delivery="Denver, CO",
            rate=2000,
            loaded_miles=1000,
            total_rpm=2.0,
            driver_match_status="REVIEW_ONCE",
        ),
    ]
    clean_exit_load = ScenarioLoad(
        reference_id="EXIT-1",
        pickup="Denver, CO",
        delivery="Houston, TX",
        rate=2600,
        loaded_miles=900,
        total_rpm=2.89,
        driver_match_status="MATCH",
    )

    return {
        "scenario_name": SCENARIO_NAME,
        "parent_load": parent_load,
        "initial_market_loads": [parent_load, *weak_denver_loads],
        "initial_zone_loads": weak_denver_loads,
        "clean_exit_load": clean_exit_load,
        "all_loads": [parent_load, *weak_denver_loads, clean_exit_load],
    }


def scenario_file_path(file_path):
    if file_path:
        return str(file_path)

    path = Path(tempfile.gettempdir()) / "market_reload_watch_scenario_records.json"
    return str(path)


def run_market_reload_watch_scenario(scenario=None, file_path=""):
    scenario = scenario or build_strong_inbound_weak_exit_scenario()
    parent_load = scenario["parent_load"]
    clean_exit_load = scenario["clean_exit_load"]
    file_path = scenario_file_path(file_path)

    market_baseline = build_market_baseline(scenario["initial_market_loads"])
    zone_snapshot = build_market_zone_snapshot(scenario["initial_zone_loads"])
    exit_classification = classify_load_exit_market(
        parent_load,
        market_baseline,
        zone_snapshot,
    )
    chain_result = score_two_load_chain(
        parent_load,
        clean_exit_load,
        market_baseline=market_baseline,
        zone_snapshot=zone_snapshot,
    )
    watch_id = "WATCH-SCENARIO-1"
    watch_start_result = start_reload_watch(
        watch_id=watch_id,
        parent_load=parent_load,
        payload=exit_classification,
        timestamp_utc="2026-05-29T10:00:00Z",
        file_path=file_path,
    )
    event_result = handle_reload_watch_event(
        watch_id=watch_id,
        event_type="CLEAN_EXIT_FOUND",
        parent_load=parent_load,
        exit_context={
            "clean_exit_count": 1,
            "review_exit_count": exit_classification["review_exit_count"],
            "rate_check_exit_count": exit_classification["rate_check_exit_count"],
        },
        best_exit_load=clean_exit_load,
        chain_result=chain_result,
        timestamp_utc="2026-05-29T10:10:00Z",
        file_path=file_path,
    )
    telegram_preview = format_reload_watch_message(
        event_result.get("action_plan") or {}
    )

    return {
        "scenario_name": scenario["scenario_name"],
        "dry_run": True,
        "sent": False,
        "file_path": file_path,
        "parent_load": load_summary(parent_load),
        "clean_exit_load": load_summary(clean_exit_load),
        "market_baseline": market_baseline,
        "zone_snapshot": zone_snapshot,
        "exit_classification": exit_classification,
        "chain_result": chain_result,
        "watch_start_result": watch_start_result,
        "event_result": event_result,
        "telegram_preview": telegram_preview,
    }


def compact_number(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)

    return value


def console_safe_text(text):
    return str(text).encode("ascii", errors="replace").decode("ascii")


def format_scenario_result(result):
    baseline = result["market_baseline"]
    city = result["exit_classification"]["delivery_city"]
    state = result["exit_classification"]["delivery_state"]
    city_key = f"{city}, {state}" if city and state else ""
    city_context = (result["zone_snapshot"].get("cities") or {}).get(city_key, {})
    action_plan = result["event_result"].get("action_plan") or {}
    watch_record = result["watch_start_result"].get("watch_record") or {}

    lines = [
        "MARKET + RELOAD WATCH SCENARIO DRY-RUN",
        "--------------------------------------",
        "Scenario: strong inbound load into weak exit market, then clean exit appears",
        "",
        "Parent load:",
        (
            f"{result['parent_load']['pickup']} -> {result['parent_load']['delivery']} | "
            f"${compact_number(result['parent_load']['rate'])} | "
            f"RPM ${result['parent_load']['total_rpm']}"
        ),
        "",
        f"Market median RPM: ${baseline['median_rpm']}",
        f"Delivery market status: {city_context.get('status', 'NEEDS CHECK')}",
        f"Exit classification: {result['exit_classification']['exit_status']}",
        f"Reload watch recommended: {result['exit_classification']['recommend_reload_watch']}",
        f"Chain status: {result['chain_result']['chain_status']}",
        f"Watch ID: {watch_record.get('watch_id', '')}",
        f"Action type: {action_plan.get('action_type', '')}",
        "",
        "TELEGRAM PREVIEW ONLY - no message sent",
        "---------------------------------------",
        console_safe_text(result["telegram_preview"]),
        "",
        "DRY RUN ONLY - no Telegram message sent",
    ]

    return "\n".join(lines)
