import json
import os
import tempfile
import unittest

from src.publish import (
    DOCS_DIR,
    MAP_TARGET,
    OLD_MAP_PATH,
    OLD_SITES_PATH,
    WEB_DIR,
    PublishError,
    check_latest,
    check_web,
    external_tag_problems,
    private_values,
    publish,
)

GOOD_HEAD = ('<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>'
             '<link rel="stylesheet" href="https://cdn.example/a.css" integrity="sha384-abc" crossorigin="anonymous">'
             '<script src="https://cdn.example/a.js" integrity="sha384-def" crossorigin="anonymous"></script>')


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.web = os.path.join(self.tmp.name, "web")
        self.docs = os.path.join(self.tmp.name, "docs")
        self.map = os.path.join(self.tmp.name, "kr.json")
        write(os.path.join(self.web, "index.html"), f"<html><head>{GOOD_HEAD}</head><body>본사</body></html>")
        write(os.path.join(self.web, "assets", "app.css"), "body{color:#101820}")
        write(os.path.join(self.web, ".DS_Store"), "x")
        write(os.path.join(self.docs, "weather-state.json"), '{"keep": true}')
        write(self.map, '{"paths": {}}')

    def tearDown(self):
        self.tmp.cleanup()

    def test_copies_web_and_map_without_touching_other_docs(self):
        published = publish(self.web, self.docs, self.map)
        self.assertEqual(sorted(["index.html", os.path.join("assets", "app.css"), MAP_TARGET]), sorted(published))
        with open(os.path.join(self.docs, "weather-state.json"), encoding="utf-8") as f:
            self.assertEqual('{"keep": true}', f.read())
        self.assertTrue(os.path.exists(os.path.join(self.docs, "assets", "app.css")))
        self.assertFalse(os.path.exists(os.path.join(self.docs, ".DS_Store")))
        with open(os.path.join(self.docs, MAP_TARGET), encoding="utf-8") as f:
            self.assertEqual({"paths": {}}, json.load(f))

    def test_external_file_without_integrity_blocks_publish(self):
        write(os.path.join(self.web, "index.html"), '<script src="https://cdn.example/x.js"></script>')
        with self.assertRaises(PublishError) as ctx:
            publish(self.web, self.docs, self.map)
        self.assertIn("https://cdn.example/x.js", str(ctx.exception))
        self.assertFalse(os.path.exists(os.path.join(self.docs, "index.html")))

    def test_preconnect_and_local_files_need_no_integrity(self):
        html = ('<link rel="preconnect" href="https://cdn.jsdelivr.net"><script src="assets/common.js"></script>'
                '<link rel="stylesheet" href="assets/app.css">')
        self.assertEqual([], external_tag_problems(html))

    def test_phone_forbidden_word_and_private_value_block_publish(self):
        write(os.path.join(self.web, "assets", "app.js"), 'const a = "010-1234-5678"; // 선제 홍길동')
        problems = check_web(self.web, blocked={"홍길동"})
        self.assertEqual(3, len(problems))
        self.assertTrue(all(p.startswith(os.path.join("assets", "app.js")) for p in problems))
        self.assertFalse(any("홍길동" in p or "010-1234" in p for p in problems))

    def test_private_values_come_from_contact_keys_only(self):
        sites = [{"site_name": "후포 공공하수처리", "manager": "홍길동", "manager_phone": "010-1234-5678", "nx": 1}]
        self.assertEqual({"홍길동", "010-1234-5678"}, private_values(sites))

    def test_check_latest_reports_kind_not_value(self):
        path = os.path.join(self.docs, "data", "latest.json")
        write(path, '{"sites": [{"name": "홍길동 현장"}]}')
        self.assertEqual(["설정의 비공개 값"], check_latest(path, {"홍길동"}))
        self.assertEqual([], check_latest(os.path.join(self.docs, "none.json"), {"홍길동"}))


class OldScreenTests(unittest.TestCase):
    def test_old_screens_live_under_docs_old(self):
        self.assertEqual(os.path.join(DOCS_DIR, "old", "index.html"), OLD_MAP_PATH)
        self.assertEqual(os.path.join(DOCS_DIR, "old", "sites.html"), OLD_SITES_PATH)

    def test_moved_pages_point_to_new_and_old_screens(self):
        for name, new, old in (("map.html", "./", "old/index.html"), ("sites.html", "./#list", "old/sites.html")):
            with self.subTest(name=name):
                with open(os.path.join(WEB_DIR, name), encoding="utf-8") as f:
                    html = f.read()
                self.assertIn(f'href="{new}"', html)
                self.assertIn(f'href="{old}"', html)


class RealWebTests(unittest.TestCase):
    @unittest.skipUnless(os.path.isdir(WEB_DIR), "web/ 없음")
    def test_real_web_passes_checks(self):
        self.assertEqual([], check_web(WEB_DIR))


if __name__ == "__main__":
    unittest.main()
