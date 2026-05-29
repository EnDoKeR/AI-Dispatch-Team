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
