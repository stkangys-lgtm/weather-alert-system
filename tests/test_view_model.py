import unittest
from datetime import date, datetime, timedelta

from src.view_model import KST, daily_series, hourly_series, now_values, observed_at, parse_pcp


def fc_rows(start, hours, pcp_for=lambda at: "강수없음", **defaults):
    rows = []
    for k in range(hours):
        at = start + timedelta(hours=k)
        row = {"fcst_date": at.strftime("%Y%m%d"), "fcst_time": at.strftime("%H%M"), "TMP": "20",
               "PCP": pcp_for(at), "POP": "30", "WSD": "1.0", "SKY": "흐림", "PTY": "없음", "REH": "85"}
        row.update(defaults)
        rows.append(row)
    return rows


class ParsePcpTests(unittest.TestCase):
    def test_labels(self):
        cases = [("강수없음", (0.0, "0")), ("1mm 미만", (0.5, "<1")), ("2.0mm", (2.0, "2")),
                 ("6.5mm", (6.5, "6.5")), ("30.0~50.0mm", (30.0, "30~50")), ("50.0mm 이상", (50.0, "50 이상")),
                 ("", (None, "-")), (None, (None, "-")), ("-", (None, "-")), ("알수없음", (None, "-"))]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(expected, parse_pcp(value))


class NowValuesTests(unittest.TestCase):
    CURRENT = {"base_date": "20260925", "base_time": "1700", "T1H": "18.6", "RN1": "31", "WSD": "4.1", "REH": "95"}

    def test_now_values(self):
        self.assertEqual({"temp": 18.6, "feels": 18.6, "rain_mm": 31.0, "wind": 4.1, "humidity": 95},
                         now_values(self.CURRENT))

    def test_missing_current(self):
        self.assertIsNone(now_values(None))
        self.assertIsNone(observed_at(None))

    def test_observed_at_is_hourly_observation_time(self):
        self.assertEqual(datetime(2026, 9, 25, 17, 0, tzinfo=KST), observed_at(self.CURRENT))


class SeriesTests(unittest.TestCase):
    def test_hourly_starts_after_observation_and_caps_at_24(self):
        wet = lambda at: "1mm 미만" if at.hour >= 20 or at.hour <= 1 else "강수없음"
        rows = fc_rows(datetime(2026, 9, 25, 15, 0), 40, pcp_for=wet)
        series = hourly_series(rows, datetime(2026, 9, 25, 17, 0, tzinfo=KST))
        self.assertEqual(24, len(series))
        self.assertEqual("2026-09-25T18:00:00+09:00", series[0]["at"])
        self.assertEqual((0.0, "0"), (series[0]["rain_mm"], series[0]["rain_label"]))
        self.assertEqual((0.5, "<1"), (series[2]["rain_mm"], series[2]["rain_label"]))
        self.assertEqual({"at", "temp", "rain_mm", "rain_label", "wind", "pop", "sky", "pty", "humidity"},
                         set(series[0]))

    def test_daily_uses_short_then_mid_and_marks_gaps(self):
        day1 = fc_rows(datetime(2026, 9, 26, 0, 0), 24)
        day1[6]["TMN"] = "17.0"
        day1[15]["TMX"] = "24.0"
        day1[10]["PTY"] = "비"
        day1[10]["POP"] = "60"
        day2 = fc_rows(datetime(2026, 9, 27, 0, 0), 24, SKY="맑음")
        for k, row in enumerate(day2):
            row["TMP"] = str(15 + k % 10)
        partial = fc_rows(datetime(2026, 9, 28, 0, 0), 3)
        mid = [
            {"date": "2026-09-29", "sky_am": "맑음", "sky_pm": "구름많음", "pop_am": 10, "pop_pm": 20, "ta_min": 17, "ta_max": 23},
            {"date": "2026-09-30", "sky_am": None, "sky_pm": None, "pop_am": None, "pop_pm": None, "ta_min": None, "ta_max": None},
        ]
        days = daily_series(day1 + day2 + partial, mid, date(2026, 9, 25))
        self.assertEqual(10, len(days))
        self.assertEqual(("2026-09-26", "2026-10-05"), (days[0]["date"], days[-1]["date"]))
        self.assertEqual({"date": "2026-09-26", "sky": "비", "pop": 60, "tmin": 17.0, "tmax": 24.0,
                          "source": "short", "missing": False}, days[0])
        self.assertEqual(("맑음", 15.0, 24.0, "short"), (days[1]["sky"], days[1]["tmin"], days[1]["tmax"], days[1]["source"]))
        self.assertTrue(days[2]["missing"])
        self.assertEqual(("구름많음", 20, 17.0, 23.0, "mid"),
                         (days[3]["sky"], days[3]["pop"], days[3]["tmin"], days[3]["tmax"], days[3]["source"]))
        self.assertTrue(days[4]["missing"])


if __name__ == "__main__":
    unittest.main()
