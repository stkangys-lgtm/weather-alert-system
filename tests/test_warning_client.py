import unittest

from src.warning_client import (
    match_warnings_to_sites,
    parse_warning_status,
    warning_display_level,
)


class WarningClientTests(unittest.TestCase):
    def test_status_parser_preserves_commas_inside_parentheses(self):
        warnings = parse_warning_status(
            "o 호우주의보 : 경기도(군포, 화성), 충청북도\n"
            "o 강풍경보 : 강원특별자치도",
            announced_at="202609201400",
        )
        self.assertEqual(2, len(warnings))
        self.assertEqual(["경기도(군포, 화성)", "충청북도"], warnings[0]["areas"])
        self.assertEqual("호우", warnings[0]["phenomenon"])
        self.assertEqual("경보", warnings[1]["level"])

    def test_warning_matches_local_area_but_not_other_city_in_same_province(self):
        warnings = parse_warning_status("o 호우주의보 : 경기도(군포, 화성)")
        sites = [
            {"site_name": "군포복합개발"},
            {"site_name": "시흥능곡 주변도로"},
        ]
        matched = match_warnings_to_sites(sites, warnings)
        self.assertEqual(1, len(matched["군포복합개발"]))
        self.assertEqual([], matched["시흥능곡 주변도로"])

    def test_yangsan_hospital_matches_yangsan_only(self):
        # 현장 DB 주소: 경남 양산시 물금읍
        site = [{"site_name": "양산 부산대병원"}]
        yangsan = parse_warning_status("o 호우경보 : 경상남도(양산, 김해)")
        self.assertEqual(["경상남도(양산, 김해)"], match_warnings_to_sites(site, yangsan)["양산 부산대병원"][0]["matched_areas"])
        other = parse_warning_status("o 호우경보 : 경상남도(창원, 김해)")
        self.assertEqual([], match_warnings_to_sites(site, other)["양산 부산대병원"])
        whole = parse_warning_status("o 강풍주의보 : 경상남도")
        self.assertEqual(1, len(match_warnings_to_sites(site, whole)["양산 부산대병원"]))

    def test_province_wide_warning_and_marine_filter(self):
        warnings = parse_warning_status(
            "o 강풍주의보 : 충청북도, 서해중부앞바다"
        )
        sites = [{"site_name": "오리온 진천신공장"}]
        matched = match_warnings_to_sites(sites, warnings)["오리온 진천신공장"]
        self.assertEqual(["충청북도"], matched[0]["matched_areas"])
        self.assertEqual("주의", warning_display_level(matched))


if __name__ == "__main__":
    unittest.main()
