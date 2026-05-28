import re

from app.market_intelligence.market_location_helpers import (
    ROUTE_TOWARD_TARGET_STATES,
    TARGET_STATE_MAP,
    location_has_state,
    location_state,
    normalize_location_text,
)
from app.market_intelligence.market_review_category import classify_review_category
from app.market_intelligence.market_contact_extractor import extract_email, extract_phone
from app.market_intelligence.market_city_distance import distance_between_known_cities
from app.market_intelligence.market_region_conflict import pickup_region_conflict_with_driver
from app.market_intelligence.market_match_status import finalize_driver_match, reset_driver_match_state
from app.market_intelligence.market_tarp_requirements import apply_tarps_requirement
from app.market_intelligence.market_document_requirements import (
    require_driver_document,
    require_one_of_driver_documents,
)
from app.market_intelligence.market_tracking_requirements import apply_tracking_requirement
from app.market_intelligence.market_direction_matcher import apply_direction_match
from app.market_intelligence.market_conestoga_rules import apply_conestoga_rules
from app.market_intelligence.market_broker_memory import apply_broker_memory
from app.market_intelligence.market_local_load_rules import apply_local_load_rules
from app.market_intelligence.market_weight_rules import apply_weight_rules
from app.market_intelligence.market_od_permit_rules import apply_od_permit_rules
from app.market_intelligence.market_quality_rules import apply_quality_rules
from app.market_intelligence.market_scoring import (
    is_good as score_is_good,
    is_qualified as score_is_qualified,
    opportunity_reason as score_opportunity_reason,
    opportunity_score as score_opportunity_score,
    priority as score_priority,
    reject_reasons as score_reject_reasons,
    suggested_action as score_suggested_action,
)
from app.market_intelligence.market_basic_metrics import (
    broker_key as basic_broker_key,
    calculate_bucket as basic_calculate_bucket,
    lane_key as basic_lane_key,
    loaded_rpm as basic_loaded_rpm,
    rpm as basic_rpm,
    to_bool as basic_to_bool,
    to_number as basic_to_number,
)
from app.market_intelligence.market_target_helpers import (
    delivery_is_along_route as target_delivery_is_along_route,
    delivery_matches_target as target_delivery_matches_target,
    is_along_route_toward_target as target_is_along_route_toward_target,
    is_strong_off_target_exception as target_is_strong_off_target_exception,
    matches_target_city_radius as target_matches_target_city_radius,
    matches_target_state_or_region as target_matches_target_state_or_region,
    off_target_review_reason as target_off_target_review_reason,
    route_toward_target_states as target_route_toward_target_states,
    should_block_off_target as target_should_block_off_target,
    target_states as target_target_states,
)


