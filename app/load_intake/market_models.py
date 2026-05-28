class MarketLoad:
    def __init__(
        self,
        pickup="",
        delivery="",
        rate=0,
        loaded_miles=0,
        empty_miles=0,
        stops=2,
        weight=0,
        broker_status="BUY",
        equipment="Conestoga",
        load_type="FULL",
    ):
        self.pickup = pickup
        self.delivery = delivery
        self.rate = rate
        self.loaded_miles = loaded_miles
        self.empty_miles = empty_miles
        self.stops = stops
        self.weight = weight
        self.broker_status = broker_status
        self.equipment = equipment
        self.load_type = load_type

    @property
    def total_miles(self):
        return self.loaded_miles + self.empty_miles

    @property
    def total_rpm(self):
        if self.total_miles == 0:
            return 0

        return round(
            self.rate / self.total_miles,
            2,
        )

    @property
    def bucket(self):
        if self.loaded_miles <= 450:
            return "0-450"

        if self.loaded_miles <= 700:
            return "450-700"

        if self.loaded_miles <= 1300:
            return "700-1300"

        return "1300+"

    def is_qualified(self):
        if self.broker_status == "NO BUY":
            return False

        if self.stops > 2:
            return False

        if self.weight > 46000:
            return False

        if self.load_type != "FULL":
            return False

        if self.total_rpm < 2.0:
            return False

        return True

    def is_good(self):
        if not self.is_qualified():
            return False

        if self.rate < 2000:
            return False

        if self.total_rpm < 2.5:
            return False

        return True
