import re


def normalize_location_text(value):
    return str(value or "").strip().lower()


def location_has_state(location, state_code):
    location = normalize_location_text(location)
    state_code = normalize_location_text(state_code)

    if not location or not state_code:
        return False

    return (
        location.endswith(f", {state_code}")
        or location.endswith(f" {state_code}")
        or f", {state_code} " in location
    )


def location_state(location):
    location = str(location or "").strip()

    if "," in location:
        parts = location.split(",")
        possible_state = parts[-1].strip().upper()
        if len(possible_state) == 2:
            return possible_state

    words = location.split()
    if words:
        possible_state = words[-1].strip().upper()
        if len(possible_state) == 2:
            return possible_state

    return ""


TARGET_STATE_MAP = {
    "texas": ["TX"],
    "tx": ["TX"],

    "midwest": ["IL", "IN", "OH", "MI", "WI", "MN", "IA", "MO", "KS", "NE", "ND", "SD"],
    "north east": ["PA", "NY", "NJ", "CT", "MA", "RI", "NH", "VT", "ME"],
    "northeast": ["PA", "NY", "NJ", "CT", "MA", "RI", "NH", "VT", "ME"],
    "south east": ["GA", "SC", "NC", "TN", "AL"],
    "southeast": ["GA", "SC", "NC", "TN", "AL"],
    "west": ["CA", "OR", "WA", "NV", "AZ", "UT", "ID"],
}


