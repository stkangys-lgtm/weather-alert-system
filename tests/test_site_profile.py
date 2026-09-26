import unittest

from src.site_profile import SITE_SHORT_NAMES, region_label, short_name, site_id


class SiteProfileTests(unittest.TestCase):
    def test_configured_id_wins(self):
        self.assertEqual("hupo", site_id({"site_name": "후포 공공하수처리", "id": "hupo"}))

    def test_default_id_is_stable_hash(self):
        self.assertEqual("5355accc", site_id({"site_name": "후포 공공하수처리"}))

    def test_short_name_precedence(self):
        self.assertEqual("후포", short_name({"site_name": "후포 공공하수처리"}))
        self.assertEqual("후포현장", short_name({"site_name": "후포 공공하수처리", "short_name": "후포현장"}))
        self.assertEqual("새 현장", short_name({"site_name": "새 현장"}))

    def test_short_names_are_unique(self):
        names = list(SITE_SHORT_NAMES.values())
        self.assertEqual(len(names), len(set(names)))

    def test_region_from_known_mapping(self):
        self.assertEqual("경상북도 울진군", region_label({"site_name": "후포 공공하수처리"}))
        self.assertEqual("서울특별시 서대문구", region_label({"site_name": "연희·연남동 공공주택"}))

    def test_region_from_config_and_override(self):
        site = {"site_name": "새 현장", "warning_regions": ["화성시", "화성"], "warning_provinces": ["경기도"]}
        self.assertEqual("경기도 화성시", region_label(site))
        self.assertEqual("직접 입력", region_label({"site_name": "새 현장", "region": "직접 입력"}))
        self.assertIsNone(region_label({"site_name": "새 현장"}))


if __name__ == "__main__":
    unittest.main()
