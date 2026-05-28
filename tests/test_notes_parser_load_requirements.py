import unittest

from app.market_intelligence.notes_parser_load_requirements import (
    detect_appointment_required,
    detect_forklift_required,
    detect_ramps_required,
    detect_straight_through,
    detect_tracking_required,
)


class TestNotesParserLoadRequirements(unittest.TestCase):
    def test_detect_forklift_required(self):
        self.assertTrue(detect_forklift_required("forklift required"))
        self.assertTrue(detect_forklift_required("moffett needed"))
        self.assertTrue(detect_forklift_required("driver unload"))
        self.assertFalse(detect_forklift_required("normal flatbed load"))

    def test_detect_ramps_required(self):
        self.assertTrue(detect_ramps_required("need ramps"))
        self.assertTrue(detect_ramps_required("ramps required"))
        self.assertTrue(detect_ramps_required("ramp needed"))
        self.assertFalse(detect_ramps_required("legal load"))

    def test_detect_tracking_required(self):
        self.assertTrue(detect_tracking_required("tracking required"))
        self.assertTrue(detect_tracking_required("macropoint"))
        self.assertTrue(detect_tracking_required("macro point"))
        self.assertTrue(detect_tracking_required("trucker tools"))
        self.assertFalse(detect_tracking_required("no tracking mentioned"))

    def test_detect_appointment_required(self):
        self.assertTrue(detect_appointment_required("appt only"))
        self.assertTrue(detect_appointment_required("appointment required"))
        self.assertTrue(detect_appointment_required("by appointment"))
        self.assertFalse(detect_appointment_required("fcfs"))

    def test_detect_straight_through(self):
        self.assertTrue(detect_straight_through("straight through"))
        self.assertTrue(detect_straight_through("deliver straight thru"))
        self.assertTrue(detect_straight_through("must deliver straight"))
        self.assertFalse(detect_straight_through("regular delivery"))


if __name__ == "__main__":
    unittest.main()
