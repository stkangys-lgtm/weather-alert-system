import unittest

from src.alert_rules import (
    _situational_closing,
    _situational_title,
    apply_official_warnings,
    build_announcement,
    judge,
)


class AlertRulesTests(unittest.TestCase):
    def test_grid_value_is_labeled_as_system_early_warning(self):
        result = judge({"WSD": "12", "RN1": "0", "T1H": "20", "REH": "50"})
        self.assertEqual("주의", result["level"])
        self.assertIn("시스템 선제알림", result["reasons"][0])
        self.assertNotIn("기상청 공식 특보", result["reasons"][0])

    def test_official_warning_is_distinguished_and_elevates_level(self):
        base = {"level": "정상", "reasons": [], "categories": []}
        warning = {
            "warning_type": "호우", "warning_level": "경보", "level_code": "3",
            "region_name": "부산광역시",
        }
        result = apply_official_warnings(base, [warning])
        self.assertEqual("경보", result["level"])
        self.assertEqual(["호우"], result["categories"])
        self.assertIn("기상청 공식 특보: 호우경보", result["reasons"][0])


class SituationalHeadingsTests(unittest.TestCase):
    def test_empty_categories_use_default_heading_and_no_closing(self):
        self.assertEqual("안전관리 유의사항", _situational_title([]))
        self.assertIsNone(_situational_closing([]))

    def test_single_category_heading(self):
        self.assertEqual("온열질환 안전관리 사항", _situational_title(["폭염"]))
        self.assertEqual("수방 안전관리 사항", _situational_title(["호우"]))
        self.assertEqual("강풍 대비 안전관리 사항", _situational_title(["강풍"]))

    def test_combined_categories_are_joined_with_kwa(self):
        # 카테고리 순서(강풍→호우→폭염)를 따라 결합한다.
        title = _situational_title(["폭염", "호우"])
        self.assertEqual("수방 및 온열질환 안전관리 사항", title)

    def test_closing_matches_active_hazards(self):
        closing = _situational_closing(["폭염"])
        self.assertIn("온열질환 예방조치", closing)
        self.assertIn("이행될 수 있도록 관리", closing)

    def test_normal_state_announcement_keeps_default_heading(self):
        site_results = [{
            "site_name": "A현장",
            "level": "정상",
            "reasons": [],
            "categories": [],
        }]
        text = build_announcement("2026-09-20 13:00", site_results)
        self.assertNotIn("온열질환 안전관리 사항", text)
        # 마무리 문단은 활성 위험이 있을 때만 추가된다.
        self.assertNotIn("실제 이행될 수 있도록", text)

    def test_affected_announcement_uses_situational_heading_and_closing(self):
        site_results = [{
            "site_name": "A현장",
            "level": "주의",
            "reasons": ["시스템 선제알림(주의) · 인근 격자 체감 33.5°C"],
            "categories": ["폭염"],
        }]
        text = build_announcement("2026-09-20 13:00", site_results)
        self.assertIn("【온열질환 안전관리 사항】", text)
        self.assertIn("온열질환 예방조치가 실제 이행될 수 있도록", text)

    def test_multiple_hazards_show_combined_heading(self):
        site_results = [
            {
                "site_name": "A현장",
                "level": "주의",
                "reasons": ["시스템 선제알림(주의) · 인근 격자 체감 33.5°C"],
                "categories": ["폭염"],
            },
            {
                "site_name": "B현장",
                "level": "경보",
                "reasons": ["시스템 선제알림(경계) · 시간당 강우 20mm"],
                "categories": ["호우"],
            },
        ]
        text = build_announcement("2026-09-20 13:00", site_results)
        self.assertIn("【수방 및 온열질환 안전관리 사항】", text)


if __name__ == "__main__":
    unittest.main()
