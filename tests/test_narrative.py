import unittest

from src.narrative import contains_forbidden, national_summary, site_notice, site_summary


def hour(at, mm=0.0, label="0", pop=30):
    return {"at": at, "temp": 20, "rain_mm": mm, "rain_label": label, "wind": 1.0, "pop": pop,
            "sky": "흐림", "pty": "없음", "humidity": 85}


HUPO_HOURLY = ([hour("2026-09-25T18:00:00+09:00"), hour("2026-09-25T19:00:00+09:00")]
               + [hour(f"2026-09-25T{h}:00:00+09:00", 0.5, "<1", 60) for h in (20, 21, 22, 23)]
               + [hour(f"2026-09-26T0{h}:00:00+09:00", 0.5, "<1", 60) for h in (0, 1)]
               + [hour("2026-09-26T02:00:00+09:00")])
LATER_RAIN = [hour("2026-09-25T18:00:00+09:00"), hour("2026-09-25T19:00:00+09:00"),
              hour("2026-09-25T20:00:00+09:00"), hour("2026-09-25T21:00:00+09:00", 2.0, "2", 60)]


def make_view(rain=0.0, wind=1.0, state="ok", as_of="2026-09-25T17:00:00+09:00", hourly=None,
              warnings=None, name="후포 공공하수처리", short="후포"):
    now = None if state == "missing" else {"temp": 18.6, "feels": 18.6, "rain_mm": rain, "wind": wind, "humidity": 95}
    return {"id": "5355accc", "name": name, "short": short, "state": state,
            "as_of": None if state == "missing" else as_of, "now": now,
            "hourly": hourly or [], "daily": [], "warnings": warnings or [], "legal": [], "legal_profile": False}


class SiteSummaryTests(unittest.TestCase):
    def test_observed_rain_with_forecast_side_by_side(self):
        self.assertEqual("지금 시간당 31mm(관측)의 매우 강한 비. 예보는 20시~내일 1시 1mm 미만.",
                         site_summary(make_view(rain=31, hourly=HUPO_HOURLY)))

    def test_no_rain_but_rain_later(self):
        self.assertEqual("지금은 비가 없습니다. 예보상 21시부터 비(강수확률 60%).",
                         site_summary(make_view(hourly=LATER_RAIN)))

    def test_no_rain_no_forecast(self):
        self.assertEqual("지금은 비가 없습니다. 24시간 안에 비 예보가 없습니다.", site_summary(make_view()))

    def test_stale_uses_observation_hour(self):
        text = site_summary(make_view(rain=5.6, state="stale", as_of="2026-09-25T15:00:00+09:00"))
        self.assertTrue(text.startswith("15시 관측 기준 시간당 5.6mm(관측)의 비."))

    def test_missing(self):
        self.assertEqual("관측 자료를 받지 못했습니다.", site_summary(make_view(state="missing")))

    def test_wind_term_only_from_four_meters(self):
        self.assertIn("바람 9.5m/s(강한 바람).", site_summary(make_view(wind=9.5)))
        self.assertNotIn("바람", site_summary(make_view(wind=3.9)))

    def test_forecast_amount_unit_placement(self):
        heavy = [hour("2026-09-25T18:00:00+09:00", 50.0, "50 이상", 90)]
        self.assertIn("예보는 18시 최대 50mm 이상.", site_summary(make_view(rain=31, hourly=heavy)))
        ranged = [hour("2026-09-25T18:00:00+09:00", 30.0, "30~50", 90)]
        self.assertIn("예보는 18시 최대 30~50mm.", site_summary(make_view(rain=31, hourly=ranged)))
        national = national_summary([make_view(rain=31, hourly=heavy)], True)
        self.assertIn("예보는 50mm 이상.", national)

    def test_official_warning_first(self):
        warning = [{"kind": "기상특보", "title": "호우주의보", "level": "주의보"}]
        self.assertTrue(site_summary(make_view(rain=31, warnings=warning)).startswith("기상청 호우주의보 발효 중."))


PRE_WIND = {"kind": "예비특보", "title": "강풍 예비특보", "level": "예비특보"}
PRE_TIMED = {"kind": "예비특보", "title": "09월 27일 새벽(00시~06시)", "level": "예비특보"}


