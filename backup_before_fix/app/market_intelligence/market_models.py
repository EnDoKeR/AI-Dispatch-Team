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
        self.origin = origin
        self.destination = destination

        self.pickup = pickup or origin
        self.delivery = delivery or destination

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

        self.target_relation = "UNKNOWN"
        self.driver_fit_status = "UNKNOWN"

        self.extra = kwargs or {}

    def _to_number(self, value):
        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return value

        text = str(value).strip()

        if not text:
            return 0

        text = text.replace("$", "")
        text = text.replace(",", "")
        text = text.replace("lbs", "")
        text = text.replace("lb", "")
        text = text.replace("mi", "")
        text = text.strip()

        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return 0

    def _to_bool(self, value):
        if isinstance(value, bool):
            return value

        if value is None:
            return False

        text = str(value).strip().lower()

        return text in ["true", "1", "yes", "y", "book", "bookable"]

    def rpm(self):
        if not self.total_miles:
            return 0

        return round(self.rate / self.total_miles, 2)

    def loaded_rpm(self):
        if not self.loaded_miles:
            return 0

        return round(self.rate / self.loaded_miles, 2)

    def calculate_bucket(self):
        miles = self.loaded_miles or self.total_miles

        if miles < 450:
            return "0-450"

        if miles < 700:
            return "450-700"

        if miles < 1300:
            return "700-1300"

        return "1300+"

    def lane_key(self):
        return f"{self.origin} -> {self.destination}"

    def broker_key(self):
        return f"{self.broker_name}|{self.broker_mc}".strip("|")

    def matches_target_city_radius(self, search_request):
        """
        Temporary safe target city check.

        MVP:
        - If target_city is empty, return False.
        - If target_city text is inside destination, return True.
        - Real radius logic will be added later.
        """
        target_city = getattr(search_request, "target_city", "") or ""
        target_city = str(target_city).strip().lower()

        if not target_city:
            return False

        destination = str(self.destination or self.delivery or "").strip().lower()

        if not destination:
            return False

        return target_city in destination

    def matches_target_state_or_region(self, search_request):
        """
        Temporary safe state / region matching.
        """

        target = getattr(search_request, "target_direction", "") or ""
        target = str(target).strip().lower()

        if not target:
            return False

        destination = str(self.destination or self.delivery or "").strip().lower()

        if not destination:
            return False

        state_regions = {
            "midwest": [
                "il", "in", "oh", "mi", "wi", "mn", "ia", "mo", "ks", "ne", "sd", "nd"
            ],
            "texas": ["tx"],
            "south": [
                "tx", "ok", "ar", "la", "ms", "al", "ga", "fl", "sc", "nc", "tn", "ky"
            ],
            "southeast": [
                "fl", "ga", "sc", "nc", "tn", "al", "ms"
            ],
            "northeast": [
                "pa", "ny", "nj", "ct", "ma", "ri", "me", "nh", "vt", "md", "de"
            ],
            "west": [
                "ca", "or", "wa", "nv", "az", "ut", "id", "mt", "wy", "co", "nm"
            ],
            "pacific northwest": ["wa", "or", "id"],
            "pnw": ["wa", "or", "id"],
            "mountain": ["co", "ut", "id", "mt", "wy", "nv", "az", "nm"],
        }

        state_aliases = {
            "texas": "tx",
            "california": "ca",
            "florida": "fl",
            "illinois": "il",
            "indiana": "in",
            "ohio": "oh",
            "michigan": "mi",
            "wisconsin": "wi",
            "minnesota": "mn",
            "iowa": "ia",
            "missouri": "mo",
            "georgia": "ga",
            "north carolina": "nc",
            "south carolina": "sc",
            "tennessee": "tn",
            "kentucky": "ky",
            "pennsylvania": "pa",
            "new york": "ny",
            "new jersey": "nj",
            "washington": "wa",
            "oregon": "or",
            "arizona": "az",
            "colorado": "co",
            "utah": "ut",
        }

        if target in destination:
            return True

        target_state = state_aliases.get(target, target)

        if destination.endswith(f", {target_state}") or destination.endswith(f" {target_state}"):
            return True

        if target in state_regions:
            for state_code in state_regions[target]:
                if destination.endswith(f", {state_code}") or destination.endswith(f" {state_code}"):
                    return True

        return False

    def is_along_route_toward_target(self, search_request):
        """
        Temporary route fallback logic.

        MVP:
        If route_fallback_active is enabled and the load goes to a generally useful state,
        allow it as REVIEW_ONCE instead of full mismatch.
        """

        route_fallback_active = getattr(search_request, "route_fallback_active", False)

        if not route_fallback_active:
            return False

        target = str(getattr(search_request, "target_direction", "") or "").lower()
        destination = str(self.destination or self.delivery or "").lower()

        along_route_map = {
            "texas": ["ga", "al", "ms", "la", "tx", "ok", "ar"],
            "midwest": ["ga", "tn", "ky", "oh", "in", "il", "mo", "wi", "mi"],
            "northeast": ["ga", "sc", "nc", "va", "md", "pa", "nj", "ny"],
            "west": ["al", "ms", "la", "tx", "ok", "nm", "az", "co", "ut"],
        }

        states = along_route_map.get(target, [])

        for state_code in states:
            if destination.endswith(f", {state_code}") or destination.endswith(f" {state_code}"):
                return True

        return False

    def apply_search_request(self, search_request):
        self.match_reasons = []
        self.review_reasons = []
        self.block_reasons = []

        self.is_blocked = False
        self.is_review_once = False
        self.is_clean_match = False

        self.target_relation = "MISMATCH"
        self.driver_fit_status = "UNKNOWN"
        self.driver_match_status = "UNKNOWN"
        self.driver_match_notes = []

        max_weight = getattr(search_request, "max_weight", 0) or 0
        max_empty = getattr(search_request, "max_empty_miles", 200) or 200
        min_total_rpm = getattr(search_request, "min_total_rpm", 0) or 0
        equipment = str(getattr(search_request, "equipment", "") or "").lower()

        notes_lower = str(self.notes or "").lower()
        posted_lower = str(self.posted_trailer_type or self.equipment or "").lower()

        # Same city / local load blocker
        if str(self.origin).strip().lower() == str(self.destination).strip().lower():
            self.is_blocked = True
            self.block_reasons.append("Same pickup and delivery city.")

        if self.loaded_miles and self.loaded_miles <= 10:
            self.is_blocked = True
            self.block_reasons.append("Loaded miles are too low / local load.")

        # Weight logic
        if max_weight and self.weight and self.weight > max_weight:
            self.is_review_once = True
            self.review_reasons.append(
                f"Weight {self.weight} is above driver setting {max_weight}."
            )

        # Empty miles logic
        if max_empty and self.empty_miles and self.empty_miles > max_empty:
            self.is_review_once = True
            self.review_reasons.append(
                f"Empty miles {self.empty_miles} are above driver setting {max_empty}."
            )

        # RPM logic
        if min_total_rpm and self.total_rpm and self.total_rpm < min_total_rpm:
            self.is_blocked = True
            self.block_reasons.append(
                f"RPM ${self.total_rpm} is below minimum ${min_total_rpm}."
            )

        # Target logic
        if self.matches_target_city_radius(search_request):
            self.target_relation = "MATCH"
            self.match_reasons.append("Destination matches target city.")
        elif self.matches_target_state_or_region(search_request):
            self.target_relation = "MATCH"
            self.match_reasons.append("Destination matches target state/region.")
        elif self.is_along_route_toward_target(search_request):
            self.target_relation = "ALONG_ROUTE"
            self.is_review_once = True
            self.review_reasons.append(
                f"Load is along route toward {getattr(search_request, 'target_direction', '')}."
            )
        else:
            self.target_relation = "MISMATCH"
            self.is_review_once = True
            self.review_reasons.append(
                f"Delivery does not match target direction: {getattr(search_request, 'target_direction', '')}."
            )

        # Conestoga logic
        no_conestoga_terms = [
            "no conestoga",
            "no conestogas",
            "no stoga",
            "no stogas",
            "conestoga wouldn't work",
            "conestoga wont work",
            "flatbed only",
        ]

        if "conestoga" in equipment:
            if any(term in notes_lower for term in no_conestoga_terms):
                self.is_blocked = True
                self.block_reasons.append("Notes say Conestoga is not accepted.")
            elif "flatbed" in posted_lower or "step" in posted_lower or posted_lower in ["f", "fd", "ft"]:
                self.is_review_once = True
                self.review_reasons.append(
                    "Posted as Flatbed/Step Deck; Conestoga must be verified."
                )

        # Notes parser quick rules
        if "hazmat" in notes_lower:
            self.is_review_once = True
            self.review_reasons.append("Hazmat requirement detected.")

        if "tanker endorsement" in notes_lower or "tanker endorsment" in notes_lower:
            self.is_review_once = True
            self.review_reasons.append("Tanker endorsement required.")

        if "twic" in notes_lower:
            self.is_review_once = True
            self.review_reasons.append("TWIC requirement detected.")

        if "tracking required" in notes_lower or "macropoint" in notes_lower:
            self.review_reasons.append("Tracking required.")

        if "6ft" in notes_lower or "6 ft" in notes_lower or "6'" in notes_lower:
            self.review_reasons.append("6 ft tarps required.")

        # Final status
        if self.is_blocked:
            self.driver_fit_status = "BLOCKED"
            self.driver_match_status = "BLOCK"
            self.driver_match_notes = self.block_reasons
        elif self.is_review_once:
            self.driver_fit_status = "REVIEW_ONCE"
            self.driver_match_status = "REVIEW_ONCE"
            self.driver_match_notes = self.review_reasons
        else:
            self.driver_fit_status = "CLEAN_MATCH"
            self.driver_match_status = "MATCH"
            self.driver_match_notes = self.match_reasons
            self.is_clean_match = True

        return self

    def is_qualified(self):
        if self.driver_match_status == "BLOCK":
            return False

        if not self.rate:
            return False

        if not self.loaded_miles and not self.total_miles:
            return False

        return True

    def is_good(self):
        if not self.is_qualified():
            return False

        if self.rate >= 3000:
            return True

        if self.total_rpm >= 3:
            return True

        return False

    def opportunity_score(self):
        score = 0

        if self.rate >= 5000:
            score += 30
        elif self.rate >= 3500:
            score += 25
        elif self.rate >= 2500:
            score += 18
        elif self.rate >= 1500:
            score += 10
        else:
            score += 5

        if self.total_rpm >= 4:
            score += 30
        elif self.total_rpm >= 3:
            score += 25
        elif self.total_rpm >= 2.5:
            score += 18
        elif self.total_rpm >= 2:
            score += 10
        else:
            score += 3

        if self.empty_miles <= 50:
            score += 15
        elif self.empty_miles <= 150:
            score += 10
        elif self.empty_miles <= 250:
            score += 5

        if self.driver_match_status == "MATCH":
            score += 20
        elif self.driver_match_status == "REVIEW_ONCE":
            score += 8
        elif self.driver_match_status == "BLOCK":
            score -= 50

        if self.delivery_zone and "GOOD" in str(self.delivery_zone).upper():
            score += 5

        return max(0, round(score))

    def priority(self):
        score = self.opportunity_score()

        if self.driver_match_status == "BLOCK":
            return "BLOCK"

        if score >= 90:
            return "HIGH"

        if score >= 75:
            return "MEDIUM"

        return "LOW"

    def suggested_action(self):
        if self.driver_match_status == "BLOCK":
            return "DO NOT SEND"

        if self.driver_match_status == "REVIEW_ONCE":
            return "REVIEW ONCE"

        if self.opportunity_score() >= 90:
            return "CALL NOW + EMAIL BACKUP"

        if self.opportunity_score() >= 75:
            return "CALL IF AVAILABLE"

        return "MONITOR"

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