ROUTE_TOWARD_TARGET_STATES = {
    "texas": ["AL", "MS", "LA", "AR", "OK", "TX"],
    "tx": ["AL", "MS", "LA", "AR", "OK", "TX"],

    "midwest": ["GA", "AL", "TN", "KY", "IN", "IL", "OH", "MO", "WI", "MI", "IA", "MN"],
    "north east": ["GA", "SC", "NC", "VA", "MD", "PA", "NJ", "NY"],
    "northeast": ["GA", "SC", "NC", "VA", "MD", "PA", "NJ", "NY"],
    "west": ["AL", "MS", "LA", "TX", "OK", "NM", "AZ", "CA", "NV", "UT"],
}
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
        all_reason_parts = []

        for attr_name in [
            "review_reasons",
            "driver_match_notes",
            "block_reasons",
            "match_reasons",
        ]:
            value = getattr(self, attr_name, [])

            if isinstance(value, list):
                all_reason_parts.extend(str(item) for item in value)
            elif value:
                all_reason_parts.append(str(value))

        notes = str(getattr(self, "notes", "") or "").lower()
        commodity = str(getattr(self, "commodity", "") or "").lower()

        reasons = " ".join(all_reason_parts).lower()

        # RATE CHECK has highest priority.
        if (
            "rate is missing" in reasons
            or "posted as $0" in reasons
            or "rate check" in reasons
            or "check rate with broker" in reasons
        ):
            return "RATE CHECK"

        # OD / PERMIT.
        if (
            "od / permit" in reasons
            or "od load" in reasons
            or "over dimension" in reasons
            or "overdimensional" in reasons
            or "permit load" in reasons
            or "permits required" in reasons
            or "permit required" in reasons
            or "wide load" in reasons
            or "oversize" in reasons
            or "over size" in reasons
            or "os/ow" in reasons
            or "od / permit" in notes
            or "od load" in notes
            or "permit load" in notes
            or "permits required" in notes
            or "permit required" in notes
            or "wide load" in notes
            or "oversize" in notes
            or "over size" in notes
            or "over-dimensional" in notes
            or "overdimensional" in notes
            or "os/ow" in notes
        ):
            return "OD / PERMIT"

        # Conestoga verify.
        if (
            "conestoga must be verified" in reasons
            or "posted as flatbed/step deck" in reasons
            or "conestoga verify" in reasons
        ):
            return "CONESTOGA VERIFY"

        # Along route should not become DOCUMENTS REQUIRED because of words like Midwest.
        if "along route" in reasons:
            return "ALONG ROUTE"

        # Document-related review.
        # Important: do NOT use generic "id" here.
        document_terms = [
            "hazmat",
            "haz mat",
            "tanker endorsement",
            "tank endorsement",
            "twic",
            "us citizen",
            "u.s. citizen",
            "green card",
            "work permit",
            "legal status",
            "ramps required",
            "need ramps",
            "dunnage",
            "must provide wood",
            "provide wood",
            "wood required",
            "blocking and bracing",
            "block and brace",
            "iso tank",
            "iso tanks",
        ]

        if any(term in reasons for term in document_terms):
            return "DOCUMENTS REQUIRED"

        if "iso tank" in notes or "iso tanks" in notes:
            return "DOCUMENTS REQUIRED"

        if "iso tank" in commodity or "iso tanks" in commodity:
            return "DOCUMENTS REQUIRED"

        if "strong off-target" in reasons:
            return "STRONG OFF-TARGET"

        if (
            "pickup time" in reasons
            or "delivery time" in reasons
            or "time check" in reasons
            or "needs check" in reasons
        ):
            return "TIME CHECK"

        if "weight" in reasons:
            return "WEIGHT CHECK"

        if (
            "tarps required" in reasons
            or "tarp required" in reasons
            or "ft tarps" in reasons
        ):
            return "TARPS REQUIRED"

        return "GENERAL REVIEW"



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

    def target_states(self, search_request):
     target = str(getattr(search_request, "target_direction", "") or "").strip().lower()
     return TARGET_STATE_MAP.get(target, [])


    def route_toward_target_states(self, search_request):
        target = str(getattr(search_request, "target_direction", "") or "").strip().lower()
        return ROUTE_TOWARD_TARGET_STATES.get(target, [])


    def delivery_matches_target(self, search_request):
        delivery_state = location_state(self.delivery)

        if not delivery_state:
            return False

        target_states = self.target_states(search_request)

        if delivery_state in target_states:
            return True

        return False


    def delivery_is_along_route(self, search_request):
        delivery_state = location_state(self.delivery)

        if not delivery_state:
            return False

        target_states = self.target_states(search_request)
        route_states = self.route_toward_target_states(search_request)

        if delivery_state in target_states:
            return True

        if delivery_state in route_states:
            return True

        return False


    def is_strong_off_target_exception(self):
        """
        Very strong load, but not in target direction.

        We keep this strict because otherwise the bot may send too many
        random high-RPM short loads that are not useful for the driver's plan.
        """
        return (
            self.total_rpm >= 4.5
            and self.rate >= 2800
            and self.empty_miles <= 150
            and self.loaded_miles >= 450
    )


    def should_block_off_target(self, search_request):
        """
        Blocks loads that do not match target and are not good route exceptions.
        """
        if self.delivery_matches_target(search_request):
            return False

        if self.delivery_is_along_route(search_request):
            return False

        if self.is_strong_off_target_exception():
            return False

        return True


    def off_target_review_reason(self, search_request):
        if self.delivery_matches_target(search_request):
            return ""

        if self.delivery_is_along_route(search_request):
            return f"Load is along route toward {search_request.target_direction}."

        if self.is_strong_off_target_exception():
            return (
                f"Strong off-target exception: RPM ${self.total_rpm} "
                f"and gross ${self.rate}, but delivery does not match target direction."
            )

        return f"Delivery does not match target direction: {search_request.target_direction}."

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

    def _extract_email(self):
        """
        Finds best available broker email from parsed_contact, broker_contact,
        broker_contact_raw, or notes.
        Also fixes common DAT-style mistakes like ` instead of .
        """

        import re

        candidates = []

        if isinstance(self.parsed_contact, dict):
            for key in ["email", "emails", "contact_email"]:
                value = self.parsed_contact.get(key)

                if isinstance(value, list):
                    candidates.extend(value)
                elif value:
                    candidates.append(value)

        candidates.extend([
            self.broker_contact,
            self.broker_contact_raw,
            self.notes,
        ])

        combined = " ".join(str(item or "") for item in candidates)

        combined = combined.replace("`", ".")
        combined = combined.replace(" dot ", ".")
        combined = combined.replace("[dot]", ".")
        combined = combined.replace("(dot)", ".")
        combined = combined.replace(" at ", "@")
        combined = combined.replace("[at]", "@")
        combined = combined.replace("(at)", "@")

        match = re.search(
            r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
            combined,
        )

        if match:
            return match.group(0).strip()

        return ""

    def _extract_phone(self):
        """
        Finds phone number from parsed_contact, broker_contact,
        broker_contact_raw, or notes.
        Keeps extension if detected.
        """

        import re

        candidates = []

        if isinstance(self.parsed_contact, dict):
            for key in ["phone", "phones", "contact_phone"]:
                value = self.parsed_contact.get(key)

                if isinstance(value, list):
                    candidates.extend(value)
                elif value:
                    candidates.append(value)

        candidates.extend([
            self.broker_contact,
            self.broker_contact_raw,
            self.notes,
        ])

        combined = " ".join(str(item or "") for item in candidates)

        phone_match = re.search(
            r"(\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4})",
            combined,
        )

        if not phone_match:
            return ""

        phone = phone_match.group(1).strip()

        ext_match = re.search(
            r"(?:ext|x|extension|ref)\s*[:#.]?\s*(\d{1,6})",
            combined,
            re.IGNORECASE,
        )

        if ext_match:
            phone = f"{phone} x{ext_match.group(1)}"

        return phone

    def pickup_region_conflict_with_driver(self, search_request):
        """
        Safety check for MVP.

        If driver location state and pickup state are clearly different,
        but empty miles are suspiciously low, we should not allow the load.

        Example:
        - Driver in Stockton, CA
        - Pickup in Lakeland, FL
        - Empty miles says 45

        That is impossible and usually means the load belongs to another
        test/search area.
        """

        driver_location = str(getattr(search_request, "current_location", "") or "").strip()
        pickup_location = str(self.pickup or self.origin or "").strip()

        if not driver_location or not pickup_location:
            return False

        driver_state = location_state(driver_location)
        pickup_state = location_state(pickup_location)

        if not driver_state or not pickup_state:
            return False

        if driver_state == pickup_state:
            return False

        nearby_states = {
            "CA": ["NV", "OR", "AZ"],
            "OR": ["CA", "WA", "ID", "NV"],
            "WA": ["OR", "ID"],
            "NV": ["CA", "OR", "ID", "UT", "AZ"],
            "AZ": ["CA", "NV", "UT", "NM"],
            "TX": ["OK", "AR", "LA", "NM"],
            "FL": ["GA", "AL"],
            "GA": ["FL", "AL", "TN", "SC", "NC"],
            "AL": ["FL", "GA", "MS", "TN"],
            "TN": ["AL", "GA", "KY", "AR", "MS", "MO", "NC"],
            "CO": ["WY", "NE", "KS", "OK", "NM", "AZ", "UT"],
            "IL": ["WI", "IA", "MO", "KY", "IN"],
            "IN": ["IL", "MI", "OH", "KY"],
            "OH": ["IN", "MI", "PA", "WV", "KY"],
        }

        allowed_neighbor_states = nearby_states.get(driver_state, [])

        if pickup_state in allowed_neighbor_states:
            return False

        if self.empty_miles <= 250:
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

        origin_text = str(self.origin or self.pickup or "").strip().lower()
        destination_text = str(self.destination or self.delivery or "").strip().lower()

        parsed_notes = self.parsed_notes or {}

        combined_text = (
            f"{self.notes} "
            f"{self.commodity} "
            f"{self.posted_trailer_type} "
            f"{self.equipment}"
        ).lower()

        def document_status(document_key):
            return getattr(search_request, document_key, None)

        def require_driver_document(document_key, document_label):
            status = document_status(document_key)

            if status is True:
                self.match_reasons.append(
                    f"{document_label} confirmed in driver profile."
                )
                return

            if status is False:
                self.is_blocked = True
                self.block_reasons.append(
                    f"{document_label} required, but driver profile says driver does not have it."
                )
                return

            self.is_review_once = True
            self.review_reasons.append(
                f"{document_label} required; ask driver and save answer in driver profile."
            )

        def require_one_of_driver_documents(document_options, requirement_label):
            confirmed_documents = []
            unknown_documents = []

            for document_key, document_label in document_options:
                status = document_status(document_key)

                if status is True:
                    confirmed_documents.append(document_label)
                elif status is None:
                    unknown_documents.append(document_label)

            if confirmed_documents:
                self.match_reasons.append(
                    f"{requirement_label} confirmed in driver profile: {', '.join(confirmed_documents)}."
                )
                return

            if unknown_documents:
                self.is_review_once = True
                self.review_reasons.append(
                    f"{requirement_label} required; ask driver about: {', '.join(unknown_documents)} and save answer in driver profile."
                )
                return

            self.is_blocked = True
            self.block_reasons.append(
                f"{requirement_label} required, but driver profile has no accepted document/status."
            )

        def get_tarp_size_feet(text):
            import re

            text = str(text or "").lower()

            match = re.search(
                r"\b(4|6|8)\s*(?:ft|feet|foot|['’])\b",
                text,
            )

            if not match:
                return 0

            return int(match.group(1))

        def detect_tarps_requirement(text):
            import re

            text = str(text or "").lower()

            no_tarp_terms = [
                "no tarp",
                "no tarps",
                "no tarping",
                "no tarp required",
                "no tarps required",
                "does not need tarps",
                "tarps not required",
                "tarp not required",
            ]

            if any(term in text for term in no_tarp_terms):
                return False, 0

            tarp_patterns = [
                r"\b4\s*(?:ft|feet|foot|['’])\s*tarps?\b",
                r"\b6\s*(?:ft|feet|foot|['’])\s*tarps?\b",
                r"\b8\s*(?:ft|feet|foot|['’])\s*tarps?\b",
                r"\b4ft\s*tarps?\b",
                r"\b6ft\s*tarps?\b",
                r"\b8ft\s*tarps?\b",
                r"\btarps?\s*required\b",
                r"\btarps?\s*req\b",
                r"\bneed\s*tarps?\b",
                r"\bneeds\s*tarps?\b",
                r"\bmust\s*tarp\b",
                r"\btarping\s*required\b",
            ]

            for pattern in tarp_patterns:
                if re.search(pattern, text):
                    required_size = get_tarp_size_feet(text)
                    return True, required_size

            return None, 0

        def apply_tarps_requirement():
            tarps_required, required_tarp_size = detect_tarps_requirement(combined_text)

            if tarps_required is not True:
                return

            driver_equipment = str(
                getattr(search_request, "equipment", "") or ""
            ).lower()

            if "conestoga" in driver_equipment:
                if required_tarp_size:
                    self.match_reasons.append(
                        f"{required_tarp_size} ft tarp requirement covered by Conestoga."
                    )
                else:
                    self.match_reasons.append(
                        "Tarp requirement covered by Conestoga."
                    )

                return

            driver_can_take_tarps_value = getattr(
                search_request,
                "driver_can_take_tarps",
                None,
            )

            driver_max_tarp_size_value = getattr(
                search_request,
                "driver_max_tarp_size",
                "",
            )

            driver_max_tarp_size_feet = get_tarp_size_feet(
                driver_max_tarp_size_value
            )

            if driver_can_take_tarps_value is True:
                if (
                    required_tarp_size
                    and driver_max_tarp_size_feet
                    and required_tarp_size > driver_max_tarp_size_feet
                ):
                    self.is_review_once = True
                    self.review_reasons.append(
                        f"{required_tarp_size} ft tarps required, but driver max tarp size is {driver_max_tarp_size_feet} ft."
                    )
                    return

                if required_tarp_size:
                    self.match_reasons.append(
                        f"{required_tarp_size} ft tarps accepted by driver profile."
                    )
                else:
                    self.match_reasons.append(
                        "Tarps accepted by driver profile."
                    )

                return

            if driver_can_take_tarps_value is False:
                self.is_blocked = True

                if required_tarp_size:
                    self.block_reasons.append(
                        f"{required_tarp_size} ft tarps required, but driver profile says driver cannot take tarps."
                    )
                else:
                    self.block_reasons.append(
                        "Tarps required, but driver profile says driver cannot take tarps."
                    )

                return

            self.is_review_once = True

            if required_tarp_size:
                self.review_reasons.append(
                    f"{required_tarp_size} ft tarps required; ask driver and save answer in driver profile."
                )
            else:
                self.review_reasons.append(
                    "Tarps required; ask driver and save answer in driver profile."
                )

        # Same city / local load blocker
        if origin_text and destination_text and origin_text == destination_text:
            self.is_local_load = True
            self.is_blocked = True
            self.block_reasons.append("Same pickup and delivery city.")

        if self.loaded_miles and self.loaded_miles <= 10:
            self.is_local_load = True
            self.is_blocked = True
            self.block_reasons.append("Loaded miles are too low / local load.")

        # Weight logic
                # Weight logic
        if max_weight and self.weight and self.weight > max_weight:
            self.is_overweight = True

            if "conestoga" in equipment:
                self.is_blocked = True
                self.block_reasons.append(
                    f"Weight {self.weight} is above Conestoga driver setting {max_weight}."
                )
            else:
                self.is_review_once = True
                self.review_reasons.append(
                    f"Weight {self.weight} is above driver setting {max_weight}."
                )

        # OD / permit logic
        is_od_note = bool(
            parsed_notes.get("is_od")
            or parsed_notes.get("is_oversize")
            or parsed_notes.get("is_wide")
            or parsed_notes.get("requires_permit")
            or parsed_notes.get("permit_load")
        )

        od_keywords = [
            "permit load",
            "permits required",
            "permit required",
            "over dimension",
            "over-dimensional",
            "overdimensional",
            "oversize",
            "over size",
            "wide load",
            "od load",
            "os/ow",
        ]

        if any(keyword in notes_lower for keyword in od_keywords):
            is_od_note = True

        if is_od_note:
            self.is_od = True

            if str(search_request.equipment or "").lower() == "conestoga":
                self.is_blocked = True
                self.block_reasons.append(
                    "OD / permit / wide load detected; Conestoga should not take OD loads."
                )
            else:
                self.is_review_once = True
                self.review_reasons.append(
                    "OD / permit / wide load detected; dispatcher must verify permits/dimensions."
                )

        # Empty miles logic
        if max_empty and self.empty_miles and self.empty_miles > max_empty:
            self.is_too_far_empty = True
            self.is_review_once = True
            self.review_reasons.append(
                f"Empty miles {self.empty_miles} are above driver setting {max_empty}."
            )
        # Rate check logic
        if not self.rate:
            self.is_review_once = True
            self.review_reasons.append(
                "Rate is missing / posted as $0; dispatcher should check rate with broker."
            )

        # RPM logic
        # RPM should not be a hard blocker.
        # It is only a quality warning / scoring factor.
        if min_total_rpm and self.total_rpm and self.total_rpm < min_total_rpm:
            self.is_low_rpm = True
            self.match_reasons.append(
                f"RPM ${self.total_rpm} is below preferred minimum ${min_total_rpm}."
            )

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
                "driver_tanker_endorsement",
                "Tanker endorsement",
            )

        # TWIC card
        if (
            "twic" in combined_text
            or "twic card" in combined_text
        ):
            require_driver_document(
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
                "driver_dunnage",
                "Dunnage / wood / blocking material",
            )

        # Tarps
        apply_tarps_requirement()

        # Tracking
        if (
            "tracking required" in combined_text
            or "macro point" in combined_text
            or "macropoint" in combined_text
        ):
            if getattr(search_request, "driver_tracking_ok", True):
                self.match_reasons.append(
                    "Tracking is accepted by driver profile."
                )
            else:
                self.is_blocked = True
                self.block_reasons.append(
                    "Tracking required, but driver profile says tracking is not accepted."
                )

        # Direction / target logic
        if self.matches_target_city_radius(search_request):
            self.target_relation = "MATCH"
            self.match_reasons.append("Destination matches target city.")

        elif self.delivery_matches_target(search_request):
            self.target_relation = "MATCH"
            self.match_reasons.append("Destination matches target state/region.")

        else:
            reason = self.off_target_review_reason(search_request)

            if self.should_block_off_target(search_request):
                self.target_relation = "MISMATCH"
                self.is_blocked = True
                self.block_reasons.append(
                    f"Delivery does not match target direction: {getattr(search_request, 'target_direction', '')}."
                )

            else:
                if self.delivery_is_along_route(search_request):
                    self.target_relation = "ALONG_ROUTE"
                else:
                    self.target_relation = "OFF_TARGET_EXCEPTION"

                self.is_review_once = True

                if reason:
                    self.review_reasons.append(reason)

        # Conestoga logic
        no_conestoga_terms = [
            "no conestoga",
            "no conestogas",
            "no stoga",
            "no stogas",
            "conestoga wouldn't work",
            "conestoga wont work",
            "conestoga will not work",
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

        if self.pickup_region_conflict_with_driver(search_request):
            self.is_blocked = True
            self.block_reasons.append(
                "Pickup appears too far from driver location."
            )

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

        if self.opportunity_score() >= 85:
            return "CALL NOW + EMAIL BACKUP"

        if self.opportunity_score() >= 75:
            return "CALL IF AVAILABLE"

        return "MONITOR"
    def reject_reasons(self):
        """
        Backward compatibility for telegram_notifier health check.
        Returns reasons why load was blocked/rejected.
        """
        if hasattr(self, "block_reasons") and self.block_reasons:
            return self.block_reasons

        return []

    def distance_between_known_cities(self, city_a, city_b):
        """
        Temporary city distance helper for reload-chain logic.

        MVP logic:
        - If cities are the same, return 0.
        - If we know the pair manually, return approximate miles.
        - If unknown, return 9999 so reload chain will not treat it as close.
        Later this should be replaced with Google Maps / geocoding.
        """

        city_a = str(city_a or "").strip().lower()
        city_b = str(city_b or "").strip().lower()

        if not city_a or not city_b:
            return 9999

        if city_a == city_b:
            return 0

        known_distances = {
            ("englewood, co", "denver, co"): 15,
            ("denver, co", "englewood, co"): 15,

            ("atlanta, ga", "marietta, ga"): 25,
            ("marietta, ga", "atlanta, ga"): 25,

            ("atlanta, ga", "fairburn, ga"): 20,
            ("fairburn, ga", "atlanta, ga"): 20,

            ("chicago, il", "dekalb, il"): 65,
            ("dekalb, il", "chicago, il"): 65,

            ("tampa, fl", "lakeland, fl"): 35,
            ("lakeland, fl", "tampa, fl"): 35,

            ("orlando, fl", "davenport, fl"): 35,
            ("davenport, fl", "orlando, fl"): 35,

            ("orlando, fl", "sanford, fl"): 25,
            ("sanford, fl", "orlando, fl"): 25,

            ("ocala, fl", "groveland, fl"): 55,
            ("groveland, fl", "ocala, fl"): 55,

            ("ocala, fl", "gainesville, fl"): 40,
            ("gainesville, fl", "ocala, fl"): 40,

            ("salt lake city, ut", "ogden, ut"): 40,
            ("ogden, ut", "salt lake city, ut"): 40,

            ("stockton, ca", "sacramento, ca"): 50,
            ("sacramento, ca", "stockton, ca"): 50,

            ("oakland, ca", "san leandro, ca"): 10,
            ("san leandro, ca", "oakland, ca"): 10,

            ("oakland, ca", "stockton, ca"): 75,
            ("stockton, ca", "oakland, ca"): 75,
        }

        return known_distances.get((city_a, city_b), 9999)

    def opportunity_reason(self):
        """
        Backward compatibility for telegram_notifier.
        Explains why this load is considered an opportunity.
        """

        reasons = []

        if self.rate >= 5000:
            reasons.append("Strong gross")
        elif self.rate >= 3000:
            reasons.append("Good gross")

        if self.total_rpm >= 4:
            reasons.append("Excellent RPM")
        elif self.total_rpm >= 3:
            reasons.append("Good RPM")

        if self.empty_miles <= 50:
            reasons.append("Low empty miles")
        elif self.empty_miles <= 150:
            reasons.append("Acceptable empty miles")

        if self.driver_match_status == "MATCH":
            reasons.append("Matches driver target")
        elif self.driver_match_status == "REVIEW_ONCE":
            reasons.append("Needs dispatcher review")

        if self.delivery_zone and "GOOD" in str(self.delivery_zone).upper():
            reasons.append("Good reload area")

        if not reasons:
            reasons.append("Potential opportunity based on current filters")

        return ", ".join(reasons)

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