class MarketLoad:
    def __init__(
        self,
        origin="",
        destination="",
        rate=0,
        loaded_miles=0,
        empty_miles=0,
        total_miles=0,
        pickup_date="",
        delivery_date="",
        pickup="",
        delivery="",
        pickup_time="",
        delivery_time="",
        weight=0,
        posted_trailer_type="",
        equipment="",
        commodity="",
        notes="",
        parsed_notes=None,
        broker_name="",
        broker_mc="",
        broker_contact="",
        broker_contact_raw="",
        parsed_contact=None,
        credit_score="",
        days_to_pay="",
        reference_id="",
        is_bookable=False,
        is_private=False,
        is_partial=False,
        is_od=False,
        is_tracking_required=False,
        broker_status="UNKNOWN",
        delivery_zone="UNKNOWN",
        **kwargs,
    ):
        self.pickup = pickup or origin
        self.delivery = delivery or destination

        self.origin = origin or self.pickup
        self.destination = destination or self.delivery

        self.rate = self._to_number(rate)
        self.loaded_miles = self._to_number(loaded_miles)
        self.empty_miles = self._to_number(empty_miles)

        if total_miles:
            self.total_miles = self._to_number(total_miles)
        else:
            self.total_miles = self.loaded_miles + self.empty_miles

        self.total_rpm = self.rpm()

        self.pickup_date = pickup_date
        self.delivery_date = delivery_date
        self.pickup_time = pickup_time
        self.delivery_time = delivery_time

        self.weight = self._to_number(weight)
        self.posted_trailer_type = posted_trailer_type or equipment
        self.equipment = equipment or posted_trailer_type
        self.commodity = commodity

        self.notes = notes
        self.parsed_notes = parsed_notes or {}

        self.broker_name = broker_name
        self.broker_mc = broker_mc
        self.broker_contact = broker_contact
        self.broker_contact_raw = broker_contact_raw
        self.parsed_contact = parsed_contact or {}

        self.primary_email = self._extract_email()
        self.primary_phone = self._extract_phone()

        self.has_email = bool(self.primary_email)
        self.has_phone = bool(self.primary_phone)

        self.credit_score = credit_score
        self.days_to_pay = days_to_pay
        self.reference_id = reference_id

        self.is_bookable = self._to_bool(is_bookable)
        self.is_private = self._to_bool(is_private)
        self.is_partial = self._to_bool(is_partial)
        self.is_od = self._to_bool(is_od)
        self.is_tracking_required = self._to_bool(is_tracking_required)

        self.broker_status = broker_status
        self.delivery_zone = delivery_zone

        self.bucket = self.calculate_bucket()

        self.driver_match_status = "UNKNOWN"
        self.driver_match_notes = []
        self.match_reasons = []
        self.review_reasons = []
        self.block_reasons = []

        self.is_blocked = False
        self.is_review_once = False
        self.is_clean_match = False

        self.is_overweight = False
        self.is_low_rpm = False
        self.is_too_far_empty = False
        self.is_local_load = False

        self.target_relation = "UNKNOWN"
        self.driver_fit_status = "UNKNOWN"

        self.extra = kwargs or {}

    def review_category(self):
        return classify_review_category(self)

    def _to_number(self, value):
        return basic_to_number(value)

    def _to_bool(self, value):
        return basic_to_bool(value)

    def rpm(self):
        return basic_rpm(self)

    def loaded_rpm(self):
        return basic_loaded_rpm(self)

    def calculate_bucket(self):
        return basic_calculate_bucket(self)

    def lane_key(self):
        return basic_lane_key(self)

    def broker_key(self):
        return basic_broker_key(self)

    def matches_target_city_radius(self, search_request):
        return target_matches_target_city_radius(self, search_request)

    def target_states(self, search_request):
        return target_target_states(search_request)

    def route_toward_target_states(self, search_request):
        return target_route_toward_target_states(search_request)

    def delivery_matches_target(self, search_request):
        return target_delivery_matches_target(self, search_request)

    def delivery_is_along_route(self, search_request):
        return target_delivery_is_along_route(self, search_request)

    def is_strong_off_target_exception(self):
        return target_is_strong_off_target_exception(self)

    def should_block_off_target(self, search_request):
        return target_should_block_off_target(self, search_request)

    def off_target_review_reason(self, search_request):
        return target_off_target_review_reason(self, search_request)

    def matches_target_state_or_region(self, search_request):
        return target_matches_target_state_or_region(self, search_request)

    def is_along_route_toward_target(self, search_request):
        return target_is_along_route_toward_target(self, search_request)

    def _extract_email(self):
        return extract_email(
            parsed_contact=self.parsed_contact,
            broker_contact=self.broker_contact,
            broker_contact_raw=self.broker_contact_raw,
            notes=self.notes,
        )

    def _extract_phone(self):
        return extract_phone(
            parsed_contact=self.parsed_contact,
            broker_contact=self.broker_contact,
            broker_contact_raw=self.broker_contact_raw,
            notes=self.notes,
        )

    def pickup_region_conflict_with_driver(self, search_request):
        return pickup_region_conflict_with_driver(self, search_request)

    def apply_search_request(self, search_request):
        reset_driver_match_state(self)

        max_weight = getattr(search_request, "max_weight", 0) or 0
        max_empty = getattr(search_request, "max_empty_miles", 200) or 200
        min_total_rpm = getattr(search_request, "min_total_rpm", 0) or 0
        equipment = str(getattr(search_request, "equipment", "") or "").lower()

        notes_lower = str(self.notes or "").lower()
        posted_lower = str(self.posted_trailer_type or self.equipment or "").lower()

        origin_text = str(self.origin or self.pickup or "").strip().lower()
        destination_text = str(self.destination or self.delivery or "").strip().lower()

        parsed_notes = self.parsed_notes or {}

        combined_text = (
            f"{self.notes} "
            f"{self.commodity} "
            f"{self.posted_trailer_type} "
            f"{self.equipment}"
        ).lower()

        # Same city / local load blocker
        apply_local_load_rules(self, origin_text, destination_text)

        # Weight logic
        apply_weight_rules(self, max_weight, equipment)

        # OD / permit logic
        apply_od_permit_rules(self, search_request, parsed_notes, notes_lower)

        # Empty miles / rate / RPM quality logic
        apply_quality_rules(self, max_empty, min_total_rpm)

        # Payment / broker no-buy warning
        if (
            "cash or zelle" in combined_text
            or "cash/zelle" in combined_text
            or "cashapp" in combined_text
            or "cash app" in combined_text
            or "zelle" in combined_text
            or "venmo" in combined_text
        ):
            self.is_blocked = True
            self.block_reasons.append(
                "Cash/Zelle type payment detected; likely no-buy / risky broker payment."
            )

        # Hazmat
        if (
            "hazmat" in combined_text
            or "haz mat" in combined_text
            or "haz-mat" in combined_text
            or "hazardous" in combined_text
        ):
            require_driver_document(
                self,
                search_request,
                "driver_hazmat",
                "Hazmat certificate",
            )

        # Tanker endorsement
        if (
            "tanker" in combined_text
            or "tank endorsement" in combined_text
            or "tanker endorsement" in combined_text
            or "tanker endorsment" in combined_text
            or "tanker endoresment" in combined_text
        ):
            require_driver_document(
                self,
                search_request,
                "driver_tanker_endorsement",
                "Tanker endorsement",
            )

        # TWIC card
        if (
            "twic" in combined_text
            or "twic card" in combined_text
        ):
            require_driver_document(
                self,
                search_request,
                "driver_twic",
                "TWIC card",
            )

        # US legal status
        if (
            "us citizen" in combined_text
            or "u.s. citizen" in combined_text
            or "citizen required" in combined_text
            or "green card" in combined_text
            or "green-card" in combined_text
            or "permanent resident" in combined_text
            or "work permit" in combined_text
            or "employment authorization" in combined_text
            or "ead card" in combined_text
        ):
            require_one_of_driver_documents(
                self,
                search_request,
                [
                    ("driver_us_citizen", "US citizen"),
                    ("driver_green_card_holder", "Green card"),
                    ("driver_work_permit", "Work permit"),
                ],
                "US legal status",
            )

        # Ramps
        if (
            "need ramps" in combined_text
            or "ramps required" in combined_text
            or "ramps req" in combined_text
            or "need ramp" in combined_text
        ):
            require_driver_document(
                self,
                search_request,
                "driver_ramps",
                "Ramps",
            )

        # Dunnage / wood / blocking / bracing
        if (
            "dunnage" in combined_text
            or "must provide wood" in combined_text
            or "provide wood" in combined_text
            or "wood required" in combined_text
            or "blocking and bracing" in combined_text
            or "block and brace" in combined_text
        ):
            require_driver_document(
                self,
                search_request,
                "driver_dunnage",
                "Dunnage / wood / blocking material",
            )

        # Tarps
        apply_tarps_requirement(self, search_request, combined_text)

        # Tracking
        apply_tracking_requirement(self, search_request, combined_text)

        # Direction / target logic
        apply_direction_match(self, search_request)

        # Conestoga logic
        apply_conestoga_rules(self, equipment, notes_lower, posted_lower)

        if self.pickup_region_conflict_with_driver(search_request):
            self.is_blocked = True
            self.block_reasons.append(
                "Pickup appears too far from driver location."
            )

        # Broker memory logic
        apply_broker_memory(self)

        finalize_driver_match(self)

        return self


    def is_qualified(self):
        return score_is_qualified(self)

    def is_good(self):
        return score_is_good(self)

    def opportunity_score(self):
        return score_opportunity_score(self)

    def priority(self):
        return score_priority(self)

    def suggested_action(self):
        return score_suggested_action(self)

    def reject_reasons(self):
        return score_reject_reasons(self)

    def distance_between_known_cities(self, city_a, city_b):
        return distance_between_known_cities(city_a, city_b)

    def opportunity_reason(self):
        return score_opportunity_reason(self)

    def to_dict(self):
        return {
            "origin": self.origin,
            "destination": self.destination,
            "pickup": self.pickup,
            "delivery": self.delivery,
            "rate": self.rate,
            "loaded_miles": self.loaded_miles,
            "empty_miles": self.empty_miles,
            "total_miles": self.total_miles,
            "total_rpm": self.total_rpm,
            "loaded_rpm": self.loaded_rpm(),
            "bucket": self.bucket,
            "pickup_date": self.pickup_date,
            "delivery_date": self.delivery_date,
            "pickup_time": self.pickup_time,
            "delivery_time": self.delivery_time,
            "weight": self.weight,
            "posted_trailer_type": self.posted_trailer_type,
            "equipment": self.equipment,
            "commodity": self.commodity,
            "notes": self.notes,
            "parsed_notes": self.parsed_notes,
            "broker_name": self.broker_name,
            "broker_mc": self.broker_mc,
            "broker_contact": self.broker_contact,
            "primary_email": self.primary_email,
            "primary_phone": self.primary_phone,
            "has_email": self.has_email,
            "has_phone": self.has_phone,
            "broker_contact_raw": self.broker_contact_raw,
            "parsed_contact": self.parsed_contact,
            "credit_score": self.credit_score,
            "days_to_pay": self.days_to_pay,
            "reference_id": self.reference_id,
            "driver_match_status": self.driver_match_status,
            "driver_match_notes": self.driver_match_notes,
            "opportunity_score": self.opportunity_score(),
            "priority": self.priority(),
            "suggested_action": self.suggested_action(),
            "is_bookable": self.is_bookable,
            "is_private": self.is_private,
            "is_partial": self.is_partial,
            "is_od": self.is_od,
            "is_tracking_required": self.is_tracking_required,
            "broker_status": self.broker_status,
            "delivery_zone": self.delivery_zone,
            "extra": self.extra,
        }