class PreliminaryWarningTests(unittest.TestCase):
    def test_summary_says_announced_not_in_effect(self):
        text = site_summary(make_view(warnings=[PRE_WIND]))
        self.assertTrue(text.startswith("기상청 강풍 예비특보 발표."), text)
        self.assertNotIn("발효", text)
        self.assertTrue(site_summary(make_view(warnings=[PRE_TIMED])).startswith(
            "기상청 예비특보(09월 27일 새벽(00시~06시)) 발표."))

    def test_official_and_preliminary_together(self):
        official = {"kind": "기상특보", "title": "호우주의보", "level": "주의보"}
        self.assertTrue(site_summary(make_view(warnings=[official, PRE_WIND])).startswith(
            "기상청 호우주의보 발효 중. 기상청 강풍 예비특보 발표."))

    def test_notice_says_announced(self):
        text = site_notice(make_view(warnings=[PRE_WIND]))
        self.assertIn("기상청 강풍 예비특보가 발표되었습니다.", text)
        self.assertNotIn("발효", text)

    def test_national_counts_only_official_warnings_as_in_effect(self):
        text = national_summary([make_view(warnings=[PRE_WIND])], True)
        self.assertIn("기상청 특보는 없습니다. 예비특보는 1개 현장에 발표되어 있습니다.", text)


class NationalSummaryTests(unittest.TestCase):
    def sites(self):
        return [make_view(rain=31, hourly=HUPO_HOURLY),
                make_view(rain=10, name="연희·연남동 공공주택", short="연희·연남"),
                make_view(rain=0, name="오리온수협 목포 김공장", short="목포 김공장")]

    def test_top_site_and_count(self):
        self.assertEqual("후포에 지금 시간당 31mm(관측)의 매우 강한 비, 예보는 1mm 미만. 그 밖에 1곳에 비. 기상청 특보는 없습니다.",
                         national_summary(self.sites(), True))

    def test_warning_failure_and_stale_are_reported(self):
        sites = self.sites()
        sites[2]["state"] = "stale"
        text = national_summary(sites, False)
        self.assertIn("기상청 특보는 확인하지 못했습니다.", text)
        self.assertIn("1개 현장은 이번 수집에 실패했습니다.", text)

    def test_all_missing(self):
        self.assertEqual("관측 자료를 받지 못했습니다.", national_summary([make_view(state="missing")], True))


class NoticeTests(unittest.TestCase):
    def test_rain_notice_in_house_style(self):
        text = site_notice(make_view(rain=31, hourly=HUPO_HOURLY))
        self.assertTrue(text.startswith("■ 공지드립니다."))
        self.assertIn("2026-09-25 17:00 관측 기준, 후포 공공하수처리 현장에 시간당 31mm의 매우 강한 비가 관측되고 있습니다.", text)
        self.assertIn("(기상청 예보: 20시~내일 1시 1mm 미만)", text)
        self.assertIn("【수방 안전관리 사항】", text)
        self.assertIn("ㅇ 배수로 및 침사지 주변 이물질 정비", text)
        self.assertIn("각 현장에서는 수방 조치가 실제 이행될 수 있도록 관리하여 주시기 바랍니다.", text)
        self.assertTrue(text.endswith("감사합니다."))

    def test_dry_notice_mentions_later_rain_without_actions(self):
        text = site_notice(make_view(hourly=LATER_RAIN))
        self.assertIn("현장에는 비가 관측되지 않았습니다.", text)
        self.assertIn("다만 예보상 21시부터 비(강수확률 60%)가 있으니 작업 계획에 참고하여 주시기 바랍니다.", text)
        self.assertNotIn("【", text)

    def test_wind_warning_adds_wind_actions(self):
        warning = [{"kind": "기상특보", "title": "강풍주의보", "level": "주의보"}]
        text = site_notice(make_view(wind=12, warnings=warning))
        self.assertIn("기상청 강풍주의보가 발효 중입니다.", text)
        self.assertIn("【강풍 대비 안전관리 사항】", text)

    def test_missing_notice(self):
        self.assertIn("관측 자료를 받지 못했습니다", site_notice(make_view(state="missing")))


class ForbiddenWordTests(unittest.TestCase):
    def test_detects_forbidden(self):
        self.assertEqual(["선제", "기준 도달"], contains_forbidden("사내 선제감시 기준 도달"))

    def test_all_outputs_are_clean(self):
        views = [make_view(rain=31, hourly=HUPO_HOURLY), make_view(hourly=LATER_RAIN), make_view(wind=15),
                 make_view(state="stale", rain=2, as_of="2026-09-25T15:00:00+09:00"), make_view(state="missing")]
        for view in views:
            for text in (site_summary(view), site_notice(view)):
                self.assertEqual([], contains_forbidden(text), text)
        self.assertEqual([], contains_forbidden(national_summary(views, True)))


if __name__ == "__main__":
    unittest.main()
