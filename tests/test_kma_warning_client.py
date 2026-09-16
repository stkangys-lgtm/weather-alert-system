import unittest

from src.kma_warning_client import (
    get_current_warnings,
    match_warnings_to_sites,
    parse_warning_csv,
)


SAMPLE = """# CURRENT WARNINGS
REG_UP,REG_UP_KO,REG_ID,REG_KO,TM_FC,TM_EF,WRN,LVL,CMD
L1000000,서울특별시,L1010000,서울특별시,202609160900,202609161000,W,2,1
L2000000,부산광역시,L2010000,부산광역시,202609160900,202609161000,R,3,1
L3000000,대전광역시,L3010000,대전광역시,202609160800,202609160900,H,2,3
"""

TEXT_SAMPLE = """S1310000,남해동부전해상,S1312020,남해동부바깥먼바다,202609160400,202609170558,풍랑,경보,발표
S1310000,남해동부전해상,S1312021,제주도앞바다,202609160400,202609170558,풍랑,주의보,해제
"""


class WarningClientTests(unittest.TestCase):
    def test_parse_current_warnings_and_exclude_cancellations(self):
        warnings = parse_warning_csv(SAMPLE)
        self.assertEqual(2, len(warnings))
        self.assertEqual("강풍", warnings[0]["warning_type"])
        self.assertEqual("주의보", warnings[0]["warning_level"])
        self.assertEqual("경보", warnings[1]["warning_level"])

    def test_parse_text_values_returned_by_approved_endpoint(self):
        warnings = parse_warning_csv(TEXT_SAMPLE)
        self.assertEqual(1, len(warnings))
        self.assertEqual("풍랑", warnings[0]["warning_type"])
        self.assertEqual("3", warnings[0]["level_code"])
        self.assertEqual("1", warnings[0]["command_code"])

    def test_match_by_code_keyword_and_site_name_fallback(self):
        warnings = parse_warning_csv(SAMPLE)
        sites = [
            {"site_name": "코드 현장", "warning_region_codes": ["L2010000"]},
            {"site_name": "키워드 현장", "warning_region_keywords": ["서울"]},
            {"site_name": "부산 자동매칭 현장"},
        ]
        matched = match_warnings_to_sites(warnings, sites)
        self.assertEqual("호우", matched["코드 현장"][0]["warning_type"])
        self.assertEqual("강풍", matched["키워드 현장"][0]["warning_type"])
        self.assertEqual("호우", matched["부산 자동매칭 현장"][0]["warning_type"])

    def test_blank_key_skips_http_request(self):
        called = []
        self.assertEqual([], get_current_warnings("", request_get=lambda *a, **k: called.append(True)))
        self.assertEqual([], called)


if __name__ == "__main__":
    unittest.main()
