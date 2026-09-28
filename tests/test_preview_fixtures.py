import json
import os
import tempfile
import unittest

from scripts.preview_fixtures import build_fixtures, main as build_main
from src.narrative import contains_forbidden
from src.view_model import SITE_FIELDS
from tests.test_view_model import build, make_item, site_cfg

ALL_FIXTURE_NAMES = {"rain", "failed", "partial", "night", "escape", "noforecast", "onset", "radarold", "noradar"}


class PreviewFixtureTests(unittest.TestCase):
    def test_variants(self):
        base = build([make_item(site=site_cfg(f"현장{k}", lat=36 + k * 0.1, lon=127 + k * 0.1)) for k in range(7)])
        fixtures = build_fixtures(base)
        self.assertEqual(ALL_FIXTURE_NAMES, set(fixtures))
        for name, latest in fixtures.items():
            with self.subTest(name=name):
                self.assertEqual(1, latest["schema"])
                self.assertTrue(all(set(s) == set(SITE_FIELDS) for s in latest["sites"]))
                self.assertEqual([], contains_forbidden(json.dumps(latest, ensure_ascii=False)))
                image = (latest["radar"] or {}).get("image") if latest["radar"] else None
                self.assertTrue(image is None or image.startswith("radar.png?v="))
        rain = fixtures["rain"]
        self.assertTrue(rain["sites"][0]["pinned"])
        self.assertEqual((1, 1), (rain["national"]["warnings"], rain["national"]["legal"]))
        self.assertEqual(["stale"] * 7, [s["state"] for s in fixtures["failed"]["sites"]])
        self.assertEqual("failed", fixtures["failed"]["status"]["current"])
        self.assertIn("missing", [s["state"] for s in fixtures["partial"]["sites"]])
        self.assertEqual("failed", fixtures["night"]["status"]["warnings"])
        self.assertIn("<b>", fixtures["escape"]["sites"][0]["name"])
        noforecast = fixtures["noforecast"]
        self.assertEqual(([], "partial"), (noforecast["sites"][2]["hourly"], noforecast["status"]["forecast"]))
        self.assertIn("예보 자료가 없습니다", noforecast["sites"][2]["summary"])
        onset = fixtures["onset"]
        self.assertEqual(("rain", 0.0), (onset["sites"][0]["now"]["precip"], onset["sites"][0]["now"]["rain_mm"]))
        self.assertEqual(2, onset["national"]["rain_sites"])

    def _base(self):
        return build([make_item(site=site_cfg(f"현장{k}", lat=36 + k * 0.1, lon=127 + k * 0.1)) for k in range(7)])

    def test_radar_ok_status_for_ordinary_fixtures(self):
        fixtures = build_fixtures(self._base())
        for name, latest in fixtures.items():
            if name in ("radarold", "noradar"):
                continue
            with self.subTest(name=name):
                self.assertEqual("ok", latest["status"]["radar"])
                self.assertIsNotNone(latest["radar"])

    def test_radarold_is_old_but_present(self):
        fixtures = build_fixtures(self._base())
        radarold = fixtures["radarold"]
        self.assertEqual("failed", radarold["status"]["radar"])
        self.assertIsNotNone(radarold["radar"])

    def test_noradar_has_no_image(self):
        fixtures = build_fixtures(self._base())
        noradar = fixtures["noradar"]
        self.assertEqual("failed", noradar["status"]["radar"])
        self.assertIsNone(noradar["radar"])

    def test_main_writes_radar_png_to_output_folder(self):
        with tempfile.TemporaryDirectory() as d:
            build_main(d)
            self.assertTrue(os.path.exists(os.path.join(d, "radar.png")))


if __name__ == "__main__":
    unittest.main()
