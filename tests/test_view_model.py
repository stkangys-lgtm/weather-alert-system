import json
import os
import re
import subprocess
import tempfile
import unittest
from datetime import date, datetime, timedelta

from src.narrative import contains_forbidden
from src.view_model import (
    KST,
    SITE_FIELDS,
    build_latest,
    daily_series,
    hourly_series,
    load_latest,
    now_values,
    observed_at,
    parse_pcp,
    publish_latest,
    write_latest,
)


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


NOW = datetime(2026, 9, 25, 17, 47, tzinfo=KST)
_UNSET = object()
PROFILE_GAP = {"status": "데이터 부족", "work_type": "site_profile", "title": "현장 작업 프로필 미등록",
               "article": "판정 전제정보", "reason": "미등록", "actions": []}


def site_cfg(name="후포 공공하수처리", **extra):
    site = {"site_name": name, "category": "토목", "lat": 36.68, "lon": 129.45, "nx": 103, "ny": 109,
            "manager": "홍길동", "manager_phone": "010-1234-5678"}
    site.update(extra)
    return site


def obs(rn1="31", t1h="18.6"):
    return {"base_date": "20260925", "base_time": "1700", "T1H": t1h, "RN1": rn1, "WSD": "4.1", "REH": "95"}


def forecast_rows():
    rows = []
    start = datetime(2026, 9, 25, 18, 0)
    for k in range(78):
        at = start + timedelta(hours=k)
        wet = (at.day == 25 and at.hour >= 20) or (at.day == 26 and at.hour <= 1)
        rows.append({"fcst_date": at.strftime("%Y%m%d"), "fcst_time": at.strftime("%H%M"), "TMP": "20",
                     "PCP": "1mm 미만" if wet else "강수없음", "POP": "60" if wet else "30", "WSD": "1.0",
                     "SKY": "흐림", "PTY": "비" if wet else "없음", "REH": "85"})
    return rows


def make_item(site=None, current=_UNSET, forecast=None, warnings=None, available=True, legal=None):
    return {"site": site or site_cfg(), "current": obs() if current is _UNSET else current,
            "forecast": forecast_rows() if forecast is None else forecast,
            "judgment": {"level": "정상", "reasons": [], "categories": []},
            "legal_signals": [PROFILE_GAP] if legal is None else legal, "legal_status": None,
            "weather_warnings": warnings or [], "weather_warnings_available": available}


def build(items, previous=None, warnings_ok=True, now=NOW):
    return build_latest(items, {}, previous=previous, now=now, warnings_ok=warnings_ok,
                        forecast_issued_at=datetime(2026, 9, 25, 14, 0), mid_issued_at=datetime(2026, 9, 25, 6, 0))


