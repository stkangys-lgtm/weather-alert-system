import unittest

from src.legal_rules import (
    STATUS_ACTION,
    STATUS_DATA_GAP,
    STATUS_STOP,
    STATUS_VERIFY,
    WORK_EXCAVATION,
    WORK_OUTDOOR_HEAT,
    WORK_STEEL,
    WORK_TOWER_OPERATION,
    evaluate_legal_signals,
)


class LegalRulesTests(unittest.TestCase):
    def test_missing_site_profile_is_visible_but_not_guessed(self):
        signals = evaluate_legal_signals({}, {"WSD": "12", "RN1": "5"})
        self.assertEqual(STATUS_DATA_GAP, signals[0]["status"])
        self.assertIn("프로필", signals[0]["title"])

    def test_steel_work_stops_at_statutory_rain_threshold(self):
        site = {
            "work_types": [WORK_STEEL],
            "active_work_types": [WORK_STEEL],
            "active_work_types_configured": True,
        }
        signals = evaluate_legal_signals(site, {"WSD": "2", "RN1": "1", "SNO": "0"})
        self.assertEqual(STATUS_STOP, signals[0]["status"])
        self.assertEqual("제383조", signals[0]["article"])

    def test_available_but_unconfirmed_steel_work_requires_verification(self):
        site = {"work_types": [WORK_STEEL]}
        signals = evaluate_legal_signals(site, {"WSD": "10", "RN1": "0", "SNO": "0"})
        self.assertEqual(STATUS_VERIFY, signals[0]["status"])

    def test_explicitly_no_active_work_has_no_legal_signal(self):
        site = {
            "work_types": [WORK_STEEL],
            "active_work_types": [],
            "active_work_types_configured": True,
        }
        self.assertEqual([], evaluate_legal_signals(site, {"RN1": "10", "SNO": "0"}))

    def test_tower_crane_does_not_use_average_wind_as_gust(self):
        site = {
            "work_types": [WORK_TOWER_OPERATION],
            "active_work_types": [WORK_TOWER_OPERATION],
            "active_work_types_configured": True,
        }
        signals = evaluate_legal_signals(site, {"WSD": "20"})
        self.assertEqual(STATUS_DATA_GAP, signals[0]["status"])
        self.assertIn("순간풍속", signals[0]["reason"])

    def test_tower_crane_stops_with_onsite_gust(self):
        site = {
            "work_types": [WORK_TOWER_OPERATION],
            "active_work_types": [WORK_TOWER_OPERATION],
            "active_work_types_configured": True,
            "site_measurements": {"gust_wind_speed": 15.1},
        }
        signals = evaluate_legal_signals(site, {"WSD": "8"})
        self.assertEqual(STATUS_STOP, signals[0]["status"])

    def test_heat_requires_onsite_measurement(self):
        site = {"work_types": [WORK_OUTDOOR_HEAT]}
        signals = evaluate_legal_signals(site, {"T1H": "36", "REH": "80"})
        self.assertEqual(STATUS_DATA_GAP, signals[0]["status"])

    def test_heat_33_requires_twenty_minutes_within_two_hours(self):
        site = {
            "work_types": [WORK_OUTDOOR_HEAT],
            "active_work_types": [WORK_OUTDOOR_HEAT],
            "active_work_types_configured": True,
            "site_measurements": {"apparent_temperature": 33},
        }
        signals = evaluate_legal_signals(site, {})
        self.assertEqual(STATUS_ACTION, signals[0]["status"])
        self.assertTrue(any("매 2시간 이내 20분 이상" in action for action in signals[0]["actions"]))

    def test_excavation_precipitation_requests_action(self):
        site = {"work_types": [WORK_EXCAVATION]}
        signals = evaluate_legal_signals(site, {"RN1": "0.5"})
        self.assertEqual(STATUS_ACTION, signals[0]["status"])


if __name__ == "__main__":
    unittest.main()
