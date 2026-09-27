import json
import os
import struct
import unittest

from src.publish import WEB_DIR


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


def read(name):
    with open(os.path.join(WEB_DIR, name), encoding="utf-8") as f:
        return f.read()


class AppManifestTests(unittest.TestCase):
    def test_hq_manifest(self):
        data = json.loads(read("manifest.webmanifest"))
        self.assertEqual(("현대아산 기상안전", "./", "#2b4775", "standalone"),
                         (data["name"], data["start_url"], data["theme_color"], data["display"]))
        sizes = {icon["sizes"]: icon["src"] for icon in data["icons"]}
        self.assertEqual({"192x192", "512x512"}, set(sizes))
        for size, src in sizes.items():
            width = int(size.split("x")[0])
            self.assertEqual((width, width), png_size(os.path.join(WEB_DIR, src)))

    def test_apple_touch_icon(self):
        self.assertEqual((180, 180), png_size(os.path.join(WEB_DIR, "assets", "icons", "apple-touch-icon.png")))

    def test_hq_page_links_manifest_and_icon(self):
        html = read("index.html")
        self.assertIn('<link rel="manifest" href="manifest.webmanifest">', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)

    def test_site_page_uses_its_own_manifest(self):
        html = read("site.html")
        self.assertIn('<link rel="manifest" id="manifest" href="manifest.webmanifest">', html)
        self.assertIn("/^[A-Za-z0-9_-]{1,64}$/.test(id)", html)
        self.assertIn('"manifests/" + id + ".webmanifest"', html)
        self.assertIn('<link rel="apple-touch-icon" href="assets/icons/apple-touch-icon.png">', html)

if __name__ == "__main__":
    unittest.main()