class BuildLatestTests(unittest.TestCase):
    def test_top_level_fields(self):
        latest = build([make_item()])
        self.assertEqual(1, latest["schema"])
        self.assertEqual("2026-09-25T17:47:00+09:00", latest["generated_at"])
        self.assertEqual("2026-09-25T17:00:00+09:00", latest["observed_at"])
        self.assertEqual("2026-09-25T14:00:00+09:00", latest["forecast_issued_at"])
        self.assertEqual("2026-09-25T06:00:00+09:00", latest["mid_issued_at"])
        self.assertEqual({"current": "ok", "forecast": "ok", "warnings": "ok", "radar": "off"}, latest["status"])
        self.assertEqual({"window": "04:17-17:47", "next_run_at": "2026-09-26T04:17:00+09:00"}, latest["schedule"])
        self.assertIsNone(latest["radar"])

    def test_site_fields_are_allowlisted(self):
        site = build([make_item()])["sites"][0]
        self.assertEqual(set(SITE_FIELDS), set(site))
        self.assertEqual(("5355accc", "후포", "경상북도 울진군", "ok"),
                         (site["id"], site["short"], site["region"], site["state"]))

    def test_no_personal_data_or_forbidden_words(self):
        text = json.dumps(build([make_item()]), ensure_ascii=False)
        self.assertNotIn("홍길동", text)
        self.assertNotIn("010-1234-5678", text)
        self.assertNotIn("manager", text)
        self.assertIsNone(re.search(r"01[016789]-?\d{3,4}-?\d{4}", text))
        self.assertEqual([], contains_forbidden(text))

    def test_national_aggregates(self):
        national = build([make_item()])["national"]
        self.assertEqual((0, 0, 1), (national["warnings"], national["legal"], national["rain_sites"]))
        self.assertEqual({"mm": 31.0, "site": "5355accc"}, national["max_rain"])
        self.assertTrue(national["summary"].startswith("후포에 지금 시간당 31mm(관측)의 매우 강한 비, 예보는 1mm 미만."))

    def test_profile_gap_is_not_a_legal_signal(self):
        site = build([make_item()])["sites"][0]
        self.assertEqual(([], False), (site["legal"], site["legal_profile"]))

    def test_legal_signal_subset_and_count(self):
        stop = {"status": "법정 작업중지", "work_type": "steel_erection", "title": "철골작업 중지",
                "article": "제383조", "reason": "강우 1mm 이상", "actions": ["철골작업 즉시 중지"]}
        item = make_item(site=site_cfg(work_types=["steel_erection"], active_work_types=["steel_erection"]), legal=[stop])
        latest = build([item])
        self.assertEqual([{"status": "법정 작업중지", "title": "철골작업 중지", "article": "제383조"}],
                         latest["sites"][0]["legal"])
        self.assertTrue(latest["sites"][0]["legal_profile"])
        self.assertEqual(1, latest["national"]["legal"])

    def test_warning_subset(self):
        warning = {"kind": "기상특보", "title": "호우주의보", "level": "주의보", "areas": ["경상북도(울진)"],
                   "matched_areas": ["경상북도(울진)"], "announced_at": "202609251600"}
        latest = build([make_item(warnings=[warning])])
        self.assertEqual([{"kind": "기상특보", "title": "호우주의보", "level": "주의보"}], latest["sites"][0]["warnings"])
        self.assertEqual(1, latest["national"]["warnings"])
        self.assertTrue(latest["sites"][0]["summary"].startswith("기상청 호우주의보 발효 중."))

    def test_warning_failure_status(self):
        self.assertEqual("failed", build([make_item(available=False)], warnings_ok=False)["status"]["warnings"])

    def test_stale_carries_last_good_values(self):
        previous = build([make_item()])
        latest = build([make_item(current=None)], previous=previous, now=NOW + timedelta(minutes=30))
        site = latest["sites"][0]
        self.assertEqual("stale", site["state"])
        self.assertEqual(previous["sites"][0]["now"], site["now"])
        self.assertEqual("2026-09-25T17:00:00+09:00", site["as_of"])
        self.assertTrue(site["summary"].startswith("17시 관측 기준 시간당 31mm(관측)"))
        self.assertEqual("failed", latest["status"]["current"])

    def test_hourly_falls_back_to_previous_forecast(self):
        previous = build([make_item()])
        later = NOW + timedelta(hours=2)
        site = build([make_item(forecast=[])], previous=previous, now=later)["sites"][0]
        self.assertTrue(site["hourly"])
        self.assertTrue(all(datetime.fromisoformat(h["at"]) > later for h in site["hourly"]))

    def test_first_run_total_failure(self):
        latest = build([make_item(current=None, forecast=[]), make_item(site=site_cfg("연희·연남동 공공주택"), current=None, forecast=[])])
        self.assertEqual(["missing", "missing"], [s["state"] for s in latest["sites"]])
        self.assertEqual("관측 자료를 받지 못했습니다.", latest["national"]["summary"])
        self.assertEqual("failed", latest["status"]["current"])
        json.dumps(latest, ensure_ascii=False)

    def test_partial_status(self):
        latest = build([make_item(), make_item(site=site_cfg("연희·연남동 공공주택"), current=None)])
        self.assertEqual("partial", latest["status"]["current"])


class LatestFileTests(unittest.TestCase):
    def test_write_then_load(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data", "latest.json")
            data = build([make_item()])
            write_latest(path, data)
            self.assertEqual(data, load_latest(path))
            self.assertEqual([], [n for n in os.listdir(os.path.dirname(path)) if n.startswith(".latest-")])

    def test_load_rejects_missing_corrupt_or_old_schema(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(load_latest(os.path.join(d, "none.json")))
            broken = os.path.join(d, "broken.json")
            with open(broken, "w", encoding="utf-8") as f:
                f.write("{not json")
            self.assertIsNone(load_latest(broken))
            old = os.path.join(d, "old.json")
            with open(old, "w", encoding="utf-8") as f:
                json.dump({"schema": 0, "sites": []}, f)
            self.assertIsNone(load_latest(old))

    def test_publish_twice_carries_last_good_values(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "data", "latest.json")
            first = publish_latest(path, [make_item()], {}, NOW)
            second = publish_latest(path, [make_item(current=None)], {}, NOW + timedelta(minutes=30))
            self.assertEqual("stale", second["sites"][0]["state"])
            self.assertEqual(first["sites"][0]["now"], second["sites"][0]["now"])

    def test_latest_json_is_committed_by_the_workflow(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            result = subprocess.run(["git", "check-ignore", "-q", "docs/data/latest.json"], cwd=root,
                                    capture_output=True)
        except OSError:
            self.skipTest("git 없음")
        if result.returncode == 128:
            self.skipTest("git 저장소 밖")
        self.assertEqual(1, result.returncode, "docs/data/latest.json이 .gitignore에 걸려 게시되지 않습니다")


if __name__ == "__main__":
    unittest.main()