class DriverProfile:
    def __init__(
        self,
        name="",
        current_location="",
        available_time="",
        equipment="",
        max_weight=40000,
        max_empty_miles=200,
        target_direction="",
        target_city="",
        target_radius_miles=200,
        min_total_rpm=2.5,
        hazmat=None,
        tanker_endorsement=None,
        twic=None,
        us_citizen=None,
        green_card_holder=None,
        work_permit=None,
        ramps=None,
        dunnage=None,
        tracking_ok=True,
        **kwargs,
    ):
        self.name = name
        self.current_location = current_location
        self.available_time = available_time
        self.equipment = equipment

        self.max_weight = self._to_number(max_weight)
        self.max_empty_miles = self._to_number(max_empty_miles)
        self.target_direction = target_direction
        self.target_city = target_city
        self.target_radius_miles = self._to_number(target_radius_miles)
        self.min_total_rpm = float(min_total_rpm or 0)

        self.hazmat = hazmat
        self.tanker_endorsement = tanker_endorsement
        self.twic = twic
        self.us_citizen = us_citizen
        self.green_card_holder = green_card_holder
        self.work_permit = work_permit

        self.ramps = ramps
        self.dunnage = dunnage
        self.tracking_ok = tracking_ok

        self.extra = kwargs or {}

    def _to_number(self, value):
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return value

        text = str(value).strip().replace(",", "")

        try:
            return int(text)
        except ValueError:
            return 0
