import json
import unittest

from scripts.preview_fixtures import build_fixtures
from src.narrative import contains_forbidden
from src.view_model import SITE_FIELDS
from tests.test_view_model import build, make_item, site_cfg


class PreviewFixtureTests(unittest.TestCase):
    def test_variants(self):
        base = build([make_item(site=site_cfg(f"현장{k}", lat=36 + k * 0.1, lon=127 + k * 0.1)) for k in range(7)])
        fixtures = build_fixtures(base)
        self.assertEqual({"rain", "failed", "partial", "night", "escape"}, set(fixtures))
        for name, latest in fixtures.items():
            with self.subTest(name=name):
                self.assertEqual(1, latest["schema"])
                self.assertTrue(all(set(s) == set(SITE_FIELDS) for s in latest["sites"]))
                self.assertEqual([], contains_forbidden(json.dumps(latest, ensure_ascii=False)))
        rain = fixtures["rain"]
        self.assertTrue(rain["sites"][0]["pinned"])
        self.assertEqual((1, 1), (rain["national"]["warnings"], rain["national"]["legal"]))
        self.assertEqual(["stale"] * 7, [s["state"] for s in fixtures["failed"]["sites"]])
        self.assertEqual("failed", fixtures["failed"]["status"]["current"])
        self.assertIn("missing", [s["state"] for s in fixtures["partial"]["sites"]])
        self.assertEqual("failed", fixtures["night"]["status"]["warnings"])
        self.assertIn("<b>", fixtures["escape"]["sites"][0]["name"])


if __name__ == "__main__":
    unittest.main()
