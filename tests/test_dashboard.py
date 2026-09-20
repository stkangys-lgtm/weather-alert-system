import unittest

from src.dashboard import build_dashboard_html


class DashboardTests(unittest.TestCase):
    def test_freshness_and_recent_change_are_rendered(self):
        rows = [{
            "site_name": "테스트 현장",
            "category": "건축",
            "current": {"T1H": "25", "REH": "60", "WSD": "2", "RN1": "0", "PTY": "없음"},
            "forecast": [],
            "mid_forecast": [],
            "events": [],
            "level": "정상",
            "reasons": [],
            "legal_signals": [{
                "status": "법정 조치 이행 필요",
                "title": "굴착부 강우·강설 점검",
                "article": "제338조~제340조",
                "reason": "강수로 현장 점검이 필요합니다.",
            }],
            "display_level": "주의",
            "weather_warnings": [{
                "kind": "기상특보", "title": "호우주의보",
                "matched_areas": ["서울"],
            }],
        }]
        changes = [{
            "site_name": "테스트 현장",
            "type": "위험 해제",
            "to_level": "정상",
        }]
        html = build_dashboard_html(
            "2026-09-15 10:47",
            rows,
            generated_at_iso="2026-09-15T10:47:00+09:00",
            recent_changes=changes,
            last_change_at="2026-09-15T10:47:00+09:00",
        )
        self.assertIn('data-generated-at="2026-09-15T10:47:00+09:00"', html)
        self.assertIn('data-missing-sites="0"', html)
        self.assertIn("최근 기상변화", html)
        self.assertIn("수집 장애 가능", html)
        self.assertIn("테스트 현장", html)
        self.assertIn("법정 조치 이행 필요", html)
        self.assertIn("제338조~제340조", html)
        self.assertIn("기상청 공식 발표", html)
        self.assertIn("호우주의보", html)


if __name__ == "__main__":
    unittest.main()
