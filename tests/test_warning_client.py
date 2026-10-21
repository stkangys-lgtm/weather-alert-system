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

    def test_name_inside_another_zone_name_does_not_match(self):
        # 2026-10-22 실제 한파주의보: 경북 '영양산지' 글자 안의 '양산'이 양산 현장에 잘못 붙었다.
        warnings = parse_warning_status(
            "o 한파주의보 : 경상북도(청도, 영주, 영양평지, 영양산지, 울진산지), "
            "경상남도(함양중부, 거창북부, 합천남부)"
        )
        matched = match_warnings_to_sites([{"site_name": "양산 부산대병원"}, {"site_name": "풍각지구 정비사업"}], warnings)
        self.assertEqual([], matched["양산 부산대병원"])
        self.assertEqual(1, len(matched["풍각지구 정비사업"]))

    def test_subzones_of_a_county(self):
        north = parse_warning_status("o 호우주의보 : 경상북도(안동북부)")
        self.assertEqual(1, len(match_warnings_to_sites([{"site_name": "포항~안동2 국도건설공사"}], north)
                                ["포항~안동2 국도건설공사"]))
        # 후포는 울진 해안(울진평지)이라 '울진산지' 특보는 해당하지 않고, 군 전체·평지 특보는 해당한다.
        hupo = [{"site_name": "후포 공공하수처리"}]
        for text, expected in (("경상북도(울진산지)", 0), ("경상북도(울진평지)", 1), ("경상북도(울진)", 1)):
            with self.subTest(area=text):
                found = match_warnings_to_sites(hupo, parse_warning_status(f"o 한파주의보 : {text}"))
                self.assertEqual(expected, len(found["후포 공공하수처리"]))

    def test_seoul_subregion_written_inside_parentheses(self):
        site = [{"site_name": "연희·연남동 공공주택"}]
        northwest = parse_warning_status("o 폭염주의보 : 서울(서북권, 동북권)")
        self.assertEqual(1, len(match_warnings_to_sites(site, northwest)["연희·연남동 공공주택"]))
        southeast = parse_warning_status("o 폭염주의보 : 서울(동남권)")
        self.assertEqual([], match_warnings_to_sites(site, southeast)["연희·연남동 공공주택"])

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
