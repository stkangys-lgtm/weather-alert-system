import unittest

from src.forecast_analyzer import analyze_short_term


class ForecastAnalyzerTests(unittest.TestCase):
    def test_heat_event_uses_estimated_feels_like_and_nonofficial_wording(self):
        events = analyze_short_term([{
            "fcst_date": "20260916", "fcst_time": "1500", "TMP": "32",
            "REH": "80", "WSD": "2", "POP": "10", "PTY": "없음",
        }])
        heat = next(event for event in events if event["kind"].startswith("고온"))
        self.assertIn("예상", heat["kind"])
        self.assertIn("추정 체감", heat["detail"])
        self.assertNotIn("폭염특보", heat["kind"] + heat["detail"])


if __name__ == "__main__":
    unittest.main()
