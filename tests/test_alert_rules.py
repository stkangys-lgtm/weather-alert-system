import unittest

from src.alert_rules import apply_official_warnings, judge


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


if __name__ == "__main__":
    unittest.main()
