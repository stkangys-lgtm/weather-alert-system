import unittest

from src.map_dashboard import build_map_html


class MapDashboardTests(unittest.TestCase):
    def test_map_is_primary_interactive_weather_view(self):
        rows = [{
            "site_name": "테스트 건축현장",
            "category": "건축",
            "lat": 37.56,
            "lon": 126.97,
            "current": {"T1H": "31", "REH": "70", "WSD": "4.2", "RN1": "0"},
            "forecast": [{"fcst_time": "1500", "TMP": "32", "POP": "20", "SKY": "맑음", "PTY": "없음"}],
            "events": [{"date": "9/16(수)", "kind": "폭염주의", "detail": "낮 최고 33°C"}],
            "level": "주의",
            "reasons": ["고온 작업 주의"],
            "legal_signals": [{
                "status": "데이터 부족", "title": "작업장소 체감온도 실측 필요",
                "article": "제562조제2항", "reason": "공공 기상자료만으로 확정할 수 없습니다.",
            }],
            "display_level": "경보",
            "weather_warnings": [{
                "kind": "기상특보", "title": "폭염경보", "matched_areas": ["서울"],
            }],
        }]

        html = build_map_html("2026-09-15 10:47", rows)

        self.assertIn("#009a44", html)
        self.assertIn("ALL SITES OVERVIEW", html)
        self.assertIn('class="marker" tabindex="0" role="button"', html)
        self.assertIn("테스트 건축현장", html)
        self.assertIn("폭염주의", html)
        self.assertIn("sites.html", html)
        self.assertIn("시간대별 예보", html)
        self.assertIn("작업장소 체감온도 실측 필요", html)
        self.assertIn("선제주의", html)
        self.assertIn("기상청 공식 발표", html)
        self.assertIn("폭염경보", html)
        self.assertIn("기상특보 경보", html)

    def test_script_payload_escapes_closing_script(self):
        rows = [{
            "site_name": "</script><script>alert(1)</script>",
            "category": "토목", "lat": 36.3, "lon": 127.4,
            "current": {}, "forecast": [], "events": [],
            "level": "데이터없음", "reasons": [],
        }]
        html = build_map_html("now", rows)
        self.assertNotIn('"</script><script>alert(1)</script>"', html)
        self.assertIn("<\\/script>", html)


if __name__ == "__main__":
    unittest.main()
